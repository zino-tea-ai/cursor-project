# -*- coding: utf-8 -*-
"""
批量下载 Top 30 竞品截图
从 screensdesign.com 下载，需要已登录会员的 Chrome 浏览器
"""

import os
import sys
import json
import time
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("[ERROR] 请先安装 selenium: pip install selenium")
    sys.exit(1)

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
QUEUE_FILE = os.path.join(BASE_DIR, "download_queue.json")
TARGET_WIDTH = 402


def load_queue():
    """加载下载队列"""
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_queue(data):
    """保存下载队列"""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def connect_to_chrome():
    """连接到已打开的 Chrome 调试窗口"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到 Chrome 浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到 Chrome: {e}")
        print("\n请确保已用以下命令启动 Chrome:")
        print('  Windows PowerShell:')
        print('  & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222')
        return None


def scroll_to_load_all(driver):
    """滚动页面加载所有图片"""
    print("  滚动页面加载图片...")
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    scroll_count = 0
    max_scrolls = 20
    
    while scroll_count < max_scrolls:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_count += 1
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


def get_screenshot_urls(driver):
    """获取页面上所有截图的URL"""
    image_urls = []
    
    selectors = [
        "img[src*='screen']",
        "img[src*='screenshot']",
        "img[data-src]",
        "img[loading='lazy']",
        "picture img",
        "img"
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                url = elem.get_attribute("src") or elem.get_attribute("data-src")
                
                if url and url.startswith("http"):
                    # 过滤掉非截图图片
                    skip_keywords = ['logo', 'icon', 'avatar', 'profile', 'favicon', 'badge', 'star', 'rating']
                    if any(skip in url.lower() for skip in skip_keywords):
                        continue
                    # 只要较大的图片（排除小图标）
                    if 'thumb' in url.lower() and 'small' in url.lower():
                        continue
                    if url not in image_urls:
                        image_urls.append(url)
        except:
            continue
    
    return image_urls


def download_and_process(url, output_path, index):
    """下载并处理图片"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        img = Image.open(BytesIO(response.content))
        
        # 转换模式
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 只处理合理尺寸的图片（排除太小的图标）
        if img.size[0] < 100 or img.size[1] < 100:
            return False
        
        # 调整尺寸
        ratio = TARGET_WIDTH / img.size[0]
        new_height = int(img.size[1] * ratio)
        img_resized = img.resize((TARGET_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 保存
        filename = f"Screen_{index:03d}.png"
        filepath = os.path.join(output_path, filename)
        img_resized.save(filepath, 'PNG', optimize=True)
        
        return True
        
    except Exception as e:
        print(f"    [SKIP] 下载失败: {str(e)[:50]}")
        return False


def download_app(driver, app_info):
    """下载单个 App 的截图"""
    name = app_info["name"]
    folder = app_info["folder"]
    url = app_info["url"]
    
    print(f"\n{'='*50}")
    print(f"[{app_info['rank']}/30] {name}")
    print(f"{'='*50}")
    
    # 创建项目文件夹
    project_path = os.path.join(PROJECTS_DIR, folder)
    screens_path = os.path.join(project_path, "screens")
    os.makedirs(screens_path, exist_ok=True)
    
    # 检查是否已有截图
    existing = len([f for f in os.listdir(screens_path) if f.endswith('.png')]) if os.path.exists(screens_path) else 0
    if existing > 50:
        print(f"  已有 {existing} 张截图，跳过")
        return existing
    
    # 导航到页面
    print(f"  打开: {url}")
    driver.get(url)
    time.sleep(3)
    
    # 检查是否需要登录
    page_source = driver.page_source.lower()
    if 'sign in' in page_source and 'upgrade' in page_source and len(page_source) < 50000:
        print("  [WARN] 可能需要登录，请检查浏览器")
        return 0
    
    # 滚动加载
    scroll_to_load_all(driver)
    
    # 获取截图URL
    print("  获取截图URL...")
    image_urls = get_screenshot_urls(driver)
    print(f"  找到 {len(image_urls)} 个候选图片")
    
    if not image_urls:
        print("  [WARN] 未找到截图，请检查页面")
        return 0
    
    # 下载图片
    print(f"  开始下载...")
    success_count = 0
    
    for i, img_url in enumerate(image_urls, 1):
        if download_and_process(img_url, screens_path, i):
            success_count += 1
            if success_count % 20 == 0:
                print(f"    已下载 {success_count} 张...")
    
    print(f"  完成! 下载了 {success_count} 张截图")
    return success_count


def show_status(queue_data):
    """显示下载状态"""
    print("\n" + "="*60)
    print("Top 30 竞品下载状态")
    print("="*60)
    
    done = 0
    pending = 0
    total_screenshots = 0
    
    for app in queue_data["queue"]:
        status_icon = "✅" if app["status"] == "done" else "⏳"
        screenshots = app.get("screenshots", 0)
        print(f"  {status_icon} [{app['rank']:2d}] {app['name']:<25} {screenshots:>3} 张")
        
        if app["status"] == "done":
            done += 1
        else:
            pending += 1
        total_screenshots += screenshots
    
    print("="*60)
    print(f"完成: {done}/30  |  待下载: {pending}  |  总截图: {total_screenshots}")
    print("="*60)


def main():
    print("="*60)
    print("Top 30 竞品截图批量下载工具")
    print("="*60)
    
    # 加载队列
    queue_data = load_queue()
    if not queue_data:
        print("[ERROR] 找不到下载队列文件")
        return
    
    # 显示当前状态
    show_status(queue_data)
    
    # 获取待下载列表
    pending_apps = [app for app in queue_data["queue"] if app["status"] != "done"]
    
    if not pending_apps:
        print("\n所有竞品已下载完成!")
        return
    
    print(f"\n待下载: {len(pending_apps)} 个竞品")
    
    # 选择模式
    print("\n选择模式:")
    print("  1. 下载全部待处理")
    print("  2. 下载指定数量")
    print("  3. 只查看状态")
    
    choice = input("\n请选择 (1/2/3): ").strip()
    
    if choice == "3":
        return
    
    count = len(pending_apps)
    if choice == "2":
        count = int(input("下载数量: ").strip())
    
    # 连接 Chrome
    driver = connect_to_chrome()
    if not driver:
        return
    
    # 开始下载
    downloaded = 0
    for app in pending_apps[:count]:
        try:
            screenshots = download_app(driver, app)
            
            # 更新状态
            if screenshots > 0:
                app["status"] = "done"
                app["screenshots"] = screenshots
                save_queue(queue_data)
                downloaded += 1
            
            # 间隔避免被限制
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n用户中断，保存进度...")
            save_queue(queue_data)
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            continue
    
    # 最终状态
    print("\n" + "="*60)
    print(f"本次下载完成: {downloaded} 个竞品")
    show_status(queue_data)


if __name__ == "__main__":
    main()

