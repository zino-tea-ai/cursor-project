# -*- coding: utf-8 -*-
import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from smart_batch_download import SmartBatchDownloader

async def test():
    downloader = SmartBatchDownloader()
    downloader.load_competitors()
    
    if await downloader.init_browser():
        # Test searching for Cal AI
        results = await downloader.search_product('Cal AI')
        print(f"\nResults found: {len(results)}")
        for r in results[:10]:
            print(f"  - {r['name']}")
            print(f"    URL: {r['url'][:70]}...")
        await downloader.close()
    else:
        print("Failed to connect to browser")

if __name__ == "__main__":
    asyncio.run(test())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from smart_batch_download import SmartBatchDownloader

async def test():
    downloader = SmartBatchDownloader()
    downloader.load_competitors()
    
    if await downloader.init_browser():
        # Test searching for Cal AI
        results = await downloader.search_product('Cal AI')
        print(f"\nResults found: {len(results)}")
        for r in results[:10]:
            print(f"  - {r['name']}")
            print(f"    URL: {r['url'][:70]}...")
        await downloader.close()
    else:
        print("Failed to connect to browser")

if __name__ == "__main__":
    asyncio.run(test())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from smart_batch_download import SmartBatchDownloader

async def test():
    downloader = SmartBatchDownloader()
    downloader.load_competitors()
    
    if await downloader.init_browser():
        # Test searching for Cal AI
        results = await downloader.search_product('Cal AI')
        print(f"\nResults found: {len(results)}")
        for r in results[:10]:
            print(f"  - {r['name']}")
            print(f"    URL: {r['url'][:70]}...")
        await downloader.close()
    else:
        print("Failed to connect to browser")

if __name__ == "__main__":
    asyncio.run(test())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from smart_batch_download import SmartBatchDownloader

async def test():
    downloader = SmartBatchDownloader()
    downloader.load_competitors()
    
    if await downloader.init_browser():
        # Test searching for Cal AI
        results = await downloader.search_product('Cal AI')
        print(f"\nResults found: {len(results)}")
        for r in results[:10]:
            print(f"  - {r['name']}")
            print(f"    URL: {r['url'][:70]}...")
        await downloader.close()
    else:
        print("Failed to connect to browser")

if __name__ == "__main__":
    asyncio.run(test())



import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from smart_batch_download import SmartBatchDownloader

async def test():
    downloader = SmartBatchDownloader()
    downloader.load_competitors()
    
    if await downloader.init_browser():
        # Test searching for Cal AI
        results = await downloader.search_product('Cal AI')
        print(f"\nResults found: {len(results)}")
        for r in results[:10]:
            print(f"  - {r['name']}")
            print(f"    URL: {r['url'][:70]}...")
        await downloader.close()
    else:
        print("Failed to connect to browser")

if __name__ == "__main__":
    asyncio.run(test())


import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from smart_batch_download import SmartBatchDownloader

async def test():
    downloader = SmartBatchDownloader()
    downloader.load_competitors()
    
    if await downloader.init_browser():
        # Test searching for Cal AI
        results = await downloader.search_product('Cal AI')
        print(f"\nResults found: {len(results)}")
        for r in results[:10]:
            print(f"  - {r['name']}")
            print(f"    URL: {r['url'][:70]}...")
        await downloader.close()
    else:
        print("Failed to connect to browser")

if __name__ == "__main__":
    asyncio.run(test())


















