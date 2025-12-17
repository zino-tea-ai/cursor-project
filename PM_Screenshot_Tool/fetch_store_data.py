#!/usr/bin/env python3
"""
从 iOS App Store 抓取商城数据和截图
使用 iTunes Search API + 网页抓取备用方案
"""

import os
import sys
import json
import time
import re
import requests
from datetime import datetime

# 配置 UTF-8 输出
sys.stdout.reconfigure(encoding='utf-8')

# 路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads_2024")

# APP 名称到 iTunes 搜索词的映射（处理名称差异）
APP_SEARCH_MAPPING = {
    "AllTrails": "AllTrails: Hike, Bike & Run",
    "Cal_AI": "Cal AI",
    "Calm": "Calm",
    "Fitbit": "Fitbit",
    "Flo": "Flo Period & Pregnancy Tracker",
    "Headspace": "Headspace: Sleep & Meditation",
    "LADDER": "Ladder: Workout & Fitness",
    "LoseIt": "Lose It! – Calorie Counter",
    "MacroFactor": "MacroFactor",
    "MyFitnessPal": "MyFitnessPal: Calorie Counter",
    "Noom": "Noom: Weight Loss & Health",
    "Peloton": "Peloton: Fitness & Workouts",
    "Runna": "Runna: Running Training Plans",
    "Strava": "Strava: Run, Bike, Hike",
    "WeightWatchers": "WeightWatchers",
    "Yazio": "YAZIO: Calorie Counter & Fasting",
}

# iTunes Search API
ITUNES_API_URL = "https://itunes.apple.com/search"


