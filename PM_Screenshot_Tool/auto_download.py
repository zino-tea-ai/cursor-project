# -*- coding: utf-8 -*-
"""
Auto Download Script - Fully automated screenshot download from screensdesign.com
Connects to existing Chrome with debugging port
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
TARGET_WIDTH = 402
CHROME_DEBUG_URL = "http://127.0.0.1:9222"


async def download_product(product_name: str):
    """Download all screenshots for a product from screensdesign.com"""
    
    print(f"\n{'='*60}")
    print(f"  Auto Download: {product_name}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = product_name.replace(" ", "_").replace(":", "").replace("-", "_")
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    os.makedirs(screens_dir, exist_ok=True)
    
    print(f"\n[1/5] Connecting to Chrome...")
    
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome
            browser = await p.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("  -> Connected to Chrome")
        except Exception as e:
            print(f"  -> ERROR: Could not connect to Chrome: {e}")
            print("  -> Make sure Chrome is running with --remote-debugging-port=9222")
            return None
        
        # Step 2: Navigate to screensdesign and search
        print(f"\n[2/5] Searching for '{product_name}'...")
        
        # Go to screensdesign.com
        await page.goto("https://screensdesign.com/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Find and click search button/input
        try:
            # Try to find search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-testid="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        break
                except:
                    continue
            
            if not search_input:
                # Maybe need to click a search icon first
                search_icons = ['button[aria-label*="search"]', '.search-icon', 'svg[class*="search"]']
                for icon in search_icons:
                    try:
                        icon_el = await page.wait_for_selector(icon, timeout=2000)
                        if icon_el:
                            await icon_el.click()
                            await asyncio.sleep(1)
                            search_input = await page.wait_for_selector('input', timeout=3000)
                            break
                    except:
                        continue
            
            if search_input:
                await search_input.fill(product_name)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"  -> Searched for '{product_name}'")
            else:
                print("  -> Could not find search input, trying direct URL...")
                # Try direct URL pattern
                search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"  -> Search error: {e}")
        
        # Step 3: Find and click on product result
        print(f"\n[3/5] Finding product page...")
        
        try:
            # Look for product links in search results
            product_links = await page.query_selector_all('a[href*="/app/"]')
            
            if not product_links:
                # Try other patterns
                product_links = await page.query_selector_all('article a, .app-card a, .result a')
            
            target_link = None
            for link in product_links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if product_name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                    target_link = link
                    print(f"  -> Found: {text}")
                    break
            
            if target_link:
                await target_link.click()
                await asyncio.sleep(3)
                print(f"  -> Navigated to product page")
            else:
                print(f"  -> Could not find '{product_name}' in results")
                # Take screenshot of current page for debugging
                debug_path = os.path.join(project_dir, "debug_search_results.png")
                await page.screenshot(path=debug_path)
                print(f"  -> Debug screenshot saved: {debug_path}")
                
                # Try to find any app links and list them
                all_links = await page.query_selector_all('a')
                app_links = []
                for link in all_links[:20]:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if href and '/app/' in href:
                            app_links.append(f"{text.strip()[:30]} -> {href}")
                    except:
                        pass
                
                if app_links:
                    print("\n  Available apps on this page:")
                    for al in app_links[:10]:
                        print(f"    - {al}")
                
                return None
                
        except Exception as e:
            print(f"  -> Navigation error: {e}")
            return None
        
        # Step 4: Download screenshots
        print(f"\n[4/5] Downloading screenshots...")
        
        try:
            # Wait for screenshots to load
            await asyncio.sleep(2)
            
            # Find all screenshot images
            img_selectors = [
                'img[src*="screen"]',
                'img[src*="screenshot"]',
                '.screenshot img',
                '.screen-image img',
                'article img',
                '.gallery img',
                'img[loading="lazy"]'
            ]
            
            images = []
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    if imgs:
                        images.extend(imgs)
                except:
                    continue
            
            # Remove duplicates by src
            seen_srcs = set()
            unique_images = []
            for img in images:
                src = await img.get_attribute('src')
                if src and src not in seen_srcs and ('screen' in src.lower() or 'cdn' in src.lower()):
                    seen_srcs.add(src)
                    unique_images.append((img, src))
            
            print(f"  -> Found {len(unique_images)} screenshots")
            
            if not unique_images:
                print("  -> No screenshots found, taking page screenshot for debugging")
                debug_path = os.path.join(project_dir, "debug_product_page.png")
                await page.screenshot(path=debug_path, full_page=True)
                return None
            
            # Download each image
            downloaded = 0
            manifest = []
            
            for idx, (img, src) in enumerate(unique_images, 1):
                try:
                    # Get full resolution URL
                    full_src = src
                    if not full_src.startswith('http'):
                        full_src = 'https://screensdesign.com' + full_src
                    
                    # Download image
                    response = requests.get(full_src, timeout=30)
                    if response.status_code == 200:
                        # Process image
                        img_data = Image.open(BytesIO(response.content))
                        
                        # Convert to RGB if needed
                        if img_data.mode in ('RGBA', 'P'):
                            img_data = img_data.convert('RGB')
                        
                        # Resize to target width
                        ratio = TARGET_WIDTH / img_data.width
                        new_height = int(img_data.height * ratio)
                        img_data = img_data.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # Save
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img_data.save(filepath, "PNG", optimize=True)
                        
                        manifest.append({
                            "index": idx,
                            "filename": filename,
                            "original_url": full_src,
                            "width": TARGET_WIDTH,
                            "height": new_height
                        })
                        
                        downloaded += 1
                        print(f"    [{idx}/{len(unique_images)}] {filename}")
                        
                except Exception as e:
                    print(f"    [{idx}] Error: {e}")
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "product": product_name,
                    "source": "screensdesign.com",
                    "downloaded_at": datetime.now().isoformat(),
                    "total_screenshots": downloaded,
                    "screenshots": manifest
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[5/5] Complete!")
            print(f"  -> Downloaded: {downloaded} screenshots")
            print(f"  -> Saved to: {screens_dir}")
            print(f"  -> Manifest: {manifest_path}")
            
            return {
                "project_dir": project_dir,
                "screenshots": downloaded,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"  -> Download error: {e}")
            return None


async def main():
    # Get product name from command line or use default
    if len(sys.argv) > 1:
        product_name = " ".join(sys.argv[1:])
    else:
        product_name = "Cal AI"
    
    result = await download_product(product_name)
    
    if result:
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {result['screenshots']} screenshots downloaded")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  FAILED: Could not download screenshots")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())


"""
Auto Download Script - Fully automated screenshot download from screensdesign.com
Connects to existing Chrome with debugging port
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
TARGET_WIDTH = 402
CHROME_DEBUG_URL = "http://127.0.0.1:9222"


