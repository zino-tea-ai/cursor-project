# -*- coding: utf-8 -*-
"""
自动搜索screensdesign.com上的产品URL - 改进版
核心改进：在网站内部搜索，而不是猜测URL
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def connect_to_chrome():
    """连接到已打开的Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到Chrome: {e}")
        return None

def search_product_on_site(driver, product_name):
    """
    在screensdesign.com网站内搜索产品
    返回找到的URL（带完整参数）
    """
    try:
        # 直接访问搜索结果页面
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        print(f"  访问搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apps/']"))
            )
        except:
            pass
        
        # 获取所有app链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        
        # 按相关性排序 - 产品名在URL中出现的优先
        product_lower = product_name.lower().replace(' ', '-')
        candidates = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/apps/" in href:
                # 提取app slug
                match = re.search(r'/apps/([^/?]+)', href)
                if match:
                    slug = match.group(1).lower()
                    
                    # 计算相关性得分
                    score = 0
                    if product_lower in slug:
                        score += 10
                    if slug.startswith(product_lower):
                        score += 5
                    # 检查产品名的每个词
                    for word in product_name.lower().split():
                        if len(word) > 2 and word in slug:
                            score += 2
                    
                    if score > 0:
                        candidates.append({
                            "url": href,
                            "slug": slug,
                            "score": score
                        })
        
        # 按得分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            print(f"  找到 {len(candidates)} 个候选，最佳匹配: {best['slug']} (得分:{best['score']})")
            
            # 访问最佳结果页面获取完整URL（带参数）
            driver.get(best['url'])
            time.sleep(2)
            full_url = driver.current_url
            
            # 确保URL带有必要的参数
            if "?" not in full_url:
                # 从原始链接中提取参数
                if "?" in best['url']:
                    full_url = best['url']
            
            return full_url
        
        # 如果搜索页面没找到，尝试浏览分类页面
        print("  搜索页面未找到，尝试浏览分类...")
        return browse_category_for_product(driver, product_name)
        
    except Exception as e:
        print(f"  搜索出错: {e}")
        return None

def browse_category_for_product(driver, product_name):
    """浏览分类页面查找产品"""
    try:
        # 访问所有apps页面
        driver.get("https://screensdesign.com/apps/")
        time.sleep(2)
        
        # 滚动加载更多
        for _ in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        # 查找匹配的链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        product_lower = product_name.lower()
        
        for link in links:
            href = link.get_attribute("href")
            if href and product_lower in href.lower():
                return href
        
        return None
    except:
        return None

def search_multiple_products(product_names):
    """
    搜索多个产品
    参数: product_names - 产品名称列表
    返回: {产品名: URL} 字典
    """
    driver = connect_to_chrome()
    if not driver:
        return {}
    
    results = {}
    
    for name in product_names:
        print(f"\n[搜索] {name}...")
        url = search_product_on_site(driver, name)
        
        if url:
            print(f"  [OK] {url}")
            results[name] = url
        else:
            print(f"  [--] 未找到")
            results[name] = None
    
    return results

