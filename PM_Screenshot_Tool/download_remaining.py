# -*- coding: utf-8 -*-
"""
下载剩余产品 - Calm 和 Runna
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 只下载剩余的产品
PRODUCTS = [
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
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] Chrome connected")
        return driver
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def download_screenshots(driver, name, url):
    print(f"\n[START] {name}")
    
    project_path = os.path.join(PROJECTS_DIR, name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # 访问页面
    driver.get(url)
    time.sleep(3)
    
    # 滚动
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print(f"  scroll {i+1}/15")
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 收集图片
    image_urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "img")
    
    for elem in elements:
        src = elem.get_attribute("src") or elem.get_attribute("data-src")
        if src and src.startswith("http"):
            if not any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'favicon']):
                if src not in image_urls:
                    image_urls.append(src)
    
    print(f"  found {len(image_urls)} images")
    
    # 下载
    count = 0
    for img_url in image_urls:
        try:
            response = requests.get(img_url, timeout=20)
            img = Image.open(BytesIO(response.content))
            
            if img.width < 200 or img.height < 200:
                continue
            
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if 'A' in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            ratio = TARGET_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
            
            count += 1
            img.save(os.path.join(downloads_path, f"Screen_{count:03d}.png"), 'PNG')
            
            if count % 20 == 0:
                print(f"  downloaded: {count}")
                
        except:
            continue
    
    print(f"[DONE] {name}: {count} screenshots")
    return count

def main():
    driver = connect_to_chrome()
    if not driver:
        return
    
    for p in PRODUCTS:
        download_screenshots(driver, p['name'], p['url'])
    
    print("\n[ALL DONE]")

if __name__ == "__main__":
    main()







"""
下载剩余产品 - Calm 和 Runna
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 只下载剩余的产品
PRODUCTS = [
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
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] Chrome connected")
        return driver
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def download_screenshots(driver, name, url):
    print(f"\n[START] {name}")
    
    project_path = os.path.join(PROJECTS_DIR, name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # 访问页面
    driver.get(url)
    time.sleep(3)
    
    # 滚动
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print(f"  scroll {i+1}/15")
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 收集图片
    image_urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "img")
    
    for elem in elements:
        src = elem.get_attribute("src") or elem.get_attribute("data-src")
        if src and src.startswith("http"):
            if not any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'favicon']):
                if src not in image_urls:
                    image_urls.append(src)
    
    print(f"  found {len(image_urls)} images")
    
    # 下载
    count = 0
    for img_url in image_urls:
        try:
            response = requests.get(img_url, timeout=20)
            img = Image.open(BytesIO(response.content))
            
            if img.width < 200 or img.height < 200:
                continue
            
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if 'A' in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            ratio = TARGET_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
            
            count += 1
            img.save(os.path.join(downloads_path, f"Screen_{count:03d}.png"), 'PNG')
            
            if count % 20 == 0:
                print(f"  downloaded: {count}")
                
        except:
            continue
    
    print(f"[DONE] {name}: {count} screenshots")
    return count

def main():
    driver = connect_to_chrome()
    if not driver:
        return
    
    for p in PRODUCTS:
        download_screenshots(driver, p['name'], p['url'])
    
    print("\n[ALL DONE]")

if __name__ == "__main__":
    main()







"""
下载剩余产品 - Calm 和 Runna
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 只下载剩余的产品
PRODUCTS = [
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
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] Chrome connected")
        return driver
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def download_screenshots(driver, name, url):
    print(f"\n[START] {name}")
    
    project_path = os.path.join(PROJECTS_DIR, name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # 访问页面
    driver.get(url)
    time.sleep(3)
    
    # 滚动
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print(f"  scroll {i+1}/15")
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 收集图片
    image_urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "img")
    
    for elem in elements:
        src = elem.get_attribute("src") or elem.get_attribute("data-src")
        if src and src.startswith("http"):
            if not any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'favicon']):
                if src not in image_urls:
                    image_urls.append(src)
    
    print(f"  found {len(image_urls)} images")
    
    # 下载
    count = 0
    for img_url in image_urls:
        try:
            response = requests.get(img_url, timeout=20)
            img = Image.open(BytesIO(response.content))
            
            if img.width < 200 or img.height < 200:
                continue
            
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if 'A' in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            ratio = TARGET_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
            
            count += 1
            img.save(os.path.join(downloads_path, f"Screen_{count:03d}.png"), 'PNG')
            
            if count % 20 == 0:
                print(f"  downloaded: {count}")
                
        except:
            continue
    
    print(f"[DONE] {name}: {count} screenshots")
    return count

def main():
    driver = connect_to_chrome()
    if not driver:
        return
    
    for p in PRODUCTS:
        download_screenshots(driver, p['name'], p['url'])
    
    print("\n[ALL DONE]")

if __name__ == "__main__":
    main()







"""
下载剩余产品 - Calm 和 Runna
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 只下载剩余的产品
PRODUCTS = [
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
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] Chrome connected")
        return driver
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def download_screenshots(driver, name, url):
    print(f"\n[START] {name}")
    
    project_path = os.path.join(PROJECTS_DIR, name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # 访问页面
    driver.get(url)
    time.sleep(3)
    
    # 滚动
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print(f"  scroll {i+1}/15")
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 收集图片
    image_urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "img")
    
    for elem in elements:
        src = elem.get_attribute("src") or elem.get_attribute("data-src")
        if src and src.startswith("http"):
            if not any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'favicon']):
                if src not in image_urls:
                    image_urls.append(src)
    
    print(f"  found {len(image_urls)} images")
    
    # 下载
    count = 0
    for img_url in image_urls:
        try:
            response = requests.get(img_url, timeout=20)
            img = Image.open(BytesIO(response.content))
            
            if img.width < 200 or img.height < 200:
                continue
            
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if 'A' in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            ratio = TARGET_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
            
            count += 1
            img.save(os.path.join(downloads_path, f"Screen_{count:03d}.png"), 'PNG')
            
            if count % 20 == 0:
                print(f"  downloaded: {count}")
                
        except:
            continue
    
    print(f"[DONE] {name}: {count} screenshots")
    return count

