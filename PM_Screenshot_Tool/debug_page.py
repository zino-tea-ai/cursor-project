# -*- coding: utf-8 -*-
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("Navigating to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"Current URL: {page.url}")
        
        # Get all inputs
        inputs = await page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                input_type = await inp.get_attribute('type') or ''
                print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}'")
            except:
                pass
        
        # Look for anything with "search" in class or text
        search_elements = await page.query_selector_all('[class*="search"], [placeholder*="Search"]')
        print(f"Found {len(search_elements)} search-related elements")
        
        # Take screenshot
        screenshot_path = os.path.join(BASE_DIR, "debug_homepage.png")
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
        # Also check if there's a modal blocking
        modals = await page.query_selector_all('[class*="modal"], [class*="popup"], [class*="dialog"]')
        print(f"Found {len(modals)} modal/popup elements")

if __name__ == "__main__":
    asyncio.run(debug_page())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("Navigating to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"Current URL: {page.url}")
        
        # Get all inputs
        inputs = await page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                input_type = await inp.get_attribute('type') or ''
                print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}'")
            except:
                pass
        
        # Look for anything with "search" in class or text
        search_elements = await page.query_selector_all('[class*="search"], [placeholder*="Search"]')
        print(f"Found {len(search_elements)} search-related elements")
        
        # Take screenshot
        screenshot_path = os.path.join(BASE_DIR, "debug_homepage.png")
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
        # Also check if there's a modal blocking
        modals = await page.query_selector_all('[class*="modal"], [class*="popup"], [class*="dialog"]')
        print(f"Found {len(modals)} modal/popup elements")

if __name__ == "__main__":
    asyncio.run(debug_page())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("Navigating to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"Current URL: {page.url}")
        
        # Get all inputs
        inputs = await page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                input_type = await inp.get_attribute('type') or ''
                print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}'")
            except:
                pass
        
        # Look for anything with "search" in class or text
        search_elements = await page.query_selector_all('[class*="search"], [placeholder*="Search"]')
        print(f"Found {len(search_elements)} search-related elements")
        
        # Take screenshot
        screenshot_path = os.path.join(BASE_DIR, "debug_homepage.png")
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
        # Also check if there's a modal blocking
        modals = await page.query_selector_all('[class*="modal"], [class*="popup"], [class*="dialog"]')
        print(f"Found {len(modals)} modal/popup elements")

if __name__ == "__main__":
    asyncio.run(debug_page())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("Navigating to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"Current URL: {page.url}")
        
        # Get all inputs
        inputs = await page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                input_type = await inp.get_attribute('type') or ''
                print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}'")
            except:
                pass
        
        # Look for anything with "search" in class or text
        search_elements = await page.query_selector_all('[class*="search"], [placeholder*="Search"]')
        print(f"Found {len(search_elements)} search-related elements")
        
        # Take screenshot
        screenshot_path = os.path.join(BASE_DIR, "debug_homepage.png")
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
        # Also check if there's a modal blocking
        modals = await page.query_selector_all('[class*="modal"], [class*="popup"], [class*="dialog"]')
        print(f"Found {len(modals)} modal/popup elements")

if __name__ == "__main__":
    asyncio.run(debug_page())



import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("Navigating to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"Current URL: {page.url}")
        
        # Get all inputs
        inputs = await page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                input_type = await inp.get_attribute('type') or ''
                print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}'")
            except:
                pass
        
        # Look for anything with "search" in class or text
        search_elements = await page.query_selector_all('[class*="search"], [placeholder*="Search"]')
        print(f"Found {len(search_elements)} search-related elements")
        
        # Take screenshot
        screenshot_path = os.path.join(BASE_DIR, "debug_homepage.png")
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
        # Also check if there's a modal blocking
        modals = await page.query_selector_all('[class*="modal"], [class*="popup"], [class*="dialog"]')
        print(f"Found {len(modals)} modal/popup elements")

if __name__ == "__main__":
    asyncio.run(debug_page())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("Navigating to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        print(f"Current URL: {page.url}")
        
        # Get all inputs
        inputs = await page.query_selector_all('input')
        print(f"Found {len(inputs)} input elements")
        for i, inp in enumerate(inputs):
            try:
                placeholder = await inp.get_attribute('placeholder') or ''
                input_type = await inp.get_attribute('type') or ''
                print(f"  Input {i}: type='{input_type}', placeholder='{placeholder}'")
            except:
                pass
        
        # Look for anything with "search" in class or text
        search_elements = await page.query_selector_all('[class*="search"], [placeholder*="Search"]')
        print(f"Found {len(search_elements)} search-related elements")
        
        # Take screenshot
        screenshot_path = os.path.join(BASE_DIR, "debug_homepage.png")
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved: {screenshot_path}")
        
        # Also check if there's a modal blocking
        modals = await page.query_selector_all('[class*="modal"], [class*="popup"], [class*="dialog"]')
        print(f"Found {len(modals)} modal/popup elements")

if __name__ == "__main__":
    asyncio.run(debug_page())


















