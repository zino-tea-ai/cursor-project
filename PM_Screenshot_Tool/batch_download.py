# -*- coding: utf-8 -*-
"""
批量下载截图工具
依次下载多个产品的截图并自动分类
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 待下载的产品列表 - 用户确认的正确URL
PRODUCTS = [
    {
        "name": "Strava_Analysis",
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/?ts=0&vt=1&id=961"
    },
    {
        "name": "Flo_Analysis",
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/?ts=0&vt=1&id=877"
    },
    {
        "name": "Calm_Analysis",
        "url": "https://screensdesign.com/apps/calm/?ts=0&vt=1&id=883"
    },
    {
        "name": "Runna_Analysis",
        "url": "https://screensdesign.com/apps/runna-running-training-plans/?ts=0&vt=1&id=902"
    }
]

def connect_to_chrome():
    """连接到Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接Chrome: {e}")
        return None

def download_product_screenshots(driver, product_name, url):
    """下载单个产品的所有截图"""
    print(f"\n{'='*60}")
    print(f"下载: {product_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # 创建项目目录
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    try:
        # 访问页面
        print("[1/4] 访问页面...")
        driver.get(url)
        time.sleep(3)
        
        # 滚动加载所有图片
        print("[2/4] 滚动加载图片...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"      滚动 {scroll_count}次, 高度: {new_height}px")
            if new_height == last_height or scroll_count > 20:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 收集图片URL
        print("[3/4] 收集图片URL...")
        image_urls = []
        
        # 多种选择器尝试
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']", 
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            ".screen-item img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src") or elem.get_attribute("data-src")
                    if src and src.startswith("http"):
                        # 过滤非截图图片
                        skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button']
                        if not any(kw in src.lower() for kw in skip_keywords):
                            # 检查图片尺寸（如果可以）
                            width = elem.get_attribute("width") or elem.get_attribute("naturalWidth")
                            if width:
                                try:
                                    if int(width) < 100:
                                        continue
                                except:
                                    pass
                            if src not in image_urls:
                                image_urls.append(src)
            except:
                continue
        
        print(f"      找到 {len(image_urls)} 个图片URL")
        
        if not image_urls:
            print("[ERROR] 未找到任何图片!")
            return 0
        
        # 下载并处理图片
        print("[4/4] 下载并处理图片...")
        success_count = 0
        
        for i, img_url in enumerate(image_urls, 1):
            try:
                # 下载
                response = requests.get(img_url, timeout=30)
                img = Image.open(BytesIO(response.content))
                
                # 检查是否是合理的截图尺寸
                if img.width < 200 or img.height < 200:
                    continue
                
                # 转换模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整尺寸
                ratio = TARGET_WIDTH / img.width
                new_height = int(img.height * ratio)
                img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                # 保存
                filename = f"Screen_{success_count+1:03d}.png"
                filepath = os.path.join(downloads_path, filename)
                img_resized.save(filepath, 'PNG', optimize=True)
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"      已下载: {success_count}张")
                    
            except Exception as e:
                continue
        
        print(f"\n[完成] {product_name}: 成功下载 {success_count} 张截图")
        return success_count
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return 0

def classify_screenshots(product_name):
    """对截图进行简单分类"""
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        return 0
    
    # 清空/创建Screens目录
    if os.path.exists(screens_path):
        import shutil
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        return 0
    
    # 基于数量的智能分类
    # 根据经验，大多数App的截图分布大致为：
    # - Onboarding: 前30%
    # - Paywall: 5-10%
    # - Main功能: 60%
    
    categories = []
    
    if total >= 50:
        # 大量截图，详细分类
        categories = [
            ("01_Launch", 1, min(2, total)),
            ("02_Onboarding", 3, int(total * 0.25)),
            ("03_Paywall", int(total * 0.25) + 1, int(total * 0.35)),
            ("04_Main", int(total * 0.35) + 1, int(total * 0.6)),
            ("05_Features", int(total * 0.6) + 1, int(total * 0.8)),
            ("06_Settings", int(total * 0.8) + 1, total),
        ]
    elif total >= 20:
        # 中等数量
        categories = [
            ("01_Onboarding", 1, int(total * 0.3)),
            ("02_Paywall", int(total * 0.3) + 1, int(total * 0.4)),
            ("03_Main", int(total * 0.4) + 1, int(total * 0.7)),
            ("04_Other", int(total * 0.7) + 1, total),
        ]
    else:
        # 少量截图
        categories = [
            ("01_Onboarding", 1, int(total * 0.4)),
            ("02_Main", int(total * 0.4) + 1, total),
        ]
    
    # 复制并重命名
    import shutil
    classified_count = 0
    
    for category_name, start, end in categories:
        for i in range(start - 1, min(end, total)):
            if i < len(screenshots):
                src = os.path.join(downloads_path, screenshots[i])
                step_num = i - (start - 1) + 1
                new_name = f"{category_name}_{step_num:02d}.png"
                dst = os.path.join(screens_path, new_name)
                shutil.copy2(src, dst)
                classified_count += 1
    
    return classified_count

