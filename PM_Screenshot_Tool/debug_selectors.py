# -*- coding: utf-8 -*-
import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Should already be on search results page
        print(f"Current URL: {page.url}")
        
        # Close popup first
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Try different selectors
        selectors_to_try = [
            'a[href*="/apps/"]',
            'a[href*="/app/"]',
            'a[href*="cal-ai"]',
            '[class*="app-card"]',
            '[class*="AppCard"]',
            'article',
            'article a',
            '.grid a',
            'a[href*="screensdesign"]'
        ]
        
        for sel in selectors_to_try:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"\n{sel}: {len(elements)} found")
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute('href')
                        text = (await el.inner_text())[:50].replace('\n', ' ')
                        print(f"  {i}: {text}... -> {href}")
            except Exception as e:
                print(f"{sel}: Error - {e}")
        
        # Try to get all links
        print("\n\nAll links on page:")
        all_links = await page.query_selector_all('a')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'cal' in href.lower():
                text = (await link.inner_text())[:30]
                print(f"  {text} -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_selectors())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Should already be on search results page
        print(f"Current URL: {page.url}")
        
        # Close popup first
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Try different selectors
        selectors_to_try = [
            'a[href*="/apps/"]',
            'a[href*="/app/"]',
            'a[href*="cal-ai"]',
            '[class*="app-card"]',
            '[class*="AppCard"]',
            'article',
            'article a',
            '.grid a',
            'a[href*="screensdesign"]'
        ]
        
        for sel in selectors_to_try:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"\n{sel}: {len(elements)} found")
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute('href')
                        text = (await el.inner_text())[:50].replace('\n', ' ')
                        print(f"  {i}: {text}... -> {href}")
            except Exception as e:
                print(f"{sel}: Error - {e}")
        
        # Try to get all links
        print("\n\nAll links on page:")
        all_links = await page.query_selector_all('a')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'cal' in href.lower():
                text = (await link.inner_text())[:30]
                print(f"  {text} -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_selectors())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Should already be on search results page
        print(f"Current URL: {page.url}")
        
        # Close popup first
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Try different selectors
        selectors_to_try = [
            'a[href*="/apps/"]',
            'a[href*="/app/"]',
            'a[href*="cal-ai"]',
            '[class*="app-card"]',
            '[class*="AppCard"]',
            'article',
            'article a',
            '.grid a',
            'a[href*="screensdesign"]'
        ]
        
        for sel in selectors_to_try:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"\n{sel}: {len(elements)} found")
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute('href')
                        text = (await el.inner_text())[:50].replace('\n', ' ')
                        print(f"  {i}: {text}... -> {href}")
            except Exception as e:
                print(f"{sel}: Error - {e}")
        
        # Try to get all links
        print("\n\nAll links on page:")
        all_links = await page.query_selector_all('a')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'cal' in href.lower():
                text = (await link.inner_text())[:30]
                print(f"  {text} -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_selectors())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Should already be on search results page
        print(f"Current URL: {page.url}")
        
        # Close popup first
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Try different selectors
        selectors_to_try = [
            'a[href*="/apps/"]',
            'a[href*="/app/"]',
            'a[href*="cal-ai"]',
            '[class*="app-card"]',
            '[class*="AppCard"]',
            'article',
            'article a',
            '.grid a',
            'a[href*="screensdesign"]'
        ]
        
        for sel in selectors_to_try:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"\n{sel}: {len(elements)} found")
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute('href')
                        text = (await el.inner_text())[:50].replace('\n', ' ')
                        print(f"  {i}: {text}... -> {href}")
            except Exception as e:
                print(f"{sel}: Error - {e}")
        
        # Try to get all links
        print("\n\nAll links on page:")
        all_links = await page.query_selector_all('a')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'cal' in href.lower():
                text = (await link.inner_text())[:30]
                print(f"  {text} -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_selectors())



import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Should already be on search results page
        print(f"Current URL: {page.url}")
        
        # Close popup first
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Try different selectors
        selectors_to_try = [
            'a[href*="/apps/"]',
            'a[href*="/app/"]',
            'a[href*="cal-ai"]',
            '[class*="app-card"]',
            '[class*="AppCard"]',
            'article',
            'article a',
            '.grid a',
            'a[href*="screensdesign"]'
        ]
        
        for sel in selectors_to_try:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"\n{sel}: {len(elements)} found")
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute('href')
                        text = (await el.inner_text())[:50].replace('\n', ' ')
                        print(f"  {i}: {text}... -> {href}")
            except Exception as e:
                print(f"{sel}: Error - {e}")
        
        # Try to get all links
        print("\n\nAll links on page:")
        all_links = await page.query_selector_all('a')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'cal' in href.lower():
                text = (await link.inner_text())[:30]
                print(f"  {text} -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_selectors())


import asyncio
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright

async def debug_selectors():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp('http://127.0.0.1:9222')
        context = browser.contexts[0]
        page = context.pages[0]
        
        # Should already be on search results page
        print(f"Current URL: {page.url}")
        
        # Close popup first
        await page.keyboard.press('Escape')
        await asyncio.sleep(1)
        
        # Try different selectors
        selectors_to_try = [
            'a[href*="/apps/"]',
            'a[href*="/app/"]',
            'a[href*="cal-ai"]',
            '[class*="app-card"]',
            '[class*="AppCard"]',
            'article',
            'article a',
            '.grid a',
            'a[href*="screensdesign"]'
        ]
        
        for sel in selectors_to_try:
            try:
                elements = await page.query_selector_all(sel)
                if elements:
                    print(f"\n{sel}: {len(elements)} found")
                    for i, el in enumerate(elements[:3]):
                        href = await el.get_attribute('href')
                        text = (await el.inner_text())[:50].replace('\n', ' ')
                        print(f"  {i}: {text}... -> {href}")
            except Exception as e:
                print(f"{sel}: Error - {e}")
        
        # Try to get all links
        print("\n\nAll links on page:")
        all_links = await page.query_selector_all('a')
        for link in all_links:
            href = await link.get_attribute('href')
            if href and 'cal' in href.lower():
                text = (await link.inner_text())[:30]
                print(f"  {text} -> {href}")

if __name__ == "__main__":
    asyncio.run(debug_selectors())


