def main():
    """主函数 - 搜索指定产品"""
    import sys
    
    # 默认搜索列表
    default_products = ["Strava", "Flo", "Calm", "Runna"]
    
    # 如果有命令行参数，使用参数作为搜索列表
    if len(sys.argv) > 1:
        products = sys.argv[1:]
    else:
        products = default_products
    
    print("=" * 60)
    print("screensdesign.com 产品搜索工具 (改进版)")
    print("=" * 60)
    print(f"待搜索: {', '.join(products)}")
    
    results = search_multiple_products(products)
    
    print("\n" + "=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    found = 0
    for name, url in results.items():
        if url:
            print(f"[OK] {name}: {url}")
            found += 1
        else:
            print(f"[--] {name}: 未找到")
    
    print(f"\n找到: {found}/{len(products)}")
    
    # 保存结果
    with open("search_results.txt", "w", encoding="utf-8") as f:
        for name, url in results.items():
            f.write(f"{name}: {url or 'NOT_FOUND'}\n")
    
    return results

if __name__ == "__main__":
    main()

自动搜索screensdesign.com上的产品URL - 改进版
核心改进：在网站内部搜索，而不是猜测URL
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def connect_to_chrome():
    """连接到已打开的Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到Chrome: {e}")
        return None

def search_product_on_site(driver, product_name):
    """
    在screensdesign.com网站内搜索产品
    返回找到的URL（带完整参数）
    """
    try:
        # 直接访问搜索结果页面
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        print(f"  访问搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apps/']"))
            )
        except:
            pass
        
        # 获取所有app链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        
        # 按相关性排序 - 产品名在URL中出现的优先
        product_lower = product_name.lower().replace(' ', '-')
        candidates = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/apps/" in href:
                # 提取app slug
                match = re.search(r'/apps/([^/?]+)', href)
                if match:
                    slug = match.group(1).lower()
                    
                    # 计算相关性得分
                    score = 0
                    if product_lower in slug:
                        score += 10
                    if slug.startswith(product_lower):
                        score += 5
                    # 检查产品名的每个词
                    for word in product_name.lower().split():
                        if len(word) > 2 and word in slug:
                            score += 2
                    
                    if score > 0:
                        candidates.append({
                            "url": href,
                            "slug": slug,
                            "score": score
                        })
        
        # 按得分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            print(f"  找到 {len(candidates)} 个候选，最佳匹配: {best['slug']} (得分:{best['score']})")
            
            # 访问最佳结果页面获取完整URL（带参数）
            driver.get(best['url'])
            time.sleep(2)
            full_url = driver.current_url
            
            # 确保URL带有必要的参数
            if "?" not in full_url:
                # 从原始链接中提取参数
                if "?" in best['url']:
                    full_url = best['url']
            
            return full_url
        
        # 如果搜索页面没找到，尝试浏览分类页面
        print("  搜索页面未找到，尝试浏览分类...")
        return browse_category_for_product(driver, product_name)
        
    except Exception as e:
        print(f"  搜索出错: {e}")
        return None

def browse_category_for_product(driver, product_name):
    """浏览分类页面查找产品"""
    try:
        # 访问所有apps页面
        driver.get("https://screensdesign.com/apps/")
        time.sleep(2)
        
        # 滚动加载更多
        for _ in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        # 查找匹配的链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        product_lower = product_name.lower()
        
        for link in links:
            href = link.get_attribute("href")
            if href and product_lower in href.lower():
                return href
        
        return None
    except:
        return None

def search_multiple_products(product_names):
    """
    搜索多个产品
    参数: product_names - 产品名称列表
    返回: {产品名: URL} 字典
    """
    driver = connect_to_chrome()
    if not driver:
        return {}
    
    results = {}
    
    for name in product_names:
        print(f"\n[搜索] {name}...")
        url = search_product_on_site(driver, name)
        
        if url:
            print(f"  [OK] {url}")
            results[name] = url
        else:
            print(f"  [--] 未找到")
            results[name] = None
    
    return results

def main():
    """主函数 - 搜索指定产品"""
    import sys
    
    # 默认搜索列表
    default_products = ["Strava", "Flo", "Calm", "Runna"]
    
    # 如果有命令行参数，使用参数作为搜索列表
    if len(sys.argv) > 1:
        products = sys.argv[1:]
    else:
        products = default_products
    
    print("=" * 60)
    print("screensdesign.com 产品搜索工具 (改进版)")
    print("=" * 60)
    print(f"待搜索: {', '.join(products)}")
    
    results = search_multiple_products(products)
    
    print("\n" + "=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    found = 0
    for name, url in results.items():
        if url:
            print(f"[OK] {name}: {url}")
            found += 1
        else:
            print(f"[--] {name}: 未找到")
    
    print(f"\n找到: {found}/{len(products)}")
    
    # 保存结果
    with open("search_results.txt", "w", encoding="utf-8") as f:
        for name, url in results.items():
            f.write(f"{name}: {url or 'NOT_FOUND'}\n")
    
    return results

if __name__ == "__main__":
    main()

自动搜索screensdesign.com上的产品URL - 改进版
核心改进：在网站内部搜索，而不是猜测URL
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def connect_to_chrome():
    """连接到已打开的Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到Chrome: {e}")
        return None

def search_product_on_site(driver, product_name):
    """
    在screensdesign.com网站内搜索产品
    返回找到的URL（带完整参数）
    """
    try:
        # 直接访问搜索结果页面
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        print(f"  访问搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apps/']"))
            )
        except:
            pass
        
        # 获取所有app链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        
        # 按相关性排序 - 产品名在URL中出现的优先
        product_lower = product_name.lower().replace(' ', '-')
        candidates = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/apps/" in href:
                # 提取app slug
                match = re.search(r'/apps/([^/?]+)', href)
                if match:
                    slug = match.group(1).lower()
                    
                    # 计算相关性得分
                    score = 0
                    if product_lower in slug:
                        score += 10
                    if slug.startswith(product_lower):
                        score += 5
                    # 检查产品名的每个词
                    for word in product_name.lower().split():
                        if len(word) > 2 and word in slug:
                            score += 2
                    
                    if score > 0:
                        candidates.append({
                            "url": href,
                            "slug": slug,
                            "score": score
                        })
        
        # 按得分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            print(f"  找到 {len(candidates)} 个候选，最佳匹配: {best['slug']} (得分:{best['score']})")
            
            # 访问最佳结果页面获取完整URL（带参数）
            driver.get(best['url'])
            time.sleep(2)
            full_url = driver.current_url
            
            # 确保URL带有必要的参数
            if "?" not in full_url:
                # 从原始链接中提取参数
                if "?" in best['url']:
                    full_url = best['url']
            
            return full_url
        
        # 如果搜索页面没找到，尝试浏览分类页面
        print("  搜索页面未找到，尝试浏览分类...")
        return browse_category_for_product(driver, product_name)
        
    except Exception as e:
        print(f"  搜索出错: {e}")
        return None