def main():
    print("=" * 60)
    print("批量截图采集工具")
    print("=" * 60)
    print(f"待采集产品: {len(PRODUCTS)}个")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print()
    
    driver = connect_to_chrome()
    if not driver:
        print("\n请确保Chrome以调试模式运行:")
        print('chrome.exe --remote-debugging-port=9222')
        return
    
    results = []
    
    for product in PRODUCTS:
        count = download_product_screenshots(driver, product['name'], product['url'])
        
        if count > 0:
            # 简单分类
            print(f"\n[分类] 正在分类 {product['name']}...")
            classified = classify_screenshots(product['name'])
            print(f"      已分类: {classified}张")
        
        results.append({
            "name": product['name'],
            "count": count
        })
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("采集完成 - 汇总报告")
    print("=" * 60)
    
    total_screenshots = 0
    for r in results:
        status = "[OK]" if r['count'] > 0 else "[--]"
        print(f"{status} {r['name']}: {r['count']}张")
        total_screenshots += r['count']
    
    print(f"\n总计: {total_screenshots}张截图")
    print(f"保存位置: {PROJECTS_DIR}")

if __name__ == "__main__":
    main()







"""
批量下载截图工具
依次下载多个产品的截图并自动分类
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 待下载的产品列表 - 用户确认的正确URL
PRODUCTS = [
    {
        "name": "Strava_Analysis",
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/?ts=0&vt=1&id=961"
    },
    {
        "name": "Flo_Analysis",
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/?ts=0&vt=1&id=877"
    },
    {
        "name": "Calm_Analysis",
        "url": "https://screensdesign.com/apps/calm/?ts=0&vt=1&id=883"
    },
    {
        "name": "Runna_Analysis",
        "url": "https://screensdesign.com/apps/runna-running-training-plans/?ts=0&vt=1&id=902"
    }
]

def connect_to_chrome():
    """连接到Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接Chrome: {e}")
        return None

def download_product_screenshots(driver, product_name, url):
    """下载单个产品的所有截图"""
    print(f"\n{'='*60}")
    print(f"下载: {product_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # 创建项目目录
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    try:
        # 访问页面
        print("[1/4] 访问页面...")
        driver.get(url)
        time.sleep(3)
        
        # 滚动加载所有图片
        print("[2/4] 滚动加载图片...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"      滚动 {scroll_count}次, 高度: {new_height}px")
            if new_height == last_height or scroll_count > 20:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 收集图片URL
        print("[3/4] 收集图片URL...")
        image_urls = []
        
        # 多种选择器尝试
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']", 
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            ".screen-item img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src") or elem.get_attribute("data-src")
                    if src and src.startswith("http"):
                        # 过滤非截图图片
                        skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button']
                        if not any(kw in src.lower() for kw in skip_keywords):
                            # 检查图片尺寸（如果可以）
                            width = elem.get_attribute("width") or elem.get_attribute("naturalWidth")
                            if width:
                                try:
                                    if int(width) < 100:
                                        continue
                                except:
                                    pass
                            if src not in image_urls:
                                image_urls.append(src)
            except:
                continue
        
        print(f"      找到 {len(image_urls)} 个图片URL")
        
        if not image_urls:
            print("[ERROR] 未找到任何图片!")
            return 0
        
        # 下载并处理图片
        print("[4/4] 下载并处理图片...")
        success_count = 0
        
        for i, img_url in enumerate(image_urls, 1):
            try:
                # 下载
                response = requests.get(img_url, timeout=30)
                img = Image.open(BytesIO(response.content))
                
                # 检查是否是合理的截图尺寸
                if img.width < 200 or img.height < 200:
                    continue
                
                # 转换模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整尺寸
                ratio = TARGET_WIDTH / img.width
                new_height = int(img.height * ratio)
                img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                # 保存
                filename = f"Screen_{success_count+1:03d}.png"
                filepath = os.path.join(downloads_path, filename)
                img_resized.save(filepath, 'PNG', optimize=True)
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"      已下载: {success_count}张")
                    
            except Exception as e:
                continue
        
        print(f"\n[完成] {product_name}: 成功下载 {success_count} 张截图")
        return success_count
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return 0

