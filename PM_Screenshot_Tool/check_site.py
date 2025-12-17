# -*- coding: utf-8 -*-
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_site():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to search page
        print("Navigating to search page...")
        await page.goto('https://screensdesign.com/?s=cal+ai', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        
        # Get all links
        all_links = await page.query_selector_all('a')
        print(f"Total links: {len(all_links)}")
        
        # Filter app links
        app_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and '/apps/' in href:
                    text = await link.inner_text()
                    text = text.strip().replace('\n', ' ')[:60]
                    app_links.append((href, text))
            except:
                pass
        
        print(f"\nApp links found: {len(app_links)}")
        for href, text in app_links[:15]:
            print(f"  - {text}")
            print(f"    {href}")
        
        # Take screenshot
        screenshot_path = "C:/Users/WIN/Desktop/Cursor Project/PM_Screenshot_Tool/debug_search.png"
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(check_site())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_site():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to search page
        print("Navigating to search page...")
        await page.goto('https://screensdesign.com/?s=cal+ai', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        
        # Get all links
        all_links = await page.query_selector_all('a')
        print(f"Total links: {len(all_links)}")
        
        # Filter app links
        app_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and '/apps/' in href:
                    text = await link.inner_text()
                    text = text.strip().replace('\n', ' ')[:60]
                    app_links.append((href, text))
            except:
                pass
        
        print(f"\nApp links found: {len(app_links)}")
        for href, text in app_links[:15]:
            print(f"  - {text}")
            print(f"    {href}")
        
        # Take screenshot
        screenshot_path = "C:/Users/WIN/Desktop/Cursor Project/PM_Screenshot_Tool/debug_search.png"
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(check_site())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_site():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to search page
        print("Navigating to search page...")
        await page.goto('https://screensdesign.com/?s=cal+ai', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        
        # Get all links
        all_links = await page.query_selector_all('a')
        print(f"Total links: {len(all_links)}")
        
        # Filter app links
        app_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and '/apps/' in href:
                    text = await link.inner_text()
                    text = text.strip().replace('\n', ' ')[:60]
                    app_links.append((href, text))
            except:
                pass
        
        print(f"\nApp links found: {len(app_links)}")
        for href, text in app_links[:15]:
            print(f"  - {text}")
            print(f"    {href}")
        
        # Take screenshot
        screenshot_path = "C:/Users/WIN/Desktop/Cursor Project/PM_Screenshot_Tool/debug_search.png"
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(check_site())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_site():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to search page
        print("Navigating to search page...")
        await page.goto('https://screensdesign.com/?s=cal+ai', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        
        # Get all links
        all_links = await page.query_selector_all('a')
        print(f"Total links: {len(all_links)}")
        
        # Filter app links
        app_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and '/apps/' in href:
                    text = await link.inner_text()
                    text = text.strip().replace('\n', ' ')[:60]
                    app_links.append((href, text))
            except:
                pass
        
        print(f"\nApp links found: {len(app_links)}")
        for href, text in app_links[:15]:
            print(f"  - {text}")
            print(f"    {href}")
        
        # Take screenshot
        screenshot_path = "C:/Users/WIN/Desktop/Cursor Project/PM_Screenshot_Tool/debug_search.png"
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(check_site())



import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_site():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to search page
        print("Navigating to search page...")
        await page.goto('https://screensdesign.com/?s=cal+ai', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        
        # Get all links
        all_links = await page.query_selector_all('a')
        print(f"Total links: {len(all_links)}")
        
        # Filter app links
        app_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and '/apps/' in href:
                    text = await link.inner_text()
                    text = text.strip().replace('\n', ' ')[:60]
                    app_links.append((href, text))
            except:
                pass
        
        print(f"\nApp links found: {len(app_links)}")
        for href, text in app_links[:15]:
            print(f"  - {text}")
            print(f"    {href}")
        
        # Take screenshot
        screenshot_path = "C:/Users/WIN/Desktop/Cursor Project/PM_Screenshot_Tool/debug_search.png"
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(check_site())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def check_site():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to search page
        print("Navigating to search page...")
        await page.goto('https://screensdesign.com/?s=cal+ai', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        print(f"URL: {page.url}")
        
        # Get all links
        all_links = await page.query_selector_all('a')
        print(f"Total links: {len(all_links)}")
        
        # Filter app links
        app_links = []
        for link in all_links:
            try:
                href = await link.get_attribute('href')
                if href and '/apps/' in href:
                    text = await link.inner_text()
                    text = text.strip().replace('\n', ' ')[:60]
                    app_links.append((href, text))
            except:
                pass
        
        print(f"\nApp links found: {len(app_links)}")
        for href, text in app_links[:15]:
            print(f"  - {text}")
            print(f"    {href}")
        
        # Take screenshot
        screenshot_path = "C:/Users/WIN/Desktop/Cursor Project/PM_Screenshot_Tool/debug_search.png"
        await page.screenshot(path=screenshot_path)
        print(f"\nScreenshot saved: {screenshot_path}")

if __name__ == "__main__":
    asyncio.run(check_site())


