def main():
    driver = connect_to_chrome()
    if not driver:
        return
    
    for p in PRODUCTS:
        download_screenshots(driver, p['name'], p['url'])
    
    print("\n[ALL DONE]")

if __name__ == "__main__":
    main()








"""
下载剩余产品 - Calm 和 Runna
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 只下载剩余的产品
PRODUCTS = [
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
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] Chrome connected")
        return driver
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def download_screenshots(driver, name, url):
    print(f"\n[START] {name}")
    
    project_path = os.path.join(PROJECTS_DIR, name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # 访问页面
    driver.get(url)
    time.sleep(3)
    
    # 滚动
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print(f"  scroll {i+1}/15")
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 收集图片
    image_urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "img")
    
    for elem in elements:
        src = elem.get_attribute("src") or elem.get_attribute("data-src")
        if src and src.startswith("http"):
            if not any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'favicon']):
                if src not in image_urls:
                    image_urls.append(src)
    
    print(f"  found {len(image_urls)} images")
    
    # 下载
    count = 0
    for img_url in image_urls:
        try:
            response = requests.get(img_url, timeout=20)
            img = Image.open(BytesIO(response.content))
            
            if img.width < 200 or img.height < 200:
                continue
            
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if 'A' in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            ratio = TARGET_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
            
            count += 1
            img.save(os.path.join(downloads_path, f"Screen_{count:03d}.png"), 'PNG')
            
            if count % 20 == 0:
                print(f"  downloaded: {count}")
                
        except:
            continue
    
    print(f"[DONE] {name}: {count} screenshots")
    return count

def main():
    driver = connect_to_chrome()
    if not driver:
        return
    
    for p in PRODUCTS:
        download_screenshots(driver, p['name'], p['url'])
    
    print("\n[ALL DONE]")

if __name__ == "__main__":
    main()







"""
下载剩余产品 - Calm 和 Runna
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TARGET_WIDTH = 402

# 只下载剩余的产品
PRODUCTS = [
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
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] Chrome connected")
        return driver
    except Exception as e:
        print(f"[ERROR] {e}")
        return None

def download_screenshots(driver, name, url):
    print(f"\n[START] {name}")
    
    project_path = os.path.join(PROJECTS_DIR, name)
    downloads_path = os.path.join(project_path, "Downloads")
    os.makedirs(downloads_path, exist_ok=True)
    
    # 访问页面
    driver.get(url)
    time.sleep(3)
    
    # 滚动
    for i in range(15):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        print(f"  scroll {i+1}/15")
    
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)
    
    # 收集图片
    image_urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "img")
    
    for elem in elements:
        src = elem.get_attribute("src") or elem.get_attribute("data-src")
        if src and src.startswith("http"):
            if not any(kw in src.lower() for kw in ['logo', 'icon', 'avatar', 'favicon']):
                if src not in image_urls:
                    image_urls.append(src)
    
    print(f"  found {len(image_urls)} images")
    
    # 下载
    count = 0
    for img_url in image_urls:
        try:
            response = requests.get(img_url, timeout=20)
            img = Image.open(BytesIO(response.content))
            
            if img.width < 200 or img.height < 200:
                continue
            
            if img.mode in ('RGBA', 'P', 'LA'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if 'A' in img.mode:
                    bg.paste(img, mask=img.split()[-1])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            ratio = TARGET_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((TARGET_WIDTH, new_h), Image.Resampling.LANCZOS)
            
            count += 1
            img.save(os.path.join(downloads_path, f"Screen_{count:03d}.png"), 'PNG')
            
            if count % 20 == 0:
                print(f"  downloaded: {count}")
                
        except:
            continue
    
    print(f"[DONE] {name}: {count} screenshots")
    return count

def main():
    driver = connect_to_chrome()
    if not driver:
        return
    
    for p in PRODUCTS:
        download_screenshots(driver, p['name'], p['url'])
    
    print("\n[ALL DONE]")

if __name__ == "__main__":
    main()