def classify_screenshots(product_name):
    """对截图进行简单分类"""
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        return 0
    
    # 清空/创建Screens目录
    if os.path.exists(screens_path):
        import shutil
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        return 0
    
    # 基于数量的智能分类
    # 根据经验，大多数App的截图分布大致为：
    # - Onboarding: 前30%
    # - Paywall: 5-10%
    # - Main功能: 60%
    
    categories = []
    
    if total >= 50:
        # 大量截图，详细分类
        categories = [
            ("01_Launch", 1, min(2, total)),
            ("02_Onboarding", 3, int(total * 0.25)),
            ("03_Paywall", int(total * 0.25) + 1, int(total * 0.35)),
            ("04_Main", int(total * 0.35) + 1, int(total * 0.6)),
            ("05_Features", int(total * 0.6) + 1, int(total * 0.8)),
            ("06_Settings", int(total * 0.8) + 1, total),
        ]
    elif total >= 20:
        # 中等数量
        categories = [
            ("01_Onboarding", 1, int(total * 0.3)),
            ("02_Paywall", int(total * 0.3) + 1, int(total * 0.4)),
            ("03_Main", int(total * 0.4) + 1, int(total * 0.7)),
            ("04_Other", int(total * 0.7) + 1, total),
        ]
    else:
        # 少量截图
        categories = [
            ("01_Onboarding", 1, int(total * 0.4)),
            ("02_Main", int(total * 0.4) + 1, total),
        ]
    
    # 复制并重命名
    import shutil
    classified_count = 0
    
    for category_name, start, end in categories:
        for i in range(start - 1, min(end, total)):
            if i < len(screenshots):
                src = os.path.join(downloads_path, screenshots[i])
                step_num = i - (start - 1) + 1
                new_name = f"{category_name}_{step_num:02d}.png"
                dst = os.path.join(screens_path, new_name)
                shutil.copy2(src, dst)
                classified_count += 1
    
    return classified_count

def main():
    print("=" * 60)
    print("批量截图采集工具")
    print("=" * 60)
    print(f"待采集产品: {len(PRODUCTS)}个")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print()
    
    driver = connect_to_chrome()
    if not driver:
        print("\n请确保Chrome以调试模式运行:")
        print('chrome.exe --remote-debugging-port=9222')
        return
    
    results = []
    
    for product in PRODUCTS:
        count = download_product_screenshots(driver, product['name'], product['url'])
        
        if count > 0:
            # 简单分类
            print(f"\n[分类] 正在分类 {product['name']}...")
            classified = classify_screenshots(product['name'])
            print(f"      已分类: {classified}张")
        
        results.append({
            "name": product['name'],
            "count": count
        })
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("采集完成 - 汇总报告")
    print("=" * 60)
    
    total_screenshots = 0
    for r in results:
        status = "[OK]" if r['count'] > 0 else "[--]"
        print(f"{status} {r['name']}: {r['count']}张")
        total_screenshots += r['count']
    
    print(f"\n总计: {total_screenshots}张截图")
    print(f"保存位置: {PROJECTS_DIR}")

if __name__ == "__main__":
    main()







"""
批量下载截图工具
依次下载多个产品的截图并自动分类
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 待下载的产品列表 - 用户确认的正确URL
PRODUCTS = [
    {
        "name": "Strava_Analysis",
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/?ts=0&vt=1&id=961"
    },
    {
        "name": "Flo_Analysis",
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/?ts=0&vt=1&id=877"
    },
    {
        "name": "Calm_Analysis",
        "url": "https://screensdesign.com/apps/calm/?ts=0&vt=1&id=883"
    },
    {
        "name": "Runna_Analysis",
        "url": "https://screensdesign.com/apps/runna-running-training-plans/?ts=0&vt=1&id=902"
    }
]

def connect_to_chrome():
    """连接到Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接Chrome: {e}")
        return None