def search_app(search_term, country="us"):
    """搜索 App Store 应用"""
    params = {
        "term": search_term,
        "entity": "software",
        "country": country,
        "limit": 5  # 获取前5个结果以便匹配
    }
    
    try:
        response = requests.get(ITUNES_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("resultCount", 0) > 0:
            return data["results"]
        return []
    except Exception as e:
        print(f"  ❌ API 请求失败: {e}")
        return []


def find_best_match(results, app_name):
    """从搜索结果中找到最佳匹配"""
    if not results:
        return None
    
    # 优先精确匹配
    search_lower = app_name.lower().replace("_", " ")
    for result in results:
        track_name = result.get("trackName", "").lower()
        if search_lower in track_name or track_name in search_lower:
            return result
    
    # 否则返回第一个结果
    return results[0]


def download_image(url, save_path):
    """下载图片"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"    ⚠️ 下载失败: {e}")
        return False


def format_file_size(size_bytes):
    """格式化文件大小"""
    if not size_bytes:
        return "未知"
    
    size_mb = int(size_bytes) / (1024 * 1024)
    return f"{size_mb:.1f} MB"


def scrape_screenshots_from_webpage(store_url):
    """从 App Store 网页抓取截图 URL（使用页面内嵌 JSON 数据）"""
    if not store_url:
        return []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(store_url, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
        
        screenshot_urls = []
        
        # 方法1：从页面内嵌 JSON 数据中提取（最可靠）
        script_pattern = r'<script[^>]*>(.*?)</script>'
        for match in re.findall(script_pattern, html, re.DOTALL):
            if 'product_media_phone_' in match:
                json_start = match.find('{')
                if json_start >= 0:
                    # 找到完整的 JSON 对象
                    brace_count = 0
                    json_end = json_start
                    for i, c in enumerate(match[json_start:]):
                        if c == '{': brace_count += 1
                        elif c == '}': brace_count -= 1
                        if brace_count == 0:
                            json_end = json_start + i + 1
                            break
                    json_str = match[json_start:json_end]
                    try:
                        import json
                        data = json.loads(json_str)
                        phone_items = data.get('data', {}).get('shelfMapping', {}).get('product_media_phone_', {}).get('items', [])
                        
                        for item in phone_items:
                            screenshot = item.get('screenshot', {})
                            template = screenshot.get('template', '')
                            width = screenshot.get('width', 1284)
                            height = screenshot.get('height', 2778)
                            crop = screenshot.get('crop', 'bb')
                            
                            if template and '{w}' in template:
                                # 替换模板占位符生成高清 URL
                                url = template.replace('{w}', str(width))
                                url = url.replace('{h}', str(height))
                                url = url.replace('{c}', crop)
                                url = url.replace('{f}', 'jpg')
                                screenshot_urls.append(url)
                        
                        if screenshot_urls:
                            print(f"    ✅ 从 JSON 数据提取到 {len(screenshot_urls)} 张截图")
                            return screenshot_urls
                    except Exception as e:
                        print(f"    ⚠️ JSON 解析失败: {e}")
                break
        
        # 方法2：正则匹配备用方案
        if not screenshot_urls:
            print(f"    ⚠️ JSON 方法未找到，尝试正则匹配...")
            full_pattern = r'(https://is\d+-ssl\.mzstatic\.com/image/thumb/Purple[^"\']*?)/\d+x\d+[^"\']*?\.(?:jpg|png|webp)'
            seen_bases = set()
            for match in re.finditer(full_pattern, html):
                base_url = match.group(1)
                if base_url not in seen_bases and 'AppIcon' not in base_url and 'Placeholder' not in base_url:
                    seen_bases.add(base_url)
                    hd_url = f"{base_url}/1284x2778bb.jpg"
                    screenshot_urls.append(hd_url)
            
            if screenshot_urls:
                print(f"    ✅ 从正则匹配提取到 {len(screenshot_urls)} 张截图")
        
        return screenshot_urls[:15]  # 最多返回15张
    except Exception as e:
        print(f"    ❌ 网页抓取失败: {e}")
        return []


def process_app(app_name, search_term, force=False):
    """处理单个 APP
    
    Args:
        app_name: APP 目录名
        search_term: iTunes 搜索词
        force: 是否强制重新下载
    """
    print(f"\n📱 处理: {app_name}")
    print(f"   搜索词: {search_term}")
    
    app_dir = os.path.join(DOWNLOADS_DIR, app_name)
    store_dir = os.path.join(app_dir, "store")
    info_file = os.path.join(app_dir, "store_info.json")
    
    # 检查是否已经抓取过（除非强制模式）
    if not force and os.path.exists(info_file):
        with open(info_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("screenshots_downloaded"):
            print(f"   ✅ 已存在，跳过 (使用 --force 强制重新下载)")
            return existing
    
    if force:
        print(f"   🔄 强制模式：重新下载")
        # 清理旧的截图文件
        if os.path.exists(store_dir):
            import shutil
            shutil.rmtree(store_dir)
    
    # 搜索 API
    results = search_app(search_term)
    if not results:
        print(f"   ❌ 未找到应用")
        return None
    
    # 找到最佳匹配
    app_data = find_best_match(results, app_name)
    if not app_data:
        print(f"   ❌ 无法匹配")
        return None
    
    print(f"   ✅ 找到: {app_data.get('trackName')}")
    
    # 提取关键信息
    store_info = {
        "app_name": app_name,
        "track_name": app_data.get("trackName", ""),
        "subtitle": app_data.get("subtitle", ""),
        "bundle_id": app_data.get("bundleId", ""),
        "average_rating": app_data.get("averageUserRating", 0),
        "rating_count": app_data.get("userRatingCount", 0),
        "price": app_data.get("price", 0),
        "formatted_price": app_data.get("formattedPrice", "Free"),
        "file_size": format_file_size(app_data.get("fileSizeBytes")),
        "file_size_bytes": app_data.get("fileSizeBytes", 0),
        "release_date": app_data.get("releaseDate", ""),
        "current_version_date": app_data.get("currentVersionReleaseDate", ""),
        "version": app_data.get("version", ""),
        "description": app_data.get("description", "")[:500] + "...",  # 截断描述
        "developer": app_data.get("artistName", ""),
        "primary_genre": app_data.get("primaryGenreName", ""),
        "screenshot_urls": [],  # 将从网页获取
        "ipad_screenshot_urls": app_data.get("ipadScreenshotUrls", []),
        "icon_url": app_data.get("artworkUrl512", app_data.get("artworkUrl100", "")),
        "store_url": app_data.get("trackViewUrl", ""),
        "fetched_at": datetime.now().isoformat(),
        "screenshots_downloaded": False
    }
    
    # 创建 store 目录
    os.makedirs(store_dir, exist_ok=True)
    
    # 始终优先从网页抓取截图（比 API 更完整）
    screenshot_urls = []
    if store_info["store_url"]:
        print(f"   📸 从 App Store 网页获取截图...")
        screenshot_urls = scrape_screenshots_from_webpage(store_info["store_url"])
    
    # 如果网页抓取失败，使用 API 返回的截图
    if not screenshot_urls:
        screenshot_urls = app_data.get("screenshotUrls", [])
        if screenshot_urls:
            print(f"   📸 使用 API 返回的 {len(screenshot_urls)} 张截图")
            store_info["screenshots_source"] = "api"
    else:
        store_info["screenshots_source"] = "webpage"
    
    store_info["screenshot_urls"] = screenshot_urls
    
    print(f"   📥 下载 {len(screenshot_urls)} 张截图...")
    
    downloaded_files = []
    for i, url in enumerate(screenshot_urls, 1):
        filename = f"screenshot_{i:02d}.png"
        save_path = os.path.join(store_dir, filename)
        
        if download_image(url, save_path):
            downloaded_files.append(filename)
            print(f"      ✓ {filename}")
        
        time.sleep(0.3)  # 避免请求过快
    
    # 下载图标
    if store_info["icon_url"]:
        icon_path = os.path.join(store_dir, "icon.png")
        if download_image(store_info["icon_url"], icon_path):
            print(f"      ✓ icon.png")
    
    store_info["screenshots_downloaded"] = True
    store_info["downloaded_files"] = downloaded_files
    
    # 保存信息
    with open(info_file, "w", encoding="utf-8") as f:
        json.dump(store_info, f, ensure_ascii=False, indent=2)
    
    print(f"   💾 保存: store_info.json ({len(downloaded_files)} 张截图)")
    
    return store_info


def generate_comparison_report(all_data):
    """生成对比报告"""
    report_path = os.path.join(DOWNLOADS_DIR, "store_comparison.json")
    
    # 过滤有效数据
    valid_data = [d for d in all_data if d is not None]
    
    # 按评分排序
    valid_data.sort(key=lambda x: x.get("average_rating", 0), reverse=True)
    
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_apps": len(valid_data),
        "apps": []
    }
    
    for data in valid_data:
        report["apps"].append({
            "name": data.get("app_name"),
            "track_name": data.get("track_name"),
            "subtitle": data.get("subtitle"),
            "rating": round(data.get("average_rating", 0), 1),
            "rating_count": data.get("rating_count", 0),
            "price": data.get("formatted_price"),
            "size": data.get("file_size"),
            "screenshot_count": len(data.get("screenshot_urls", [])),
            "developer": data.get("developer"),
            "genre": data.get("primary_genre"),
            "last_update": data.get("current_version_date", "")[:10],
            "store_url": data.get("store_url")
        })
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 对比报告已保存: {report_path}")
    
    return report


def print_summary(report):
    """打印摘要"""
    print("\n" + "=" * 60)
    print("📊 App Store 数据摘要")
    print("=" * 60)
    
    print(f"\n{'应用名称':<20} {'评分':<6} {'评论数':<12} {'价格':<10} {'截图数':<6}")
    print("-" * 60)
    
    for app in report["apps"]:
        name = app["name"][:18]
        rating = f"{app['rating']:.1f}" if app['rating'] else "N/A"
        count = f"{app['rating_count']:,}" if app['rating_count'] else "N/A"
        price = app["price"] or "Free"
        screenshots = app["screenshot_count"]
        
        print(f"{name:<20} {rating:<6} {count:<12} {price:<10} {screenshots:<6}")
    
    print("=" * 60)


def main():
    # 解析命令行参数
    force = "--force" in sys.argv
    
    print("🚀 开始抓取 iOS App Store 数据 (美区)")
    if force:
        print("⚠️  强制模式：将重新下载所有截图")
    print(f"📂 目标目录: {DOWNLOADS_DIR}")
    
    # 获取所有 APP 目录
    if not os.path.exists(DOWNLOADS_DIR):
        print("❌ downloads_2024 目录不存在")
        return
    
    app_dirs = []
    for name in os.listdir(DOWNLOADS_DIR):
        dir_path = os.path.join(DOWNLOADS_DIR, name)
        # 排除备份目录和 JSON 文件
        if os.path.isdir(dir_path) and not name.endswith("_backup") and not name.startswith("."):
            app_dirs.append(name)
    
    print(f"\n📱 发现 {len(app_dirs)} 个 APP 目录")
    
    # 处理每个 APP
    all_data = []
    for app_name in sorted(app_dirs):
        search_term = APP_SEARCH_MAPPING.get(app_name, app_name)
        data = process_app(app_name, search_term, force=force)
        all_data.append(data)
        time.sleep(1)  # API 请求间隔
    
    # 生成对比报告
    report = generate_comparison_report(all_data)
    
    # 打印摘要
    print_summary(report)
    
    print("\n✅ 完成！")
    print("\n💡 提示: 使用 --force 参数可强制重新下载所有截图")


if __name__ == "__main__":
    main()

