# -*- coding: utf-8 -*-
"""
下载 Yazio 截图的脚本
App ID: 869
Video ID: 2668
URL: https://screensdesign.com/apps/yazio-calorie-counter-diet/?ts=0&vt=1&id=869
API: https://api.screensdesign.com/v1/appvideoscreens/?page_size=200&app=869&order=timestamp&app_video=2668
"""
import os
import sys
import requests
from io import BytesIO
from PIL import Image
import json

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE_DIR, "downloads_2024", "Yazio")
TARGET_WIDTH = 402
APP_ID = 869
VIDEO_ID = 2668

def download_screenshots():
    """下载截图"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': 'https://screensdesign.com/',
        'Origin': 'https://screensdesign.com'
    }
    
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 清理旧的缩略图缓存
    thumb_dir = os.path.join(TARGET_DIR, "thumbs_small")
    if os.path.exists(thumb_dir):
        import shutil
        shutil.rmtree(thumb_dir)
        print("已清理缩略图缓存")
    
    # 获取截图列表 - 使用正确的 API
    url = f"https://api.screensdesign.com/v1/appvideoscreens/?page_size=500&app={APP_ID}&order=timestamp&app_video={VIDEO_ID}"
    
    print(f"获取截图列表: {url}")
    
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"响应状态: {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"响应内容: {resp.text[:500]}")
            return 0
            
        data = resp.json()
        screens = data.get('results', [])
        total_count = data.get('count', len(screens))
        print(f"找到 {len(screens)} 个截图 (总数: {total_count})")
        
        if not screens:
            print("没有找到截图！")
            return 0
        
        # 保存 manifest
        with open(os.path.join(TARGET_DIR, "manifest.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("已保存 manifest.json")
        
        # 删除现有的 png 文件
        for f in os.listdir(TARGET_DIR):
            if f.endswith('.png') and f[0].isdigit():
                os.remove(os.path.join(TARGET_DIR, f))
        print("已清理旧截图")
        
        # 下载
        downloaded = 0
        failed = 0
        for idx, screen in enumerate(screens, 1):
            image_url = screen.get('screen')
            if not image_url:
                continue
            
            filename = f"{idx:04d}.png"
            filepath = os.path.join(TARGET_DIR, filename)
            
            try:
                img_resp = requests.get(image_url, headers=headers, timeout=60)
                if img_resp.status_code == 200:
                    img = Image.open(BytesIO(img_resp.content))
                    if img.mode in ('RGBA', 'P', 'LA'):
                        img = img.convert('RGB')
                    
                    if img.width > 0:
                        ratio = TARGET_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                    
                    img.save(filepath, "PNG", optimize=True)
                    downloaded += 1
                    
                    if downloaded % 20 == 0:
                        print(f"已下载 {downloaded}/{len(screens)}...")
                else:
                    failed += 1
                    print(f"下载 {idx} 失败: HTTP {img_resp.status_code}")
            except Exception as e:
                failed += 1
                print(f"下载 {idx} 失败: {e}")
        
        print(f"\n{'='*60}")
        print(f"完成！下载了 {downloaded} 张截图到 {TARGET_DIR}")
        if failed > 0:
            print(f"失败: {failed} 张")
        print(f"{'='*60}")
        return downloaded
        
    except Exception as e:
        print(f"获取截图列表失败: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    print("="*60)
    print(f"  Yazio 截图下载器")
    print(f"  App ID: {APP_ID}, Video ID: {VIDEO_ID}")
    print("="*60)
    
    download_screenshots()

if __name__ == "__main__":
    main()