def download_product_screenshots(driver, product_name, url):
    """下载单个产品的所有截图"""
    print(f"\n{'='*60}")
    print(f"下载: {product_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # 创建项目目录
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    try:
        # 访问页面
        print("[1/4] 访问页面...")
        driver.get(url)
        time.sleep(3)
        
        # 滚动加载所有图片
        print("[2/4] 滚动加载图片...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"      滚动 {scroll_count}次, 高度: {new_height}px")
            if new_height == last_height or scroll_count > 20:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 收集图片URL
        print("[3/4] 收集图片URL...")
        image_urls = []
        
        # 多种选择器尝试
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']", 
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            ".screen-item img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src") or elem.get_attribute("data-src")
                    if src and src.startswith("http"):
                        # 过滤非截图图片
                        skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button']
                        if not any(kw in src.lower() for kw in skip_keywords):
                            # 检查图片尺寸（如果可以）
                            width = elem.get_attribute("width") or elem.get_attribute("naturalWidth")
                            if width:
                                try:
                                    if int(width) < 100:
                                        continue
                                except:
                                    pass
                            if src not in image_urls:
                                image_urls.append(src)
            except:
                continue
        
        print(f"      找到 {len(image_urls)} 个图片URL")
        
        if not image_urls:
            print("[ERROR] 未找到任何图片!")
            return 0
        
        # 下载并处理图片
        print("[4/4] 下载并处理图片...")
        success_count = 0
        
        for i, img_url in enumerate(image_urls, 1):
            try:
                # 下载
                response = requests.get(img_url, timeout=30)
                img = Image.open(BytesIO(response.content))
                
                # 检查是否是合理的截图尺寸
                if img.width < 200 or img.height < 200:
                    continue
                
                # 转换模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整尺寸
                ratio = TARGET_WIDTH / img.width
                new_height = int(img.height * ratio)
                img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                # 保存
                filename = f"Screen_{success_count+1:03d}.png"
                filepath = os.path.join(downloads_path, filename)
                img_resized.save(filepath, 'PNG', optimize=True)
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"      已下载: {success_count}张")
                    
            except Exception as e:
                continue
        
        print(f"\n[完成] {product_name}: 成功下载 {success_count} 张截图")
        return success_count
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return 0

def classify_screenshots(product_name):
    """对截图进行简单分类"""
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        return 0
    
    # 清空/创建Screens目录
    if os.path.exists(screens_path):
        import shutil
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        return 0
    
    # 基于数量的智能分类
    # 根据经验，大多数App的截图分布大致为：
    # - Onboarding: 前30%
    # - Paywall: 5-10%
    # - Main功能: 60%
    
    categories = []
    
    if total >= 50:
        # 大量截图，详细分类
        categories = [
            ("01_Launch", 1, min(2, total)),
            ("02_Onboarding", 3, int(total * 0.25)),
            ("03_Paywall", int(total * 0.25) + 1, int(total * 0.35)),
            ("04_Main", int(total * 0.35) + 1, int(total * 0.6)),
            ("05_Features", int(total * 0.6) + 1, int(total * 0.8)),
            ("06_Settings", int(total * 0.8) + 1, total),
        ]
    elif total >= 20:
        # 中等数量
        categories = [
            ("01_Onboarding", 1, int(total * 0.3)),
            ("02_Paywall", int(total * 0.3) + 1, int(total * 0.4)),
            ("03_Main", int(total * 0.4) + 1, int(total * 0.7)),
            ("04_Other", int(total * 0.7) + 1, total),
        ]
    else:
        # 少量截图
        categories = [
            ("01_Onboarding", 1, int(total * 0.4)),
            ("02_Main", int(total * 0.4) + 1, total),
        ]
    
    # 复制并重命名
    import shutil
    classified_count = 0
    
    for category_name, start, end in categories:
        for i in range(start - 1, min(end, total)):
            if i < len(screenshots):
                src = os.path.join(downloads_path, screenshots[i])
                step_num = i - (start - 1) + 1
                new_name = f"{category_name}_{step_num:02d}.png"
                dst = os.path.join(screens_path, new_name)
                shutil.copy2(src, dst)
                classified_count += 1
    
    return classified_count

def main():
    print("=" * 60)
    print("批量截图采集工具")
    print("=" * 60)
    print(f"待采集产品: {len(PRODUCTS)}个")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print()
    
    driver = connect_to_chrome()
    if not driver:
        print("\n请确保Chrome以调试模式运行:")
        print('chrome.exe --remote-debugging-port=9222')
        return
    
    results = []
    
    for product in PRODUCTS:
        count = download_product_screenshots(driver, product['name'], product['url'])
        
        if count > 0:
            # 简单分类
            print(f"\n[分类] 正在分类 {product['name']}...")
            classified = classify_screenshots(product['name'])
            print(f"      已分类: {classified}张")
        
        results.append({
            "name": product['name'],
            "count": count
        })
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("采集完成 - 汇总报告")
    print("=" * 60)
    
    total_screenshots = 0
    for r in results:
        status = "[OK]" if r['count'] > 0 else "[--]"
        print(f"{status} {r['name']}: {r['count']}张")
        total_screenshots += r['count']
    
    print(f"\n总计: {total_screenshots}张截图")
    print(f"保存位置: {PROJECTS_DIR}")

if __name__ == "__main__":
    main()







