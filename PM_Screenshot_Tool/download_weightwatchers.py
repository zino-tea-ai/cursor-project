# -*- coding: utf-8 -*-
"""
下载 WeightWatchers 截图的脚本
直接从 screensdesign.com API 获取截图列表并下载
"""
import os
import sys
import requests
from io import BytesIO
from PIL import Image
import json

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE_DIR, "downloads_2024", "WeightWatchers")
TARGET_WIDTH = 402  # 标准宽度

# WeightWatchers 的 App ID
APP_ID = 932
APP_VIDEO_ID = 942

def download_weightwatchers():
    """下载 WeightWatchers 截图"""
    
    print(f"\n{'='*60}")
    print("  WeightWatchers 截图下载器")
    print(f"{'='*60}")
    
    # 确保目录存在
    os.makedirs(TARGET_DIR, exist_ok=True)
    
    # 获取截图列表
    print("\n1. 获取截图列表...")
    api_url = f"https://api.screensdesign.com/v1/appvideoscreens/?page_size=200&app={APP_ID}&order=timestamp&app_video={APP_VIDEO_ID}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/',
        'Accept': 'application/json'
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"   获取截图列表失败: {e}")
        return 0
    
    # 解析截图列表
    screens = data.get('results', [])
    print(f"   找到 {len(screens)} 个截图")
    
    if not screens:
        print("   没有找到截图！")
        return 0
    
    # 保存 manifest
    manifest_path = os.path.join(TARGET_DIR, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"   已保存 manifest: {manifest_path}")
    
    # 下载截图
    print("\n2. 开始下载截图...")
    downloaded = 0
    
    for idx, screen in enumerate(screens, 1):
        try:
            # 获取图片 URL - 在 screen 字段中
            image_url = screen.get('screen')
            
            if not image_url:
                print(f"   跳过 {idx}: 无图片 URL")
                continue
            
            # 下载图片
            img_response = requests.get(image_url, headers=headers, timeout=60)
            
            if img_response.status_code == 200:
                img = Image.open(BytesIO(img_response.content))
                
                # 转换颜色模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    img = img.convert('RGB')
                
                # 调整尺寸
                if img.width > 0:
                    ratio = TARGET_WIDTH / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                
                # 保存 - 使用 0001.png 格式
                filename = f"{idx:04d}.png"
                filepath = os.path.join(TARGET_DIR, filename)
                img.save(filepath, "PNG", optimize=True)
                
                downloaded += 1
                if downloaded % 10 == 0:
                    print(f"   已下载 {downloaded}/{len(screens)}...")
            else:
                print(f"   下载失败 {idx}: HTTP {img_response.status_code}")
                        
        except Exception as e:
            print(f"   下载 {idx} 失败: {e}")
            continue
    
    print(f"\n{'='*60}")
    print(f"  完成！共下载 {downloaded} 张截图")
    print(f"  保存位置: {TARGET_DIR}")
    print(f"{'='*60}")
    
    return downloaded

if __name__ == "__main__":
    download_weightwatchers()