async def download_product(product_name: str):
    """Download all screenshots for a product from screensdesign.com"""
    
    print(f"\n{'='*60}")
    print(f"  Auto Download: {product_name}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = product_name.replace(" ", "_").replace(":", "").replace("-", "_")
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    os.makedirs(screens_dir, exist_ok=True)
    
    print(f"\n[1/5] Connecting to Chrome...")
    
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome
            browser = await p.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("  -> Connected to Chrome")
        except Exception as e:
            print(f"  -> ERROR: Could not connect to Chrome: {e}")
            print("  -> Make sure Chrome is running with --remote-debugging-port=9222")
            return None
        
        # Step 2: Navigate to screensdesign and search
        print(f"\n[2/5] Searching for '{product_name}'...")
        
        # Go to screensdesign.com
        await page.goto("https://screensdesign.com/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Find and click search button/input
        try:
            # Try to find search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-testid="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        break
                except:
                    continue
            
            if not search_input:
                # Maybe need to click a search icon first
                search_icons = ['button[aria-label*="search"]', '.search-icon', 'svg[class*="search"]']
                for icon in search_icons:
                    try:
                        icon_el = await page.wait_for_selector(icon, timeout=2000)
                        if icon_el:
                            await icon_el.click()
                            await asyncio.sleep(1)
                            search_input = await page.wait_for_selector('input', timeout=3000)
                            break
                    except:
                        continue
            
            if search_input:
                await search_input.fill(product_name)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"  -> Searched for '{product_name}'")
            else:
                print("  -> Could not find search input, trying direct URL...")
                # Try direct URL pattern
                search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"  -> Search error: {e}")
        
        # Step 3: Find and click on product result
        print(f"\n[3/5] Finding product page...")
        
        try:
            # Look for product links in search results
            product_links = await page.query_selector_all('a[href*="/app/"]')
            
            if not product_links:
                # Try other patterns
                product_links = await page.query_selector_all('article a, .app-card a, .result a')
            
            target_link = None
            for link in product_links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if product_name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                    target_link = link
                    print(f"  -> Found: {text}")
                    break
            
            if target_link:
                await target_link.click()
                await asyncio.sleep(3)
                print(f"  -> Navigated to product page")
            else:
                print(f"  -> Could not find '{product_name}' in results")
                # Take screenshot of current page for debugging
                debug_path = os.path.join(project_dir, "debug_search_results.png")
                await page.screenshot(path=debug_path)
                print(f"  -> Debug screenshot saved: {debug_path}")
                
                # Try to find any app links and list them
                all_links = await page.query_selector_all('a')
                app_links = []
                for link in all_links[:20]:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if href and '/app/' in href:
                            app_links.append(f"{text.strip()[:30]} -> {href}")
                    except:
                        pass
                
                if app_links:
                    print("\n  Available apps on this page:")
                    for al in app_links[:10]:
                        print(f"    - {al}")
                
                return None
                
        except Exception as e:
            print(f"  -> Navigation error: {e}")
            return None
        
        # Step 4: Download screenshots
        print(f"\n[4/5] Downloading screenshots...")
        
        try:
            # Wait for screenshots to load
            await asyncio.sleep(2)
            
            # Find all screenshot images
            img_selectors = [
                'img[src*="screen"]',
                'img[src*="screenshot"]',
                '.screenshot img',
                '.screen-image img',
                'article img',
                '.gallery img',
                'img[loading="lazy"]'
            ]
            
            images = []
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    if imgs:
                        images.extend(imgs)
                except:
                    continue
            
            # Remove duplicates by src
            seen_srcs = set()
            unique_images = []
            for img in images:
                src = await img.get_attribute('src')
                if src and src not in seen_srcs and ('screen' in src.lower() or 'cdn' in src.lower()):
                    seen_srcs.add(src)
                    unique_images.append((img, src))
            
            print(f"  -> Found {len(unique_images)} screenshots")
            
            if not unique_images:
                print("  -> No screenshots found, taking page screenshot for debugging")
                debug_path = os.path.join(project_dir, "debug_product_page.png")
                await page.screenshot(path=debug_path, full_page=True)
                return None
            
            # Download each image
            downloaded = 0
            manifest = []
            
            for idx, (img, src) in enumerate(unique_images, 1):
                try:
                    # Get full resolution URL
                    full_src = src
                    if not full_src.startswith('http'):
                        full_src = 'https://screensdesign.com' + full_src
                    
                    # Download image
                    response = requests.get(full_src, timeout=30)
                    if response.status_code == 200:
                        # Process image
                        img_data = Image.open(BytesIO(response.content))
                        
                        # Convert to RGB if needed
                        if img_data.mode in ('RGBA', 'P'):
                            img_data = img_data.convert('RGB')
                        
                        # Resize to target width
                        ratio = TARGET_WIDTH / img_data.width
                        new_height = int(img_data.height * ratio)
                        img_data = img_data.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # Save
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img_data.save(filepath, "PNG", optimize=True)
                        
                        manifest.append({
                            "index": idx,
                            "filename": filename,
                            "original_url": full_src,
                            "width": TARGET_WIDTH,
                            "height": new_height
                        })
                        
                        downloaded += 1
                        print(f"    [{idx}/{len(unique_images)}] {filename}")
                        
                except Exception as e:
                    print(f"    [{idx}] Error: {e}")
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "product": product_name,
                    "source": "screensdesign.com",
                    "downloaded_at": datetime.now().isoformat(),
                    "total_screenshots": downloaded,
                    "screenshots": manifest
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[5/5] Complete!")
            print(f"  -> Downloaded: {downloaded} screenshots")
            print(f"  -> Saved to: {screens_dir}")
            print(f"  -> Manifest: {manifest_path}")
            
            return {
                "project_dir": project_dir,
                "screenshots": downloaded,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"  -> Download error: {e}")
            return None