"""
批量下载截图工具
依次下载多个产品的截图并自动分类
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 待下载的产品列表 - 用户确认的正确URL
PRODUCTS = [
    {
        "name": "Strava_Analysis",
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/?ts=0&vt=1&id=961"
    },
    {
        "name": "Flo_Analysis",
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/?ts=0&vt=1&id=877"
    },
    {
        "name": "Calm_Analysis",
        "url": "https://screensdesign.com/apps/calm/?ts=0&vt=1&id=883"
    },
    {
        "name": "Runna_Analysis",
        "url": "https://screensdesign.com/apps/runna-running-training-plans/?ts=0&vt=1&id=902"
    }
]

def connect_to_chrome():
    """连接到Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接Chrome: {e}")
        return None

def download_product_screenshots(driver, product_name, url):
    """下载单个产品的所有截图"""
    print(f"\n{'='*60}")
    print(f"下载: {product_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # 创建项目目录
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    try:
        # 访问页面
        print("[1/4] 访问页面...")
        driver.get(url)
        time.sleep(3)
        
        # 滚动加载所有图片
        print("[2/4] 滚动加载图片...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"      滚动 {scroll_count}次, 高度: {new_height}px")
            if new_height == last_height or scroll_count > 20:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 收集图片URL
        print("[3/4] 收集图片URL...")
        image_urls = []
        
        # 多种选择器尝试
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']", 
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            ".screen-item img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src") or elem.get_attribute("data-src")
                    if src and src.startswith("http"):
                        # 过滤非截图图片
                        skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button']
                        if not any(kw in src.lower() for kw in skip_keywords):
                            # 检查图片尺寸（如果可以）
                            width = elem.get_attribute("width") or elem.get_attribute("naturalWidth")
                            if width:
                                try:
                                    if int(width) < 100:
                                        continue
                                except:
                                    pass
                            if src not in image_urls:
                                image_urls.append(src)
            except:
                continue
        
        print(f"      找到 {len(image_urls)} 个图片URL")
        
        if not image_urls:
            print("[ERROR] 未找到任何图片!")
            return 0
        
        # 下载并处理图片
        print("[4/4] 下载并处理图片...")
        success_count = 0
        
        for i, img_url in enumerate(image_urls, 1):
            try:
                # 下载
                response = requests.get(img_url, timeout=30)
                img = Image.open(BytesIO(response.content))
                
                # 检查是否是合理的截图尺寸
                if img.width < 200 or img.height < 200:
                    continue
                
                # 转换模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整尺寸
                ratio = TARGET_WIDTH / img.width
                new_height = int(img.height * ratio)
                img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                # 保存
                filename = f"Screen_{success_count+1:03d}.png"
                filepath = os.path.join(downloads_path, filename)
                img_resized.save(filepath, 'PNG', optimize=True)
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"      已下载: {success_count}张")
                    
            except Exception as e:
                continue
        
        print(f"\n[完成] {product_name}: 成功下载 {success_count} 张截图")
        return success_count
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return 0

def classify_screenshots(product_name):
    """对截图进行简单分类"""
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        return 0
    
    # 清空/创建Screens目录
    if os.path.exists(screens_path):
        import shutil
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        return 0
    
    # 基于数量的智能分类
    # 根据经验，大多数App的截图分布大致为：
    # - Onboarding: 前30%
    # - Paywall: 5-10%
    # - Main功能: 60%
    
    categories = []
    
    if total >= 50:
        # 大量截图，详细分类
        categories = [
            ("01_Launch", 1, min(2, total)),
            ("02_Onboarding", 3, int(total * 0.25)),
            ("03_Paywall", int(total * 0.25) + 1, int(total * 0.35)),
            ("04_Main", int(total * 0.35) + 1, int(total * 0.6)),
            ("05_Features", int(total * 0.6) + 1, int(total * 0.8)),
            ("06_Settings", int(total * 0.8) + 1, total),
        ]
    elif total >= 20:
        # 中等数量
        categories = [
            ("01_Onboarding", 1, int(total * 0.3)),
            ("02_Paywall", int(total * 0.3) + 1, int(total * 0.4)),
            ("03_Main", int(total * 0.4) + 1, int(total * 0.7)),
            ("04_Other", int(total * 0.7) + 1, total),
        ]
    else:
        # 少量截图
        categories = [
            ("01_Onboarding", 1, int(total * 0.4)),
            ("02_Main", int(total * 0.4) + 1, total),
        ]
    
    # 复制并重命名
    import shutil
    classified_count = 0
    
    for category_name, start, end in categories:
        for i in range(start - 1, min(end, total)):
            if i < len(screenshots):
                src = os.path.join(downloads_path, screenshots[i])
                step_num = i - (start - 1) + 1
                new_name = f"{category_name}_{step_num:02d}.png"
                dst = os.path.join(screens_path, new_name)
                shutil.copy2(src, dst)
                classified_count += 1
    
    return classified_count