def browse_category_for_product(driver, product_name):
    """浏览分类页面查找产品"""
    try:
        # 访问所有apps页面
        driver.get("https://screensdesign.com/apps/")
        time.sleep(2)
        
        # 滚动加载更多
        for _ in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        # 查找匹配的链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        product_lower = product_name.lower()
        
        for link in links:
            href = link.get_attribute("href")
            if href and product_lower in href.lower():
                return href
        
        return None
    except:
        return None

def search_multiple_products(product_names):
    """
    搜索多个产品
    参数: product_names - 产品名称列表
    返回: {产品名: URL} 字典
    """
    driver = connect_to_chrome()
    if not driver:
        return {}
    
    results = {}
    
    for name in product_names:
        print(f"\n[搜索] {name}...")
        url = search_product_on_site(driver, name)
        
        if url:
            print(f"  [OK] {url}")
            results[name] = url
        else:
            print(f"  [--] 未找到")
            results[name] = None
    
    return results

def main():
    """主函数 - 搜索指定产品"""
    import sys
    
    # 默认搜索列表
    default_products = ["Strava", "Flo", "Calm", "Runna"]
    
    # 如果有命令行参数，使用参数作为搜索列表
    if len(sys.argv) > 1:
        products = sys.argv[1:]
    else:
        products = default_products
    
    print("=" * 60)
    print("screensdesign.com 产品搜索工具 (改进版)")
    print("=" * 60)
    print(f"待搜索: {', '.join(products)}")
    
    results = search_multiple_products(products)
    
    print("\n" + "=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    found = 0
    for name, url in results.items():
        if url:
            print(f"[OK] {name}: {url}")
            found += 1
        else:
            print(f"[--] {name}: 未找到")
    
    print(f"\n找到: {found}/{len(products)}")
    
    # 保存结果
    with open("search_results.txt", "w", encoding="utf-8") as f:
        for name, url in results.items():
            f.write(f"{name}: {url or 'NOT_FOUND'}\n")
    
    return results

if __name__ == "__main__":
    main()

自动搜索screensdesign.com上的产品URL - 改进版
核心改进：在网站内部搜索，而不是猜测URL
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def connect_to_chrome():
    """连接到已打开的Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到Chrome: {e}")
        return None

def search_product_on_site(driver, product_name):
    """
    在screensdesign.com网站内搜索产品
    返回找到的URL（带完整参数）
    """
    try:
        # 直接访问搜索结果页面
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        print(f"  访问搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apps/']"))
            )
        except:
            pass
        
        # 获取所有app链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        
        # 按相关性排序 - 产品名在URL中出现的优先
        product_lower = product_name.lower().replace(' ', '-')
        candidates = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/apps/" in href:
                # 提取app slug
                match = re.search(r'/apps/([^/?]+)', href)
                if match:
                    slug = match.group(1).lower()
                    
                    # 计算相关性得分
                    score = 0
                    if product_lower in slug:
                        score += 10
                    if slug.startswith(product_lower):
                        score += 5
                    # 检查产品名的每个词
                    for word in product_name.lower().split():
                        if len(word) > 2 and word in slug:
                            score += 2
                    
                    if score > 0:
                        candidates.append({
                            "url": href,
                            "slug": slug,
                            "score": score
                        })
        
        # 按得分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            print(f"  找到 {len(candidates)} 个候选，最佳匹配: {best['slug']} (得分:{best['score']})")
            
            # 访问最佳结果页面获取完整URL（带参数）
            driver.get(best['url'])
            time.sleep(2)
            full_url = driver.current_url
            
            # 确保URL带有必要的参数
            if "?" not in full_url:
                # 从原始链接中提取参数
                if "?" in best['url']:
                    full_url = best['url']
            
            return full_url
        
        # 如果搜索页面没找到，尝试浏览分类页面
        print("  搜索页面未找到，尝试浏览分类...")
        return browse_category_for_product(driver, product_name)
        
    except Exception as e:
        print(f"  搜索出错: {e}")
        return None

def browse_category_for_product(driver, product_name):
    """浏览分类页面查找产品"""
    try:
        # 访问所有apps页面
        driver.get("https://screensdesign.com/apps/")
        time.sleep(2)
        
        # 滚动加载更多
        for _ in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        # 查找匹配的链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        product_lower = product_name.lower()
        
        for link in links:
            href = link.get_attribute("href")
            if href and product_lower in href.lower():
                return href
        
        return None
    except:
        return None

def search_multiple_products(product_names):
    """
    搜索多个产品
    参数: product_names - 产品名称列表
    返回: {产品名: URL} 字典
    """
    driver = connect_to_chrome()
    if not driver:
        return {}
    
    results = {}
    
    for name in product_names:
        print(f"\n[搜索] {name}...")
        url = search_product_on_site(driver, name)
        
        if url:
            print(f"  [OK] {url}")
            results[name] = url
        else:
            print(f"  [--] 未找到")
            results[name] = None
    
    return results

def main():
    """主函数 - 搜索指定产品"""
    import sys
    
    # 默认搜索列表
    default_products = ["Strava", "Flo", "Calm", "Runna"]
    
    # 如果有命令行参数，使用参数作为搜索列表
    if len(sys.argv) > 1:
        products = sys.argv[1:]
    else:
        products = default_products
    
    print("=" * 60)
    print("screensdesign.com 产品搜索工具 (改进版)")
    print("=" * 60)
    print(f"待搜索: {', '.join(products)}")
    
    results = search_multiple_products(products)
    
    print("\n" + "=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    found = 0
    for name, url in results.items():
        if url:
            print(f"[OK] {name}: {url}")
            found += 1
        else:
            print(f"[--] {name}: 未找到")
    
    print(f"\n找到: {found}/{len(products)}")
    
    # 保存结果
    with open("search_results.txt", "w", encoding="utf-8") as f:
        for name, url in results.items():
            f.write(f"{name}: {url or 'NOT_FOUND'}\n")
    
    return results

if __name__ == "__main__":
    main()

自动搜索screensdesign.com上的产品URL - 改进版
核心改进：在网站内部搜索，而不是猜测URL
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def connect_to_chrome():
    """连接到已打开的Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到Chrome: {e}")
        return None

def search_product_on_site(driver, product_name):
    """
    在screensdesign.com网站内搜索产品
    返回找到的URL（带完整参数）
    """
    try:
        # 直接访问搜索结果页面
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        print(f"  访问搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apps/']"))
            )
        except:
            pass
        
        # 获取所有app链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        
        # 按相关性排序 - 产品名在URL中出现的优先
        product_lower = product_name.lower().replace(' ', '-')
        candidates = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/apps/" in href:
                # 提取app slug
                match = re.search(r'/apps/([^/?]+)', href)
                if match:
                    slug = match.group(1).lower()
                    
                    # 计算相关性得分
                    score = 0
                    if product_lower in slug:
                        score += 10
                    if slug.startswith(product_lower):
                        score += 5
                    # 检查产品名的每个词
                    for word in product_name.lower().split():
                        if len(word) > 2 and word in slug:
                            score += 2
                    
                    if score > 0:
                        candidates.append({
                            "url": href,
                            "slug": slug,
                            "score": score
                        })
        
        # 按得分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            print(f"  找到 {len(candidates)} 个候选，最佳匹配: {best['slug']} (得分:{best['score']})")
            
            # 访问最佳结果页面获取完整URL（带参数）
            driver.get(best['url'])
            time.sleep(2)
            full_url = driver.current_url
            
            # 确保URL带有必要的参数
            if "?" not in full_url:
                # 从原始链接中提取参数
                if "?" in best['url']:
                    full_url = best['url']
            
            return full_url
        
        # 如果搜索页面没找到，尝试浏览分类页面
        print("  搜索页面未找到，尝试浏览分类...")
        return browse_category_for_product(driver, product_name)
        
    except Exception as e:
        print(f"  搜索出错: {e}")
        return None

