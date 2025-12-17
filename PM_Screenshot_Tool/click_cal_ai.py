# -*- coding: utf-8 -*-
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def click_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"Current URL: {page.url}")
        
        # Find and click Cal AI - Calorie Tracker
        h3_elements = await page.query_selector_all('h3')
        print(f"Found {len(h3_elements)} H3 elements")
        
        for h3 in h3_elements:
            text = await h3.inner_text()
            if 'Cal AI' in text:
                print(f"Found: {text}")
                
                # Get parent container to click
                parent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                
                # Click the parent div (card)
                print("Clicking on the card...")
                await parent.click()
                await asyncio.sleep(3)
                
                # Check new URL
                print(f"New URL: {page.url}")
                
                # Take screenshot
                await page.screenshot(path=os.path.join(BASE_DIR, "cal_ai_page.png"))
                print(f"Screenshot saved: cal_ai_page.png")
                
                # Now look for screenshot images
                imgs = await page.query_selector_all('img')
                print(f"\nFound {len(imgs)} images")
                
                for i, img in enumerate(imgs[:15]):
                    src = await img.get_attribute('src')
                    if src:
                        print(f"  {i}: {src[:80]}...")
                
                break

if __name__ == "__main__":
    asyncio.run(click_cal_ai())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def click_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"Current URL: {page.url}")
        
        # Find and click Cal AI - Calorie Tracker
        h3_elements = await page.query_selector_all('h3')
        print(f"Found {len(h3_elements)} H3 elements")
        
        for h3 in h3_elements:
            text = await h3.inner_text()
            if 'Cal AI' in text:
                print(f"Found: {text}")
                
                # Get parent container to click
                parent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                
                # Click the parent div (card)
                print("Clicking on the card...")
                await parent.click()
                await asyncio.sleep(3)
                
                # Check new URL
                print(f"New URL: {page.url}")
                
                # Take screenshot
                await page.screenshot(path=os.path.join(BASE_DIR, "cal_ai_page.png"))
                print(f"Screenshot saved: cal_ai_page.png")
                
                # Now look for screenshot images
                imgs = await page.query_selector_all('img')
                print(f"\nFound {len(imgs)} images")
                
                for i, img in enumerate(imgs[:15]):
                    src = await img.get_attribute('src')
                    if src:
                        print(f"  {i}: {src[:80]}...")
                
                break

if __name__ == "__main__":
    asyncio.run(click_cal_ai())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def click_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"Current URL: {page.url}")
        
        # Find and click Cal AI - Calorie Tracker
        h3_elements = await page.query_selector_all('h3')
        print(f"Found {len(h3_elements)} H3 elements")
        
        for h3 in h3_elements:
            text = await h3.inner_text()
            if 'Cal AI' in text:
                print(f"Found: {text}")
                
                # Get parent container to click
                parent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                
                # Click the parent div (card)
                print("Clicking on the card...")
                await parent.click()
                await asyncio.sleep(3)
                
                # Check new URL
                print(f"New URL: {page.url}")
                
                # Take screenshot
                await page.screenshot(path=os.path.join(BASE_DIR, "cal_ai_page.png"))
                print(f"Screenshot saved: cal_ai_page.png")
                
                # Now look for screenshot images
                imgs = await page.query_selector_all('img')
                print(f"\nFound {len(imgs)} images")
                
                for i, img in enumerate(imgs[:15]):
                    src = await img.get_attribute('src')
                    if src:
                        print(f"  {i}: {src[:80]}...")
                
                break

if __name__ == "__main__":
    asyncio.run(click_cal_ai())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def click_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"Current URL: {page.url}")
        
        # Find and click Cal AI - Calorie Tracker
        h3_elements = await page.query_selector_all('h3')
        print(f"Found {len(h3_elements)} H3 elements")
        
        for h3 in h3_elements:
            text = await h3.inner_text()
            if 'Cal AI' in text:
                print(f"Found: {text}")
                
                # Get parent container to click
                parent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                
                # Click the parent div (card)
                print("Clicking on the card...")
                await parent.click()
                await asyncio.sleep(3)
                
                # Check new URL
                print(f"New URL: {page.url}")
                
                # Take screenshot
                await page.screenshot(path=os.path.join(BASE_DIR, "cal_ai_page.png"))
                print(f"Screenshot saved: cal_ai_page.png")
                
                # Now look for screenshot images
                imgs = await page.query_selector_all('img')
                print(f"\nFound {len(imgs)} images")
                
                for i, img in enumerate(imgs[:15]):
                    src = await img.get_attribute('src')
                    if src:
                        print(f"  {i}: {src[:80]}...")
                
                break

if __name__ == "__main__":
    asyncio.run(click_cal_ai())



import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def click_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"Current URL: {page.url}")
        
        # Find and click Cal AI - Calorie Tracker
        h3_elements = await page.query_selector_all('h3')
        print(f"Found {len(h3_elements)} H3 elements")
        
        for h3 in h3_elements:
            text = await h3.inner_text()
            if 'Cal AI' in text:
                print(f"Found: {text}")
                
                # Get parent container to click
                parent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                
                # Click the parent div (card)
                print("Clicking on the card...")
                await parent.click()
                await asyncio.sleep(3)
                
                # Check new URL
                print(f"New URL: {page.url}")
                
                # Take screenshot
                await page.screenshot(path=os.path.join(BASE_DIR, "cal_ai_page.png"))
                print(f"Screenshot saved: cal_ai_page.png")
                
                # Now look for screenshot images
                imgs = await page.query_selector_all('img')
                print(f"\nFound {len(imgs)} images")
                
                for i, img in enumerate(imgs[:15]):
                    src = await img.get_attribute('src')
                    if src:
                        print(f"  {i}: {src[:80]}...")
                
                break

if __name__ == "__main__":
    asyncio.run(click_cal_ai())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def click_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"Current URL: {page.url}")
        
        # Find and click Cal AI - Calorie Tracker
        h3_elements = await page.query_selector_all('h3')
        print(f"Found {len(h3_elements)} H3 elements")
        
        for h3 in h3_elements:
            text = await h3.inner_text()
            if 'Cal AI' in text:
                print(f"Found: {text}")
                
                # Get parent container to click
                parent = await h3.evaluate_handle('el => el.parentElement.parentElement')
                
                # Click the parent div (card)
                print("Clicking on the card...")
                await parent.click()
                await asyncio.sleep(3)
                
                # Check new URL
                print(f"New URL: {page.url}")
                
                # Take screenshot
                await page.screenshot(path=os.path.join(BASE_DIR, "cal_ai_page.png"))
                print(f"Screenshot saved: cal_ai_page.png")
                
                # Now look for screenshot images
                imgs = await page.query_selector_all('img')
                print(f"\nFound {len(imgs)} images")
                
                for i, img in enumerate(imgs[:15]):
                    src = await img.get_attribute('src')
                    if src:
                        print(f"  {i}: {src[:80]}...")
                
                break

if __name__ == "__main__":
    asyncio.run(click_cal_ai())


















