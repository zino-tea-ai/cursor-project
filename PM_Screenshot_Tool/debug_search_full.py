# -*- coding: utf-8 -*-
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Screenshot before search
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_1_before.png"))
        print("   Screenshot: debug_1_before.png")
        
        print("2. Pressing Escape to close popup...")
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print("3. Looking for search element...")
        # Try different ways to find search
        search_text = await page.query_selector('text=/Search.*apps/')
        if search_text:
            print("   Found 'Search X apps' text, clicking...")
            await search_text.click()
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(BASE_DIR, "debug_2_after_click.png"))
            print("   Screenshot: debug_2_after_click.png")
        
        print("4. Looking for input fields...")
        inputs = await page.query_selector_all('input')
        print(f"   Found {len(inputs)} inputs")
        
        for i, inp in enumerate(inputs):
            try:
                is_visible = await inp.is_visible()
                if is_visible:
                    print(f"   Input {i} is visible, typing 'Cal AI'...")
                    await inp.fill('Cal AI')
                    await asyncio.sleep(2)
                    await page.screenshot(path=os.path.join(BASE_DIR, "debug_3_typed.png"))
                    print("   Screenshot: debug_3_typed.png")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"   Input {i} error: {e}")
        
        # Final screenshot
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_4_final.png"))
        print("5. Screenshot: debug_4_final.png")
        
        # Check current URL
        print(f"   Current URL: {page.url}")
        
        # List all app links
        links = await page.query_selector_all('a[href*="/apps/"]')
        print(f"6. Found {len(links)} app links")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:40]
            print(f"   {i}: {text} -> {href[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_search())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Screenshot before search
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_1_before.png"))
        print("   Screenshot: debug_1_before.png")
        
        print("2. Pressing Escape to close popup...")
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print("3. Looking for search element...")
        # Try different ways to find search
        search_text = await page.query_selector('text=/Search.*apps/')
        if search_text:
            print("   Found 'Search X apps' text, clicking...")
            await search_text.click()
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(BASE_DIR, "debug_2_after_click.png"))
            print("   Screenshot: debug_2_after_click.png")
        
        print("4. Looking for input fields...")
        inputs = await page.query_selector_all('input')
        print(f"   Found {len(inputs)} inputs")
        
        for i, inp in enumerate(inputs):
            try:
                is_visible = await inp.is_visible()
                if is_visible:
                    print(f"   Input {i} is visible, typing 'Cal AI'...")
                    await inp.fill('Cal AI')
                    await asyncio.sleep(2)
                    await page.screenshot(path=os.path.join(BASE_DIR, "debug_3_typed.png"))
                    print("   Screenshot: debug_3_typed.png")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"   Input {i} error: {e}")
        
        # Final screenshot
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_4_final.png"))
        print("5. Screenshot: debug_4_final.png")
        
        # Check current URL
        print(f"   Current URL: {page.url}")
        
        # List all app links
        links = await page.query_selector_all('a[href*="/apps/"]')
        print(f"6. Found {len(links)} app links")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:40]
            print(f"   {i}: {text} -> {href[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_search())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Screenshot before search
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_1_before.png"))
        print("   Screenshot: debug_1_before.png")
        
        print("2. Pressing Escape to close popup...")
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print("3. Looking for search element...")
        # Try different ways to find search
        search_text = await page.query_selector('text=/Search.*apps/')
        if search_text:
            print("   Found 'Search X apps' text, clicking...")
            await search_text.click()
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(BASE_DIR, "debug_2_after_click.png"))
            print("   Screenshot: debug_2_after_click.png")
        
        print("4. Looking for input fields...")
        inputs = await page.query_selector_all('input')
        print(f"   Found {len(inputs)} inputs")
        
        for i, inp in enumerate(inputs):
            try:
                is_visible = await inp.is_visible()
                if is_visible:
                    print(f"   Input {i} is visible, typing 'Cal AI'...")
                    await inp.fill('Cal AI')
                    await asyncio.sleep(2)
                    await page.screenshot(path=os.path.join(BASE_DIR, "debug_3_typed.png"))
                    print("   Screenshot: debug_3_typed.png")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"   Input {i} error: {e}")
        
        # Final screenshot
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_4_final.png"))
        print("5. Screenshot: debug_4_final.png")
        
        # Check current URL
        print(f"   Current URL: {page.url}")
        
        # List all app links
        links = await page.query_selector_all('a[href*="/apps/"]')
        print(f"6. Found {len(links)} app links")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:40]
            print(f"   {i}: {text} -> {href[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_search())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Screenshot before search
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_1_before.png"))
        print("   Screenshot: debug_1_before.png")
        
        print("2. Pressing Escape to close popup...")
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print("3. Looking for search element...")
        # Try different ways to find search
        search_text = await page.query_selector('text=/Search.*apps/')
        if search_text:
            print("   Found 'Search X apps' text, clicking...")
            await search_text.click()
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(BASE_DIR, "debug_2_after_click.png"))
            print("   Screenshot: debug_2_after_click.png")
        
        print("4. Looking for input fields...")
        inputs = await page.query_selector_all('input')
        print(f"   Found {len(inputs)} inputs")
        
        for i, inp in enumerate(inputs):
            try:
                is_visible = await inp.is_visible()
                if is_visible:
                    print(f"   Input {i} is visible, typing 'Cal AI'...")
                    await inp.fill('Cal AI')
                    await asyncio.sleep(2)
                    await page.screenshot(path=os.path.join(BASE_DIR, "debug_3_typed.png"))
                    print("   Screenshot: debug_3_typed.png")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"   Input {i} error: {e}")
        
        # Final screenshot
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_4_final.png"))
        print("5. Screenshot: debug_4_final.png")
        
        # Check current URL
        print(f"   Current URL: {page.url}")
        
        # List all app links
        links = await page.query_selector_all('a[href*="/apps/"]')
        print(f"6. Found {len(links)} app links")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:40]
            print(f"   {i}: {text} -> {href[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_search())



import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Screenshot before search
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_1_before.png"))
        print("   Screenshot: debug_1_before.png")
        
        print("2. Pressing Escape to close popup...")
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print("3. Looking for search element...")
        # Try different ways to find search
        search_text = await page.query_selector('text=/Search.*apps/')
        if search_text:
            print("   Found 'Search X apps' text, clicking...")
            await search_text.click()
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(BASE_DIR, "debug_2_after_click.png"))
            print("   Screenshot: debug_2_after_click.png")
        
        print("4. Looking for input fields...")
        inputs = await page.query_selector_all('input')
        print(f"   Found {len(inputs)} inputs")
        
        for i, inp in enumerate(inputs):
            try:
                is_visible = await inp.is_visible()
                if is_visible:
                    print(f"   Input {i} is visible, typing 'Cal AI'...")
                    await inp.fill('Cal AI')
                    await asyncio.sleep(2)
                    await page.screenshot(path=os.path.join(BASE_DIR, "debug_3_typed.png"))
                    print("   Screenshot: debug_3_typed.png")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"   Input {i} error: {e}")
        
        # Final screenshot
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_4_final.png"))
        print("5. Screenshot: debug_4_final.png")
        
        # Check current URL
        print(f"   Current URL: {page.url}")
        
        # List all app links
        links = await page.query_selector_all('a[href*="/apps/"]')
        print(f"6. Found {len(links)} app links")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:40]
            print(f"   {i}: {text} -> {href[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_search())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

async def debug_search():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        print("1. Going to screensdesign.com...")
        await page.goto('https://screensdesign.com/', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # Screenshot before search
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_1_before.png"))
        print("   Screenshot: debug_1_before.png")
        
        print("2. Pressing Escape to close popup...")
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print("3. Looking for search element...")
        # Try different ways to find search
        search_text = await page.query_selector('text=/Search.*apps/')
        if search_text:
            print("   Found 'Search X apps' text, clicking...")
            await search_text.click()
            await asyncio.sleep(2)
            await page.screenshot(path=os.path.join(BASE_DIR, "debug_2_after_click.png"))
            print("   Screenshot: debug_2_after_click.png")
        
        print("4. Looking for input fields...")
        inputs = await page.query_selector_all('input')
        print(f"   Found {len(inputs)} inputs")
        
        for i, inp in enumerate(inputs):
            try:
                is_visible = await inp.is_visible()
                if is_visible:
                    print(f"   Input {i} is visible, typing 'Cal AI'...")
                    await inp.fill('Cal AI')
                    await asyncio.sleep(2)
                    await page.screenshot(path=os.path.join(BASE_DIR, "debug_3_typed.png"))
                    print("   Screenshot: debug_3_typed.png")
                    
                    # Press Enter
                    await page.keyboard.press('Enter')
                    await asyncio.sleep(3)
                    break
            except Exception as e:
                print(f"   Input {i} error: {e}")
        
        # Final screenshot
        await page.screenshot(path=os.path.join(BASE_DIR, "debug_4_final.png"))
        print("5. Screenshot: debug_4_final.png")
        
        # Check current URL
        print(f"   Current URL: {page.url}")
        
        # List all app links
        links = await page.query_selector_all('a[href*="/apps/"]')
        print(f"6. Found {len(links)} app links")
        for i, link in enumerate(links[:5]):
            href = await link.get_attribute('href')
            text = (await link.inner_text()).strip()[:40]
            print(f"   {i}: {text} -> {href[:50]}...")

if __name__ == "__main__":
    asyncio.run(debug_search())


















