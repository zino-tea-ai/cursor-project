# -*- coding: utf-8 -*-
"""
Smart Downloader - Playwright-based screenshot downloader
Features:
- Persistent session (login once, use forever)
- Auto search by product name
- Download with original order preserved
- Save manifest.json for validation
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
SESSION_DIR = os.path.join(BASE_DIR, ".browser_session")
TARGET_WIDTH = 402


class SmartDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def init(self, headless=False):
        """Initialize browser with persistent session"""
        self.playwright = await async_playwright().start()
        
        # Use persistent context to save login state
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print("[INIT] Browser started with persistent session")
        
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[CLOSE] Browser closed")
    
    async def check_login(self) -> bool:
        """Check if logged in to screensdesign"""
        try:
            await self.page.goto("https://screensdesign.com", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check for login indicator (adjust selector based on actual site)
            # Look for common logged-in indicators
            logged_in = await self.page.locator("text=My Account").count() > 0 or \
                       await self.page.locator("text=Log out").count() > 0 or \
                       await self.page.locator("text=Dashboard").count() > 0 or \
                       await self.page.locator("[class*='avatar']").count() > 0
            
            return logged_in
        except Exception as e:
            print(f"[ERROR] Check login failed: {e}")
            return False
    
    async def wait_for_login(self):
        """Wait for user to manually login"""
        print("\n" + "="*60)
        print("[LOGIN] Please login to screensdesign.com in the browser window")
        print("        After login, press Enter here to continue...")
        print("="*60)
        
        await self.page.goto("https://screensdesign.com/login")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Verify login
        if await self.check_login():
            print("[LOGIN] Login successful! Session saved.")
            return True
        else:
            print("[LOGIN] Login verification failed. Please try again.")
            return False
    
    async def search_product(self, product_name: str) -> list:
        """Search for a product and return list of matching results"""
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        
        print(f"[SEARCH] Searching for: {product_name}")
        await self.page.goto(search_url, timeout=30000)
        await self.page.wait_for_load_state("networkidle")
        
        # Find search results (adjust selectors based on actual site structure)
        results = []
        
        # Try different selectors
        selectors = [
            ".app-card a",
            ".search-result a",
            "article a",
            ".grid-item a"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements[:10]:  # Limit to first 10
                    href = await elem.get_attribute("href")
                    text = await elem.inner_text()
                    if href and "apps/" in href:
                        results.append({
                            "name": text.strip()[:50],
                            "url": href if href.startswith("http") else f"https://screensdesign.com{href}"
                        })
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_results.append(r)
        
        print(f"[SEARCH] Found {len(unique_results)} results")
        return unique_results
    
    async def download_product(self, product_name: str, url: str = None) -> dict:
        """
        Download all screenshots from a product page
        
        Args:
            product_name: Name for the project folder
            url: Direct URL (optional, will search if not provided)
        
        Returns:
            {
                "success": bool,
                "count": int,
                "project_path": str,
                "manifest": dict
            }
        """
        project_name = f"{product_name.replace(' ', '_')}_Analysis"
        project_path = os.path.join(PROJECTS_DIR, project_name)
        downloads_path = os.path.join(project_path, "Downloads")
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # If no URL provided, search for it
        if not url:
            results = await self.search_product(product_name)
            if not results:
                print(f"[ERROR] No results found for: {product_name}")
                return {"success": False, "count": 0, "error": "Not found"}
            
            # Use first result
            url = results[0]["url"]
            print(f"[SELECT] Using: {results[0]['name']} - {url}")
        
        print(f"\n[DOWNLOAD] Starting download: {product_name}")
        print(f"           URL: {url}")
        
        try:
            # Navigate to product page
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            
            # Scroll to load all images
            print("[DOWNLOAD] Scrolling to load all images...")
            await self._scroll_to_load_all()
            
            # Collect image URLs
            print("[DOWNLOAD] Collecting image URLs...")
            image_urls = await self._collect_image_urls()
            
            if not image_urls:
                print("[ERROR] No images found!")
                return {"success": False, "count": 0, "error": "No images"}
            
            print(f"[DOWNLOAD] Found {len(image_urls)} images")
            
            # Download images
            manifest = {
                "source_url": url,
                "product_name": product_name,
                "download_time": datetime.now().isoformat(),
                "screens": []
            }
            
            success_count = 0
            
            for i, img_url in enumerate(image_urls, 1):
                try:
                    # Download image
                    response = requests.get(img_url, timeout=30)
                    img = Image.open(BytesIO(response.content))
                    
                    # Skip small images
                    if img.width < 200 or img.height < 200:
                        continue
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                    
                    # Save
                    filename = f"Screen_{success_count+1:03d}.png"
                    filepath = os.path.join(downloads_path, filename)
                    img_resized.save(filepath, 'PNG', optimize=True)
                    
                    # Record in manifest
                    manifest["screens"].append({
                        "index": success_count + 1,
                        "original_url": img_url,
                        "local_file": filename
                    })
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        print(f"           Downloaded: {success_count}")
                        
                except Exception as e:
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_path, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[DONE] Downloaded {success_count} screenshots")
            print(f"       Saved to: {project_path}")
            
            return {
                "success": True,
                "count": success_count,
                "project_path": project_path,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}
    
    async def _scroll_to_load_all(self):
        """Scroll page to load all lazy-loaded images"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < 30:  # Max 30 scrolls
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def _collect_image_urls(self) -> list:
        """Collect all screenshot URLs from the page"""
        image_urls = []
        
        # Multiple selectors for different site structures
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']",
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                
                for elem in elements:
                    src = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # Skip non-screenshot images
                    skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button', 'ad']
                    if any(kw in src.lower() for kw in skip_keywords):
                        continue
                    
                    if src not in image_urls:
                        image_urls.append(src)
                        
            except:
                continue
        
        return image_urls


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Screenshot Downloader")
    parser.add_argument("product", nargs="?", help="Product name to download")
    parser.add_argument("--url", help="Direct URL to product page")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    downloader = SmartDownloader()
    
    try:
        # Start browser
        await downloader.init(headless=args.headless)
        
        # Check/handle login
        if args.login or not await downloader.check_login():
            success = await downloader.wait_for_login()
            if not success:
                print("[ERROR] Login failed")
                return
        else:
            print("[OK] Already logged in")
        
        # Download if product specified
        if args.product:
            result = await downloader.download_product(args.product, args.url)
            
            if result["success"]:
                print(f"\n[SUCCESS] Downloaded {result['count']} screenshots!")
                print(f"          Project: {result['project_path']}")
                
                # Auto-run QA check
                print("\n[QA] Running quality check...")
                try:
                    from qa.triggers import trigger_download_check
                    project_name = os.path.basename(result['project_path'])
                    qa_result = await trigger_download_check(project_name, result['project_path'])
                    
                    if qa_result and not qa_result.get('passed', True):
                        print(f"[QA] Found {len(qa_result.get('issues', []))} issues - see qa_report.json")
                except Exception as e:
                    print(f"[QA] Check skipped: {e}")
                
            else:
                print(f"\n[FAILED] {result.get('error', 'Unknown error')}")
        else:
            print("\n[READY] Browser ready. Use --product to download.")
            print("        Example: python smart_downloader.py Calm")
            print("\n        Press Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())


Smart Downloader - Playwright-based screenshot downloader
Features:
- Persistent session (login once, use forever)
- Auto search by product name
- Download with original order preserved
- Save manifest.json for validation
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
SESSION_DIR = os.path.join(BASE_DIR, ".browser_session")
TARGET_WIDTH = 402


class SmartDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def init(self, headless=False):
        """Initialize browser with persistent session"""
        self.playwright = await async_playwright().start()
        
        # Use persistent context to save login state
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print("[INIT] Browser started with persistent session")
        
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[CLOSE] Browser closed")
    
    async def check_login(self) -> bool:
        """Check if logged in to screensdesign"""
        try:
            await self.page.goto("https://screensdesign.com", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check for login indicator (adjust selector based on actual site)
            # Look for common logged-in indicators
            logged_in = await self.page.locator("text=My Account").count() > 0 or \
                       await self.page.locator("text=Log out").count() > 0 or \
                       await self.page.locator("text=Dashboard").count() > 0 or \
                       await self.page.locator("[class*='avatar']").count() > 0
            
            return logged_in
        except Exception as e:
            print(f"[ERROR] Check login failed: {e}")
            return False
    
    async def wait_for_login(self):
        """Wait for user to manually login"""
        print("\n" + "="*60)
        print("[LOGIN] Please login to screensdesign.com in the browser window")
        print("        After login, press Enter here to continue...")
        print("="*60)
        
        await self.page.goto("https://screensdesign.com/login")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Verify login
        if await self.check_login():
            print("[LOGIN] Login successful! Session saved.")
            return True
        else:
            print("[LOGIN] Login verification failed. Please try again.")
            return False
    
    async def search_product(self, product_name: str) -> list:
        """Search for a product and return list of matching results"""
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        
        print(f"[SEARCH] Searching for: {product_name}")
        await self.page.goto(search_url, timeout=30000)
        await self.page.wait_for_load_state("networkidle")
        
        # Find search results (adjust selectors based on actual site structure)
        results = []
        
        # Try different selectors
        selectors = [
            ".app-card a",
            ".search-result a",
            "article a",
            ".grid-item a"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements[:10]:  # Limit to first 10
                    href = await elem.get_attribute("href")
                    text = await elem.inner_text()
                    if href and "apps/" in href:
                        results.append({
                            "name": text.strip()[:50],
                            "url": href if href.startswith("http") else f"https://screensdesign.com{href}"
                        })
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_results.append(r)
        
        print(f"[SEARCH] Found {len(unique_results)} results")
        return unique_results
    
    async def download_product(self, product_name: str, url: str = None) -> dict:
        """
        Download all screenshots from a product page
        
        Args:
            product_name: Name for the project folder
            url: Direct URL (optional, will search if not provided)
        
        Returns:
            {
                "success": bool,
                "count": int,
                "project_path": str,
                "manifest": dict
            }
        """
        project_name = f"{product_name.replace(' ', '_')}_Analysis"
        project_path = os.path.join(PROJECTS_DIR, project_name)
        downloads_path = os.path.join(project_path, "Downloads")
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # If no URL provided, search for it
        if not url:
            results = await self.search_product(product_name)
            if not results:
                print(f"[ERROR] No results found for: {product_name}")
                return {"success": False, "count": 0, "error": "Not found"}
            
            # Use first result
            url = results[0]["url"]
            print(f"[SELECT] Using: {results[0]['name']} - {url}")
        
        print(f"\n[DOWNLOAD] Starting download: {product_name}")
        print(f"           URL: {url}")
        
        try:
            # Navigate to product page
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            
            # Scroll to load all images
            print("[DOWNLOAD] Scrolling to load all images...")
            await self._scroll_to_load_all()
            
            # Collect image URLs
            print("[DOWNLOAD] Collecting image URLs...")
            image_urls = await self._collect_image_urls()
            
            if not image_urls:
                print("[ERROR] No images found!")
                return {"success": False, "count": 0, "error": "No images"}
            
            print(f"[DOWNLOAD] Found {len(image_urls)} images")
            
            # Download images
            manifest = {
                "source_url": url,
                "product_name": product_name,
                "download_time": datetime.now().isoformat(),
                "screens": []
            }
            
            success_count = 0
            
            for i, img_url in enumerate(image_urls, 1):
                try:
                    # Download image
                    response = requests.get(img_url, timeout=30)
                    img = Image.open(BytesIO(response.content))
                    
                    # Skip small images
                    if img.width < 200 or img.height < 200:
                        continue
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                    
                    # Save
                    filename = f"Screen_{success_count+1:03d}.png"
                    filepath = os.path.join(downloads_path, filename)
                    img_resized.save(filepath, 'PNG', optimize=True)
                    
                    # Record in manifest
                    manifest["screens"].append({
                        "index": success_count + 1,
                        "original_url": img_url,
                        "local_file": filename
                    })
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        print(f"           Downloaded: {success_count}")
                        
                except Exception as e:
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_path, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[DONE] Downloaded {success_count} screenshots")
            print(f"       Saved to: {project_path}")
            
            return {
                "success": True,
                "count": success_count,
                "project_path": project_path,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}
    
    async def _scroll_to_load_all(self):
        """Scroll page to load all lazy-loaded images"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < 30:  # Max 30 scrolls
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def _collect_image_urls(self) -> list:
        """Collect all screenshot URLs from the page"""
        image_urls = []
        
        # Multiple selectors for different site structures
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']",
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                
                for elem in elements:
                    src = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # Skip non-screenshot images
                    skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button', 'ad']
                    if any(kw in src.lower() for kw in skip_keywords):
                        continue
                    
                    if src not in image_urls:
                        image_urls.append(src)
                        
            except:
                continue
        
        return image_urls


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Screenshot Downloader")
    parser.add_argument("product", nargs="?", help="Product name to download")
    parser.add_argument("--url", help="Direct URL to product page")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    downloader = SmartDownloader()
    
    try:
        # Start browser
        await downloader.init(headless=args.headless)
        
        # Check/handle login
        if args.login or not await downloader.check_login():
            success = await downloader.wait_for_login()
            if not success:
                print("[ERROR] Login failed")
                return
        else:
            print("[OK] Already logged in")
        
        # Download if product specified
        if args.product:
            result = await downloader.download_product(args.product, args.url)
            
            if result["success"]:
                print(f"\n[SUCCESS] Downloaded {result['count']} screenshots!")
                print(f"          Project: {result['project_path']}")
                
                # Auto-run QA check
                print("\n[QA] Running quality check...")
                try:
                    from qa.triggers import trigger_download_check
                    project_name = os.path.basename(result['project_path'])
                    qa_result = await trigger_download_check(project_name, result['project_path'])
                    
                    if qa_result and not qa_result.get('passed', True):
                        print(f"[QA] Found {len(qa_result.get('issues', []))} issues - see qa_report.json")
                except Exception as e:
                    print(f"[QA] Check skipped: {e}")
                
            else:
                print(f"\n[FAILED] {result.get('error', 'Unknown error')}")
        else:
            print("\n[READY] Browser ready. Use --product to download.")
            print("        Example: python smart_downloader.py Calm")
            print("\n        Press Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())


Smart Downloader - Playwright-based screenshot downloader
Features:
- Persistent session (login once, use forever)
- Auto search by product name
- Download with original order preserved
- Save manifest.json for validation
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
SESSION_DIR = os.path.join(BASE_DIR, ".browser_session")
TARGET_WIDTH = 402


class SmartDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def init(self, headless=False):
        """Initialize browser with persistent session"""
        self.playwright = await async_playwright().start()
        
        # Use persistent context to save login state
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print("[INIT] Browser started with persistent session")
        
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[CLOSE] Browser closed")
    
    async def check_login(self) -> bool:
        """Check if logged in to screensdesign"""
        try:
            await self.page.goto("https://screensdesign.com", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check for login indicator (adjust selector based on actual site)
            # Look for common logged-in indicators
            logged_in = await self.page.locator("text=My Account").count() > 0 or \
                       await self.page.locator("text=Log out").count() > 0 or \
                       await self.page.locator("text=Dashboard").count() > 0 or \
                       await self.page.locator("[class*='avatar']").count() > 0
            
            return logged_in
        except Exception as e:
            print(f"[ERROR] Check login failed: {e}")
            return False
    
    async def wait_for_login(self):
        """Wait for user to manually login"""
        print("\n" + "="*60)
        print("[LOGIN] Please login to screensdesign.com in the browser window")
        print("        After login, press Enter here to continue...")
        print("="*60)
        
        await self.page.goto("https://screensdesign.com/login")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Verify login
        if await self.check_login():
            print("[LOGIN] Login successful! Session saved.")
            return True
        else:
            print("[LOGIN] Login verification failed. Please try again.")
            return False
    
    async def search_product(self, product_name: str) -> list:
        """Search for a product and return list of matching results"""
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        
        print(f"[SEARCH] Searching for: {product_name}")
        await self.page.goto(search_url, timeout=30000)
        await self.page.wait_for_load_state("networkidle")
        
        # Find search results (adjust selectors based on actual site structure)
        results = []
        
        # Try different selectors
        selectors = [
            ".app-card a",
            ".search-result a",
            "article a",
            ".grid-item a"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements[:10]:  # Limit to first 10
                    href = await elem.get_attribute("href")
                    text = await elem.inner_text()
                    if href and "apps/" in href:
                        results.append({
                            "name": text.strip()[:50],
                            "url": href if href.startswith("http") else f"https://screensdesign.com{href}"
                        })
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_results.append(r)
        
        print(f"[SEARCH] Found {len(unique_results)} results")
        return unique_results
    
    async def download_product(self, product_name: str, url: str = None) -> dict:
        """
        Download all screenshots from a product page
        
        Args:
            product_name: Name for the project folder
            url: Direct URL (optional, will search if not provided)
        
        Returns:
            {
                "success": bool,
                "count": int,
                "project_path": str,
                "manifest": dict
            }
        """
        project_name = f"{product_name.replace(' ', '_')}_Analysis"
        project_path = os.path.join(PROJECTS_DIR, project_name)
        downloads_path = os.path.join(project_path, "Downloads")
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # If no URL provided, search for it
        if not url:
            results = await self.search_product(product_name)
            if not results:
                print(f"[ERROR] No results found for: {product_name}")
                return {"success": False, "count": 0, "error": "Not found"}
            
            # Use first result
            url = results[0]["url"]
            print(f"[SELECT] Using: {results[0]['name']} - {url}")
        
        print(f"\n[DOWNLOAD] Starting download: {product_name}")
        print(f"           URL: {url}")
        
        try:
            # Navigate to product page
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            
            # Scroll to load all images
            print("[DOWNLOAD] Scrolling to load all images...")
            await self._scroll_to_load_all()
            
            # Collect image URLs
            print("[DOWNLOAD] Collecting image URLs...")
            image_urls = await self._collect_image_urls()
            
            if not image_urls:
                print("[ERROR] No images found!")
                return {"success": False, "count": 0, "error": "No images"}
            
            print(f"[DOWNLOAD] Found {len(image_urls)} images")
            
            # Download images
            manifest = {
                "source_url": url,
                "product_name": product_name,
                "download_time": datetime.now().isoformat(),
                "screens": []
            }
            
            success_count = 0
            
            for i, img_url in enumerate(image_urls, 1):
                try:
                    # Download image
                    response = requests.get(img_url, timeout=30)
                    img = Image.open(BytesIO(response.content))
                    
                    # Skip small images
                    if img.width < 200 or img.height < 200:
                        continue
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                    
                    # Save
                    filename = f"Screen_{success_count+1:03d}.png"
                    filepath = os.path.join(downloads_path, filename)
                    img_resized.save(filepath, 'PNG', optimize=True)
                    
                    # Record in manifest
                    manifest["screens"].append({
                        "index": success_count + 1,
                        "original_url": img_url,
                        "local_file": filename
                    })
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        print(f"           Downloaded: {success_count}")
                        
                except Exception as e:
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_path, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[DONE] Downloaded {success_count} screenshots")
            print(f"       Saved to: {project_path}")
            
            return {
                "success": True,
                "count": success_count,
                "project_path": project_path,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}
    
    async def _scroll_to_load_all(self):
        """Scroll page to load all lazy-loaded images"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < 30:  # Max 30 scrolls
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def _collect_image_urls(self) -> list:
        """Collect all screenshot URLs from the page"""
        image_urls = []
        
        # Multiple selectors for different site structures
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']",
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                
                for elem in elements:
                    src = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # Skip non-screenshot images
                    skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button', 'ad']
                    if any(kw in src.lower() for kw in skip_keywords):
                        continue
                    
                    if src not in image_urls:
                        image_urls.append(src)
                        
            except:
                continue
        
        return image_urls


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Screenshot Downloader")
    parser.add_argument("product", nargs="?", help="Product name to download")
    parser.add_argument("--url", help="Direct URL to product page")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    downloader = SmartDownloader()
    
    try:
        # Start browser
        await downloader.init(headless=args.headless)
        
        # Check/handle login
        if args.login or not await downloader.check_login():
            success = await downloader.wait_for_login()
            if not success:
                print("[ERROR] Login failed")
                return
        else:
            print("[OK] Already logged in")
        
        # Download if product specified
        if args.product:
            result = await downloader.download_product(args.product, args.url)
            
            if result["success"]:
                print(f"\n[SUCCESS] Downloaded {result['count']} screenshots!")
                print(f"          Project: {result['project_path']}")
                
                # Auto-run QA check
                print("\n[QA] Running quality check...")
                try:
                    from qa.triggers import trigger_download_check
                    project_name = os.path.basename(result['project_path'])
                    qa_result = await trigger_download_check(project_name, result['project_path'])
                    
                    if qa_result and not qa_result.get('passed', True):
                        print(f"[QA] Found {len(qa_result.get('issues', []))} issues - see qa_report.json")
                except Exception as e:
                    print(f"[QA] Check skipped: {e}")
                
            else:
                print(f"\n[FAILED] {result.get('error', 'Unknown error')}")
        else:
            print("\n[READY] Browser ready. Use --product to download.")
            print("        Example: python smart_downloader.py Calm")
            print("\n        Press Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())


Smart Downloader - Playwright-based screenshot downloader
Features:
- Persistent session (login once, use forever)
- Auto search by product name
- Download with original order preserved
- Save manifest.json for validation
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
SESSION_DIR = os.path.join(BASE_DIR, ".browser_session")
TARGET_WIDTH = 402


class SmartDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def init(self, headless=False):
        """Initialize browser with persistent session"""
        self.playwright = await async_playwright().start()
        
        # Use persistent context to save login state
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print("[INIT] Browser started with persistent session")
        
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[CLOSE] Browser closed")
    
    async def check_login(self) -> bool:
        """Check if logged in to screensdesign"""
        try:
            await self.page.goto("https://screensdesign.com", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check for login indicator (adjust selector based on actual site)
            # Look for common logged-in indicators
            logged_in = await self.page.locator("text=My Account").count() > 0 or \
                       await self.page.locator("text=Log out").count() > 0 or \
                       await self.page.locator("text=Dashboard").count() > 0 or \
                       await self.page.locator("[class*='avatar']").count() > 0
            
            return logged_in
        except Exception as e:
            print(f"[ERROR] Check login failed: {e}")
            return False
    
    async def wait_for_login(self):
        """Wait for user to manually login"""
        print("\n" + "="*60)
        print("[LOGIN] Please login to screensdesign.com in the browser window")
        print("        After login, press Enter here to continue...")
        print("="*60)
        
        await self.page.goto("https://screensdesign.com/login")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Verify login
        if await self.check_login():
            print("[LOGIN] Login successful! Session saved.")
            return True
        else:
            print("[LOGIN] Login verification failed. Please try again.")
            return False
    
    async def search_product(self, product_name: str) -> list:
        """Search for a product and return list of matching results"""
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        
        print(f"[SEARCH] Searching for: {product_name}")
        await self.page.goto(search_url, timeout=30000)
        await self.page.wait_for_load_state("networkidle")
        
        # Find search results (adjust selectors based on actual site structure)
        results = []
        
        # Try different selectors
        selectors = [
            ".app-card a",
            ".search-result a",
            "article a",
            ".grid-item a"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements[:10]:  # Limit to first 10
                    href = await elem.get_attribute("href")
                    text = await elem.inner_text()
                    if href and "apps/" in href:
                        results.append({
                            "name": text.strip()[:50],
                            "url": href if href.startswith("http") else f"https://screensdesign.com{href}"
                        })
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_results.append(r)
        
        print(f"[SEARCH] Found {len(unique_results)} results")
        return unique_results
    
    async def download_product(self, product_name: str, url: str = None) -> dict:
        """
        Download all screenshots from a product page
        
        Args:
            product_name: Name for the project folder
            url: Direct URL (optional, will search if not provided)
        
        Returns:
            {
                "success": bool,
                "count": int,
                "project_path": str,
                "manifest": dict
            }
        """
        project_name = f"{product_name.replace(' ', '_')}_Analysis"
        project_path = os.path.join(PROJECTS_DIR, project_name)
        downloads_path = os.path.join(project_path, "Downloads")
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # If no URL provided, search for it
        if not url:
            results = await self.search_product(product_name)
            if not results:
                print(f"[ERROR] No results found for: {product_name}")
                return {"success": False, "count": 0, "error": "Not found"}
            
            # Use first result
            url = results[0]["url"]
            print(f"[SELECT] Using: {results[0]['name']} - {url}")
        
        print(f"\n[DOWNLOAD] Starting download: {product_name}")
        print(f"           URL: {url}")
        
        try:
            # Navigate to product page
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            
            # Scroll to load all images
            print("[DOWNLOAD] Scrolling to load all images...")
            await self._scroll_to_load_all()
            
            # Collect image URLs
            print("[DOWNLOAD] Collecting image URLs...")
            image_urls = await self._collect_image_urls()
            
            if not image_urls:
                print("[ERROR] No images found!")
                return {"success": False, "count": 0, "error": "No images"}
            
            print(f"[DOWNLOAD] Found {len(image_urls)} images")
            
            # Download images
            manifest = {
                "source_url": url,
                "product_name": product_name,
                "download_time": datetime.now().isoformat(),
                "screens": []
            }
            
            success_count = 0
            
            for i, img_url in enumerate(image_urls, 1):
                try:
                    # Download image
                    response = requests.get(img_url, timeout=30)
                    img = Image.open(BytesIO(response.content))
                    
                    # Skip small images
                    if img.width < 200 or img.height < 200:
                        continue
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                    
                    # Save
                    filename = f"Screen_{success_count+1:03d}.png"
                    filepath = os.path.join(downloads_path, filename)
                    img_resized.save(filepath, 'PNG', optimize=True)
                    
                    # Record in manifest
                    manifest["screens"].append({
                        "index": success_count + 1,
                        "original_url": img_url,
                        "local_file": filename
                    })
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        print(f"           Downloaded: {success_count}")
                        
                except Exception as e:
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_path, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[DONE] Downloaded {success_count} screenshots")
            print(f"       Saved to: {project_path}")
            
            return {
                "success": True,
                "count": success_count,
                "project_path": project_path,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}
    
    async def _scroll_to_load_all(self):
        """Scroll page to load all lazy-loaded images"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < 30:  # Max 30 scrolls
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def _collect_image_urls(self) -> list:
        """Collect all screenshot URLs from the page"""
        image_urls = []
        
        # Multiple selectors for different site structures
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']",
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                
                for elem in elements:
                    src = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # Skip non-screenshot images
                    skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button', 'ad']
                    if any(kw in src.lower() for kw in skip_keywords):
                        continue
                    
                    if src not in image_urls:
                        image_urls.append(src)
                        
            except:
                continue
        
        return image_urls


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Screenshot Downloader")
    parser.add_argument("product", nargs="?", help="Product name to download")
    parser.add_argument("--url", help="Direct URL to product page")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    downloader = SmartDownloader()
    
    try:
        # Start browser
        await downloader.init(headless=args.headless)
        
        # Check/handle login
        if args.login or not await downloader.check_login():
            success = await downloader.wait_for_login()
            if not success:
                print("[ERROR] Login failed")
                return
        else:
            print("[OK] Already logged in")
        
        # Download if product specified
        if args.product:
            result = await downloader.download_product(args.product, args.url)
            
            if result["success"]:
                print(f"\n[SUCCESS] Downloaded {result['count']} screenshots!")
                print(f"          Project: {result['project_path']}")
                
                # Auto-run QA check
                print("\n[QA] Running quality check...")
                try:
                    from qa.triggers import trigger_download_check
                    project_name = os.path.basename(result['project_path'])
                    qa_result = await trigger_download_check(project_name, result['project_path'])
                    
                    if qa_result and not qa_result.get('passed', True):
                        print(f"[QA] Found {len(qa_result.get('issues', []))} issues - see qa_report.json")
                except Exception as e:
                    print(f"[QA] Check skipped: {e}")
                
            else:
                print(f"\n[FAILED] {result.get('error', 'Unknown error')}")
        else:
            print("\n[READY] Browser ready. Use --product to download.")
            print("        Example: python smart_downloader.py Calm")
            print("\n        Press Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())


Smart Downloader - Playwright-based screenshot downloader
Features:
- Persistent session (login once, use forever)
- Auto search by product name
- Download with original order preserved
- Save manifest.json for validation
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
SESSION_DIR = os.path.join(BASE_DIR, ".browser_session")
TARGET_WIDTH = 402


class SmartDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def init(self, headless=False):
        """Initialize browser with persistent session"""
        self.playwright = await async_playwright().start()
        
        # Use persistent context to save login state
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print("[INIT] Browser started with persistent session")
        
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[CLOSE] Browser closed")
    
    async def check_login(self) -> bool:
        """Check if logged in to screensdesign"""
        try:
            await self.page.goto("https://screensdesign.com", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check for login indicator (adjust selector based on actual site)
            # Look for common logged-in indicators
            logged_in = await self.page.locator("text=My Account").count() > 0 or \
                       await self.page.locator("text=Log out").count() > 0 or \
                       await self.page.locator("text=Dashboard").count() > 0 or \
                       await self.page.locator("[class*='avatar']").count() > 0
            
            return logged_in
        except Exception as e:
            print(f"[ERROR] Check login failed: {e}")
            return False
    
    async def wait_for_login(self):
        """Wait for user to manually login"""
        print("\n" + "="*60)
        print("[LOGIN] Please login to screensdesign.com in the browser window")
        print("        After login, press Enter here to continue...")
        print("="*60)
        
        await self.page.goto("https://screensdesign.com/login")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Verify login
        if await self.check_login():
            print("[LOGIN] Login successful! Session saved.")
            return True
        else:
            print("[LOGIN] Login verification failed. Please try again.")
            return False
    
    async def search_product(self, product_name: str) -> list:
        """Search for a product and return list of matching results"""
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        
        print(f"[SEARCH] Searching for: {product_name}")
        await self.page.goto(search_url, timeout=30000)
        await self.page.wait_for_load_state("networkidle")
        
        # Find search results (adjust selectors based on actual site structure)
        results = []
        
        # Try different selectors
        selectors = [
            ".app-card a",
            ".search-result a",
            "article a",
            ".grid-item a"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements[:10]:  # Limit to first 10
                    href = await elem.get_attribute("href")
                    text = await elem.inner_text()
                    if href and "apps/" in href:
                        results.append({
                            "name": text.strip()[:50],
                            "url": href if href.startswith("http") else f"https://screensdesign.com{href}"
                        })
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_results.append(r)
        
        print(f"[SEARCH] Found {len(unique_results)} results")
        return unique_results
    
    async def download_product(self, product_name: str, url: str = None) -> dict:
        """
        Download all screenshots from a product page
        
        Args:
            product_name: Name for the project folder
            url: Direct URL (optional, will search if not provided)
        
        Returns:
            {
                "success": bool,
                "count": int,
                "project_path": str,
                "manifest": dict
            }
        """
        project_name = f"{product_name.replace(' ', '_')}_Analysis"
        project_path = os.path.join(PROJECTS_DIR, project_name)
        downloads_path = os.path.join(project_path, "Downloads")
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # If no URL provided, search for it
        if not url:
            results = await self.search_product(product_name)
            if not results:
                print(f"[ERROR] No results found for: {product_name}")
                return {"success": False, "count": 0, "error": "Not found"}
            
            # Use first result
            url = results[0]["url"]
            print(f"[SELECT] Using: {results[0]['name']} - {url}")
        
        print(f"\n[DOWNLOAD] Starting download: {product_name}")
        print(f"           URL: {url}")
        
        try:
            # Navigate to product page
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            
            # Scroll to load all images
            print("[DOWNLOAD] Scrolling to load all images...")
            await self._scroll_to_load_all()
            
            # Collect image URLs
            print("[DOWNLOAD] Collecting image URLs...")
            image_urls = await self._collect_image_urls()
            
            if not image_urls:
                print("[ERROR] No images found!")
                return {"success": False, "count": 0, "error": "No images"}
            
            print(f"[DOWNLOAD] Found {len(image_urls)} images")
            
            # Download images
            manifest = {
                "source_url": url,
                "product_name": product_name,
                "download_time": datetime.now().isoformat(),
                "screens": []
            }
            
            success_count = 0
            
            for i, img_url in enumerate(image_urls, 1):
                try:
                    # Download image
                    response = requests.get(img_url, timeout=30)
                    img = Image.open(BytesIO(response.content))
                    
                    # Skip small images
                    if img.width < 200 or img.height < 200:
                        continue
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                    
                    # Save
                    filename = f"Screen_{success_count+1:03d}.png"
                    filepath = os.path.join(downloads_path, filename)
                    img_resized.save(filepath, 'PNG', optimize=True)
                    
                    # Record in manifest
                    manifest["screens"].append({
                        "index": success_count + 1,
                        "original_url": img_url,
                        "local_file": filename
                    })
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        print(f"           Downloaded: {success_count}")
                        
                except Exception as e:
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_path, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[DONE] Downloaded {success_count} screenshots")
            print(f"       Saved to: {project_path}")
            
            return {
                "success": True,
                "count": success_count,
                "project_path": project_path,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}
    
    async def _scroll_to_load_all(self):
        """Scroll page to load all lazy-loaded images"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < 30:  # Max 30 scrolls
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def _collect_image_urls(self) -> list:
        """Collect all screenshot URLs from the page"""
        image_urls = []
        
        # Multiple selectors for different site structures
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']",
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                
                for elem in elements:
                    src = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # Skip non-screenshot images
                    skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button', 'ad']
                    if any(kw in src.lower() for kw in skip_keywords):
                        continue
                    
                    if src not in image_urls:
                        image_urls.append(src)
                        
            except:
                continue
        
        return image_urls


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Screenshot Downloader")
    parser.add_argument("product", nargs="?", help="Product name to download")
    parser.add_argument("--url", help="Direct URL to product page")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    downloader = SmartDownloader()
    
    try:
        # Start browser
        await downloader.init(headless=args.headless)
        
        # Check/handle login
        if args.login or not await downloader.check_login():
            success = await downloader.wait_for_login()
            if not success:
                print("[ERROR] Login failed")
                return
        else:
            print("[OK] Already logged in")
        
        # Download if product specified
        if args.product:
            result = await downloader.download_product(args.product, args.url)
            
            if result["success"]:
                print(f"\n[SUCCESS] Downloaded {result['count']} screenshots!")
                print(f"          Project: {result['project_path']}")
                
                # Auto-run QA check
                print("\n[QA] Running quality check...")
                try:
                    from qa.triggers import trigger_download_check
                    project_name = os.path.basename(result['project_path'])
                    qa_result = await trigger_download_check(project_name, result['project_path'])
                    
                    if qa_result and not qa_result.get('passed', True):
                        print(f"[QA] Found {len(qa_result.get('issues', []))} issues - see qa_report.json")
                except Exception as e:
                    print(f"[QA] Check skipped: {e}")
                
            else:
                print(f"\n[FAILED] {result.get('error', 'Unknown error')}")
        else:
            print("\n[READY] Browser ready. Use --product to download.")
            print("        Example: python smart_downloader.py Calm")
            print("\n        Press Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())


Smart Downloader - Playwright-based screenshot downloader
Features:
- Persistent session (login once, use forever)
- Auto search by product name
- Download with original order preserved
- Save manifest.json for validation
"""

import os
import sys
import json
import time
import asyncio
import requests
from datetime import datetime
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
SESSION_DIR = os.path.join(BASE_DIR, ".browser_session")
TARGET_WIDTH = 402


class SmartDownloader:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
    async def init(self, headless=False):
        """Initialize browser with persistent session"""
        self.playwright = await async_playwright().start()
        
        # Use persistent context to save login state
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=headless,
            viewport={"width": 1280, "height": 900}
        )
        
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        print("[INIT] Browser started with persistent session")
        
    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[CLOSE] Browser closed")
    
    async def check_login(self) -> bool:
        """Check if logged in to screensdesign"""
        try:
            await self.page.goto("https://screensdesign.com", timeout=30000)
            await self.page.wait_for_load_state("networkidle")
            
            # Check for login indicator (adjust selector based on actual site)
            # Look for common logged-in indicators
            logged_in = await self.page.locator("text=My Account").count() > 0 or \
                       await self.page.locator("text=Log out").count() > 0 or \
                       await self.page.locator("text=Dashboard").count() > 0 or \
                       await self.page.locator("[class*='avatar']").count() > 0
            
            return logged_in
        except Exception as e:
            print(f"[ERROR] Check login failed: {e}")
            return False
    
    async def wait_for_login(self):
        """Wait for user to manually login"""
        print("\n" + "="*60)
        print("[LOGIN] Please login to screensdesign.com in the browser window")
        print("        After login, press Enter here to continue...")
        print("="*60)
        
        await self.page.goto("https://screensdesign.com/login")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Verify login
        if await self.check_login():
            print("[LOGIN] Login successful! Session saved.")
            return True
        else:
            print("[LOGIN] Login verification failed. Please try again.")
            return False
    
    async def search_product(self, product_name: str) -> list:
        """Search for a product and return list of matching results"""
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        
        print(f"[SEARCH] Searching for: {product_name}")
        await self.page.goto(search_url, timeout=30000)
        await self.page.wait_for_load_state("networkidle")
        
        # Find search results (adjust selectors based on actual site structure)
        results = []
        
        # Try different selectors
        selectors = [
            ".app-card a",
            ".search-result a",
            "article a",
            ".grid-item a"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                for elem in elements[:10]:  # Limit to first 10
                    href = await elem.get_attribute("href")
                    text = await elem.inner_text()
                    if href and "apps/" in href:
                        results.append({
                            "name": text.strip()[:50],
                            "url": href if href.startswith("http") else f"https://screensdesign.com{href}"
                        })
            except:
                continue
        
        # Remove duplicates
        seen = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen:
                seen.add(r["url"])
                unique_results.append(r)
        
        print(f"[SEARCH] Found {len(unique_results)} results")
        return unique_results
    
    async def download_product(self, product_name: str, url: str = None) -> dict:
        """
        Download all screenshots from a product page
        
        Args:
            product_name: Name for the project folder
            url: Direct URL (optional, will search if not provided)
        
        Returns:
            {
                "success": bool,
                "count": int,
                "project_path": str,
                "manifest": dict
            }
        """
        project_name = f"{product_name.replace(' ', '_')}_Analysis"
        project_path = os.path.join(PROJECTS_DIR, project_name)
        downloads_path = os.path.join(project_path, "Downloads")
        
        os.makedirs(downloads_path, exist_ok=True)
        
        # If no URL provided, search for it
        if not url:
            results = await self.search_product(product_name)
            if not results:
                print(f"[ERROR] No results found for: {product_name}")
                return {"success": False, "count": 0, "error": "Not found"}
            
            # Use first result
            url = results[0]["url"]
            print(f"[SELECT] Using: {results[0]['name']} - {url}")
        
        print(f"\n[DOWNLOAD] Starting download: {product_name}")
        print(f"           URL: {url}")
        
        try:
            # Navigate to product page
            await self.page.goto(url, timeout=60000)
            await self.page.wait_for_load_state("networkidle")
            
            # Scroll to load all images
            print("[DOWNLOAD] Scrolling to load all images...")
            await self._scroll_to_load_all()
            
            # Collect image URLs
            print("[DOWNLOAD] Collecting image URLs...")
            image_urls = await self._collect_image_urls()
            
            if not image_urls:
                print("[ERROR] No images found!")
                return {"success": False, "count": 0, "error": "No images"}
            
            print(f"[DOWNLOAD] Found {len(image_urls)} images")
            
            # Download images
            manifest = {
                "source_url": url,
                "product_name": product_name,
                "download_time": datetime.now().isoformat(),
                "screens": []
            }
            
            success_count = 0
            
            for i, img_url in enumerate(image_urls, 1):
                try:
                    # Download image
                    response = requests.get(img_url, timeout=30)
                    img = Image.open(BytesIO(response.content))
                    
                    # Skip small images
                    if img.width < 200 or img.height < 200:
                        continue
                    
                    # Convert to RGB
                    if img.mode in ('RGBA', 'P', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode in ('RGBA', 'LA'):
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Resize
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                    
                    # Save
                    filename = f"Screen_{success_count+1:03d}.png"
                    filepath = os.path.join(downloads_path, filename)
                    img_resized.save(filepath, 'PNG', optimize=True)
                    
                    # Record in manifest
                    manifest["screens"].append({
                        "index": success_count + 1,
                        "original_url": img_url,
                        "local_file": filename
                    })
                    
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        print(f"           Downloaded: {success_count}")
                        
                except Exception as e:
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_path, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            print(f"\n[DONE] Downloaded {success_count} screenshots")
            print(f"       Saved to: {project_path}")
            
            return {
                "success": True,
                "count": success_count,
                "project_path": project_path,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"[ERROR] Download failed: {e}")
            return {"success": False, "count": 0, "error": str(e)}
    
    async def _scroll_to_load_all(self):
        """Scroll page to load all lazy-loaded images"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_count = 0
        
        while scroll_count < 30:  # Max 30 scrolls
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            scroll_count += 1
            
            if new_height == last_height:
                break
            last_height = new_height
        
        # Scroll back to top
        await self.page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
    
    async def _collect_image_urls(self) -> list:
        """Collect all screenshot URLs from the page"""
        image_urls = []
        
        # Multiple selectors for different site structures
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']",
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                
                for elem in elements:
                    src = await elem.get_attribute("src") or await elem.get_attribute("data-src")
                    
                    if not src or not src.startswith("http"):
                        continue
                    
                    # Skip non-screenshot images
                    skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button', 'ad']
                    if any(kw in src.lower() for kw in skip_keywords):
                        continue
                    
                    if src not in image_urls:
                        image_urls.append(src)
                        
            except:
                continue
        
        return image_urls


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Screenshot Downloader")
    parser.add_argument("product", nargs="?", help="Product name to download")
    parser.add_argument("--url", help="Direct URL to product page")
    parser.add_argument("--login", action="store_true", help="Force re-login")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    downloader = SmartDownloader()
    
    try:
        # Start browser
        await downloader.init(headless=args.headless)
        
        # Check/handle login
        if args.login or not await downloader.check_login():
            success = await downloader.wait_for_login()
            if not success:
                print("[ERROR] Login failed")
                return
        else:
            print("[OK] Already logged in")
        
        # Download if product specified
        if args.product:
            result = await downloader.download_product(args.product, args.url)
            
            if result["success"]:
                print(f"\n[SUCCESS] Downloaded {result['count']} screenshots!")
                print(f"          Project: {result['project_path']}")
                
                # Auto-run QA check
                print("\n[QA] Running quality check...")
                try:
                    from qa.triggers import trigger_download_check
                    project_name = os.path.basename(result['project_path'])
                    qa_result = await trigger_download_check(project_name, result['project_path'])
                    
                    if qa_result and not qa_result.get('passed', True):
                        print(f"[QA] Found {len(qa_result.get('issues', []))} issues - see qa_report.json")
                except Exception as e:
                    print(f"[QA] Check skipped: {e}")
                
            else:
                print(f"\n[FAILED] {result.get('error', 'Unknown error')}")
        else:
            print("\n[READY] Browser ready. Use --product to download.")
            print("        Example: python smart_downloader.py Calm")
            print("\n        Press Enter to close browser...")
            await asyncio.get_event_loop().run_in_executor(None, input)
            
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())

