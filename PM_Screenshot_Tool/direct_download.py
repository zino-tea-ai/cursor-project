# -*- coding: utf-8 -*-
"""
Direct download - Visit app page directly using URL pattern
screensdesign.com URL pattern: /apps/{app-slug}/
"""
import asyncio
import sys
import os
import re
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

async def download_app(app_name: str, app_slug: str = None):
    """Download screenshots for a specific app"""
    
    # Generate slug from app name if not provided
    if not app_slug:
        # Convert "Cal AI - Calorie Tracker" to "cal-ai-calorie-tracker"
        app_slug = app_name.lower()
        app_slug = re.sub(r'[^a-z0-9\s-]', '', app_slug)
        app_slug = re.sub(r'\s+', '-', app_slug)
        app_slug = re.sub(r'-+', '-', app_slug).strip('-')
    
    print(f"\n{'='*60}")
    print(f"  Downloading: {app_name}")
    print(f"  Slug: {app_slug}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = re.sub(r'[^\w\s-]', '', app_name).replace(' ', '_')
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    
    # Clear existing screens
    if os.path.exists(screens_dir):
        import shutil
        shutil.rmtree(screens_dir)
    os.makedirs(screens_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Try direct URL
        app_url = f"https://screensdesign.com/apps/{app_slug}/"
        print(f"\n1. Trying direct URL: {app_url}")
        
        response = await page.goto(app_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if page exists
        if response.status == 404 or 'not found' in (await page.title()).lower():
            print(f"   Page not found, trying search instead...")
            
            # Fall back to search
            await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # Click search
            search = await page.query_selector('text=/Search/')
            if search:
                await search.click()
                await asyncio.sleep(1)
            
            inp = await page.query_selector('input:visible')
            if inp:
                simple_name = app_name.split(':')[0].split(' - ')[0].strip()
                await inp.fill(simple_name)
                await asyncio.sleep(1)
                await page.keyboard.press('Enter')
                await asyncio.sleep(5)  # Wait longer for search results
        
        print(f"2. Current URL: {page.url}")
        
        # Wait for content to fully load
        await asyncio.sleep(3)
        
        # Scroll to load all images
        print("3. Scrolling to load all images...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Find all screenshot images
        # Pattern: media.screensdesign.com/avs-pp/ (actual screenshots)
        # Exclude: media.screensdesign.com/appicon-thumbs/ (app icons)
        all_imgs = await page.query_selector_all('img')
        
        image_urls = []
        seen_urls = set()
        
        for img in all_imgs:
            try:
                src = await img.get_attribute('src')
                if src and 'media.screensdesign.com/avs' in src and src not in seen_urls:
                    if 'appicon' not in src:
                        seen_urls.add(src)
                        image_urls.append(src)
            except:
                continue
        
        print(f"4. Found {len(image_urls)} screenshot URLs")
        
        # Save debug screenshot
        await page.screenshot(path=os.path.join(project_dir, "debug_page.png"))
        
        if not image_urls:
            print("   No screenshots found!")
            return 0
        
        # Download images
        print("5. Downloading screenshots...")
        downloaded = 0
        manifest = []
        
        for idx, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    'Referer': 'https://screensdesign.com/'
                })
                
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    filename = f"Screen_{idx:03d}.png"
                    filepath = os.path.join(screens_dir, filename)
                    img.save(filepath, "PNG", optimize=True)
                    
                    manifest.append({
                        "index": idx,
                        "filename": filename,
                        "original_url": url
                    })
                    
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   Downloaded {downloaded}/{len(image_urls)}...")
                        
            except Exception as e:
                print(f"   Error {idx}: {e}")
                continue
        
        # Save manifest
        manifest_path = os.path.join(project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({
                "product": app_name,
                "slug": app_slug,
                "source": "screensdesign.com",
                "url": page.url,
                "downloaded_at": datetime.now().isoformat(),
                "total": downloaded,
                "screenshots": manifest
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"  DONE! Downloaded {downloaded} screenshots")
        print(f"  Saved to: {screens_dir}")
        print(f"{'='*60}")
        
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_name = " ".join(sys.argv[1:])
    else:
        app_name = "Cal AI"
    
    # Try common slug variations
    asyncio.run(download_app(app_name))


"""
Direct download - Visit app page directly using URL pattern
screensdesign.com URL pattern: /apps/{app-slug}/
"""
import asyncio
import sys
import os
import re
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

async def download_app(app_name: str, app_slug: str = None):
    """Download screenshots for a specific app"""
    
    # Generate slug from app name if not provided
    if not app_slug:
        # Convert "Cal AI - Calorie Tracker" to "cal-ai-calorie-tracker"
        app_slug = app_name.lower()
        app_slug = re.sub(r'[^a-z0-9\s-]', '', app_slug)
        app_slug = re.sub(r'\s+', '-', app_slug)
        app_slug = re.sub(r'-+', '-', app_slug).strip('-')
    
    print(f"\n{'='*60}")
    print(f"  Downloading: {app_name}")
    print(f"  Slug: {app_slug}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = re.sub(r'[^\w\s-]', '', app_name).replace(' ', '_')
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    
    # Clear existing screens
    if os.path.exists(screens_dir):
        import shutil
        shutil.rmtree(screens_dir)
    os.makedirs(screens_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Try direct URL
        app_url = f"https://screensdesign.com/apps/{app_slug}/"
        print(f"\n1. Trying direct URL: {app_url}")
        
        response = await page.goto(app_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if page exists
        if response.status == 404 or 'not found' in (await page.title()).lower():
            print(f"   Page not found, trying search instead...")
            
            # Fall back to search
            await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # Click search
            search = await page.query_selector('text=/Search/')
            if search:
                await search.click()
                await asyncio.sleep(1)
            
            inp = await page.query_selector('input:visible')
            if inp:
                simple_name = app_name.split(':')[0].split(' - ')[0].strip()
                await inp.fill(simple_name)
                await asyncio.sleep(1)
                await page.keyboard.press('Enter')
                await asyncio.sleep(5)  # Wait longer for search results
        
        print(f"2. Current URL: {page.url}")
        
        # Wait for content to fully load
        await asyncio.sleep(3)
        
        # Scroll to load all images
        print("3. Scrolling to load all images...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Find all screenshot images
        # Pattern: media.screensdesign.com/avs-pp/ (actual screenshots)
        # Exclude: media.screensdesign.com/appicon-thumbs/ (app icons)
        all_imgs = await page.query_selector_all('img')
        
        image_urls = []
        seen_urls = set()
        
        for img in all_imgs:
            try:
                src = await img.get_attribute('src')
                if src and 'media.screensdesign.com/avs' in src and src not in seen_urls:
                    if 'appicon' not in src:
                        seen_urls.add(src)
                        image_urls.append(src)
            except:
                continue
        
        print(f"4. Found {len(image_urls)} screenshot URLs")
        
        # Save debug screenshot
        await page.screenshot(path=os.path.join(project_dir, "debug_page.png"))
        
        if not image_urls:
            print("   No screenshots found!")
            return 0
        
        # Download images
        print("5. Downloading screenshots...")
        downloaded = 0
        manifest = []
        
        for idx, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    'Referer': 'https://screensdesign.com/'
                })
                
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    filename = f"Screen_{idx:03d}.png"
                    filepath = os.path.join(screens_dir, filename)
                    img.save(filepath, "PNG", optimize=True)
                    
                    manifest.append({
                        "index": idx,
                        "filename": filename,
                        "original_url": url
                    })
                    
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   Downloaded {downloaded}/{len(image_urls)}...")
                        
            except Exception as e:
                print(f"   Error {idx}: {e}")
                continue
        
        # Save manifest
        manifest_path = os.path.join(project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({
                "product": app_name,
                "slug": app_slug,
                "source": "screensdesign.com",
                "url": page.url,
                "downloaded_at": datetime.now().isoformat(),
                "total": downloaded,
                "screenshots": manifest
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"  DONE! Downloaded {downloaded} screenshots")
        print(f"  Saved to: {screens_dir}")
        print(f"{'='*60}")
        
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_name = " ".join(sys.argv[1:])
    else:
        app_name = "Cal AI"
    
    # Try common slug variations
    asyncio.run(download_app(app_name))


"""
Direct download - Visit app page directly using URL pattern
screensdesign.com URL pattern: /apps/{app-slug}/
"""
import asyncio
import sys
import os
import re
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

async def download_app(app_name: str, app_slug: str = None):
    """Download screenshots for a specific app"""
    
    # Generate slug from app name if not provided
    if not app_slug:
        # Convert "Cal AI - Calorie Tracker" to "cal-ai-calorie-tracker"
        app_slug = app_name.lower()
        app_slug = re.sub(r'[^a-z0-9\s-]', '', app_slug)
        app_slug = re.sub(r'\s+', '-', app_slug)
        app_slug = re.sub(r'-+', '-', app_slug).strip('-')
    
    print(f"\n{'='*60}")
    print(f"  Downloading: {app_name}")
    print(f"  Slug: {app_slug}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = re.sub(r'[^\w\s-]', '', app_name).replace(' ', '_')
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    
    # Clear existing screens
    if os.path.exists(screens_dir):
        import shutil
        shutil.rmtree(screens_dir)
    os.makedirs(screens_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Try direct URL
        app_url = f"https://screensdesign.com/apps/{app_slug}/"
        print(f"\n1. Trying direct URL: {app_url}")
        
        response = await page.goto(app_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if page exists
        if response.status == 404 or 'not found' in (await page.title()).lower():
            print(f"   Page not found, trying search instead...")
            
            # Fall back to search
            await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # Click search
            search = await page.query_selector('text=/Search/')
            if search:
                await search.click()
                await asyncio.sleep(1)
            
            inp = await page.query_selector('input:visible')
            if inp:
                simple_name = app_name.split(':')[0].split(' - ')[0].strip()
                await inp.fill(simple_name)
                await asyncio.sleep(1)
                await page.keyboard.press('Enter')
                await asyncio.sleep(5)  # Wait longer for search results
        
        print(f"2. Current URL: {page.url}")
        
        # Wait for content to fully load
        await asyncio.sleep(3)
        
        # Scroll to load all images
        print("3. Scrolling to load all images...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Find all screenshot images
        # Pattern: media.screensdesign.com/avs-pp/ (actual screenshots)
        # Exclude: media.screensdesign.com/appicon-thumbs/ (app icons)
        all_imgs = await page.query_selector_all('img')
        
        image_urls = []
        seen_urls = set()
        
        for img in all_imgs:
            try:
                src = await img.get_attribute('src')
                if src and 'media.screensdesign.com/avs' in src and src not in seen_urls:
                    if 'appicon' not in src:
                        seen_urls.add(src)
                        image_urls.append(src)
            except:
                continue
        
        print(f"4. Found {len(image_urls)} screenshot URLs")
        
        # Save debug screenshot
        await page.screenshot(path=os.path.join(project_dir, "debug_page.png"))
        
        if not image_urls:
            print("   No screenshots found!")
            return 0
        
        # Download images
        print("5. Downloading screenshots...")
        downloaded = 0
        manifest = []
        
        for idx, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    'Referer': 'https://screensdesign.com/'
                })
                
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    filename = f"Screen_{idx:03d}.png"
                    filepath = os.path.join(screens_dir, filename)
                    img.save(filepath, "PNG", optimize=True)
                    
                    manifest.append({
                        "index": idx,
                        "filename": filename,
                        "original_url": url
                    })
                    
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   Downloaded {downloaded}/{len(image_urls)}...")
                        
            except Exception as e:
                print(f"   Error {idx}: {e}")
                continue
        
        # Save manifest
        manifest_path = os.path.join(project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({
                "product": app_name,
                "slug": app_slug,
                "source": "screensdesign.com",
                "url": page.url,
                "downloaded_at": datetime.now().isoformat(),
                "total": downloaded,
                "screenshots": manifest
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"  DONE! Downloaded {downloaded} screenshots")
        print(f"  Saved to: {screens_dir}")
        print(f"{'='*60}")
        
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_name = " ".join(sys.argv[1:])
    else:
        app_name = "Cal AI"
    
    # Try common slug variations
    asyncio.run(download_app(app_name))


"""
Direct download - Visit app page directly using URL pattern
screensdesign.com URL pattern: /apps/{app-slug}/
"""
import asyncio
import sys
import os
import re
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

async def download_app(app_name: str, app_slug: str = None):
    """Download screenshots for a specific app"""
    
    # Generate slug from app name if not provided
    if not app_slug:
        # Convert "Cal AI - Calorie Tracker" to "cal-ai-calorie-tracker"
        app_slug = app_name.lower()
        app_slug = re.sub(r'[^a-z0-9\s-]', '', app_slug)
        app_slug = re.sub(r'\s+', '-', app_slug)
        app_slug = re.sub(r'-+', '-', app_slug).strip('-')
    
    print(f"\n{'='*60}")
    print(f"  Downloading: {app_name}")
    print(f"  Slug: {app_slug}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = re.sub(r'[^\w\s-]', '', app_name).replace(' ', '_')
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    
    # Clear existing screens
    if os.path.exists(screens_dir):
        import shutil
        shutil.rmtree(screens_dir)
    os.makedirs(screens_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Try direct URL
        app_url = f"https://screensdesign.com/apps/{app_slug}/"
        print(f"\n1. Trying direct URL: {app_url}")
        
        response = await page.goto(app_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if page exists
        if response.status == 404 or 'not found' in (await page.title()).lower():
            print(f"   Page not found, trying search instead...")
            
            # Fall back to search
            await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # Click search
            search = await page.query_selector('text=/Search/')
            if search:
                await search.click()
                await asyncio.sleep(1)
            
            inp = await page.query_selector('input:visible')
            if inp:
                simple_name = app_name.split(':')[0].split(' - ')[0].strip()
                await inp.fill(simple_name)
                await asyncio.sleep(1)
                await page.keyboard.press('Enter')
                await asyncio.sleep(5)  # Wait longer for search results
        
        print(f"2. Current URL: {page.url}")
        
        # Wait for content to fully load
        await asyncio.sleep(3)
        
        # Scroll to load all images
        print("3. Scrolling to load all images...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Find all screenshot images
        # Pattern: media.screensdesign.com/avs-pp/ (actual screenshots)
        # Exclude: media.screensdesign.com/appicon-thumbs/ (app icons)
        all_imgs = await page.query_selector_all('img')
        
        image_urls = []
        seen_urls = set()
        
        for img in all_imgs:
            try:
                src = await img.get_attribute('src')
                if src and 'media.screensdesign.com/avs' in src and src not in seen_urls:
                    if 'appicon' not in src:
                        seen_urls.add(src)
                        image_urls.append(src)
            except:
                continue
        
        print(f"4. Found {len(image_urls)} screenshot URLs")
        
        # Save debug screenshot
        await page.screenshot(path=os.path.join(project_dir, "debug_page.png"))
        
        if not image_urls:
            print("   No screenshots found!")
            return 0
        
        # Download images
        print("5. Downloading screenshots...")
        downloaded = 0
        manifest = []
        
        for idx, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    'Referer': 'https://screensdesign.com/'
                })
                
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    filename = f"Screen_{idx:03d}.png"
                    filepath = os.path.join(screens_dir, filename)
                    img.save(filepath, "PNG", optimize=True)
                    
                    manifest.append({
                        "index": idx,
                        "filename": filename,
                        "original_url": url
                    })
                    
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   Downloaded {downloaded}/{len(image_urls)}...")
                        
            except Exception as e:
                print(f"   Error {idx}: {e}")
                continue
        
        # Save manifest
        manifest_path = os.path.join(project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({
                "product": app_name,
                "slug": app_slug,
                "source": "screensdesign.com",
                "url": page.url,
                "downloaded_at": datetime.now().isoformat(),
                "total": downloaded,
                "screenshots": manifest
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"  DONE! Downloaded {downloaded} screenshots")
        print(f"  Saved to: {screens_dir}")
        print(f"{'='*60}")
        
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_name = " ".join(sys.argv[1:])
    else:
        app_name = "Cal AI"
    
    # Try common slug variations
    asyncio.run(download_app(app_name))



"""
Direct download - Visit app page directly using URL pattern
screensdesign.com URL pattern: /apps/{app-slug}/
"""
import asyncio
import sys
import os
import re
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

async def download_app(app_name: str, app_slug: str = None):
    """Download screenshots for a specific app"""
    
    # Generate slug from app name if not provided
    if not app_slug:
        # Convert "Cal AI - Calorie Tracker" to "cal-ai-calorie-tracker"
        app_slug = app_name.lower()
        app_slug = re.sub(r'[^a-z0-9\s-]', '', app_slug)
        app_slug = re.sub(r'\s+', '-', app_slug)
        app_slug = re.sub(r'-+', '-', app_slug).strip('-')
    
    print(f"\n{'='*60}")
    print(f"  Downloading: {app_name}")
    print(f"  Slug: {app_slug}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = re.sub(r'[^\w\s-]', '', app_name).replace(' ', '_')
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    
    # Clear existing screens
    if os.path.exists(screens_dir):
        import shutil
        shutil.rmtree(screens_dir)
    os.makedirs(screens_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Try direct URL
        app_url = f"https://screensdesign.com/apps/{app_slug}/"
        print(f"\n1. Trying direct URL: {app_url}")
        
        response = await page.goto(app_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if page exists
        if response.status == 404 or 'not found' in (await page.title()).lower():
            print(f"   Page not found, trying search instead...")
            
            # Fall back to search
            await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # Click search
            search = await page.query_selector('text=/Search/')
            if search:
                await search.click()
                await asyncio.sleep(1)
            
            inp = await page.query_selector('input:visible')
            if inp:
                simple_name = app_name.split(':')[0].split(' - ')[0].strip()
                await inp.fill(simple_name)
                await asyncio.sleep(1)
                await page.keyboard.press('Enter')
                await asyncio.sleep(5)  # Wait longer for search results
        
        print(f"2. Current URL: {page.url}")
        
        # Wait for content to fully load
        await asyncio.sleep(3)
        
        # Scroll to load all images
        print("3. Scrolling to load all images...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Find all screenshot images
        # Pattern: media.screensdesign.com/avs-pp/ (actual screenshots)
        # Exclude: media.screensdesign.com/appicon-thumbs/ (app icons)
        all_imgs = await page.query_selector_all('img')
        
        image_urls = []
        seen_urls = set()
        
        for img in all_imgs:
            try:
                src = await img.get_attribute('src')
                if src and 'media.screensdesign.com/avs' in src and src not in seen_urls:
                    if 'appicon' not in src:
                        seen_urls.add(src)
                        image_urls.append(src)
            except:
                continue
        
        print(f"4. Found {len(image_urls)} screenshot URLs")
        
        # Save debug screenshot
        await page.screenshot(path=os.path.join(project_dir, "debug_page.png"))
        
        if not image_urls:
            print("   No screenshots found!")
            return 0
        
        # Download images
        print("5. Downloading screenshots...")
        downloaded = 0
        manifest = []
        
        for idx, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    'Referer': 'https://screensdesign.com/'
                })
                
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    filename = f"Screen_{idx:03d}.png"
                    filepath = os.path.join(screens_dir, filename)
                    img.save(filepath, "PNG", optimize=True)
                    
                    manifest.append({
                        "index": idx,
                        "filename": filename,
                        "original_url": url
                    })
                    
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   Downloaded {downloaded}/{len(image_urls)}...")
                        
            except Exception as e:
                print(f"   Error {idx}: {e}")
                continue
        
        # Save manifest
        manifest_path = os.path.join(project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({
                "product": app_name,
                "slug": app_slug,
                "source": "screensdesign.com",
                "url": page.url,
                "downloaded_at": datetime.now().isoformat(),
                "total": downloaded,
                "screenshots": manifest
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"  DONE! Downloaded {downloaded} screenshots")
        print(f"  Saved to: {screens_dir}")
        print(f"{'='*60}")
        
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_name = " ".join(sys.argv[1:])
    else:
        app_name = "Cal AI"
    
    # Try common slug variations
    asyncio.run(download_app(app_name))


"""
Direct download - Visit app page directly using URL pattern
screensdesign.com URL pattern: /apps/{app-slug}/
"""
import asyncio
import sys
import os
import re
import requests
from io import BytesIO
from datetime import datetime
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

async def download_app(app_name: str, app_slug: str = None):
    """Download screenshots for a specific app"""
    
    # Generate slug from app name if not provided
    if not app_slug:
        # Convert "Cal AI - Calorie Tracker" to "cal-ai-calorie-tracker"
        app_slug = app_name.lower()
        app_slug = re.sub(r'[^a-z0-9\s-]', '', app_slug)
        app_slug = re.sub(r'\s+', '-', app_slug)
        app_slug = re.sub(r'-+', '-', app_slug).strip('-')
    
    print(f"\n{'='*60}")
    print(f"  Downloading: {app_name}")
    print(f"  Slug: {app_slug}")
    print(f"{'='*60}")
    
    # Create project folder
    safe_name = re.sub(r'[^\w\s-]', '', app_name).replace(' ', '_')
    project_dir = os.path.join(PROJECTS_DIR, f"{safe_name}_Analysis")
    screens_dir = os.path.join(project_dir, "Screens")
    
    # Clear existing screens
    if os.path.exists(screens_dir):
        import shutil
        shutil.rmtree(screens_dir)
    os.makedirs(screens_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Try direct URL
        app_url = f"https://screensdesign.com/apps/{app_slug}/"
        print(f"\n1. Trying direct URL: {app_url}")
        
        response = await page.goto(app_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Check if page exists
        if response.status == 404 or 'not found' in (await page.title()).lower():
            print(f"   Page not found, trying search instead...")
            
            # Fall back to search
            await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # Click search
            search = await page.query_selector('text=/Search/')
            if search:
                await search.click()
                await asyncio.sleep(1)
            
            inp = await page.query_selector('input:visible')
            if inp:
                simple_name = app_name.split(':')[0].split(' - ')[0].strip()
                await inp.fill(simple_name)
                await asyncio.sleep(1)
                await page.keyboard.press('Enter')
                await asyncio.sleep(5)  # Wait longer for search results
        
        print(f"2. Current URL: {page.url}")
        
        # Wait for content to fully load
        await asyncio.sleep(3)
        
        # Scroll to load all images
        print("3. Scrolling to load all images...")
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.8)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(2)
        
        # Find all screenshot images
        # Pattern: media.screensdesign.com/avs-pp/ (actual screenshots)
        # Exclude: media.screensdesign.com/appicon-thumbs/ (app icons)
        all_imgs = await page.query_selector_all('img')
        
        image_urls = []
        seen_urls = set()
        
        for img in all_imgs:
            try:
                src = await img.get_attribute('src')
                if src and 'media.screensdesign.com/avs' in src and src not in seen_urls:
                    if 'appicon' not in src:
                        seen_urls.add(src)
                        image_urls.append(src)
            except:
                continue
        
        print(f"4. Found {len(image_urls)} screenshot URLs")
        
        # Save debug screenshot
        await page.screenshot(path=os.path.join(project_dir, "debug_page.png"))
        
        if not image_urls:
            print("   No screenshots found!")
            return 0
        
        # Download images
        print("5. Downloading screenshots...")
        downloaded = 0
        manifest = []
        
        for idx, url in enumerate(image_urls, 1):
            try:
                response = requests.get(url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                    'Referer': 'https://screensdesign.com/'
                })
                
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    filename = f"Screen_{idx:03d}.png"
                    filepath = os.path.join(screens_dir, filename)
                    img.save(filepath, "PNG", optimize=True)
                    
                    manifest.append({
                        "index": idx,
                        "filename": filename,
                        "original_url": url
                    })
                    
                    downloaded += 1
                    if downloaded % 10 == 0:
                        print(f"   Downloaded {downloaded}/{len(image_urls)}...")
                        
            except Exception as e:
                print(f"   Error {idx}: {e}")
                continue
        
        # Save manifest
        manifest_path = os.path.join(project_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            import json
            json.dump({
                "product": app_name,
                "slug": app_slug,
                "source": "screensdesign.com",
                "url": page.url,
                "downloaded_at": datetime.now().isoformat(),
                "total": downloaded,
                "screenshots": manifest
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"  DONE! Downloaded {downloaded} screenshots")
        print(f"  Saved to: {screens_dir}")
        print(f"{'='*60}")
        
        return downloaded


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_name = " ".join(sys.argv[1:])
    else:
        app_name = "Cal AI"
    
    # Try common slug variations
    asyncio.run(download_app(app_name))


