async def main():
    # Get product name from command line or use default
    if len(sys.argv) > 1:
        product_name = " ".join(sys.argv[1:])
    else:
        product_name = "Cal AI"
    
    result = await download_product(product_name)
    
    if result:
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {result['screenshots']} screenshots downloaded")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  FAILED: Could not download screenshots")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())


"""
Auto Download Script - Fully automated screenshot download from screensdesign.com
Connects to existing Chrome with debugging port
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
TARGET_WIDTH = 402
CHROME_DEBUG_URL = "http://127.0.0.1:9222"


async def download_product(product_name: str):
    """Download all screenshots for a product from screensdesign.com"""
    
    print(f"\n{'='*60}")
    print(f"  Auto Download: {product_name}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = product_name.replace(" ", "_").replace(":", "").replace("-", "_")
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    os.makedirs(screens_dir, exist_ok=True)
    
    print(f"\n[1/5] Connecting to Chrome...")
    
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome
            browser = await p.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("  -> Connected to Chrome")
        except Exception as e:
            print(f"  -> ERROR: Could not connect to Chrome: {e}")
            print("  -> Make sure Chrome is running with --remote-debugging-port=9222")
            return None
        
        # Step 2: Navigate to screensdesign and search
        print(f"\n[2/5] Searching for '{product_name}'...")
        
        # Go to screensdesign.com
        await page.goto("https://screensdesign.com/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Find and click search button/input
        try:
            # Try to find search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-testid="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        break
                except:
                    continue
            
            if not search_input:
                # Maybe need to click a search icon first
                search_icons = ['button[aria-label*="search"]', '.search-icon', 'svg[class*="search"]']
                for icon in search_icons:
                    try:
                        icon_el = await page.wait_for_selector(icon, timeout=2000)
                        if icon_el:
                            await icon_el.click()
                            await asyncio.sleep(1)
                            search_input = await page.wait_for_selector('input', timeout=3000)
                            break
                    except:
                        continue
            
            if search_input:
                await search_input.fill(product_name)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"  -> Searched for '{product_name}'")
            else:
                print("  -> Could not find search input, trying direct URL...")
                # Try direct URL pattern
                search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"  -> Search error: {e}")
        
        # Step 3: Find and click on product result
        print(f"\n[3/5] Finding product page...")
        
        try:
            # Look for product links in search results
            product_links = await page.query_selector_all('a[href*="/app/"]')
            
            if not product_links:
                # Try other patterns
                product_links = await page.query_selector_all('article a, .app-card a, .result a')
            
            target_link = None
            for link in product_links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if product_name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                    target_link = link
                    print(f"  -> Found: {text}")
                    break
            
            if target_link:
                await target_link.click()
                await asyncio.sleep(3)
                print(f"  -> Navigated to product page")
            else:
                print(f"  -> Could not find '{product_name}' in results")
                # Take screenshot of current page for debugging
                debug_path = os.path.join(project_dir, "debug_search_results.png")
                await page.screenshot(path=debug_path)
                print(f"  -> Debug screenshot saved: {debug_path}")
                
                # Try to find any app links and list them
                all_links = await page.query_selector_all('a')
                app_links = []
                for link in all_links[:20]:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if href and '/app/' in href:
                            app_links.append(f"{text.strip()[:30]} -> {href}")
                    except:
                        pass
                
                if app_links:
                    print("\n  Available apps on this page:")
                    for al in app_links[:10]:
                        print(f"    - {al}")
                
                return None
                
        except Exception as e:
            print(f"  -> Navigation error: {e}")
            return None
        
        # Step 4: Download screenshots
        print(f"\n[4/5] Downloading screenshots...")
        
        try:
            # Wait for screenshots to load
            await asyncio.sleep(2)
            
            # Find all screenshot images
            img_selectors = [
                'img[src*="screen"]',
                'img[src*="screenshot"]',
                '.screenshot img',
                '.screen-image img',
                'article img',
                '.gallery img',
                'img[loading="lazy"]'
            ]
            
            images = []
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    if imgs:
                        images.extend(imgs)
                except:
                    continue
            
            # Remove duplicates by src
            seen_srcs = set()
            unique_images = []
            for img in images:
                src = await img.get_attribute('src')
                if src and src not in seen_srcs and ('screen' in src.lower() or 'cdn' in src.lower()):
                    seen_srcs.add(src)
                    unique_images.append((img, src))
            
            print(f"  -> Found {len(unique_images)} screenshots")
            
            if not unique_images:
                print("  -> No screenshots found, taking page screenshot for debugging")
                debug_path = os.path.join(project_dir, "debug_product_page.png")
                await page.screenshot(path=debug_path, full_page=True)
                return None
            
            # Download each image
            downloaded = 0
            manifest = []
            
            for idx, (img, src) in enumerate(unique_images, 1):
                try:
                    # Get full resolution URL
                    full_src = src
                    if not full_src.startswith('http'):
                        full_src = 'https://screensdesign.com' + full_src
                    
                    # Download image
                    response = requests.get(full_src, timeout=30)
                    if response.status_code == 200:
                        # Process image
                        img_data = Image.open(BytesIO(response.content))
                        
                        # Convert to RGB if needed
                        if img_data.mode in ('RGBA', 'P'):
                            img_data = img_data.convert('RGB')
                        
                        # Resize to target width
                        ratio = TARGET_WIDTH / img_data.width
                        new_height = int(img_data.height * ratio)
                        img_data = img_data.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # Save
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img_data.save(filepath, "PNG", optimize=True)
                        
                        manifest.append({
                            "index": idx,
                            "filename": filename,
                            "original_url": full_src,
                            "width": TARGET_WIDTH,
                            "height": new_height
                        })
                        
                        downloaded += 1
                        print(f"    [{idx}/{len(unique_images)}] {filename}")
                        
                except Exception as e:
                    print(f"    [{idx}] Error: {e}")
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "product": product_name,
                    "source": "screensdesign.com",
                    "downloaded_at": datetime.now().isoformat(),
                    "total_screenshots": downloaded,
                    "screenshots": manifest
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[5/5] Complete!")
            print(f"  -> Downloaded: {downloaded} screenshots")
            print(f"  -> Saved to: {screens_dir}")
            print(f"  -> Manifest: {manifest_path}")
            
            return {
                "project_dir": project_dir,
                "screenshots": downloaded,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"  -> Download error: {e}")
            return None


async def main():
    # Get product name from command line or use default
    if len(sys.argv) > 1:
        product_name = " ".join(sys.argv[1:])
    else:
        product_name = "Cal AI"
    
    result = await download_product(product_name)
    
    if result:
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {result['screenshots']} screenshots downloaded")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  FAILED: Could not download screenshots")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())


"""
Auto Download Script - Fully automated screenshot download from screensdesign.com
Connects to existing Chrome with debugging port
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
TARGET_WIDTH = 402
CHROME_DEBUG_URL = "http://127.0.0.1:9222"