def browse_category_for_product(driver, product_name):
    """浏览分类页面查找产品"""
    try:
        # 访问所有apps页面
        driver.get("https://screensdesign.com/apps/")
        time.sleep(2)
        
        # 滚动加载更多
        for _ in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        # 查找匹配的链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        product_lower = product_name.lower()
        
        for link in links:
            href = link.get_attribute("href")
            if href and product_lower in href.lower():
                return href
        
        return None
    except:
        return None

def search_multiple_products(product_names):
    """
    搜索多个产品
    参数: product_names - 产品名称列表
    返回: {产品名: URL} 字典
    """
    driver = connect_to_chrome()
    if not driver:
        return {}
    
    results = {}
    
    for name in product_names:
        print(f"\n[搜索] {name}...")
        url = search_product_on_site(driver, name)
        
        if url:
            print(f"  [OK] {url}")
            results[name] = url
        else:
            print(f"  [--] 未找到")
            results[name] = None
    
    return results

def main():
    """主函数 - 搜索指定产品"""
    import sys
    
    # 默认搜索列表
    default_products = ["Strava", "Flo", "Calm", "Runna"]
    
    # 如果有命令行参数，使用参数作为搜索列表
    if len(sys.argv) > 1:
        products = sys.argv[1:]
    else:
        products = default_products
    
    print("=" * 60)
    print("screensdesign.com 产品搜索工具 (改进版)")
    print("=" * 60)
    print(f"待搜索: {', '.join(products)}")
    
    results = search_multiple_products(products)
    
    print("\n" + "=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    found = 0
    for name, url in results.items():
        if url:
            print(f"[OK] {name}: {url}")
            found += 1
        else:
            print(f"[--] {name}: 未找到")
    
    print(f"\n找到: {found}/{len(products)}")
    
    # 保存结果
    with open("search_results.txt", "w", encoding="utf-8") as f:
        for name, url in results.items():
            f.write(f"{name}: {url or 'NOT_FOUND'}\n")
    
    return results

if __name__ == "__main__":
    main()

自动搜索screensdesign.com上的产品URL - 改进版
核心改进：在网站内部搜索，而不是猜测URL
"""

import sys
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def connect_to_chrome():
    """连接到已打开的Chrome调试实例"""
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("[OK] 成功连接到Chrome浏览器")
        return driver
    except Exception as e:
        print(f"[ERROR] 无法连接到Chrome: {e}")
        return None

def search_product_on_site(driver, product_name):
    """
    在screensdesign.com网站内搜索产品
    返回找到的URL（带完整参数）
    """
    try:
        # 直接访问搜索结果页面
        search_url = f"https://screensdesign.com/?s={product_name.replace(' ', '+')}"
        print(f"  访问搜索页面: {search_url}")
        driver.get(search_url)
        time.sleep(3)
        
        # 等待页面加载
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/apps/']"))
            )
        except:
            pass
        
        # 获取所有app链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        
        # 按相关性排序 - 产品名在URL中出现的优先
        product_lower = product_name.lower().replace(' ', '-')
        candidates = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/apps/" in href:
                # 提取app slug
                match = re.search(r'/apps/([^/?]+)', href)
                if match:
                    slug = match.group(1).lower()
                    
                    # 计算相关性得分
                    score = 0
                    if product_lower in slug:
                        score += 10
                    if slug.startswith(product_lower):
                        score += 5
                    # 检查产品名的每个词
                    for word in product_name.lower().split():
                        if len(word) > 2 and word in slug:
                            score += 2
                    
                    if score > 0:
                        candidates.append({
                            "url": href,
                            "slug": slug,
                            "score": score
                        })
        
        # 按得分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        if candidates:
            best = candidates[0]
            print(f"  找到 {len(candidates)} 个候选，最佳匹配: {best['slug']} (得分:{best['score']})")
            
            # 访问最佳结果页面获取完整URL（带参数）
            driver.get(best['url'])
            time.sleep(2)
            full_url = driver.current_url
            
            # 确保URL带有必要的参数
            if "?" not in full_url:
                # 从原始链接中提取参数
                if "?" in best['url']:
                    full_url = best['url']
            
            return full_url
        
        # 如果搜索页面没找到，尝试浏览分类页面
        print("  搜索页面未找到，尝试浏览分类...")
        return browse_category_for_product(driver, product_name)
        
    except Exception as e:
        print(f"  搜索出错: {e}")
        return None

def browse_category_for_product(driver, product_name):
    """浏览分类页面查找产品"""
    try:
        # 访问所有apps页面
        driver.get("https://screensdesign.com/apps/")
        time.sleep(2)
        
        # 滚动加载更多
        for _ in range(15):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)
        
        # 查找匹配的链接
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/apps/']")
        product_lower = product_name.lower()
        
        for link in links:
            href = link.get_attribute("href")
            if href and product_lower in href.lower():
                return href
        
        return None
    except:
        return None

def search_multiple_products(product_names):
    """
    搜索多个产品
    参数: product_names - 产品名称列表
    返回: {产品名: URL} 字典
    """
    driver = connect_to_chrome()
    if not driver:
        return {}
    
    results = {}
    
    for name in product_names:
        print(f"\n[搜索] {name}...")
        url = search_product_on_site(driver, name)
        
        if url:
            print(f"  [OK] {url}")
            results[name] = url
        else:
            print(f"  [--] 未找到")
            results[name] = None
    
    return results

def main():
    """主函数 - 搜索指定产品"""
    import sys
    
    # 默认搜索列表
    default_products = ["Strava", "Flo", "Calm", "Runna"]
    
    # 如果有命令行参数，使用参数作为搜索列表
    if len(sys.argv) > 1:
        products = sys.argv[1:]
    else:
        products = default_products
    
    print("=" * 60)
    print("screensdesign.com 产品搜索工具 (改进版)")
    print("=" * 60)
    print(f"待搜索: {', '.join(products)}")
    
    results = search_multiple_products(products)
    
    print("\n" + "=" * 60)
    print("搜索结果")
    print("=" * 60)
    
    found = 0
    for name, url in results.items():
        if url:
            print(f"[OK] {name}: {url}")
            found += 1
        else:
            print(f"[--] {name}: 未找到")
    
    print(f"\n找到: {found}/{len(products)}")
    
    # 保存结果
    with open("search_results.txt", "w", encoding="utf-8") as f:
        for name, url in results.items():
            f.write(f"{name}: {url or 'NOT_FOUND'}\n")
    
    return results

if __name__ == "__main__":
    main()