def main():
    print("=" * 60)
    print("批量截图采集工具")
    print("=" * 60)
    print(f"待采集产品: {len(PRODUCTS)}个")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print()
    
    driver = connect_to_chrome()
    if not driver:
        print("\n请确保Chrome以调试模式运行:")
        print('chrome.exe --remote-debugging-port=9222')
        return
    
    results = []
    
    for product in PRODUCTS:
        count = download_product_screenshots(driver, product['name'], product['url'])
        
        if count > 0:
            # 简单分类
            print(f"\n[分类] 正在分类 {product['name']}...")
            classified = classify_screenshots(product['name'])
            print(f"      已分类: {classified}张")
        
        results.append({
            "name": product['name'],
            "count": count
        })
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("采集完成 - 汇总报告")
    print("=" * 60)
    
    total_screenshots = 0
    for r in results:
        status = "[OK]" if r['count'] > 0 else "[--]"
        print(f"{status} {r['name']}: {r['count']}张")
        total_screenshots += r['count']
    
    print(f"\n总计: {total_screenshots}张截图")
    print(f"保存位置: {PROJECTS_DIR}")

if __name__ == "__main__":
    main()








"""
批量下载截图工具
依次下载多个产品的截图并自动分类
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 待下载的产品列表 - 用户确认的正确URL
PRODUCTS = [
    {
        "name": "Strava_Analysis",
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/?ts=0&vt=1&id=961"
    },
    {
        "name": "Flo_Analysis",
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/?ts=0&vt=1&id=877"
    },
    {
        "name": "Calm_Analysis",
        "url": "https://screensdesign.com/apps/calm/?ts=0&vt=1&id=883"
    },
    {
        "name": "Runna_Analysis",
        "url": "https://screensdesign.com/apps/runna-running-training-plans/?ts=0&vt=1&id=902"
    }
]

def connect_to_chrome():
    """连接到Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接Chrome: {e}")
        return None

def download_product_screenshots(driver, product_name, url):
    """下载单个产品的所有截图"""
    print(f"\n{'='*60}")
    print(f"下载: {product_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # 创建项目目录
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    try:
        # 访问页面
        print("[1/4] 访问页面...")
        driver.get(url)
        time.sleep(3)
        
        # 滚动加载所有图片
        print("[2/4] 滚动加载图片...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"      滚动 {scroll_count}次, 高度: {new_height}px")
            if new_height == last_height or scroll_count > 20:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 收集图片URL
        print("[3/4] 收集图片URL...")
        image_urls = []
        
        # 多种选择器尝试
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']", 
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            ".screen-item img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src") or elem.get_attribute("data-src")
                    if src and src.startswith("http"):
                        # 过滤非截图图片
                        skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button']
                        if not any(kw in src.lower() for kw in skip_keywords):
                            # 检查图片尺寸（如果可以）
                            width = elem.get_attribute("width") or elem.get_attribute("naturalWidth")
                            if width:
                                try:
                                    if int(width) < 100:
                                        continue
                                except:
                                    pass
                            if src not in image_urls:
                                image_urls.append(src)
            except:
                continue
        
        print(f"      找到 {len(image_urls)} 个图片URL")
        
        if not image_urls:
            print("[ERROR] 未找到任何图片!")
            return 0
        
        # 下载并处理图片
        print("[4/4] 下载并处理图片...")
        success_count = 0
        
        for i, img_url in enumerate(image_urls, 1):
            try:
                # 下载
                response = requests.get(img_url, timeout=30)
                img = Image.open(BytesIO(response.content))
                
                # 检查是否是合理的截图尺寸
                if img.width < 200 or img.height < 200:
                    continue
                
                # 转换模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整尺寸
                ratio = TARGET_WIDTH / img.width
                new_height = int(img.height * ratio)
                img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                # 保存
                filename = f"Screen_{success_count+1:03d}.png"
                filepath = os.path.join(downloads_path, filename)
                img_resized.save(filepath, 'PNG', optimize=True)
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"      已下载: {success_count}张")
                    
            except Exception as e:
                continue
        
        print(f"\n[完成] {product_name}: 成功下载 {success_count} 张截图")
        return success_count
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return 0

