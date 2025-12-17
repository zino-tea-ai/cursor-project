# -*- coding: utf-8 -*-
"""Explore screensdesign.com app page structure"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign and searching for Cal AI...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Dismiss popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Click search
        search = await page.query_selector('text=/Search/')
        if search:
            await search.click()
            await asyncio.sleep(1)
        
        # Type search term
        inp = await page.query_selector('input:visible')
        if inp:
            await inp.fill('Cal AI')
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        
        print(f"2. Search completed. URL: {page.url}")
        await page.screenshot(path=os.path.join(BASE_DIR, "explore_1_search.png"))
        
        # Find Cal AI card and click it
        print("3. Looking for Cal AI card...")
        h3_list = await page.query_selector_all('h3')
        
        for h3 in h3_list:
            text = await h3.inner_text()
            if 'Cal AI' in text and 'Calorie' in text:
                print(f"   Found: {text}")
                
                # Get bounding box
                box = await h3.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}")
                    
                    # Click on the card (click on a point above the H3, which should be the card)
                    await page.mouse.click(box['x'] + 50, box['y'] - 100)
                    await asyncio.sleep(3)
                    
                    print(f"4. After click. URL: {page.url}")
                    await page.screenshot(path=os.path.join(BASE_DIR, "explore_2_after_click.png"))
                    
                    # Check if modal opened or page changed
                    # Look for modal/dialog
                    modals = await page.query_selector_all('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    print(f"   Modals found: {len(modals)}")
                    
                    # Look for close button
                    close_btns = await page.query_selector_all('[aria-label="Close"], button:has-text("×")')
                    print(f"   Close buttons found: {len(close_btns)}")
                    
                    # Check images on page now
                    imgs = await page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                    print(f"   Screenshot images: {len(imgs)}")
                    
                    break

if __name__ == "__main__":
    asyncio.run(explore())


"""Explore screensdesign.com app page structure"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign and searching for Cal AI...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Dismiss popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Click search
        search = await page.query_selector('text=/Search/')
        if search:
            await search.click()
            await asyncio.sleep(1)
        
        # Type search term
        inp = await page.query_selector('input:visible')
        if inp:
            await inp.fill('Cal AI')
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        
        print(f"2. Search completed. URL: {page.url}")
        await page.screenshot(path=os.path.join(BASE_DIR, "explore_1_search.png"))
        
        # Find Cal AI card and click it
        print("3. Looking for Cal AI card...")
        h3_list = await page.query_selector_all('h3')
        
        for h3 in h3_list:
            text = await h3.inner_text()
            if 'Cal AI' in text and 'Calorie' in text:
                print(f"   Found: {text}")
                
                # Get bounding box
                box = await h3.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}")
                    
                    # Click on the card (click on a point above the H3, which should be the card)
                    await page.mouse.click(box['x'] + 50, box['y'] - 100)
                    await asyncio.sleep(3)
                    
                    print(f"4. After click. URL: {page.url}")
                    await page.screenshot(path=os.path.join(BASE_DIR, "explore_2_after_click.png"))
                    
                    # Check if modal opened or page changed
                    # Look for modal/dialog
                    modals = await page.query_selector_all('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    print(f"   Modals found: {len(modals)}")
                    
                    # Look for close button
                    close_btns = await page.query_selector_all('[aria-label="Close"], button:has-text("×")')
                    print(f"   Close buttons found: {len(close_btns)}")
                    
                    # Check images on page now
                    imgs = await page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                    print(f"   Screenshot images: {len(imgs)}")
                    
                    break

if __name__ == "__main__":
    asyncio.run(explore())


"""Explore screensdesign.com app page structure"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign and searching for Cal AI...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Dismiss popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Click search
        search = await page.query_selector('text=/Search/')
        if search:
            await search.click()
            await asyncio.sleep(1)
        
        # Type search term
        inp = await page.query_selector('input:visible')
        if inp:
            await inp.fill('Cal AI')
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        
        print(f"2. Search completed. URL: {page.url}")
        await page.screenshot(path=os.path.join(BASE_DIR, "explore_1_search.png"))
        
        # Find Cal AI card and click it
        print("3. Looking for Cal AI card...")
        h3_list = await page.query_selector_all('h3')
        
        for h3 in h3_list:
            text = await h3.inner_text()
            if 'Cal AI' in text and 'Calorie' in text:
                print(f"   Found: {text}")
                
                # Get bounding box
                box = await h3.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}")
                    
                    # Click on the card (click on a point above the H3, which should be the card)
                    await page.mouse.click(box['x'] + 50, box['y'] - 100)
                    await asyncio.sleep(3)
                    
                    print(f"4. After click. URL: {page.url}")
                    await page.screenshot(path=os.path.join(BASE_DIR, "explore_2_after_click.png"))
                    
                    # Check if modal opened or page changed
                    # Look for modal/dialog
                    modals = await page.query_selector_all('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    print(f"   Modals found: {len(modals)}")
                    
                    # Look for close button
                    close_btns = await page.query_selector_all('[aria-label="Close"], button:has-text("×")')
                    print(f"   Close buttons found: {len(close_btns)}")
                    
                    # Check images on page now
                    imgs = await page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                    print(f"   Screenshot images: {len(imgs)}")
                    
                    break

if __name__ == "__main__":
    asyncio.run(explore())


"""Explore screensdesign.com app page structure"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign and searching for Cal AI...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Dismiss popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Click search
        search = await page.query_selector('text=/Search/')
        if search:
            await search.click()
            await asyncio.sleep(1)
        
        # Type search term
        inp = await page.query_selector('input:visible')
        if inp:
            await inp.fill('Cal AI')
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        
        print(f"2. Search completed. URL: {page.url}")
        await page.screenshot(path=os.path.join(BASE_DIR, "explore_1_search.png"))
        
        # Find Cal AI card and click it
        print("3. Looking for Cal AI card...")
        h3_list = await page.query_selector_all('h3')
        
        for h3 in h3_list:
            text = await h3.inner_text()
            if 'Cal AI' in text and 'Calorie' in text:
                print(f"   Found: {text}")
                
                # Get bounding box
                box = await h3.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}")
                    
                    # Click on the card (click on a point above the H3, which should be the card)
                    await page.mouse.click(box['x'] + 50, box['y'] - 100)
                    await asyncio.sleep(3)
                    
                    print(f"4. After click. URL: {page.url}")
                    await page.screenshot(path=os.path.join(BASE_DIR, "explore_2_after_click.png"))
                    
                    # Check if modal opened or page changed
                    # Look for modal/dialog
                    modals = await page.query_selector_all('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    print(f"   Modals found: {len(modals)}")
                    
                    # Look for close button
                    close_btns = await page.query_selector_all('[aria-label="Close"], button:has-text("×")')
                    print(f"   Close buttons found: {len(close_btns)}")
                    
                    # Check images on page now
                    imgs = await page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                    print(f"   Screenshot images: {len(imgs)}")
                    
                    break

if __name__ == "__main__":
    asyncio.run(explore())



"""Explore screensdesign.com app page structure"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign and searching for Cal AI...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Dismiss popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Click search
        search = await page.query_selector('text=/Search/')
        if search:
            await search.click()
            await asyncio.sleep(1)
        
        # Type search term
        inp = await page.query_selector('input:visible')
        if inp:
            await inp.fill('Cal AI')
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        
        print(f"2. Search completed. URL: {page.url}")
        await page.screenshot(path=os.path.join(BASE_DIR, "explore_1_search.png"))
        
        # Find Cal AI card and click it
        print("3. Looking for Cal AI card...")
        h3_list = await page.query_selector_all('h3')
        
        for h3 in h3_list:
            text = await h3.inner_text()
            if 'Cal AI' in text and 'Calorie' in text:
                print(f"   Found: {text}")
                
                # Get bounding box
                box = await h3.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}")
                    
                    # Click on the card (click on a point above the H3, which should be the card)
                    await page.mouse.click(box['x'] + 50, box['y'] - 100)
                    await asyncio.sleep(3)
                    
                    print(f"4. After click. URL: {page.url}")
                    await page.screenshot(path=os.path.join(BASE_DIR, "explore_2_after_click.png"))
                    
                    # Check if modal opened or page changed
                    # Look for modal/dialog
                    modals = await page.query_selector_all('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    print(f"   Modals found: {len(modals)}")
                    
                    # Look for close button
                    close_btns = await page.query_selector_all('[aria-label="Close"], button:has-text("×")')
                    print(f"   Close buttons found: {len(close_btns)}")
                    
                    # Check images on page now
                    imgs = await page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                    print(f"   Screenshot images: {len(imgs)}")
                    
                    break

if __name__ == "__main__":
    asyncio.run(explore())


"""Explore screensdesign.com app page structure"""
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def explore():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign and searching for Cal AI...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)
        
        # Dismiss popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Click search
        search = await page.query_selector('text=/Search/')
        if search:
            await search.click()
            await asyncio.sleep(1)
        
        # Type search term
        inp = await page.query_selector('input:visible')
        if inp:
            await inp.fill('Cal AI')
            await asyncio.sleep(1)
            await page.keyboard.press('Enter')
            await asyncio.sleep(3)
        
        print(f"2. Search completed. URL: {page.url}")
        await page.screenshot(path=os.path.join(BASE_DIR, "explore_1_search.png"))
        
        # Find Cal AI card and click it
        print("3. Looking for Cal AI card...")
        h3_list = await page.query_selector_all('h3')
        
        for h3 in h3_list:
            text = await h3.inner_text()
            if 'Cal AI' in text and 'Calorie' in text:
                print(f"   Found: {text}")
                
                # Get bounding box
                box = await h3.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}")
                    
                    # Click on the card (click on a point above the H3, which should be the card)
                    await page.mouse.click(box['x'] + 50, box['y'] - 100)
                    await asyncio.sleep(3)
                    
                    print(f"4. After click. URL: {page.url}")
                    await page.screenshot(path=os.path.join(BASE_DIR, "explore_2_after_click.png"))
                    
                    # Check if modal opened or page changed
                    # Look for modal/dialog
                    modals = await page.query_selector_all('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    print(f"   Modals found: {len(modals)}")
                    
                    # Look for close button
                    close_btns = await page.query_selector_all('[aria-label="Close"], button:has-text("×")')
                    print(f"   Close buttons found: {len(close_btns)}")
                    
                    # Check images on page now
                    imgs = await page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                    print(f"   Screenshot images: {len(imgs)}")
                    
                    break

if __name__ == "__main__":
    asyncio.run(explore())


















