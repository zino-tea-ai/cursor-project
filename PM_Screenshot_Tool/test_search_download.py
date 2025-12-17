# -*- coding: utf-8 -*-
"""
Test search -> enter app page -> download flow
"""
import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_batch_download import SmartBatchDownloader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def test_cal_ai():
    """Test search and download for Cal AI"""
    
    print("="*60)
    print("  Testing Search -> App Page -> Download")
    print("="*60)
    
    downloader = SmartBatchDownloader()
    
    cal_ai_product = {
        "app_name": "Cal AI - Calorie Tracker",
        "publisher": "Viral Development",
        "category": "Health & Fitness"
    }
    
    # Initialize browser
    if not await downloader.init_browser():
        print("[ERROR] Could not connect to browser")
        return
    
    try:
        # Clean old project
        import shutil
        old_dir = os.path.join(BASE_DIR, "projects", "Cal_AI_-_Calorie_Tracker_Analysis")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"Cleaned old project folder")
        
        result = await downloader.process_product(cal_ai_product)
        
        print("\n" + "="*60)
        print("  Result")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result['status'] == 'success':
            # Check downloaded files
            screens_dir = os.path.join(result['project_dir'], 'Screens')
            if os.path.exists(screens_dir):
                files = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
                print(f"\n  Downloaded {len(files)} screenshots")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(test_cal_ai())


"""
Test search -> enter app page -> download flow
"""
import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_batch_download import SmartBatchDownloader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def test_cal_ai():
    """Test search and download for Cal AI"""
    
    print("="*60)
    print("  Testing Search -> App Page -> Download")
    print("="*60)
    
    downloader = SmartBatchDownloader()
    
    cal_ai_product = {
        "app_name": "Cal AI - Calorie Tracker",
        "publisher": "Viral Development",
        "category": "Health & Fitness"
    }
    
    # Initialize browser
    if not await downloader.init_browser():
        print("[ERROR] Could not connect to browser")
        return
    
    try:
        # Clean old project
        import shutil
        old_dir = os.path.join(BASE_DIR, "projects", "Cal_AI_-_Calorie_Tracker_Analysis")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"Cleaned old project folder")
        
        result = await downloader.process_product(cal_ai_product)
        
        print("\n" + "="*60)
        print("  Result")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result['status'] == 'success':
            # Check downloaded files
            screens_dir = os.path.join(result['project_dir'], 'Screens')
            if os.path.exists(screens_dir):
                files = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
                print(f"\n  Downloaded {len(files)} screenshots")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(test_cal_ai())


"""
Test search -> enter app page -> download flow
"""
import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_batch_download import SmartBatchDownloader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def test_cal_ai():
    """Test search and download for Cal AI"""
    
    print("="*60)
    print("  Testing Search -> App Page -> Download")
    print("="*60)
    
    downloader = SmartBatchDownloader()
    
    cal_ai_product = {
        "app_name": "Cal AI - Calorie Tracker",
        "publisher": "Viral Development",
        "category": "Health & Fitness"
    }
    
    # Initialize browser
    if not await downloader.init_browser():
        print("[ERROR] Could not connect to browser")
        return
    
    try:
        # Clean old project
        import shutil
        old_dir = os.path.join(BASE_DIR, "projects", "Cal_AI_-_Calorie_Tracker_Analysis")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"Cleaned old project folder")
        
        result = await downloader.process_product(cal_ai_product)
        
        print("\n" + "="*60)
        print("  Result")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result['status'] == 'success':
            # Check downloaded files
            screens_dir = os.path.join(result['project_dir'], 'Screens')
            if os.path.exists(screens_dir):
                files = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
                print(f"\n  Downloaded {len(files)} screenshots")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(test_cal_ai())


"""
Test search -> enter app page -> download flow
"""
import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_batch_download import SmartBatchDownloader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def test_cal_ai():
    """Test search and download for Cal AI"""
    
    print("="*60)
    print("  Testing Search -> App Page -> Download")
    print("="*60)
    
    downloader = SmartBatchDownloader()
    
    cal_ai_product = {
        "app_name": "Cal AI - Calorie Tracker",
        "publisher": "Viral Development",
        "category": "Health & Fitness"
    }
    
    # Initialize browser
    if not await downloader.init_browser():
        print("[ERROR] Could not connect to browser")
        return
    
    try:
        # Clean old project
        import shutil
        old_dir = os.path.join(BASE_DIR, "projects", "Cal_AI_-_Calorie_Tracker_Analysis")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"Cleaned old project folder")
        
        result = await downloader.process_product(cal_ai_product)
        
        print("\n" + "="*60)
        print("  Result")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result['status'] == 'success':
            # Check downloaded files
            screens_dir = os.path.join(result['project_dir'], 'Screens')
            if os.path.exists(screens_dir):
                files = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
                print(f"\n  Downloaded {len(files)} screenshots")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(test_cal_ai())



"""
Test search -> enter app page -> download flow
"""
import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_batch_download import SmartBatchDownloader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def test_cal_ai():
    """Test search and download for Cal AI"""
    
    print("="*60)
    print("  Testing Search -> App Page -> Download")
    print("="*60)
    
    downloader = SmartBatchDownloader()
    
    cal_ai_product = {
        "app_name": "Cal AI - Calorie Tracker",
        "publisher": "Viral Development",
        "category": "Health & Fitness"
    }
    
    # Initialize browser
    if not await downloader.init_browser():
        print("[ERROR] Could not connect to browser")
        return
    
    try:
        # Clean old project
        import shutil
        old_dir = os.path.join(BASE_DIR, "projects", "Cal_AI_-_Calorie_Tracker_Analysis")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"Cleaned old project folder")
        
        result = await downloader.process_product(cal_ai_product)
        
        print("\n" + "="*60)
        print("  Result")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result['status'] == 'success':
            # Check downloaded files
            screens_dir = os.path.join(result['project_dir'], 'Screens')
            if os.path.exists(screens_dir):
                files = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
                print(f"\n  Downloaded {len(files)} screenshots")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(test_cal_ai())


"""
Test search -> enter app page -> download flow
"""
import os
import sys
import asyncio
import json

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smart_batch_download import SmartBatchDownloader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def test_cal_ai():
    """Test search and download for Cal AI"""
    
    print("="*60)
    print("  Testing Search -> App Page -> Download")
    print("="*60)
    
    downloader = SmartBatchDownloader()
    
    cal_ai_product = {
        "app_name": "Cal AI - Calorie Tracker",
        "publisher": "Viral Development",
        "category": "Health & Fitness"
    }
    
    # Initialize browser
    if not await downloader.init_browser():
        print("[ERROR] Could not connect to browser")
        return
    
    try:
        # Clean old project
        import shutil
        old_dir = os.path.join(BASE_DIR, "projects", "Cal_AI_-_Calorie_Tracker_Analysis")
        if os.path.exists(old_dir):
            shutil.rmtree(old_dir)
            print(f"Cleaned old project folder")
        
        result = await downloader.process_product(cal_ai_product)
        
        print("\n" + "="*60)
        print("  Result")
        print("="*60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result['status'] == 'success':
            # Check downloaded files
            screens_dir = os.path.join(result['project_dir'], 'Screens')
            if os.path.exists(screens_dir):
                files = [f for f in os.listdir(screens_dir) if f.endswith('.png')]
                print(f"\n  Downloaded {len(files)} screenshots")
        
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(test_cal_ai())


