async def download_product(product_name: str):
    """Download all screenshots for a product from screensdesign.com"""
    
    print(f"\n{'='*60}")
    print(f"  Auto Download: {product_name}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = product_name.replace(" ", "_").replace(":", "").replace("-", "_")
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    os.makedirs(screens_dir, exist_ok=True)
    
    print(f"\n[1/5] Connecting to Chrome...")
    
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome
            browser = await p.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("  -> Connected to Chrome")
        except Exception as e:
            print(f"  -> ERROR: Could not connect to Chrome: {e}")
            print("  -> Make sure Chrome is running with --remote-debugging-port=9222")
            return None
        
        # Step 2: Navigate to screensdesign and search
        print(f"\n[2/5] Searching for '{product_name}'...")
        
        # Go to screensdesign.com
        await page.goto("https://screensdesign.com/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Find and click search button/input
        try:
            # Try to find search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-testid="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        break
                except:
                    continue
            
            if not search_input:
                # Maybe need to click a search icon first
                search_icons = ['button[aria-label*="search"]', '.search-icon', 'svg[class*="search"]']
                for icon in search_icons:
                    try:
                        icon_el = await page.wait_for_selector(icon, timeout=2000)
                        if icon_el:
                            await icon_el.click()
                            await asyncio.sleep(1)
                            search_input = await page.wait_for_selector('input', timeout=3000)
                            break
                    except:
                        continue
            
            if search_input:
                await search_input.fill(product_name)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"  -> Searched for '{product_name}'")
            else:
                print("  -> Could not find search input, trying direct URL...")
                # Try direct URL pattern
                search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"  -> Search error: {e}")
        
        # Step 3: Find and click on product result
        print(f"\n[3/5] Finding product page...")
        
        try:
            # Look for product links in search results
            product_links = await page.query_selector_all('a[href*="/app/"]')
            
            if not product_links:
                # Try other patterns
                product_links = await page.query_selector_all('article a, .app-card a, .result a')
            
            target_link = None
            for link in product_links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if product_name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                    target_link = link
                    print(f"  -> Found: {text}")
                    break
            
            if target_link:
                await target_link.click()
                await asyncio.sleep(3)
                print(f"  -> Navigated to product page")
            else:
                print(f"  -> Could not find '{product_name}' in results")
                # Take screenshot of current page for debugging
                debug_path = os.path.join(project_dir, "debug_search_results.png")
                await page.screenshot(path=debug_path)
                print(f"  -> Debug screenshot saved: {debug_path}")
                
                # Try to find any app links and list them
                all_links = await page.query_selector_all('a')
                app_links = []
                for link in all_links[:20]:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if href and '/app/' in href:
                            app_links.append(f"{text.strip()[:30]} -> {href}")
                    except:
                        pass
                
                if app_links:
                    print("\n  Available apps on this page:")
                    for al in app_links[:10]:
                        print(f"    - {al}")
                
                return None
                
        except Exception as e:
            print(f"  -> Navigation error: {e}")
            return None
        
        # Step 4: Download screenshots
        print(f"\n[4/5] Downloading screenshots...")
        
        try:
            # Wait for screenshots to load
            await asyncio.sleep(2)
            
            # Find all screenshot images
            img_selectors = [
                'img[src*="screen"]',
                'img[src*="screenshot"]',
                '.screenshot img',
                '.screen-image img',
                'article img',
                '.gallery img',
                'img[loading="lazy"]'
            ]
            
            images = []
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    if imgs:
                        images.extend(imgs)
                except:
                    continue
            
            # Remove duplicates by src
            seen_srcs = set()
            unique_images = []
            for img in images:
                src = await img.get_attribute('src')
                if src and src not in seen_srcs and ('screen' in src.lower() or 'cdn' in src.lower()):
                    seen_srcs.add(src)
                    unique_images.append((img, src))
            
            print(f"  -> Found {len(unique_images)} screenshots")
            
            if not unique_images:
                print("  -> No screenshots found, taking page screenshot for debugging")
                debug_path = os.path.join(project_dir, "debug_product_page.png")
                await page.screenshot(path=debug_path, full_page=True)
                return None
            
            # Download each image
            downloaded = 0
            manifest = []
            
            for idx, (img, src) in enumerate(unique_images, 1):
                try:
                    # Get full resolution URL
                    full_src = src
                    if not full_src.startswith('http'):
                        full_src = 'https://screensdesign.com' + full_src
                    
                    # Download image
                    response = requests.get(full_src, timeout=30)
                    if response.status_code == 200:
                        # Process image
                        img_data = Image.open(BytesIO(response.content))
                        
                        # Convert to RGB if needed
                        if img_data.mode in ('RGBA', 'P'):
                            img_data = img_data.convert('RGB')
                        
                        # Resize to target width
                        ratio = TARGET_WIDTH / img_data.width
                        new_height = int(img_data.height * ratio)
                        img_data = img_data.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # Save
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img_data.save(filepath, "PNG", optimize=True)
                        
                        manifest.append({
                            "index": idx,
                            "filename": filename,
                            "original_url": full_src,
                            "width": TARGET_WIDTH,
                            "height": new_height
                        })
                        
                        downloaded += 1
                        print(f"    [{idx}/{len(unique_images)}] {filename}")
                        
                except Exception as e:
                    print(f"    [{idx}] Error: {e}")
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "product": product_name,
                    "source": "screensdesign.com",
                    "downloaded_at": datetime.now().isoformat(),
                    "total_screenshots": downloaded,
                    "screenshots": manifest
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[5/5] Complete!")
            print(f"  -> Downloaded: {downloaded} screenshots")
            print(f"  -> Saved to: {screens_dir}")
            print(f"  -> Manifest: {manifest_path}")
            
            return {
                "project_dir": project_dir,
                "screenshots": downloaded,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"  -> Download error: {e}")
            return None