def classify_screenshots(product_name):
    """对截图进行简单分类"""
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        return 0
    
    # 清空/创建Screens目录
    if os.path.exists(screens_path):
        import shutil
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        return 0
    
    # 基于数量的智能分类
    # 根据经验，大多数App的截图分布大致为：
    # - Onboarding: 前30%
    # - Paywall: 5-10%
    # - Main功能: 60%
    
    categories = []
    
    if total >= 50:
        # 大量截图，详细分类
        categories = [
            ("01_Launch", 1, min(2, total)),
            ("02_Onboarding", 3, int(total * 0.25)),
            ("03_Paywall", int(total * 0.25) + 1, int(total * 0.35)),
            ("04_Main", int(total * 0.35) + 1, int(total * 0.6)),
            ("05_Features", int(total * 0.6) + 1, int(total * 0.8)),
            ("06_Settings", int(total * 0.8) + 1, total),
        ]
    elif total >= 20:
        # 中等数量
        categories = [
            ("01_Onboarding", 1, int(total * 0.3)),
            ("02_Paywall", int(total * 0.3) + 1, int(total * 0.4)),
            ("03_Main", int(total * 0.4) + 1, int(total * 0.7)),
            ("04_Other", int(total * 0.7) + 1, total),
        ]
    else:
        # 少量截图
        categories = [
            ("01_Onboarding", 1, int(total * 0.4)),
            ("02_Main", int(total * 0.4) + 1, total),
        ]
    
    # 复制并重命名
    import shutil
    classified_count = 0
    
    for category_name, start, end in categories:
        for i in range(start - 1, min(end, total)):
            if i < len(screenshots):
                src = os.path.join(downloads_path, screenshots[i])
                step_num = i - (start - 1) + 1
                new_name = f"{category_name}_{step_num:02d}.png"
                dst = os.path.join(screens_path, new_name)
                shutil.copy2(src, dst)
                classified_count += 1
    
    return classified_count

def main():
    print("=" * 60)
    print("批量截图采集工具")
    print("=" * 60)
    print(f"待采集产品: {len(PRODUCTS)}个")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print()
    
    driver = connect_to_chrome()
    if not driver:
        print("\n请确保Chrome以调试模式运行:")
        print('chrome.exe --remote-debugging-port=9222')
        return
    
    results = []
    
    for product in PRODUCTS:
        count = download_product_screenshots(driver, product['name'], product['url'])
        
        if count > 0:
            # 简单分类
            print(f"\n[分类] 正在分类 {product['name']}...")
            classified = classify_screenshots(product['name'])
            print(f"      已分类: {classified}张")
        
        results.append({
            "name": product['name'],
            "count": count
        })
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("采集完成 - 汇总报告")
    print("=" * 60)
    
    total_screenshots = 0
    for r in results:
        status = "[OK]" if r['count'] > 0 else "[--]"
        print(f"{status} {r['name']}: {r['count']}张")
        total_screenshots += r['count']
    
    print(f"\n总计: {total_screenshots}张截图")
    print(f"保存位置: {PROJECTS_DIR}")

if __name__ == "__main__":
    main()







"""
批量下载截图工具
依次下载多个产品的截图并自动分类
"""

import os
import sys
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 待下载的产品列表 - 用户确认的正确URL
PRODUCTS = [
    {
        "name": "Strava_Analysis",
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/?ts=0&vt=1&id=961"
    },
    {
        "name": "Flo_Analysis",
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/?ts=0&vt=1&id=877"
    },
    {
        "name": "Calm_Analysis",
        "url": "https://screensdesign.com/apps/calm/?ts=0&vt=1&id=883"
    },
    {
        "name": "Runna_Analysis",
        "url": "https://screensdesign.com/apps/runna-running-training-plans/?ts=0&vt=1&id=902"
    }
]

