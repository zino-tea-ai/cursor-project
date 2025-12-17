# -*- coding: utf-8 -*-
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def find_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"URL: {page.url}")
        
        # Find elements containing "Cal AI"
        cal_elements = await page.query_selector_all('text=/Cal AI/')
        print(f"Found {len(cal_elements)} 'Cal AI' elements")
        
        for i, el in enumerate(cal_elements[:8]):
            try:
                # Get element info
                tag = await el.evaluate('el => el.tagName')
                text = (await el.inner_text()).strip()[:80]
                print(f"\n{i}: <{tag}> {text}")
                
                # Try to find closest anchor
                closest_a = await el.evaluate('el => { const a = el.closest("a"); return a ? a.href : null; }')
                if closest_a:
                    print(f"   Closest <a> href: {closest_a}")
                
                # Try parent chain
                parent_info = await el.evaluate('''el => {
                    let info = [];
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        info.push(current.tagName + (current.href ? " href=" + current.href : ""));
                    }
                    return info;
                }''')
                print(f"   Parents: {' > '.join(parent_info[:3])}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Also try to find app cards by structure
        print("\n\nLooking for app cards...")
        cards = await page.query_selector_all('[class*="card"], [class*="Card"], article, .app, .result')
        print(f"Found {len(cards)} potential cards")
        
        for card in cards[:3]:
            try:
                text = (await card.inner_text())[:100].replace('\n', ' ')
                print(f"  Card: {text}...")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(find_cal_ai())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def find_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"URL: {page.url}")
        
        # Find elements containing "Cal AI"
        cal_elements = await page.query_selector_all('text=/Cal AI/')
        print(f"Found {len(cal_elements)} 'Cal AI' elements")
        
        for i, el in enumerate(cal_elements[:8]):
            try:
                # Get element info
                tag = await el.evaluate('el => el.tagName')
                text = (await el.inner_text()).strip()[:80]
                print(f"\n{i}: <{tag}> {text}")
                
                # Try to find closest anchor
                closest_a = await el.evaluate('el => { const a = el.closest("a"); return a ? a.href : null; }')
                if closest_a:
                    print(f"   Closest <a> href: {closest_a}")
                
                # Try parent chain
                parent_info = await el.evaluate('''el => {
                    let info = [];
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        info.push(current.tagName + (current.href ? " href=" + current.href : ""));
                    }
                    return info;
                }''')
                print(f"   Parents: {' > '.join(parent_info[:3])}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Also try to find app cards by structure
        print("\n\nLooking for app cards...")
        cards = await page.query_selector_all('[class*="card"], [class*="Card"], article, .app, .result')
        print(f"Found {len(cards)} potential cards")
        
        for card in cards[:3]:
            try:
                text = (await card.inner_text())[:100].replace('\n', ' ')
                print(f"  Card: {text}...")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(find_cal_ai())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def find_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"URL: {page.url}")
        
        # Find elements containing "Cal AI"
        cal_elements = await page.query_selector_all('text=/Cal AI/')
        print(f"Found {len(cal_elements)} 'Cal AI' elements")
        
        for i, el in enumerate(cal_elements[:8]):
            try:
                # Get element info
                tag = await el.evaluate('el => el.tagName')
                text = (await el.inner_text()).strip()[:80]
                print(f"\n{i}: <{tag}> {text}")
                
                # Try to find closest anchor
                closest_a = await el.evaluate('el => { const a = el.closest("a"); return a ? a.href : null; }')
                if closest_a:
                    print(f"   Closest <a> href: {closest_a}")
                
                # Try parent chain
                parent_info = await el.evaluate('''el => {
                    let info = [];
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        info.push(current.tagName + (current.href ? " href=" + current.href : ""));
                    }
                    return info;
                }''')
                print(f"   Parents: {' > '.join(parent_info[:3])}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Also try to find app cards by structure
        print("\n\nLooking for app cards...")
        cards = await page.query_selector_all('[class*="card"], [class*="Card"], article, .app, .result')
        print(f"Found {len(cards)} potential cards")
        
        for card in cards[:3]:
            try:
                text = (await card.inner_text())[:100].replace('\n', ' ')
                print(f"  Card: {text}...")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(find_cal_ai())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def find_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"URL: {page.url}")
        
        # Find elements containing "Cal AI"
        cal_elements = await page.query_selector_all('text=/Cal AI/')
        print(f"Found {len(cal_elements)} 'Cal AI' elements")
        
        for i, el in enumerate(cal_elements[:8]):
            try:
                # Get element info
                tag = await el.evaluate('el => el.tagName')
                text = (await el.inner_text()).strip()[:80]
                print(f"\n{i}: <{tag}> {text}")
                
                # Try to find closest anchor
                closest_a = await el.evaluate('el => { const a = el.closest("a"); return a ? a.href : null; }')
                if closest_a:
                    print(f"   Closest <a> href: {closest_a}")
                
                # Try parent chain
                parent_info = await el.evaluate('''el => {
                    let info = [];
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        info.push(current.tagName + (current.href ? " href=" + current.href : ""));
                    }
                    return info;
                }''')
                print(f"   Parents: {' > '.join(parent_info[:3])}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Also try to find app cards by structure
        print("\n\nLooking for app cards...")
        cards = await page.query_selector_all('[class*="card"], [class*="Card"], article, .app, .result')
        print(f"Found {len(cards)} potential cards")
        
        for card in cards[:3]:
            try:
                text = (await card.inner_text())[:100].replace('\n', ' ')
                print(f"  Card: {text}...")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(find_cal_ai())



import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def find_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"URL: {page.url}")
        
        # Find elements containing "Cal AI"
        cal_elements = await page.query_selector_all('text=/Cal AI/')
        print(f"Found {len(cal_elements)} 'Cal AI' elements")
        
        for i, el in enumerate(cal_elements[:8]):
            try:
                # Get element info
                tag = await el.evaluate('el => el.tagName')
                text = (await el.inner_text()).strip()[:80]
                print(f"\n{i}: <{tag}> {text}")
                
                # Try to find closest anchor
                closest_a = await el.evaluate('el => { const a = el.closest("a"); return a ? a.href : null; }')
                if closest_a:
                    print(f"   Closest <a> href: {closest_a}")
                
                # Try parent chain
                parent_info = await el.evaluate('''el => {
                    let info = [];
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        info.push(current.tagName + (current.href ? " href=" + current.href : ""));
                    }
                    return info;
                }''')
                print(f"   Parents: {' > '.join(parent_info[:3])}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Also try to find app cards by structure
        print("\n\nLooking for app cards...")
        cards = await page.query_selector_all('[class*="card"], [class*="Card"], article, .app, .result')
        print(f"Found {len(cards)} potential cards")
        
        for card in cards[:3]:
            try:
                text = (await card.inner_text())[:100].replace('\n', ' ')
                print(f"  Card: {text}...")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(find_cal_ai())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def find_cal_ai():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Close popup
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        print(f"URL: {page.url}")
        
        # Find elements containing "Cal AI"
        cal_elements = await page.query_selector_all('text=/Cal AI/')
        print(f"Found {len(cal_elements)} 'Cal AI' elements")
        
        for i, el in enumerate(cal_elements[:8]):
            try:
                # Get element info
                tag = await el.evaluate('el => el.tagName')
                text = (await el.inner_text()).strip()[:80]
                print(f"\n{i}: <{tag}> {text}")
                
                # Try to find closest anchor
                closest_a = await el.evaluate('el => { const a = el.closest("a"); return a ? a.href : null; }')
                if closest_a:
                    print(f"   Closest <a> href: {closest_a}")
                
                # Try parent chain
                parent_info = await el.evaluate('''el => {
                    let info = [];
                    let current = el;
                    for (let i = 0; i < 5; i++) {
                        current = current.parentElement;
                        if (!current) break;
                        info.push(current.tagName + (current.href ? " href=" + current.href : ""));
                    }
                    return info;
                }''')
                print(f"   Parents: {' > '.join(parent_info[:3])}")
                
            except Exception as e:
                print(f"   Error: {e}")
        
        # Also try to find app cards by structure
        print("\n\nLooking for app cards...")
        cards = await page.query_selector_all('[class*="card"], [class*="Card"], article, .app, .result')
        print(f"Found {len(cards)} potential cards")
        
        for card in cards[:3]:
            try:
                text = (await card.inner_text())[:100].replace('\n', ' ')
                print(f"  Card: {text}...")
            except:
                pass

if __name__ == "__main__":
    asyncio.run(find_cal_ai())


