async def main():
    # Get product name from command line or use default
    if len(sys.argv) > 1:
        product_name = " ".join(sys.argv[1:])
    else:
        product_name = "Cal AI"
    
    result = await download_product(product_name)
    
    if result:
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {result['screenshots']} screenshots downloaded")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  FAILED: Could not download screenshots")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())



"""
Auto Download Script - Fully automated screenshot download from screensdesign.com
Connects to existing Chrome with debugging port
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
TARGET_WIDTH = 402
CHROME_DEBUG_URL = "http://127.0.0.1:9222"


async def download_product(product_name: str):
    """Download all screenshots for a product from screensdesign.com"""
    
    print(f"\n{'='*60}")
    print(f"  Auto Download: {product_name}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = product_name.replace(" ", "_").replace(":", "").replace("-", "_")
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    os.makedirs(screens_dir, exist_ok=True)
    
    print(f"\n[1/5] Connecting to Chrome...")
    
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome
            browser = await p.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("  -> Connected to Chrome")
        except Exception as e:
            print(f"  -> ERROR: Could not connect to Chrome: {e}")
            print("  -> Make sure Chrome is running with --remote-debugging-port=9222")
            return None
        
        # Step 2: Navigate to screensdesign and search
        print(f"\n[2/5] Searching for '{product_name}'...")
        
        # Go to screensdesign.com
        await page.goto("https://screensdesign.com/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Find and click search button/input
        try:
            # Try to find search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-testid="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        break
                except:
                    continue
            
            if not search_input:
                # Maybe need to click a search icon first
                search_icons = ['button[aria-label*="search"]', '.search-icon', 'svg[class*="search"]']
                for icon in search_icons:
                    try:
                        icon_el = await page.wait_for_selector(icon, timeout=2000)
                        if icon_el:
                            await icon_el.click()
                            await asyncio.sleep(1)
                            search_input = await page.wait_for_selector('input', timeout=3000)
                            break
                    except:
                        continue
            
            if search_input:
                await search_input.fill(product_name)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"  -> Searched for '{product_name}'")
            else:
                print("  -> Could not find search input, trying direct URL...")
                # Try direct URL pattern
                search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"  -> Search error: {e}")
        
        # Step 3: Find and click on product result
        print(f"\n[3/5] Finding product page...")
        
        try:
            # Look for product links in search results
            product_links = await page.query_selector_all('a[href*="/app/"]')
            
            if not product_links:
                # Try other patterns
                product_links = await page.query_selector_all('article a, .app-card a, .result a')
            
            target_link = None
            for link in product_links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if product_name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                    target_link = link
                    print(f"  -> Found: {text}")
                    break
            
            if target_link:
                await target_link.click()
                await asyncio.sleep(3)
                print(f"  -> Navigated to product page")
            else:
                print(f"  -> Could not find '{product_name}' in results")
                # Take screenshot of current page for debugging
                debug_path = os.path.join(project_dir, "debug_search_results.png")
                await page.screenshot(path=debug_path)
                print(f"  -> Debug screenshot saved: {debug_path}")
                
                # Try to find any app links and list them
                all_links = await page.query_selector_all('a')
                app_links = []
                for link in all_links[:20]:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if href and '/app/' in href:
                            app_links.append(f"{text.strip()[:30]} -> {href}")
                    except:
                        pass
                
                if app_links:
                    print("\n  Available apps on this page:")
                    for al in app_links[:10]:
                        print(f"    - {al}")
                
                return None
                
        except Exception as e:
            print(f"  -> Navigation error: {e}")
            return None
        
        # Step 4: Download screenshots
        print(f"\n[4/5] Downloading screenshots...")
        
        try:
            # Wait for screenshots to load
            await asyncio.sleep(2)
            
            # Find all screenshot images
            img_selectors = [
                'img[src*="screen"]',
                'img[src*="screenshot"]',
                '.screenshot img',
                '.screen-image img',
                'article img',
                '.gallery img',
                'img[loading="lazy"]'
            ]
            
            images = []
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    if imgs:
                        images.extend(imgs)
                except:
                    continue
            
            # Remove duplicates by src
            seen_srcs = set()
            unique_images = []
            for img in images:
                src = await img.get_attribute('src')
                if src and src not in seen_srcs and ('screen' in src.lower() or 'cdn' in src.lower()):
                    seen_srcs.add(src)
                    unique_images.append((img, src))
            
            print(f"  -> Found {len(unique_images)} screenshots")
            
            if not unique_images:
                print("  -> No screenshots found, taking page screenshot for debugging")
                debug_path = os.path.join(project_dir, "debug_product_page.png")
                await page.screenshot(path=debug_path, full_page=True)
                return None
            
            # Download each image
            downloaded = 0
            manifest = []
            
            for idx, (img, src) in enumerate(unique_images, 1):
                try:
                    # Get full resolution URL
                    full_src = src
                    if not full_src.startswith('http'):
                        full_src = 'https://screensdesign.com' + full_src
                    
                    # Download image
                    response = requests.get(full_src, timeout=30)
                    if response.status_code == 200:
                        # Process image
                        img_data = Image.open(BytesIO(response.content))
                        
                        # Convert to RGB if needed
                        if img_data.mode in ('RGBA', 'P'):
                            img_data = img_data.convert('RGB')
                        
                        # Resize to target width
                        ratio = TARGET_WIDTH / img_data.width
                        new_height = int(img_data.height * ratio)
                        img_data = img_data.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # Save
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img_data.save(filepath, "PNG", optimize=True)
                        
                        manifest.append({
                            "index": idx,
                            "filename": filename,
                            "original_url": full_src,
                            "width": TARGET_WIDTH,
                            "height": new_height
                        })
                        
                        downloaded += 1
                        print(f"    [{idx}/{len(unique_images)}] {filename}")
                        
                except Exception as e:
                    print(f"    [{idx}] Error: {e}")
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "product": product_name,
                    "source": "screensdesign.com",
                    "downloaded_at": datetime.now().isoformat(),
                    "total_screenshots": downloaded,
                    "screenshots": manifest
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[5/5] Complete!")
            print(f"  -> Downloaded: {downloaded} screenshots")
            print(f"  -> Saved to: {screens_dir}")
            print(f"  -> Manifest: {manifest_path}")
            
            return {
                "project_dir": project_dir,
                "screenshots": downloaded,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"  -> Download error: {e}")
            return None


async def main():
    # Get product name from command line or use default
    if len(sys.argv) > 1:
        product_name = " ".join(sys.argv[1:])
    else:
        product_name = "Cal AI"
    
    result = await download_product(product_name)
    
    if result:
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {result['screenshots']} screenshots downloaded")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  FAILED: Could not download screenshots")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())


"""
Auto Download Script - Fully automated screenshot download from screensdesign.com
Connects to existing Chrome with debugging port
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
TARGET_WIDTH = 402
CHROME_DEBUG_URL = "http://127.0.0.1:9222"