def connect_to_chrome():
    """连接到Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接Chrome: {e}")
        return None

def download_product_screenshots(driver, product_name, url):
    """下载单个产品的所有截图"""
    print(f"\n{'='*60}")
    print(f"下载: {product_name}")
    print(f"URL: {url}")
    print('='*60)
    
    # 创建项目目录
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    try:
        # 访问页面
        print("[1/4] 访问页面...")
        driver.get(url)
        time.sleep(3)
        
        # 滚动加载所有图片
        print("[2/4] 滚动加载图片...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            scroll_count += 1
            print(f"      滚动 {scroll_count}次, 高度: {new_height}px")
            if new_height == last_height or scroll_count > 20:
                break
            last_height = new_height
        
        # 回到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        # 收集图片URL
        print("[3/4] 收集图片URL...")
        image_urls = []
        
        # 多种选择器尝试
        selectors = [
            "img[src*='screen']",
            "img[src*='Screen']", 
            "img[data-src*='screen']",
            "img.screen-image",
            "img.screenshot",
            ".screenshot img",
            ".screen-item img",
            "img[loading='lazy']",
            "img"
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    src = elem.get_attribute("src") or elem.get_attribute("data-src")
                    if src and src.startswith("http"):
                        # 过滤非截图图片
                        skip_keywords = ['logo', 'icon', 'avatar', 'favicon', 'sprite', 'badge', 'button']
                        if not any(kw in src.lower() for kw in skip_keywords):
                            # 检查图片尺寸（如果可以）
                            width = elem.get_attribute("width") or elem.get_attribute("naturalWidth")
                            if width:
                                try:
                                    if int(width) < 100:
                                        continue
                                except:
                                    pass
                            if src not in image_urls:
                                image_urls.append(src)
            except:
                continue
        
        print(f"      找到 {len(image_urls)} 个图片URL")
        
        if not image_urls:
            print("[ERROR] 未找到任何图片!")
            return 0
        
        # 下载并处理图片
        print("[4/4] 下载并处理图片...")
        success_count = 0
        
        for i, img_url in enumerate(image_urls, 1):
            try:
                # 下载
                response = requests.get(img_url, timeout=30)
                img = Image.open(BytesIO(response.content))
                
                # 检查是否是合理的截图尺寸
                if img.width < 200 or img.height < 200:
                    continue
                
                # 转换模式
                if img.mode in ('RGBA', 'P', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA' or img.mode == 'LA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # 调整尺寸
                ratio = TARGET_WIDTH / img.width
                new_height = int(img.height * ratio)
                img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
                
                # 保存
                filename = f"Screen_{success_count+1:03d}.png"
                filepath = os.path.join(downloads_path, filename)
                img_resized.save(filepath, 'PNG', optimize=True)
                
                success_count += 1
                if success_count % 10 == 0:
                    print(f"      已下载: {success_count}张")
                    
            except Exception as e:
                continue
        
        print(f"\n[完成] {product_name}: 成功下载 {success_count} 张截图")
        return success_count
        
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return 0

def classify_screenshots(product_name):
    """对截图进行简单分类"""
    project_path = os.path.join(PROJECTS_DIR, product_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        return 0
    
    # 清空/创建Screens目录
    if os.path.exists(screens_path):
        import shutil
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        return 0
    
    # 基于数量的智能分类
    # 根据经验，大多数App的截图分布大致为：
    # - Onboarding: 前30%
    # - Paywall: 5-10%
    # - Main功能: 60%
    
    categories = []
    
    if total >= 50:
        # 大量截图，详细分类
        categories = [
            ("01_Launch", 1, min(2, total)),
            ("02_Onboarding", 3, int(total * 0.25)),
            ("03_Paywall", int(total * 0.25) + 1, int(total * 0.35)),
            ("04_Main", int(total * 0.35) + 1, int(total * 0.6)),
            ("05_Features", int(total * 0.6) + 1, int(total * 0.8)),
            ("06_Settings", int(total * 0.8) + 1, total),
        ]
    elif total >= 20:
        # 中等数量
        categories = [
            ("01_Onboarding", 1, int(total * 0.3)),
            ("02_Paywall", int(total * 0.3) + 1, int(total * 0.4)),
            ("03_Main", int(total * 0.4) + 1, int(total * 0.7)),
            ("04_Other", int(total * 0.7) + 1, total),
        ]
    else:
        # 少量截图
        categories = [
            ("01_Onboarding", 1, int(total * 0.4)),
            ("02_Main", int(total * 0.4) + 1, total),
        ]
    
    # 复制并重命名
    import shutil
    classified_count = 0
    
    for category_name, start, end in categories:
        for i in range(start - 1, min(end, total)):
            if i < len(screenshots):
                src = os.path.join(downloads_path, screenshots[i])
                step_num = i - (start - 1) + 1
                new_name = f"{category_name}_{step_num:02d}.png"
                dst = os.path.join(screens_path, new_name)
                shutil.copy2(src, dst)
                classified_count += 1
    
    return classified_count

def main():
    print("=" * 60)
    print("批量截图采集工具")
    print("=" * 60)
    print(f"待采集产品: {len(PRODUCTS)}个")
    for p in PRODUCTS:
        print(f"  - {p['name']}")
    print()
    
    driver = connect_to_chrome()
    if not driver:
        print("\n请确保Chrome以调试模式运行:")
        print('chrome.exe --remote-debugging-port=9222')
        return
    
    results = []
    
    for product in PRODUCTS:
        count = download_product_screenshots(driver, product['name'], product['url'])
        
        if count > 0:
            # 简单分类
            print(f"\n[分类] 正在分类 {product['name']}...")
            classified = classify_screenshots(product['name'])
            print(f"      已分类: {classified}张")
        
        results.append({
            "name": product['name'],
            "count": count
        })
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("采集完成 - 汇总报告")
    print("=" * 60)
    
    total_screenshots = 0
    for r in results:
        status = "[OK]" if r['count'] > 0 else "[--]"
        print(f"{status} {r['name']}: {r['count']}张")
        total_screenshots += r['count']
    
    print(f"\n总计: {total_screenshots}张截图")
    print(f"保存位置: {PROJECTS_DIR}")

if __name__ == "__main__":
    main()























