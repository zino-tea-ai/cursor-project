# -*- coding: utf-8 -*-
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_search(search_term):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to main page
        print(f"Searching for: {search_term}")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Find search input
        search_input = await page.query_selector('input[placeholder*="Search"]')
        if search_input:
            print("Found search input")
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(search_term)
            await asyncio.sleep(2)  # Wait for autocomplete
            
            # Take screenshot
            await page.screenshot(path='debug_search_calai.png')
            print("Screenshot saved: debug_search_calai.png")
            
            # Check for dropdown/autocomplete results
            autocomplete = await page.query_selector_all('[class*="autocomplete"], [class*="dropdown"], [class*="suggest"]')
            print(f"Autocomplete elements: {len(autocomplete)}")
            
            # Get all visible text
            body_text = await page.inner_text('body')
            if 'cal' in body_text.lower():
                print("'cal' found in page text")
                # Find lines containing 'cal'
                for line in body_text.split('\n'):
                    if 'cal' in line.lower() and len(line) < 100:
                        print(f"  - {line.strip()}")
        else:
            print("Search input not found")

if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "Cal AI"
    asyncio.run(test_search(term))


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_search(search_term):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to main page
        print(f"Searching for: {search_term}")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Find search input
        search_input = await page.query_selector('input[placeholder*="Search"]')
        if search_input:
            print("Found search input")
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(search_term)
            await asyncio.sleep(2)  # Wait for autocomplete
            
            # Take screenshot
            await page.screenshot(path='debug_search_calai.png')
            print("Screenshot saved: debug_search_calai.png")
            
            # Check for dropdown/autocomplete results
            autocomplete = await page.query_selector_all('[class*="autocomplete"], [class*="dropdown"], [class*="suggest"]')
            print(f"Autocomplete elements: {len(autocomplete)}")
            
            # Get all visible text
            body_text = await page.inner_text('body')
            if 'cal' in body_text.lower():
                print("'cal' found in page text")
                # Find lines containing 'cal'
                for line in body_text.split('\n'):
                    if 'cal' in line.lower() and len(line) < 100:
                        print(f"  - {line.strip()}")
        else:
            print("Search input not found")

if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "Cal AI"
    asyncio.run(test_search(term))


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_search(search_term):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to main page
        print(f"Searching for: {search_term}")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Find search input
        search_input = await page.query_selector('input[placeholder*="Search"]')
        if search_input:
            print("Found search input")
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(search_term)
            await asyncio.sleep(2)  # Wait for autocomplete
            
            # Take screenshot
            await page.screenshot(path='debug_search_calai.png')
            print("Screenshot saved: debug_search_calai.png")
            
            # Check for dropdown/autocomplete results
            autocomplete = await page.query_selector_all('[class*="autocomplete"], [class*="dropdown"], [class*="suggest"]')
            print(f"Autocomplete elements: {len(autocomplete)}")
            
            # Get all visible text
            body_text = await page.inner_text('body')
            if 'cal' in body_text.lower():
                print("'cal' found in page text")
                # Find lines containing 'cal'
                for line in body_text.split('\n'):
                    if 'cal' in line.lower() and len(line) < 100:
                        print(f"  - {line.strip()}")
        else:
            print("Search input not found")

if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "Cal AI"
    asyncio.run(test_search(term))


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_search(search_term):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to main page
        print(f"Searching for: {search_term}")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Find search input
        search_input = await page.query_selector('input[placeholder*="Search"]')
        if search_input:
            print("Found search input")
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(search_term)
            await asyncio.sleep(2)  # Wait for autocomplete
            
            # Take screenshot
            await page.screenshot(path='debug_search_calai.png')
            print("Screenshot saved: debug_search_calai.png")
            
            # Check for dropdown/autocomplete results
            autocomplete = await page.query_selector_all('[class*="autocomplete"], [class*="dropdown"], [class*="suggest"]')
            print(f"Autocomplete elements: {len(autocomplete)}")
            
            # Get all visible text
            body_text = await page.inner_text('body')
            if 'cal' in body_text.lower():
                print("'cal' found in page text")
                # Find lines containing 'cal'
                for line in body_text.split('\n'):
                    if 'cal' in line.lower() and len(line) < 100:
                        print(f"  - {line.strip()}")
        else:
            print("Search input not found")

if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "Cal AI"
    asyncio.run(test_search(term))



import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_search(search_term):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to main page
        print(f"Searching for: {search_term}")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Find search input
        search_input = await page.query_selector('input[placeholder*="Search"]')
        if search_input:
            print("Found search input")
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(search_term)
            await asyncio.sleep(2)  # Wait for autocomplete
            
            # Take screenshot
            await page.screenshot(path='debug_search_calai.png')
            print("Screenshot saved: debug_search_calai.png")
            
            # Check for dropdown/autocomplete results
            autocomplete = await page.query_selector_all('[class*="autocomplete"], [class*="dropdown"], [class*="suggest"]')
            print(f"Autocomplete elements: {len(autocomplete)}")
            
            # Get all visible text
            body_text = await page.inner_text('body')
            if 'cal' in body_text.lower():
                print("'cal' found in page text")
                # Find lines containing 'cal'
                for line in body_text.split('\n'):
                    if 'cal' in line.lower() and len(line) < 100:
                        print(f"  - {line.strip()}")
        else:
            print("Search input not found")

if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "Cal AI"
    asyncio.run(test_search(term))


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def test_search(search_term):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Go to main page
        print(f"Searching for: {search_term}")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Find search input
        search_input = await page.query_selector('input[placeholder*="Search"]')
        if search_input:
            print("Found search input")
            await search_input.click()
            await asyncio.sleep(0.5)
            await search_input.fill(search_term)
            await asyncio.sleep(2)  # Wait for autocomplete
            
            # Take screenshot
            await page.screenshot(path='debug_search_calai.png')
            print("Screenshot saved: debug_search_calai.png")
            
            # Check for dropdown/autocomplete results
            autocomplete = await page.query_selector_all('[class*="autocomplete"], [class*="dropdown"], [class*="suggest"]')
            print(f"Autocomplete elements: {len(autocomplete)}")
            
            # Get all visible text
            body_text = await page.inner_text('body')
            if 'cal' in body_text.lower():
                print("'cal' found in page text")
                # Find lines containing 'cal'
                for line in body_text.split('\n'):
                    if 'cal' in line.lower() and len(line) < 100:
                        print(f"  - {line.strip()}")
        else:
            print("Search input not found")

if __name__ == "__main__":
    term = sys.argv[1] if len(sys.argv) > 1 else "Cal AI"
    asyncio.run(test_search(term))


