async def download_product(product_name: str):
    """Download all screenshots for a product from screensdesign.com"""
    
    print(f"\n{'='*60}")
    print(f"  Auto Download: {product_name}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = product_name.replace(" ", "_").replace(":", "").replace("-", "_")
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    os.makedirs(screens_dir, exist_ok=True)
    
    print(f"\n[1/5] Connecting to Chrome...")
    
    async with async_playwright() as p:
        try:
            # Connect to existing Chrome
            browser = await p.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            context = browser.contexts[0]
            page = context.pages[0] if context.pages else await context.new_page()
            print("  -> Connected to Chrome")
        except Exception as e:
            print(f"  -> ERROR: Could not connect to Chrome: {e}")
            print("  -> Make sure Chrome is running with --remote-debugging-port=9222")
            return None
        
        # Step 2: Navigate to screensdesign and search
        print(f"\n[2/5] Searching for '{product_name}'...")
        
        # Go to screensdesign.com
        await page.goto("https://screensdesign.com/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        
        # Find and click search button/input
        try:
            # Try to find search input
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                '.search-input',
                '#search',
                '[data-testid="search"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.wait_for_selector(selector, timeout=3000)
                    if search_input:
                        break
                except:
                    continue
            
            if not search_input:
                # Maybe need to click a search icon first
                search_icons = ['button[aria-label*="search"]', '.search-icon', 'svg[class*="search"]']
                for icon in search_icons:
                    try:
                        icon_el = await page.wait_for_selector(icon, timeout=2000)
                        if icon_el:
                            await icon_el.click()
                            await asyncio.sleep(1)
                            search_input = await page.wait_for_selector('input', timeout=3000)
                            break
                    except:
                        continue
            
            if search_input:
                await search_input.fill(product_name)
                await page.keyboard.press("Enter")
                await asyncio.sleep(3)
                print(f"  -> Searched for '{product_name}'")
            else:
                print("  -> Could not find search input, trying direct URL...")
                # Try direct URL pattern
                search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"  -> Search error: {e}")
        
        # Step 3: Find and click on product result
        print(f"\n[3/5] Finding product page...")
        
        try:
            # Look for product links in search results
            product_links = await page.query_selector_all('a[href*="/app/"]')
            
            if not product_links:
                # Try other patterns
                product_links = await page.query_selector_all('article a, .app-card a, .result a')
            
            target_link = None
            for link in product_links:
                text = await link.inner_text()
                href = await link.get_attribute('href')
                if product_name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                    target_link = link
                    print(f"  -> Found: {text}")
                    break
            
            if target_link:
                await target_link.click()
                await asyncio.sleep(3)
                print(f"  -> Navigated to product page")
            else:
                print(f"  -> Could not find '{product_name}' in results")
                # Take screenshot of current page for debugging
                debug_path = os.path.join(project_dir, "debug_search_results.png")
                await page.screenshot(path=debug_path)
                print(f"  -> Debug screenshot saved: {debug_path}")
                
                # Try to find any app links and list them
                all_links = await page.query_selector_all('a')
                app_links = []
                for link in all_links[:20]:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if href and '/app/' in href:
                            app_links.append(f"{text.strip()[:30]} -> {href}")
                    except:
                        pass
                
                if app_links:
                    print("\n  Available apps on this page:")
                    for al in app_links[:10]:
                        print(f"    - {al}")
                
                return None
                
        except Exception as e:
            print(f"  -> Navigation error: {e}")
            return None
        
        # Step 4: Download screenshots
        print(f"\n[4/5] Downloading screenshots...")
        
        try:
            # Wait for screenshots to load
            await asyncio.sleep(2)
            
            # Find all screenshot images
            img_selectors = [
                'img[src*="screen"]',
                'img[src*="screenshot"]',
                '.screenshot img',
                '.screen-image img',
                'article img',
                '.gallery img',
                'img[loading="lazy"]'
            ]
            
            images = []
            for selector in img_selectors:
                try:
                    imgs = await page.query_selector_all(selector)
                    if imgs:
                        images.extend(imgs)
                except:
                    continue
            
            # Remove duplicates by src
            seen_srcs = set()
            unique_images = []
            for img in images:
                src = await img.get_attribute('src')
                if src and src not in seen_srcs and ('screen' in src.lower() or 'cdn' in src.lower()):
                    seen_srcs.add(src)
                    unique_images.append((img, src))
            
            print(f"  -> Found {len(unique_images)} screenshots")
            
            if not unique_images:
                print("  -> No screenshots found, taking page screenshot for debugging")
                debug_path = os.path.join(project_dir, "debug_product_page.png")
                await page.screenshot(path=debug_path, full_page=True)
                return None
            
            # Download each image
            downloaded = 0
            manifest = []
            
            for idx, (img, src) in enumerate(unique_images, 1):
                try:
                    # Get full resolution URL
                    full_src = src
                    if not full_src.startswith('http'):
                        full_src = 'https://screensdesign.com' + full_src
                    
                    # Download image
                    response = requests.get(full_src, timeout=30)
                    if response.status_code == 200:
                        # Process image
                        img_data = Image.open(BytesIO(response.content))
                        
                        # Convert to RGB if needed
                        if img_data.mode in ('RGBA', 'P'):
                            img_data = img_data.convert('RGB')
                        
                        # Resize to target width
                        ratio = TARGET_WIDTH / img_data.width
                        new_height = int(img_data.height * ratio)
                        img_data = img_data.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # Save
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img_data.save(filepath, "PNG", optimize=True)
                        
                        manifest.append({
                            "index": idx,
                            "filename": filename,
                            "original_url": full_src,
                            "width": TARGET_WIDTH,
                            "height": new_height
                        })
                        
                        downloaded += 1
                        print(f"    [{idx}/{len(unique_images)}] {filename}")
                        
                except Exception as e:
                    print(f"    [{idx}] Error: {e}")
                    continue
            
            # Save manifest
            manifest_path = os.path.join(project_dir, "manifest.json")
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "product": product_name,
                    "source": "screensdesign.com",
                    "downloaded_at": datetime.now().isoformat(),
                    "total_screenshots": downloaded,
                    "screenshots": manifest
                }, f, indent=2, ensure_ascii=False)
            
            print(f"\n[5/5] Complete!")
            print(f"  -> Downloaded: {downloaded} screenshots")
            print(f"  -> Saved to: {screens_dir}")
            print(f"  -> Manifest: {manifest_path}")
            
            return {
                "project_dir": project_dir,
                "screenshots": downloaded,
                "manifest": manifest
            }
            
        except Exception as e:
            print(f"  -> Download error: {e}")
            return None


async def main():
    # Get product name from command line or use default
    if len(sys.argv) > 1:
        product_name = " ".join(sys.argv[1:])
    else:
        product_name = "Cal AI"
    
    result = await download_product(product_name)
    
    if result:
        print(f"\n{'='*60}")
        print(f"  SUCCESS: {result['screenshots']} screenshots downloaded")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  FAILED: Could not download screenshots")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())


















