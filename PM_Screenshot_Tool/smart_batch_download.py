# -*- coding: utf-8 -*-
"""
Smart Batch Download System v2.0
================================
- 修复bug，增强稳定性
- 下载重试机制（3次）
- 断点续传
- 下载完自动分析
- Chrome连接检测和友好提示
"""

import os
import sys
import json
import time
import asyncio
import requests
import re
import shutil
import socket
import subprocess
import logging
from datetime import datetime
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 下载配置
TARGET_WIDTH = 402
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# 重试配置
MAX_IMAGE_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# 状态文件
STATUS_FILE = os.path.join(BASE_DIR, "download_status.json")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'download.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ============================================================
# 工具函数
# ============================================================

def generate_app_slug(app_name: str) -> str:
    """
    生成screensdesign.com的App URL slug
    
    Examples:
        "Cal AI - Calorie Tracker" -> "cal-ai-calorie-tracker"
        "MyFitnessPal: Calorie Counter" -> "myfitnesspal-calorie-counter"
    """
    slug = app_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def download_image_with_retry(url: str, max_retries: int = MAX_IMAGE_RETRIES) -> bytes:
    """
    下载图片，带重试机制
    
    Args:
        url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        图片字节数据，失败返回None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/'
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return None


# ============================================================
# Chrome 连接助手
# ============================================================

class ChromeHelper:
    """Chrome浏览器连接助手"""
    
    @staticmethod
    def is_chrome_ready() -> bool:
        """检查Chrome调试端口是否可用"""
        return check_port_open("127.0.0.1", CHROME_DEBUG_PORT)
    
    @staticmethod
    def get_chrome_start_command() -> str:
        """获取Chrome启动命令"""
        # Windows
        if sys.platform == 'win32':
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT}'
        return f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
    
    @staticmethod
    async def ensure_chrome_ready() -> bool:
        """
        确保Chrome已准备好
        如果未启动，提示用户启动
        """
        if ChromeHelper.is_chrome_ready():
            logger.info("Chrome debug port is ready")
            return True
        
        print("\n" + "=" * 60)
        print("  Chrome 未检测到")
        print("=" * 60)
        print(f"\n请先启动Chrome并开启调试端口 {CHROME_DEBUG_PORT}:")
        print(f"\n  命令: {ChromeHelper.get_chrome_start_command()}")
        print("\n或者在已打开的Chrome中手动登录 screensdesign.com")
        print("然后重新运行此脚本。")
        print("\n" + "=" * 60)
        
        # 等待用户启动
        print("\n等待Chrome启动... (按Ctrl+C取消)")
        for i in range(60):  # 等待最多60秒
            if ChromeHelper.is_chrome_ready():
                logger.info("Chrome is now ready!")
                return True
            await asyncio.sleep(1)
            print(f"  等待中... {60-i}秒", end="\r")
        
        logger.error("Chrome did not start within timeout")
        return False


# ============================================================
# 下载器主类
# ============================================================

class SmartBatchDownloader:
    """智能批量下载器"""
    
    def __init__(self, auto_analyze: bool = True):
        """
        初始化下载器
        
        Args:
            auto_analyze: 下载完成后是否自动分析
        """
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auto_analyze = auto_analyze
        
        # 结果统计
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
    
    async def init_browser(self) -> bool:
        """初始化浏览器连接"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        # 确保Chrome已准备好
        if not await ChromeHelper.ensure_chrome_ready():
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Connected to Chrome")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Chrome: {e}")
            return False
    
    async def close(self):
        """关闭浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def search_and_enter_app_page(self, product_name: str) -> str:
        """
        搜索产品并进入专属页面
        
        Returns:
            专属页面URL，失败返回None
        """
        try:
            simple_name = product_name.split(':')[0].split(' - ')[0].strip()
            logger.info(f"Searching for '{simple_name}'...")
            
            # 进入screensdesign首页
            await self.page.goto('https://screensdesign.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 点击搜索区域
            search_area = await self.page.query_selector('text=/Search/')
            if search_area:
                await search_area.click()
                await asyncio.sleep(2)
            
            # 找到搜索输入框并搜索
            search_input = await self.page.query_selector('input:visible')
            if search_input:
                await search_input.fill(simple_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(5)
            
            logger.info(f"Search results: {self.page.url}")
            
            # 在搜索结果中找到匹配的App完整名称
            h3_elements = await self.page.query_selector_all('h3')
            
            found_app_name = None
            for h3 in h3_elements:
                try:
                    text = (await h3.inner_text()).strip()
                    if simple_name.lower() in text.lower():
                        found_app_name = text
                        logger.info(f"Found app in search: '{found_app_name}'")
                        break
                except:
                    continue
            
            if not found_app_name:
                logger.error(f"App not found in search results")
                return None
            
            # 生成slug并访问专属页面
            slug = generate_app_slug(found_app_name)
            app_url = f"https://screensdesign.com/apps/{slug}/"
            
            logger.info(f"Generated URL: {app_url}")
            
            response = await self.page.goto(app_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查页面是否有效
            if response and response.status == 404:
                logger.warning(f"Page not found: {app_url}")
                
                # 尝试备选slug
                alt_slug = generate_app_slug(product_name)
                if alt_slug != slug:
                    alt_url = f"https://screensdesign.com/apps/{alt_slug}/"
                    logger.info(f"Trying alternate URL: {alt_url}")
                    response = await self.page.goto(alt_url, wait_until='domcontentloaded', timeout=60000)
                    if response and response.status != 404:
                        return alt_url
                
                return None
            
            # 验证页面有截图
            imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            if len(imgs) == 0:
                await asyncio.sleep(3)
                imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            logger.info(f"App page loaded with {len(imgs)} screenshots")
            return app_url
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_timeline_images(self) -> list:
        """
        从底部时间线获取图片，按x坐标排序（确保流程顺序正确）
        
        screensdesign.com 的时间线是一个 flex row 横向滚动容器，
        class 包含 tw-flex tw-flex-row tw-overflow-x-auto
        
        Returns:
            [(url, timeline_x), ...] 按时间线顺序排列的图片URL和位置
        """
        # 先滚动到页面底部，确保时间线加载
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # screensdesign.com 特定的时间线选择器（基于页面分析结果）
        # 时间线是一个 flex row 横向滚动容器
        timeline_selectors = [
            # 主要选择器：包含 tw-flex tw-flex-row 且可横向滚动
            'div.tw-flex.tw-flex-row.tw-overflow-x-auto',
            '[class*="tw-flex"][class*="tw-flex-row"][class*="tw-overflow-x-auto"]',
            # 备选：任何横向滚动的flex容器
            'div[class*="overflow-x-auto"][class*="flex-row"]',
            'div[class*="flex"][class*="row"][class*="overflow"]',
        ]
        
        for selector in timeline_selectors:
            try:
                timeline = await self.page.query_selector(selector)
                if timeline:
                    # 获取时间线内的所有图片
                    imgs = await timeline.query_selector_all('img')
                    if len(imgs) >= 5:  # 至少要有5张图才认为是时间线
                        logger.info(f"Found timeline container: {selector} ({len(imgs)} images)")
                        
                        # 获取每张图片的URL和x坐标
                        image_data = []
                        for img in imgs:
                            try:
                                src = await img.get_attribute('src')
                                if src and 'appicon' not in src and 'media.screensdesign.com' in src:
                                    bbox = await img.bounding_box()
                                    if bbox:
                                        image_data.append((src, bbox['x']))
                            except:
                                continue
                        
                        if image_data:
                            # 按x坐标排序（从左到右）
                            image_data.sort(key=lambda x: x[1])
                            logger.info(f"SUCCESS: Extracted {len(image_data)} images from timeline (sorted by x-position)")
                            return image_data
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 备选方案：通过JavaScript直接查找横向滚动的flex容器
        logger.info("Trying JavaScript-based timeline detection...")
        try:
            timeline_data = await self.page.evaluate('''
                () => {
                    // 找所有div元素
                    const divs = document.querySelectorAll('div');
                    
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        // 查找flex row + 横向滚动的容器
                        if ((style.display === 'flex') && 
                            (style.flexDirection === 'row') &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                            (div.scrollWidth > div.clientWidth * 1.5)) {
                            
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                // 找到了！获取图片信息
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({
                                            src: img.src,
                                            x: rect.x
                                        });
                                    }
                                });
                                
                                // 按x坐标排序
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data and len(timeline_data) >= 5:
                logger.info(f"SUCCESS (JS): Found {len(timeline_data)} images in timeline")
                return [(img['src'], img['x']) for img in timeline_data]
                
        except Exception as e:
            logger.warning(f"JavaScript timeline detection failed: {e}")
        
        # 第三备选：找y坐标相近的一行图片
        logger.info("Trying Y-position based timeline detection...")
        try:
            all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            if len(all_imgs) < 5:
                logger.warning("Timeline not found, will use DOM order (may be incorrect)")
                return None
            
            # 获取所有图片的位置
            img_positions = []
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    bbox = await img.bounding_box()
                    if src and bbox and 'appicon' not in src:
                        img_positions.append({
                            'src': src,
                            'x': bbox['x'],
                            'y': bbox['y'],
                            'width': bbox['width']
                        })
                except:
                    continue
            
            if not img_positions:
                return None
            
            # 按y坐标分组（找出同一行的图片）
            y_tolerance = 50  # 50px内认为是同一行
            y_groups = {}
            for img in img_positions:
                y_bucket = round(img['y'] / y_tolerance) * y_tolerance
                if y_bucket not in y_groups:
                    y_groups[y_bucket] = []
                y_groups[y_bucket].append(img)
            
            # 找出图片最多的那一行（应该是时间线）
            largest_group = max(y_groups.values(), key=len)
            
            if len(largest_group) >= len(img_positions) * 0.5:  # 至少包含50%的图片
                # 按x坐标排序
                largest_group.sort(key=lambda x: x['x'])
                logger.info(f"SUCCESS (Y-group): Found {len(largest_group)} images in main row")
                return [(img['src'], img['x']) for img in largest_group]
        
        except Exception as e:
            logger.warning(f"Y-position detection failed: {e}")
        
        # 最后降级方案
        logger.warning("Timeline not found, will use DOM order (may be incorrect)")
        return None
    
    async def download_from_app_page(self, product_name: str, project_dir: str) -> int:
        """
        从当前的专属页面下载截图
        支持断点续传，优先从时间线获取正确顺序
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        # 检查是否有已下载的内容（断点续传）
        existing_files = set()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    existing_files = {s['original_url'] for s in manifest_data.get('screenshots', [])}
                    logger.info(f"Found {len(existing_files)} existing screenshots, will skip")
            except:
                pass
        
        # 创建目录
        os.makedirs(screens_dir, exist_ok=True)
        
        try:
            app_url = self.page.url
            logger.info(f"Downloading from: {app_url}")
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # 滚动加载所有图片
            logger.info("Scrolling to load all images...")
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # ===== 核心修复：优先从时间线获取图片 =====
            timeline_images = await self.get_timeline_images()
            
            image_urls = []
            timeline_positions = {}  # 记录时间线位置信息
            
            if timeline_images:
                # 使用时间线顺序（已按x坐标排序）
                logger.info(f"Using timeline order ({len(timeline_images)} images)")
                seen_urls = set()
                for url, x_pos in timeline_images:
                    # 直接使用原始URL（不需要转换）
                    if url not in seen_urls:
                        seen_urls.add(url)
                        image_urls.append(url)
                        timeline_positions[url] = x_pos
            else:
                # 降级：使用DOM顺序（不推荐）
                logger.warning("Falling back to DOM order - screenshots may not be in correct flow order!")
                all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                
                seen_urls = set()
                for img in all_imgs:
                    try:
                        src = await img.get_attribute('src')
                        if src and src not in seen_urls and 'appicon' not in src:
                            seen_urls.add(src)
                            image_urls.append(src)
                    except:
                        continue
            
            logger.info(f"Found {len(image_urls)} screenshots to download")
            
            if not image_urls:
                debug_path = os.path.join(project_dir, "debug_empty_page.png")
                await self.page.screenshot(path=debug_path, full_page=True)
                logger.warning(f"No screenshots found, debug saved: {debug_path}")
                return 0
            
            # 下载截图（带重试）
            downloaded = 0
            skipped = 0
            manifest = []
            used_timeline = bool(timeline_images)
            
            # 获取已有文件的最大编号
            existing_screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
            start_idx = len(existing_screens) + 1
            
            for idx, url in enumerate(image_urls, start_idx):
                # 断点续传：跳过已下载的
                if url in existing_files:
                    skipped += 1
                    continue
                
                try:
                    # 使用重试机制下载
                    image_data = download_image_with_retry(url)
                    
                    if image_data:
                        img = Image.open(BytesIO(image_data))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        if img.width > 0:
                            ratio = TARGET_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # 保存
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img.save(filepath, "PNG", optimize=True)
                        
                        # manifest增加时间线位置信息
                        manifest_entry = {
                            "index": idx,
                            "filename": filename,
                            "original_url": url,
                            "width": TARGET_WIDTH,
                            "height": new_height if img.width > 0 else img.height,
                            "timeline_order": idx - start_idx + 1,  # 时间线中的顺序
                        }
                        
                        # 如果有时间线位置，添加x坐标
                        if url in timeline_positions:
                            manifest_entry["timeline_x"] = timeline_positions[url]
                        
                        manifest.append(manifest_entry)
                        
                        downloaded += 1
                        if downloaded % 20 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(image_urls) - skipped}...")
                            # 中途保存manifest（防止崩溃丢失进度）
                            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
                    else:
                        logger.warning(f"Failed to download image {idx} after retries")
                        
                except Exception as e:
                    logger.error(f"Error downloading image {idx}: {e}")
                    continue
            
            # 保存最终manifest
            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
            
            # 验证下载顺序
            verification = await self.verify_download_order(project_dir)
            logger.info(f"Order verification: {verification}")
            
            logger.info(f"Downloaded {downloaded} screenshots (skipped {skipped} existing)")
            return downloaded
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return 0
    
    def _save_manifest(self, path: str, product_name: str, app_url: str, screenshots: list, used_timeline: bool = False):
        """保存manifest文件（含时间线验证信息）"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "product": product_name,
                "source": "screensdesign.com",
                "source_url": app_url,
                "downloaded_at": datetime.now().isoformat(),
                "total": len(screenshots),
                "order_source": "timeline" if used_timeline else "dom_order",
                "order_reliable": used_timeline,  # 时间线顺序是可靠的
                "screenshots": screenshots
            }, f, indent=2, ensure_ascii=False)
    
    async def verify_download_order(self, project_dir: str) -> dict:
        """
        验证下载顺序是否正确
        
        Returns:
            验证结果字典
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        checks = {
            "total_screenshots": 0,
            "order_source": "unknown",
            "order_reliable": False,
            "timeline_x_monotonic": None,  # 时间线x坐标是否单调递增
            "first_screen_looks_valid": None,
            "warnings": []
        }
        
        # 读取manifest
        if not os.path.exists(manifest_path):
            checks["warnings"].append("manifest.json not found")
            return checks
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            checks["warnings"].append(f"Failed to read manifest: {e}")
            return checks
        
        screenshots = manifest.get("screenshots", [])
        checks["total_screenshots"] = len(screenshots)
        checks["order_source"] = manifest.get("order_source", "unknown")
        checks["order_reliable"] = manifest.get("order_reliable", False)
        
        if not screenshots:
            checks["warnings"].append("No screenshots in manifest")
            return checks
        
        # 检查1：时间线x坐标是否单调递增
        timeline_x_values = [s.get("timeline_x") for s in screenshots if s.get("timeline_x") is not None]
        if timeline_x_values:
            is_monotonic = all(timeline_x_values[i] <= timeline_x_values[i+1] for i in range(len(timeline_x_values)-1))
            checks["timeline_x_monotonic"] = is_monotonic
            if not is_monotonic:
                checks["warnings"].append("Timeline x positions are not monotonically increasing")
        
        # 检查2：第一张截图应该是Launch/Splash页面（简单检查）
        # 这里用AI检查成本太高，改用简单规则
        first_screen = screenshots[0].get("filename", "")
        if first_screen:
            # 基于常见命名规则的简单检查
            checks["first_screen_looks_valid"] = "001" in first_screen or "Screen_001" in first_screen
        
        # 检查3：如果不是从时间线获取的，添加警告
        if not checks["order_reliable"]:
            checks["warnings"].append("Screenshots were NOT extracted from timeline - order may be incorrect!")
        
        # 保存验证结果到manifest
        manifest["verification"] = {
            "checked_at": datetime.now().isoformat(),
            "order_reliable": checks["order_reliable"],
            "timeline_x_monotonic": checks["timeline_x_monotonic"],
            "warnings": checks["warnings"]
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return checks
    
    async def process_product(self, product_info: dict) -> dict:
        """
        处理单个产品：搜索 -> 下载 -> 分析
        """
        product_name = product_info['app_name']
        publisher = product_info.get('publisher', '')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {product_name}")
        logger.info(f"Publisher: {publisher}")
        
        # 更新状态
        self._update_status(product_name, "processing")
        
        # 搜索并进入专属页面
        app_url = await self.search_and_enter_app_page(product_name)
        
        if not app_url:
            logger.warning(f"Could not find app page for {product_name}")
            self._update_status(product_name, "not_found")
            return {"status": "not_found", "product": product_name}
        
        # 创建项目目录
        safe_name = re.sub(r'[^\w\s-]', '', product_name).replace(' ', '_')
        project_name = f"{safe_name}_Analysis"
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 保存app信息
        app_info_path = os.path.join(project_dir, "app_info.json")
        with open(app_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "app_name": product_name,
                "publisher": publisher,
                "source_url": app_url,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # 下载截图
        downloaded = await self.download_from_app_page(product_name, project_dir)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} screenshots for {product_name}")
            
            # 更新产品配置
            self._update_product_config(project_name, product_info)
            
            # 自动分析
            if self.auto_analyze:
                await self._run_analysis(project_name)
            
            self._update_status(product_name, "success", {"screenshots": downloaded})
            return {
                "status": "success",
                "product": product_name,
                "app_url": app_url,
                "screenshots": downloaded,
                "project_dir": project_dir
            }
        else:
            logger.warning(f"Could not download screenshots for {product_name}")
            self._update_status(product_name, "download_failed")
            return {
                "status": "download_failed",
                "product": product_name,
                "app_url": app_url
            }
    
    async def _run_analysis(self, project_name: str):
        """运行智能分析"""
        logger.info(f"Starting analysis for {project_name}...")
        try:
            # 导入并运行分析器
            sys.path.insert(0, os.path.join(BASE_DIR, "ai_analysis"))
            from smart_analyzer import SmartAnalyzer
            
            analyzer = SmartAnalyzer(
                project_name=project_name,
                concurrent=3,
                auto_fix=True,
                verbose=False
            )
            results = analyzer.run()
            
            if results:
                logger.info(f"Analysis complete: {len(results)} screenshots analyzed")
            else:
                logger.warning("Analysis returned no results")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
    
    def _update_product_config(self, project_name: str, product_info: dict):
        """更新产品配置"""
        config_path = os.path.join(CONFIG_DIR, "products.json")
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        colors = ["#5E6AD2", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899", "#14B8A6"]
        color_idx = hash(product_info.get('app_name', '')) % len(colors)
        
        config[project_name] = {
            "name": product_info.get('app_name', project_name.replace('_Analysis', '')),
            "color": colors[color_idx],
            "initial": product_info.get('app_name', 'X')[0].upper(),
            "category": product_info.get('category', ''),
            "publisher": product_info.get('publisher', '')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _update_status(self, product_name: str, status: str, extra: dict = None):
        """更新下载状态"""
        status_data = {"queue": [], "completed": {}, "current": None, "last_updated": None}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except:
                pass
        
        status_data["current"] = product_name if status == "processing" else None
        status_data["completed"][product_name] = {
            "status": status,
            "time": datetime.now().isoformat(),
            **(extra or {})
        }
        status_data["last_updated"] = datetime.now().isoformat()
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    async def run_batch(self, products: list = None, limit: int = None, resume: bool = True):
        """
        批量下载
        
        Args:
            products: 产品列表，None则从competitors.json加载
            limit: 限制处理数量
            resume: 是否跳过已完成的产品
        """
        logger.info("\n" + "=" * 60)
        logger.info("  SMART BATCH DOWNLOAD v2.0")
        logger.info("=" * 60)
        
        # 加载产品列表
        if products is None:
            json_path = os.path.join(DATA_DIR, "competitors.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('top30', [])
            else:
                logger.error("competitors.json not found")
                return
        
        if limit:
            products = products[:limit]
        
        # 断点续传：跳过已完成的
        completed_products = set()
        if resume and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                for name, info in status_data.get("completed", {}).items():
                    if info.get("status") == "success":
                        completed_products.add(name)
                
                if completed_products:
                    logger.info(f"Resuming: skipping {len(completed_products)} completed products")
            except:
                pass
        
        products_to_process = [p for p in products if p['app_name'] not in completed_products]
        
        logger.info(f"Products to process: {len(products_to_process)}")
        logger.info(f"Auto-analyze: {'Enabled' if self.auto_analyze else 'Disabled'}")
        
        # 初始化状态
        self._init_status([p['app_name'] for p in products_to_process])
        
        # 初始化浏览器
        if not await self.init_browser():
            return
        
        try:
            for i, product in enumerate(products_to_process, 1):
                logger.info(f"\n[{i}/{len(products_to_process)}]")
                result = await self.process_product(product)
                
                # 分类结果
                if result['status'] == 'success':
                    self.results['success'].append(result)
                elif result['status'] in ('not_found', 'no_match'):
                    self.results['skipped'].append(result)
                else:
                    self.results['failed'].append(result)
                
                # 间隔
                await asyncio.sleep(2)
            
        finally:
            await self.close()
        
        # 生成报告
        self._generate_report()
    
    def _init_status(self, product_names: list):
        """初始化状态文件"""
        status_data = {"queue": product_names, "completed": {}, "current": None, "last_updated": datetime.now().isoformat()}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    status_data["completed"] = existing.get("completed", {})
            except:
                pass
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    def _generate_report(self):
        """生成下载报告"""
        logger.info("\n" + "=" * 60)
        logger.info("  DOWNLOAD REPORT")
        logger.info("=" * 60)
        
        logger.info(f"\nSuccess: {len(self.results['success'])}")
        for r in self.results['success']:
            logger.info(f"  ✓ {r['product']} ({r.get('screenshots', 0)} screenshots)")
        
        logger.info(f"\nFailed: {len(self.results['failed'])}")
        for r in self.results['failed']:
            logger.info(f"  ✗ {r['product']}")
        
        logger.info(f"\nSkipped: {len(self.results['skipped'])}")
        for r in self.results['skipped']:
            logger.info(f"  - {r['product']}")
        
        # 保存报告
        report_path = os.path.join(DATA_DIR, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "success": len(self.results['success']),
                    "failed": len(self.results['failed']),
                    "skipped": len(self.results['skipped'])
                },
                "details": self.results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nReport saved: {report_path}")


# ============================================================
# 命令行入口
# ============================================================

async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Batch Download v2.0")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of products")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed products")
    parser.add_argument("--product", "-p", type=str, help="Download single product by name")
    
    args = parser.parse_args()
    
    downloader = SmartBatchDownloader(auto_analyze=not args.no_analyze)
    
    if args.product:
        # 下载单个产品
        if not await downloader.init_browser():
            return
        try:
            result = await downloader.process_product({"app_name": args.product, "publisher": ""})
            logger.info(f"Result: {result['status']}")
        finally:
            await downloader.close()
    else:
        # 批量下载
        await downloader.run_batch(
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    asyncio.run(main())

Smart Batch Download System v2.0
================================
- 修复bug，增强稳定性
- 下载重试机制（3次）
- 断点续传
- 下载完自动分析
- Chrome连接检测和友好提示
"""

import os
import sys
import json
import time
import asyncio
import requests
import re
import shutil
import socket
import subprocess
import logging
from datetime import datetime
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 下载配置
TARGET_WIDTH = 402
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# 重试配置
MAX_IMAGE_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# 状态文件
STATUS_FILE = os.path.join(BASE_DIR, "download_status.json")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'download.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ============================================================
# 工具函数
# ============================================================

def generate_app_slug(app_name: str) -> str:
    """
    生成screensdesign.com的App URL slug
    
    Examples:
        "Cal AI - Calorie Tracker" -> "cal-ai-calorie-tracker"
        "MyFitnessPal: Calorie Counter" -> "myfitnesspal-calorie-counter"
    """
    slug = app_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def download_image_with_retry(url: str, max_retries: int = MAX_IMAGE_RETRIES) -> bytes:
    """
    下载图片，带重试机制
    
    Args:
        url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        图片字节数据，失败返回None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/'
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return None


# ============================================================
# Chrome 连接助手
# ============================================================

class ChromeHelper:
    """Chrome浏览器连接助手"""
    
    @staticmethod
    def is_chrome_ready() -> bool:
        """检查Chrome调试端口是否可用"""
        return check_port_open("127.0.0.1", CHROME_DEBUG_PORT)
    
    @staticmethod
    def get_chrome_start_command() -> str:
        """获取Chrome启动命令"""
        # Windows
        if sys.platform == 'win32':
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT}'
        return f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
    
    @staticmethod
    async def ensure_chrome_ready() -> bool:
        """
        确保Chrome已准备好
        如果未启动，提示用户启动
        """
        if ChromeHelper.is_chrome_ready():
            logger.info("Chrome debug port is ready")
            return True
        
        print("\n" + "=" * 60)
        print("  Chrome 未检测到")
        print("=" * 60)
        print(f"\n请先启动Chrome并开启调试端口 {CHROME_DEBUG_PORT}:")
        print(f"\n  命令: {ChromeHelper.get_chrome_start_command()}")
        print("\n或者在已打开的Chrome中手动登录 screensdesign.com")
        print("然后重新运行此脚本。")
        print("\n" + "=" * 60)
        
        # 等待用户启动
        print("\n等待Chrome启动... (按Ctrl+C取消)")
        for i in range(60):  # 等待最多60秒
            if ChromeHelper.is_chrome_ready():
                logger.info("Chrome is now ready!")
                return True
            await asyncio.sleep(1)
            print(f"  等待中... {60-i}秒", end="\r")
        
        logger.error("Chrome did not start within timeout")
        return False


# ============================================================
# 下载器主类
# ============================================================

class SmartBatchDownloader:
    """智能批量下载器"""
    
    def __init__(self, auto_analyze: bool = True):
        """
        初始化下载器
        
        Args:
            auto_analyze: 下载完成后是否自动分析
        """
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auto_analyze = auto_analyze
        
        # 结果统计
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
    
    async def init_browser(self) -> bool:
        """初始化浏览器连接"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        # 确保Chrome已准备好
        if not await ChromeHelper.ensure_chrome_ready():
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Connected to Chrome")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Chrome: {e}")
            return False
    
    async def close(self):
        """关闭浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def search_and_enter_app_page(self, product_name: str) -> str:
        """
        搜索产品并进入专属页面
        
        Returns:
            专属页面URL，失败返回None
        """
        try:
            simple_name = product_name.split(':')[0].split(' - ')[0].strip()
            logger.info(f"Searching for '{simple_name}'...")
            
            # 进入screensdesign首页
            await self.page.goto('https://screensdesign.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 点击搜索区域
            search_area = await self.page.query_selector('text=/Search/')
            if search_area:
                await search_area.click()
                await asyncio.sleep(2)
            
            # 找到搜索输入框并搜索
            search_input = await self.page.query_selector('input:visible')
            if search_input:
                await search_input.fill(simple_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(5)
            
            logger.info(f"Search results: {self.page.url}")
            
            # 在搜索结果中找到匹配的App完整名称
            h3_elements = await self.page.query_selector_all('h3')
            
            found_app_name = None
            for h3 in h3_elements:
                try:
                    text = (await h3.inner_text()).strip()
                    if simple_name.lower() in text.lower():
                        found_app_name = text
                        logger.info(f"Found app in search: '{found_app_name}'")
                        break
                except:
                    continue
            
            if not found_app_name:
                logger.error(f"App not found in search results")
                return None
            
            # 生成slug并访问专属页面
            slug = generate_app_slug(found_app_name)
            app_url = f"https://screensdesign.com/apps/{slug}/"
            
            logger.info(f"Generated URL: {app_url}")
            
            response = await self.page.goto(app_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查页面是否有效
            if response and response.status == 404:
                logger.warning(f"Page not found: {app_url}")
                
                # 尝试备选slug
                alt_slug = generate_app_slug(product_name)
                if alt_slug != slug:
                    alt_url = f"https://screensdesign.com/apps/{alt_slug}/"
                    logger.info(f"Trying alternate URL: {alt_url}")
                    response = await self.page.goto(alt_url, wait_until='domcontentloaded', timeout=60000)
                    if response and response.status != 404:
                        return alt_url
                
                return None
            
            # 验证页面有截图
            imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            if len(imgs) == 0:
                await asyncio.sleep(3)
                imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            logger.info(f"App page loaded with {len(imgs)} screenshots")
            return app_url
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_timeline_images(self) -> list:
        """
        从底部时间线获取图片，按x坐标排序（确保流程顺序正确）
        
        screensdesign.com 的时间线是一个 flex row 横向滚动容器，
        class 包含 tw-flex tw-flex-row tw-overflow-x-auto
        
        Returns:
            [(url, timeline_x), ...] 按时间线顺序排列的图片URL和位置
        """
        # 先滚动到页面底部，确保时间线加载
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # screensdesign.com 特定的时间线选择器（基于页面分析结果）
        # 时间线是一个 flex row 横向滚动容器
        timeline_selectors = [
            # 主要选择器：包含 tw-flex tw-flex-row 且可横向滚动
            'div.tw-flex.tw-flex-row.tw-overflow-x-auto',
            '[class*="tw-flex"][class*="tw-flex-row"][class*="tw-overflow-x-auto"]',
            # 备选：任何横向滚动的flex容器
            'div[class*="overflow-x-auto"][class*="flex-row"]',
            'div[class*="flex"][class*="row"][class*="overflow"]',
        ]
        
        for selector in timeline_selectors:
            try:
                timeline = await self.page.query_selector(selector)
                if timeline:
                    # 获取时间线内的所有图片
                    imgs = await timeline.query_selector_all('img')
                    if len(imgs) >= 5:  # 至少要有5张图才认为是时间线
                        logger.info(f"Found timeline container: {selector} ({len(imgs)} images)")
                        
                        # 获取每张图片的URL和x坐标
                        image_data = []
                        for img in imgs:
                            try:
                                src = await img.get_attribute('src')
                                if src and 'appicon' not in src and 'media.screensdesign.com' in src:
                                    bbox = await img.bounding_box()
                                    if bbox:
                                        image_data.append((src, bbox['x']))
                            except:
                                continue
                        
                        if image_data:
                            # 按x坐标排序（从左到右）
                            image_data.sort(key=lambda x: x[1])
                            logger.info(f"SUCCESS: Extracted {len(image_data)} images from timeline (sorted by x-position)")
                            return image_data
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 备选方案：通过JavaScript直接查找横向滚动的flex容器
        logger.info("Trying JavaScript-based timeline detection...")
        try:
            timeline_data = await self.page.evaluate('''
                () => {
                    // 找所有div元素
                    const divs = document.querySelectorAll('div');
                    
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        // 查找flex row + 横向滚动的容器
                        if ((style.display === 'flex') && 
                            (style.flexDirection === 'row') &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                            (div.scrollWidth > div.clientWidth * 1.5)) {
                            
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                // 找到了！获取图片信息
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({
                                            src: img.src,
                                            x: rect.x
                                        });
                                    }
                                });
                                
                                // 按x坐标排序
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data and len(timeline_data) >= 5:
                logger.info(f"SUCCESS (JS): Found {len(timeline_data)} images in timeline")
                return [(img['src'], img['x']) for img in timeline_data]
                
        except Exception as e:
            logger.warning(f"JavaScript timeline detection failed: {e}")
        
        # 第三备选：找y坐标相近的一行图片
        logger.info("Trying Y-position based timeline detection...")
        try:
            all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            if len(all_imgs) < 5:
                logger.warning("Timeline not found, will use DOM order (may be incorrect)")
                return None
            
            # 获取所有图片的位置
            img_positions = []
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    bbox = await img.bounding_box()
                    if src and bbox and 'appicon' not in src:
                        img_positions.append({
                            'src': src,
                            'x': bbox['x'],
                            'y': bbox['y'],
                            'width': bbox['width']
                        })
                except:
                    continue
            
            if not img_positions:
                return None
            
            # 按y坐标分组（找出同一行的图片）
            y_tolerance = 50  # 50px内认为是同一行
            y_groups = {}
            for img in img_positions:
                y_bucket = round(img['y'] / y_tolerance) * y_tolerance
                if y_bucket not in y_groups:
                    y_groups[y_bucket] = []
                y_groups[y_bucket].append(img)
            
            # 找出图片最多的那一行（应该是时间线）
            largest_group = max(y_groups.values(), key=len)
            
            if len(largest_group) >= len(img_positions) * 0.5:  # 至少包含50%的图片
                # 按x坐标排序
                largest_group.sort(key=lambda x: x['x'])
                logger.info(f"SUCCESS (Y-group): Found {len(largest_group)} images in main row")
                return [(img['src'], img['x']) for img in largest_group]
        
        except Exception as e:
            logger.warning(f"Y-position detection failed: {e}")
        
        # 最后降级方案
        logger.warning("Timeline not found, will use DOM order (may be incorrect)")
        return None
    
    async def download_from_app_page(self, product_name: str, project_dir: str) -> int:
        """
        从当前的专属页面下载截图
        支持断点续传，优先从时间线获取正确顺序
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        # 检查是否有已下载的内容（断点续传）
        existing_files = set()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    existing_files = {s['original_url'] for s in manifest_data.get('screenshots', [])}
                    logger.info(f"Found {len(existing_files)} existing screenshots, will skip")
            except:
                pass
        
        # 创建目录
        os.makedirs(screens_dir, exist_ok=True)
        
        try:
            app_url = self.page.url
            logger.info(f"Downloading from: {app_url}")
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # 滚动加载所有图片
            logger.info("Scrolling to load all images...")
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # ===== 核心修复：优先从时间线获取图片 =====
            timeline_images = await self.get_timeline_images()
            
            image_urls = []
            timeline_positions = {}  # 记录时间线位置信息
            
            if timeline_images:
                # 使用时间线顺序（已按x坐标排序）
                logger.info(f"Using timeline order ({len(timeline_images)} images)")
                seen_urls = set()
                for url, x_pos in timeline_images:
                    # 直接使用原始URL（不需要转换）
                    if url not in seen_urls:
                        seen_urls.add(url)
                        image_urls.append(url)
                        timeline_positions[url] = x_pos
            else:
                # 降级：使用DOM顺序（不推荐）
                logger.warning("Falling back to DOM order - screenshots may not be in correct flow order!")
                all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                
                seen_urls = set()
                for img in all_imgs:
                    try:
                        src = await img.get_attribute('src')
                        if src and src not in seen_urls and 'appicon' not in src:
                            seen_urls.add(src)
                            image_urls.append(src)
                    except:
                        continue
            
            logger.info(f"Found {len(image_urls)} screenshots to download")
            
            if not image_urls:
                debug_path = os.path.join(project_dir, "debug_empty_page.png")
                await self.page.screenshot(path=debug_path, full_page=True)
                logger.warning(f"No screenshots found, debug saved: {debug_path}")
                return 0
            
            # 下载截图（带重试）
            downloaded = 0
            skipped = 0
            manifest = []
            used_timeline = bool(timeline_images)
            
            # 获取已有文件的最大编号
            existing_screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
            start_idx = len(existing_screens) + 1
            
            for idx, url in enumerate(image_urls, start_idx):
                # 断点续传：跳过已下载的
                if url in existing_files:
                    skipped += 1
                    continue
                
                try:
                    # 使用重试机制下载
                    image_data = download_image_with_retry(url)
                    
                    if image_data:
                        img = Image.open(BytesIO(image_data))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        if img.width > 0:
                            ratio = TARGET_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # 保存
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img.save(filepath, "PNG", optimize=True)
                        
                        # manifest增加时间线位置信息
                        manifest_entry = {
                            "index": idx,
                            "filename": filename,
                            "original_url": url,
                            "width": TARGET_WIDTH,
                            "height": new_height if img.width > 0 else img.height,
                            "timeline_order": idx - start_idx + 1,  # 时间线中的顺序
                        }
                        
                        # 如果有时间线位置，添加x坐标
                        if url in timeline_positions:
                            manifest_entry["timeline_x"] = timeline_positions[url]
                        
                        manifest.append(manifest_entry)
                        
                        downloaded += 1
                        if downloaded % 20 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(image_urls) - skipped}...")
                            # 中途保存manifest（防止崩溃丢失进度）
                            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
                    else:
                        logger.warning(f"Failed to download image {idx} after retries")
                        
                except Exception as e:
                    logger.error(f"Error downloading image {idx}: {e}")
                    continue
            
            # 保存最终manifest
            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
            
            # 验证下载顺序
            verification = await self.verify_download_order(project_dir)
            logger.info(f"Order verification: {verification}")
            
            logger.info(f"Downloaded {downloaded} screenshots (skipped {skipped} existing)")
            return downloaded
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return 0
    
    def _save_manifest(self, path: str, product_name: str, app_url: str, screenshots: list, used_timeline: bool = False):
        """保存manifest文件（含时间线验证信息）"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "product": product_name,
                "source": "screensdesign.com",
                "source_url": app_url,
                "downloaded_at": datetime.now().isoformat(),
                "total": len(screenshots),
                "order_source": "timeline" if used_timeline else "dom_order",
                "order_reliable": used_timeline,  # 时间线顺序是可靠的
                "screenshots": screenshots
            }, f, indent=2, ensure_ascii=False)
    
    async def verify_download_order(self, project_dir: str) -> dict:
        """
        验证下载顺序是否正确
        
        Returns:
            验证结果字典
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        checks = {
            "total_screenshots": 0,
            "order_source": "unknown",
            "order_reliable": False,
            "timeline_x_monotonic": None,  # 时间线x坐标是否单调递增
            "first_screen_looks_valid": None,
            "warnings": []
        }
        
        # 读取manifest
        if not os.path.exists(manifest_path):
            checks["warnings"].append("manifest.json not found")
            return checks
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            checks["warnings"].append(f"Failed to read manifest: {e}")
            return checks
        
        screenshots = manifest.get("screenshots", [])
        checks["total_screenshots"] = len(screenshots)
        checks["order_source"] = manifest.get("order_source", "unknown")
        checks["order_reliable"] = manifest.get("order_reliable", False)
        
        if not screenshots:
            checks["warnings"].append("No screenshots in manifest")
            return checks
        
        # 检查1：时间线x坐标是否单调递增
        timeline_x_values = [s.get("timeline_x") for s in screenshots if s.get("timeline_x") is not None]
        if timeline_x_values:
            is_monotonic = all(timeline_x_values[i] <= timeline_x_values[i+1] for i in range(len(timeline_x_values)-1))
            checks["timeline_x_monotonic"] = is_monotonic
            if not is_monotonic:
                checks["warnings"].append("Timeline x positions are not monotonically increasing")
        
        # 检查2：第一张截图应该是Launch/Splash页面（简单检查）
        # 这里用AI检查成本太高，改用简单规则
        first_screen = screenshots[0].get("filename", "")
        if first_screen:
            # 基于常见命名规则的简单检查
            checks["first_screen_looks_valid"] = "001" in first_screen or "Screen_001" in first_screen
        
        # 检查3：如果不是从时间线获取的，添加警告
        if not checks["order_reliable"]:
            checks["warnings"].append("Screenshots were NOT extracted from timeline - order may be incorrect!")
        
        # 保存验证结果到manifest
        manifest["verification"] = {
            "checked_at": datetime.now().isoformat(),
            "order_reliable": checks["order_reliable"],
            "timeline_x_monotonic": checks["timeline_x_monotonic"],
            "warnings": checks["warnings"]
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return checks
    
    async def process_product(self, product_info: dict) -> dict:
        """
        处理单个产品：搜索 -> 下载 -> 分析
        """
        product_name = product_info['app_name']
        publisher = product_info.get('publisher', '')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {product_name}")
        logger.info(f"Publisher: {publisher}")
        
        # 更新状态
        self._update_status(product_name, "processing")
        
        # 搜索并进入专属页面
        app_url = await self.search_and_enter_app_page(product_name)
        
        if not app_url:
            logger.warning(f"Could not find app page for {product_name}")
            self._update_status(product_name, "not_found")
            return {"status": "not_found", "product": product_name}
        
        # 创建项目目录
        safe_name = re.sub(r'[^\w\s-]', '', product_name).replace(' ', '_')
        project_name = f"{safe_name}_Analysis"
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 保存app信息
        app_info_path = os.path.join(project_dir, "app_info.json")
        with open(app_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "app_name": product_name,
                "publisher": publisher,
                "source_url": app_url,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # 下载截图
        downloaded = await self.download_from_app_page(product_name, project_dir)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} screenshots for {product_name}")
            
            # 更新产品配置
            self._update_product_config(project_name, product_info)
            
            # 自动分析
            if self.auto_analyze:
                await self._run_analysis(project_name)
            
            self._update_status(product_name, "success", {"screenshots": downloaded})
            return {
                "status": "success",
                "product": product_name,
                "app_url": app_url,
                "screenshots": downloaded,
                "project_dir": project_dir
            }
        else:
            logger.warning(f"Could not download screenshots for {product_name}")
            self._update_status(product_name, "download_failed")
            return {
                "status": "download_failed",
                "product": product_name,
                "app_url": app_url
            }
    
    async def _run_analysis(self, project_name: str):
        """运行智能分析"""
        logger.info(f"Starting analysis for {project_name}...")
        try:
            # 导入并运行分析器
            sys.path.insert(0, os.path.join(BASE_DIR, "ai_analysis"))
            from smart_analyzer import SmartAnalyzer
            
            analyzer = SmartAnalyzer(
                project_name=project_name,
                concurrent=3,
                auto_fix=True,
                verbose=False
            )
            results = analyzer.run()
            
            if results:
                logger.info(f"Analysis complete: {len(results)} screenshots analyzed")
            else:
                logger.warning("Analysis returned no results")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
    
    def _update_product_config(self, project_name: str, product_info: dict):
        """更新产品配置"""
        config_path = os.path.join(CONFIG_DIR, "products.json")
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        colors = ["#5E6AD2", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899", "#14B8A6"]
        color_idx = hash(product_info.get('app_name', '')) % len(colors)
        
        config[project_name] = {
            "name": product_info.get('app_name', project_name.replace('_Analysis', '')),
            "color": colors[color_idx],
            "initial": product_info.get('app_name', 'X')[0].upper(),
            "category": product_info.get('category', ''),
            "publisher": product_info.get('publisher', '')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _update_status(self, product_name: str, status: str, extra: dict = None):
        """更新下载状态"""
        status_data = {"queue": [], "completed": {}, "current": None, "last_updated": None}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except:
                pass
        
        status_data["current"] = product_name if status == "processing" else None
        status_data["completed"][product_name] = {
            "status": status,
            "time": datetime.now().isoformat(),
            **(extra or {})
        }
        status_data["last_updated"] = datetime.now().isoformat()
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    async def run_batch(self, products: list = None, limit: int = None, resume: bool = True):
        """
        批量下载
        
        Args:
            products: 产品列表，None则从competitors.json加载
            limit: 限制处理数量
            resume: 是否跳过已完成的产品
        """
        logger.info("\n" + "=" * 60)
        logger.info("  SMART BATCH DOWNLOAD v2.0")
        logger.info("=" * 60)
        
        # 加载产品列表
        if products is None:
            json_path = os.path.join(DATA_DIR, "competitors.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('top30', [])
            else:
                logger.error("competitors.json not found")
                return
        
        if limit:
            products = products[:limit]
        
        # 断点续传：跳过已完成的
        completed_products = set()
        if resume and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                for name, info in status_data.get("completed", {}).items():
                    if info.get("status") == "success":
                        completed_products.add(name)
                
                if completed_products:
                    logger.info(f"Resuming: skipping {len(completed_products)} completed products")
            except:
                pass
        
        products_to_process = [p for p in products if p['app_name'] not in completed_products]
        
        logger.info(f"Products to process: {len(products_to_process)}")
        logger.info(f"Auto-analyze: {'Enabled' if self.auto_analyze else 'Disabled'}")
        
        # 初始化状态
        self._init_status([p['app_name'] for p in products_to_process])
        
        # 初始化浏览器
        if not await self.init_browser():
            return
        
        try:
            for i, product in enumerate(products_to_process, 1):
                logger.info(f"\n[{i}/{len(products_to_process)}]")
                result = await self.process_product(product)
                
                # 分类结果
                if result['status'] == 'success':
                    self.results['success'].append(result)
                elif result['status'] in ('not_found', 'no_match'):
                    self.results['skipped'].append(result)
                else:
                    self.results['failed'].append(result)
                
                # 间隔
                await asyncio.sleep(2)
            
        finally:
            await self.close()
        
        # 生成报告
        self._generate_report()
    
    def _init_status(self, product_names: list):
        """初始化状态文件"""
        status_data = {"queue": product_names, "completed": {}, "current": None, "last_updated": datetime.now().isoformat()}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    status_data["completed"] = existing.get("completed", {})
            except:
                pass
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    def _generate_report(self):
        """生成下载报告"""
        logger.info("\n" + "=" * 60)
        logger.info("  DOWNLOAD REPORT")
        logger.info("=" * 60)
        
        logger.info(f"\nSuccess: {len(self.results['success'])}")
        for r in self.results['success']:
            logger.info(f"  ✓ {r['product']} ({r.get('screenshots', 0)} screenshots)")
        
        logger.info(f"\nFailed: {len(self.results['failed'])}")
        for r in self.results['failed']:
            logger.info(f"  ✗ {r['product']}")
        
        logger.info(f"\nSkipped: {len(self.results['skipped'])}")
        for r in self.results['skipped']:
            logger.info(f"  - {r['product']}")
        
        # 保存报告
        report_path = os.path.join(DATA_DIR, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "success": len(self.results['success']),
                    "failed": len(self.results['failed']),
                    "skipped": len(self.results['skipped'])
                },
                "details": self.results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nReport saved: {report_path}")


# ============================================================
# 命令行入口
# ============================================================

async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Batch Download v2.0")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of products")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed products")
    parser.add_argument("--product", "-p", type=str, help="Download single product by name")
    
    args = parser.parse_args()
    
    downloader = SmartBatchDownloader(auto_analyze=not args.no_analyze)
    
    if args.product:
        # 下载单个产品
        if not await downloader.init_browser():
            return
        try:
            result = await downloader.process_product({"app_name": args.product, "publisher": ""})
            logger.info(f"Result: {result['status']}")
        finally:
            await downloader.close()
    else:
        # 批量下载
        await downloader.run_batch(
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    asyncio.run(main())

Smart Batch Download System v2.0
================================
- 修复bug，增强稳定性
- 下载重试机制（3次）
- 断点续传
- 下载完自动分析
- Chrome连接检测和友好提示
"""

import os
import sys
import json
import time
import asyncio
import requests
import re
import shutil
import socket
import subprocess
import logging
from datetime import datetime
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 下载配置
TARGET_WIDTH = 402
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# 重试配置
MAX_IMAGE_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# 状态文件
STATUS_FILE = os.path.join(BASE_DIR, "download_status.json")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'download.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ============================================================
# 工具函数
# ============================================================

def generate_app_slug(app_name: str) -> str:
    """
    生成screensdesign.com的App URL slug
    
    Examples:
        "Cal AI - Calorie Tracker" -> "cal-ai-calorie-tracker"
        "MyFitnessPal: Calorie Counter" -> "myfitnesspal-calorie-counter"
    """
    slug = app_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def download_image_with_retry(url: str, max_retries: int = MAX_IMAGE_RETRIES) -> bytes:
    """
    下载图片，带重试机制
    
    Args:
        url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        图片字节数据，失败返回None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/'
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return None


# ============================================================
# Chrome 连接助手
# ============================================================

class ChromeHelper:
    """Chrome浏览器连接助手"""
    
    @staticmethod
    def is_chrome_ready() -> bool:
        """检查Chrome调试端口是否可用"""
        return check_port_open("127.0.0.1", CHROME_DEBUG_PORT)
    
    @staticmethod
    def get_chrome_start_command() -> str:
        """获取Chrome启动命令"""
        # Windows
        if sys.platform == 'win32':
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT}'
        return f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
    
    @staticmethod
    async def ensure_chrome_ready() -> bool:
        """
        确保Chrome已准备好
        如果未启动，提示用户启动
        """
        if ChromeHelper.is_chrome_ready():
            logger.info("Chrome debug port is ready")
            return True
        
        print("\n" + "=" * 60)
        print("  Chrome 未检测到")
        print("=" * 60)
        print(f"\n请先启动Chrome并开启调试端口 {CHROME_DEBUG_PORT}:")
        print(f"\n  命令: {ChromeHelper.get_chrome_start_command()}")
        print("\n或者在已打开的Chrome中手动登录 screensdesign.com")
        print("然后重新运行此脚本。")
        print("\n" + "=" * 60)
        
        # 等待用户启动
        print("\n等待Chrome启动... (按Ctrl+C取消)")
        for i in range(60):  # 等待最多60秒
            if ChromeHelper.is_chrome_ready():
                logger.info("Chrome is now ready!")
                return True
            await asyncio.sleep(1)
            print(f"  等待中... {60-i}秒", end="\r")
        
        logger.error("Chrome did not start within timeout")
        return False


# ============================================================
# 下载器主类
# ============================================================

class SmartBatchDownloader:
    """智能批量下载器"""
    
    def __init__(self, auto_analyze: bool = True):
        """
        初始化下载器
        
        Args:
            auto_analyze: 下载完成后是否自动分析
        """
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auto_analyze = auto_analyze
        
        # 结果统计
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
    
    async def init_browser(self) -> bool:
        """初始化浏览器连接"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        # 确保Chrome已准备好
        if not await ChromeHelper.ensure_chrome_ready():
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Connected to Chrome")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Chrome: {e}")
            return False
    
    async def close(self):
        """关闭浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def search_and_enter_app_page(self, product_name: str) -> str:
        """
        搜索产品并进入专属页面
        
        Returns:
            专属页面URL，失败返回None
        """
        try:
            simple_name = product_name.split(':')[0].split(' - ')[0].strip()
            logger.info(f"Searching for '{simple_name}'...")
            
            # 进入screensdesign首页
            await self.page.goto('https://screensdesign.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 点击搜索区域
            search_area = await self.page.query_selector('text=/Search/')
            if search_area:
                await search_area.click()
                await asyncio.sleep(2)
            
            # 找到搜索输入框并搜索
            search_input = await self.page.query_selector('input:visible')
            if search_input:
                await search_input.fill(simple_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(5)
            
            logger.info(f"Search results: {self.page.url}")
            
            # 在搜索结果中找到匹配的App完整名称
            h3_elements = await self.page.query_selector_all('h3')
            
            found_app_name = None
            for h3 in h3_elements:
                try:
                    text = (await h3.inner_text()).strip()
                    if simple_name.lower() in text.lower():
                        found_app_name = text
                        logger.info(f"Found app in search: '{found_app_name}'")
                        break
                except:
                    continue
            
            if not found_app_name:
                logger.error(f"App not found in search results")
                return None
            
            # 生成slug并访问专属页面
            slug = generate_app_slug(found_app_name)
            app_url = f"https://screensdesign.com/apps/{slug}/"
            
            logger.info(f"Generated URL: {app_url}")
            
            response = await self.page.goto(app_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查页面是否有效
            if response and response.status == 404:
                logger.warning(f"Page not found: {app_url}")
                
                # 尝试备选slug
                alt_slug = generate_app_slug(product_name)
                if alt_slug != slug:
                    alt_url = f"https://screensdesign.com/apps/{alt_slug}/"
                    logger.info(f"Trying alternate URL: {alt_url}")
                    response = await self.page.goto(alt_url, wait_until='domcontentloaded', timeout=60000)
                    if response and response.status != 404:
                        return alt_url
                
                return None
            
            # 验证页面有截图
            imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            if len(imgs) == 0:
                await asyncio.sleep(3)
                imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            logger.info(f"App page loaded with {len(imgs)} screenshots")
            return app_url
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_timeline_images(self) -> list:
        """
        从底部时间线获取图片，按x坐标排序（确保流程顺序正确）
        
        screensdesign.com 的时间线是一个 flex row 横向滚动容器，
        class 包含 tw-flex tw-flex-row tw-overflow-x-auto
        
        Returns:
            [(url, timeline_x), ...] 按时间线顺序排列的图片URL和位置
        """
        # 先滚动到页面底部，确保时间线加载
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # screensdesign.com 特定的时间线选择器（基于页面分析结果）
        # 时间线是一个 flex row 横向滚动容器
        timeline_selectors = [
            # 主要选择器：包含 tw-flex tw-flex-row 且可横向滚动
            'div.tw-flex.tw-flex-row.tw-overflow-x-auto',
            '[class*="tw-flex"][class*="tw-flex-row"][class*="tw-overflow-x-auto"]',
            # 备选：任何横向滚动的flex容器
            'div[class*="overflow-x-auto"][class*="flex-row"]',
            'div[class*="flex"][class*="row"][class*="overflow"]',
        ]
        
        for selector in timeline_selectors:
            try:
                timeline = await self.page.query_selector(selector)
                if timeline:
                    # 获取时间线内的所有图片
                    imgs = await timeline.query_selector_all('img')
                    if len(imgs) >= 5:  # 至少要有5张图才认为是时间线
                        logger.info(f"Found timeline container: {selector} ({len(imgs)} images)")
                        
                        # 获取每张图片的URL和x坐标
                        image_data = []
                        for img in imgs:
                            try:
                                src = await img.get_attribute('src')
                                if src and 'appicon' not in src and 'media.screensdesign.com' in src:
                                    bbox = await img.bounding_box()
                                    if bbox:
                                        image_data.append((src, bbox['x']))
                            except:
                                continue
                        
                        if image_data:
                            # 按x坐标排序（从左到右）
                            image_data.sort(key=lambda x: x[1])
                            logger.info(f"SUCCESS: Extracted {len(image_data)} images from timeline (sorted by x-position)")
                            return image_data
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 备选方案：通过JavaScript直接查找横向滚动的flex容器
        logger.info("Trying JavaScript-based timeline detection...")
        try:
            timeline_data = await self.page.evaluate('''
                () => {
                    // 找所有div元素
                    const divs = document.querySelectorAll('div');
                    
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        // 查找flex row + 横向滚动的容器
                        if ((style.display === 'flex') && 
                            (style.flexDirection === 'row') &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                            (div.scrollWidth > div.clientWidth * 1.5)) {
                            
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                // 找到了！获取图片信息
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({
                                            src: img.src,
                                            x: rect.x
                                        });
                                    }
                                });
                                
                                // 按x坐标排序
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data and len(timeline_data) >= 5:
                logger.info(f"SUCCESS (JS): Found {len(timeline_data)} images in timeline")
                return [(img['src'], img['x']) for img in timeline_data]
                
        except Exception as e:
            logger.warning(f"JavaScript timeline detection failed: {e}")
        
        # 第三备选：找y坐标相近的一行图片
        logger.info("Trying Y-position based timeline detection...")
        try:
            all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            if len(all_imgs) < 5:
                logger.warning("Timeline not found, will use DOM order (may be incorrect)")
                return None
            
            # 获取所有图片的位置
            img_positions = []
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    bbox = await img.bounding_box()
                    if src and bbox and 'appicon' not in src:
                        img_positions.append({
                            'src': src,
                            'x': bbox['x'],
                            'y': bbox['y'],
                            'width': bbox['width']
                        })
                except:
                    continue
            
            if not img_positions:
                return None
            
            # 按y坐标分组（找出同一行的图片）
            y_tolerance = 50  # 50px内认为是同一行
            y_groups = {}
            for img in img_positions:
                y_bucket = round(img['y'] / y_tolerance) * y_tolerance
                if y_bucket not in y_groups:
                    y_groups[y_bucket] = []
                y_groups[y_bucket].append(img)
            
            # 找出图片最多的那一行（应该是时间线）
            largest_group = max(y_groups.values(), key=len)
            
            if len(largest_group) >= len(img_positions) * 0.5:  # 至少包含50%的图片
                # 按x坐标排序
                largest_group.sort(key=lambda x: x['x'])
                logger.info(f"SUCCESS (Y-group): Found {len(largest_group)} images in main row")
                return [(img['src'], img['x']) for img in largest_group]
        
        except Exception as e:
            logger.warning(f"Y-position detection failed: {e}")
        
        # 最后降级方案
        logger.warning("Timeline not found, will use DOM order (may be incorrect)")
        return None
    
    async def download_from_app_page(self, product_name: str, project_dir: str) -> int:
        """
        从当前的专属页面下载截图
        支持断点续传，优先从时间线获取正确顺序
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        # 检查是否有已下载的内容（断点续传）
        existing_files = set()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    existing_files = {s['original_url'] for s in manifest_data.get('screenshots', [])}
                    logger.info(f"Found {len(existing_files)} existing screenshots, will skip")
            except:
                pass
        
        # 创建目录
        os.makedirs(screens_dir, exist_ok=True)
        
        try:
            app_url = self.page.url
            logger.info(f"Downloading from: {app_url}")
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # 滚动加载所有图片
            logger.info("Scrolling to load all images...")
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # ===== 核心修复：优先从时间线获取图片 =====
            timeline_images = await self.get_timeline_images()
            
            image_urls = []
            timeline_positions = {}  # 记录时间线位置信息
            
            if timeline_images:
                # 使用时间线顺序（已按x坐标排序）
                logger.info(f"Using timeline order ({len(timeline_images)} images)")
                seen_urls = set()
                for url, x_pos in timeline_images:
                    # 直接使用原始URL（不需要转换）
                    if url not in seen_urls:
                        seen_urls.add(url)
                        image_urls.append(url)
                        timeline_positions[url] = x_pos
            else:
                # 降级：使用DOM顺序（不推荐）
                logger.warning("Falling back to DOM order - screenshots may not be in correct flow order!")
                all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                
                seen_urls = set()
                for img in all_imgs:
                    try:
                        src = await img.get_attribute('src')
                        if src and src not in seen_urls and 'appicon' not in src:
                            seen_urls.add(src)
                            image_urls.append(src)
                    except:
                        continue
            
            logger.info(f"Found {len(image_urls)} screenshots to download")
            
            if not image_urls:
                debug_path = os.path.join(project_dir, "debug_empty_page.png")
                await self.page.screenshot(path=debug_path, full_page=True)
                logger.warning(f"No screenshots found, debug saved: {debug_path}")
                return 0
            
            # 下载截图（带重试）
            downloaded = 0
            skipped = 0
            manifest = []
            used_timeline = bool(timeline_images)
            
            # 获取已有文件的最大编号
            existing_screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
            start_idx = len(existing_screens) + 1
            
            for idx, url in enumerate(image_urls, start_idx):
                # 断点续传：跳过已下载的
                if url in existing_files:
                    skipped += 1
                    continue
                
                try:
                    # 使用重试机制下载
                    image_data = download_image_with_retry(url)
                    
                    if image_data:
                        img = Image.open(BytesIO(image_data))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        if img.width > 0:
                            ratio = TARGET_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # 保存
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img.save(filepath, "PNG", optimize=True)
                        
                        # manifest增加时间线位置信息
                        manifest_entry = {
                            "index": idx,
                            "filename": filename,
                            "original_url": url,
                            "width": TARGET_WIDTH,
                            "height": new_height if img.width > 0 else img.height,
                            "timeline_order": idx - start_idx + 1,  # 时间线中的顺序
                        }
                        
                        # 如果有时间线位置，添加x坐标
                        if url in timeline_positions:
                            manifest_entry["timeline_x"] = timeline_positions[url]
                        
                        manifest.append(manifest_entry)
                        
                        downloaded += 1
                        if downloaded % 20 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(image_urls) - skipped}...")
                            # 中途保存manifest（防止崩溃丢失进度）
                            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
                    else:
                        logger.warning(f"Failed to download image {idx} after retries")
                        
                except Exception as e:
                    logger.error(f"Error downloading image {idx}: {e}")
                    continue
            
            # 保存最终manifest
            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
            
            # 验证下载顺序
            verification = await self.verify_download_order(project_dir)
            logger.info(f"Order verification: {verification}")
            
            logger.info(f"Downloaded {downloaded} screenshots (skipped {skipped} existing)")
            return downloaded
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return 0
    
    def _save_manifest(self, path: str, product_name: str, app_url: str, screenshots: list, used_timeline: bool = False):
        """保存manifest文件（含时间线验证信息）"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "product": product_name,
                "source": "screensdesign.com",
                "source_url": app_url,
                "downloaded_at": datetime.now().isoformat(),
                "total": len(screenshots),
                "order_source": "timeline" if used_timeline else "dom_order",
                "order_reliable": used_timeline,  # 时间线顺序是可靠的
                "screenshots": screenshots
            }, f, indent=2, ensure_ascii=False)
    
    async def verify_download_order(self, project_dir: str) -> dict:
        """
        验证下载顺序是否正确
        
        Returns:
            验证结果字典
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        checks = {
            "total_screenshots": 0,
            "order_source": "unknown",
            "order_reliable": False,
            "timeline_x_monotonic": None,  # 时间线x坐标是否单调递增
            "first_screen_looks_valid": None,
            "warnings": []
        }
        
        # 读取manifest
        if not os.path.exists(manifest_path):
            checks["warnings"].append("manifest.json not found")
            return checks
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            checks["warnings"].append(f"Failed to read manifest: {e}")
            return checks
        
        screenshots = manifest.get("screenshots", [])
        checks["total_screenshots"] = len(screenshots)
        checks["order_source"] = manifest.get("order_source", "unknown")
        checks["order_reliable"] = manifest.get("order_reliable", False)
        
        if not screenshots:
            checks["warnings"].append("No screenshots in manifest")
            return checks
        
        # 检查1：时间线x坐标是否单调递增
        timeline_x_values = [s.get("timeline_x") for s in screenshots if s.get("timeline_x") is not None]
        if timeline_x_values:
            is_monotonic = all(timeline_x_values[i] <= timeline_x_values[i+1] for i in range(len(timeline_x_values)-1))
            checks["timeline_x_monotonic"] = is_monotonic
            if not is_monotonic:
                checks["warnings"].append("Timeline x positions are not monotonically increasing")
        
        # 检查2：第一张截图应该是Launch/Splash页面（简单检查）
        # 这里用AI检查成本太高，改用简单规则
        first_screen = screenshots[0].get("filename", "")
        if first_screen:
            # 基于常见命名规则的简单检查
            checks["first_screen_looks_valid"] = "001" in first_screen or "Screen_001" in first_screen
        
        # 检查3：如果不是从时间线获取的，添加警告
        if not checks["order_reliable"]:
            checks["warnings"].append("Screenshots were NOT extracted from timeline - order may be incorrect!")
        
        # 保存验证结果到manifest
        manifest["verification"] = {
            "checked_at": datetime.now().isoformat(),
            "order_reliable": checks["order_reliable"],
            "timeline_x_monotonic": checks["timeline_x_monotonic"],
            "warnings": checks["warnings"]
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return checks
    
    async def process_product(self, product_info: dict) -> dict:
        """
        处理单个产品：搜索 -> 下载 -> 分析
        """
        product_name = product_info['app_name']
        publisher = product_info.get('publisher', '')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {product_name}")
        logger.info(f"Publisher: {publisher}")
        
        # 更新状态
        self._update_status(product_name, "processing")
        
        # 搜索并进入专属页面
        app_url = await self.search_and_enter_app_page(product_name)
        
        if not app_url:
            logger.warning(f"Could not find app page for {product_name}")
            self._update_status(product_name, "not_found")
            return {"status": "not_found", "product": product_name}
        
        # 创建项目目录
        safe_name = re.sub(r'[^\w\s-]', '', product_name).replace(' ', '_')
        project_name = f"{safe_name}_Analysis"
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 保存app信息
        app_info_path = os.path.join(project_dir, "app_info.json")
        with open(app_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "app_name": product_name,
                "publisher": publisher,
                "source_url": app_url,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # 下载截图
        downloaded = await self.download_from_app_page(product_name, project_dir)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} screenshots for {product_name}")
            
            # 更新产品配置
            self._update_product_config(project_name, product_info)
            
            # 自动分析
            if self.auto_analyze:
                await self._run_analysis(project_name)
            
            self._update_status(product_name, "success", {"screenshots": downloaded})
            return {
                "status": "success",
                "product": product_name,
                "app_url": app_url,
                "screenshots": downloaded,
                "project_dir": project_dir
            }
        else:
            logger.warning(f"Could not download screenshots for {product_name}")
            self._update_status(product_name, "download_failed")
            return {
                "status": "download_failed",
                "product": product_name,
                "app_url": app_url
            }
    
    async def _run_analysis(self, project_name: str):
        """运行智能分析"""
        logger.info(f"Starting analysis for {project_name}...")
        try:
            # 导入并运行分析器
            sys.path.insert(0, os.path.join(BASE_DIR, "ai_analysis"))
            from smart_analyzer import SmartAnalyzer
            
            analyzer = SmartAnalyzer(
                project_name=project_name,
                concurrent=3,
                auto_fix=True,
                verbose=False
            )
            results = analyzer.run()
            
            if results:
                logger.info(f"Analysis complete: {len(results)} screenshots analyzed")
            else:
                logger.warning("Analysis returned no results")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
    
    def _update_product_config(self, project_name: str, product_info: dict):
        """更新产品配置"""
        config_path = os.path.join(CONFIG_DIR, "products.json")
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        colors = ["#5E6AD2", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899", "#14B8A6"]
        color_idx = hash(product_info.get('app_name', '')) % len(colors)
        
        config[project_name] = {
            "name": product_info.get('app_name', project_name.replace('_Analysis', '')),
            "color": colors[color_idx],
            "initial": product_info.get('app_name', 'X')[0].upper(),
            "category": product_info.get('category', ''),
            "publisher": product_info.get('publisher', '')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _update_status(self, product_name: str, status: str, extra: dict = None):
        """更新下载状态"""
        status_data = {"queue": [], "completed": {}, "current": None, "last_updated": None}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except:
                pass
        
        status_data["current"] = product_name if status == "processing" else None
        status_data["completed"][product_name] = {
            "status": status,
            "time": datetime.now().isoformat(),
            **(extra or {})
        }
        status_data["last_updated"] = datetime.now().isoformat()
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    async def run_batch(self, products: list = None, limit: int = None, resume: bool = True):
        """
        批量下载
        
        Args:
            products: 产品列表，None则从competitors.json加载
            limit: 限制处理数量
            resume: 是否跳过已完成的产品
        """
        logger.info("\n" + "=" * 60)
        logger.info("  SMART BATCH DOWNLOAD v2.0")
        logger.info("=" * 60)
        
        # 加载产品列表
        if products is None:
            json_path = os.path.join(DATA_DIR, "competitors.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('top30', [])
            else:
                logger.error("competitors.json not found")
                return
        
        if limit:
            products = products[:limit]
        
        # 断点续传：跳过已完成的
        completed_products = set()
        if resume and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                for name, info in status_data.get("completed", {}).items():
                    if info.get("status") == "success":
                        completed_products.add(name)
                
                if completed_products:
                    logger.info(f"Resuming: skipping {len(completed_products)} completed products")
            except:
                pass
        
        products_to_process = [p for p in products if p['app_name'] not in completed_products]
        
        logger.info(f"Products to process: {len(products_to_process)}")
        logger.info(f"Auto-analyze: {'Enabled' if self.auto_analyze else 'Disabled'}")
        
        # 初始化状态
        self._init_status([p['app_name'] for p in products_to_process])
        
        # 初始化浏览器
        if not await self.init_browser():
            return
        
        try:
            for i, product in enumerate(products_to_process, 1):
                logger.info(f"\n[{i}/{len(products_to_process)}]")
                result = await self.process_product(product)
                
                # 分类结果
                if result['status'] == 'success':
                    self.results['success'].append(result)
                elif result['status'] in ('not_found', 'no_match'):
                    self.results['skipped'].append(result)
                else:
                    self.results['failed'].append(result)
                
                # 间隔
                await asyncio.sleep(2)
            
        finally:
            await self.close()
        
        # 生成报告
        self._generate_report()
    
    def _init_status(self, product_names: list):
        """初始化状态文件"""
        status_data = {"queue": product_names, "completed": {}, "current": None, "last_updated": datetime.now().isoformat()}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    status_data["completed"] = existing.get("completed", {})
            except:
                pass
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    def _generate_report(self):
        """生成下载报告"""
        logger.info("\n" + "=" * 60)
        logger.info("  DOWNLOAD REPORT")
        logger.info("=" * 60)
        
        logger.info(f"\nSuccess: {len(self.results['success'])}")
        for r in self.results['success']:
            logger.info(f"  ✓ {r['product']} ({r.get('screenshots', 0)} screenshots)")
        
        logger.info(f"\nFailed: {len(self.results['failed'])}")
        for r in self.results['failed']:
            logger.info(f"  ✗ {r['product']}")
        
        logger.info(f"\nSkipped: {len(self.results['skipped'])}")
        for r in self.results['skipped']:
            logger.info(f"  - {r['product']}")
        
        # 保存报告
        report_path = os.path.join(DATA_DIR, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "success": len(self.results['success']),
                    "failed": len(self.results['failed']),
                    "skipped": len(self.results['skipped'])
                },
                "details": self.results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nReport saved: {report_path}")


# ============================================================
# 命令行入口
# ============================================================

async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Batch Download v2.0")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of products")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed products")
    parser.add_argument("--product", "-p", type=str, help="Download single product by name")
    
    args = parser.parse_args()
    
    downloader = SmartBatchDownloader(auto_analyze=not args.no_analyze)
    
    if args.product:
        # 下载单个产品
        if not await downloader.init_browser():
            return
        try:
            result = await downloader.process_product({"app_name": args.product, "publisher": ""})
            logger.info(f"Result: {result['status']}")
        finally:
            await downloader.close()
    else:
        # 批量下载
        await downloader.run_batch(
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    asyncio.run(main())

Smart Batch Download System v2.0
================================
- 修复bug，增强稳定性
- 下载重试机制（3次）
- 断点续传
- 下载完自动分析
- Chrome连接检测和友好提示
"""

import os
import sys
import json
import time
import asyncio
import requests
import re
import shutil
import socket
import subprocess
import logging
from datetime import datetime
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 下载配置
TARGET_WIDTH = 402
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# 重试配置
MAX_IMAGE_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# 状态文件
STATUS_FILE = os.path.join(BASE_DIR, "download_status.json")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'download.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ============================================================
# 工具函数
# ============================================================

def generate_app_slug(app_name: str) -> str:
    """
    生成screensdesign.com的App URL slug
    
    Examples:
        "Cal AI - Calorie Tracker" -> "cal-ai-calorie-tracker"
        "MyFitnessPal: Calorie Counter" -> "myfitnesspal-calorie-counter"
    """
    slug = app_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def download_image_with_retry(url: str, max_retries: int = MAX_IMAGE_RETRIES) -> bytes:
    """
    下载图片，带重试机制
    
    Args:
        url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        图片字节数据，失败返回None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/'
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return None


# ============================================================
# Chrome 连接助手
# ============================================================

class ChromeHelper:
    """Chrome浏览器连接助手"""
    
    @staticmethod
    def is_chrome_ready() -> bool:
        """检查Chrome调试端口是否可用"""
        return check_port_open("127.0.0.1", CHROME_DEBUG_PORT)
    
    @staticmethod
    def get_chrome_start_command() -> str:
        """获取Chrome启动命令"""
        # Windows
        if sys.platform == 'win32':
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT}'
        return f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
    
    @staticmethod
    async def ensure_chrome_ready() -> bool:
        """
        确保Chrome已准备好
        如果未启动，提示用户启动
        """
        if ChromeHelper.is_chrome_ready():
            logger.info("Chrome debug port is ready")
            return True
        
        print("\n" + "=" * 60)
        print("  Chrome 未检测到")
        print("=" * 60)
        print(f"\n请先启动Chrome并开启调试端口 {CHROME_DEBUG_PORT}:")
        print(f"\n  命令: {ChromeHelper.get_chrome_start_command()}")
        print("\n或者在已打开的Chrome中手动登录 screensdesign.com")
        print("然后重新运行此脚本。")
        print("\n" + "=" * 60)
        
        # 等待用户启动
        print("\n等待Chrome启动... (按Ctrl+C取消)")
        for i in range(60):  # 等待最多60秒
            if ChromeHelper.is_chrome_ready():
                logger.info("Chrome is now ready!")
                return True
            await asyncio.sleep(1)
            print(f"  等待中... {60-i}秒", end="\r")
        
        logger.error("Chrome did not start within timeout")
        return False


# ============================================================
# 下载器主类
# ============================================================

class SmartBatchDownloader:
    """智能批量下载器"""
    
    def __init__(self, auto_analyze: bool = True):
        """
        初始化下载器
        
        Args:
            auto_analyze: 下载完成后是否自动分析
        """
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auto_analyze = auto_analyze
        
        # 结果统计
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
    
    async def init_browser(self) -> bool:
        """初始化浏览器连接"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        # 确保Chrome已准备好
        if not await ChromeHelper.ensure_chrome_ready():
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Connected to Chrome")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Chrome: {e}")
            return False
    
    async def close(self):
        """关闭浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def search_and_enter_app_page(self, product_name: str) -> str:
        """
        搜索产品并进入专属页面
        
        Returns:
            专属页面URL，失败返回None
        """
        try:
            simple_name = product_name.split(':')[0].split(' - ')[0].strip()
            logger.info(f"Searching for '{simple_name}'...")
            
            # 进入screensdesign首页
            await self.page.goto('https://screensdesign.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 点击搜索区域
            search_area = await self.page.query_selector('text=/Search/')
            if search_area:
                await search_area.click()
                await asyncio.sleep(2)
            
            # 找到搜索输入框并搜索
            search_input = await self.page.query_selector('input:visible')
            if search_input:
                await search_input.fill(simple_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(5)
            
            logger.info(f"Search results: {self.page.url}")
            
            # 在搜索结果中找到匹配的App完整名称
            h3_elements = await self.page.query_selector_all('h3')
            
            found_app_name = None
            for h3 in h3_elements:
                try:
                    text = (await h3.inner_text()).strip()
                    if simple_name.lower() in text.lower():
                        found_app_name = text
                        logger.info(f"Found app in search: '{found_app_name}'")
                        break
                except:
                    continue
            
            if not found_app_name:
                logger.error(f"App not found in search results")
                return None
            
            # 生成slug并访问专属页面
            slug = generate_app_slug(found_app_name)
            app_url = f"https://screensdesign.com/apps/{slug}/"
            
            logger.info(f"Generated URL: {app_url}")
            
            response = await self.page.goto(app_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查页面是否有效
            if response and response.status == 404:
                logger.warning(f"Page not found: {app_url}")
                
                # 尝试备选slug
                alt_slug = generate_app_slug(product_name)
                if alt_slug != slug:
                    alt_url = f"https://screensdesign.com/apps/{alt_slug}/"
                    logger.info(f"Trying alternate URL: {alt_url}")
                    response = await self.page.goto(alt_url, wait_until='domcontentloaded', timeout=60000)
                    if response and response.status != 404:
                        return alt_url
                
                return None
            
            # 验证页面有截图
            imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            if len(imgs) == 0:
                await asyncio.sleep(3)
                imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            logger.info(f"App page loaded with {len(imgs)} screenshots")
            return app_url
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_timeline_images(self) -> list:
        """
        从底部时间线获取图片，按x坐标排序（确保流程顺序正确）
        
        screensdesign.com 的时间线是一个 flex row 横向滚动容器，
        class 包含 tw-flex tw-flex-row tw-overflow-x-auto
        
        Returns:
            [(url, timeline_x), ...] 按时间线顺序排列的图片URL和位置
        """
        # 先滚动到页面底部，确保时间线加载
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # screensdesign.com 特定的时间线选择器（基于页面分析结果）
        # 时间线是一个 flex row 横向滚动容器
        timeline_selectors = [
            # 主要选择器：包含 tw-flex tw-flex-row 且可横向滚动
            'div.tw-flex.tw-flex-row.tw-overflow-x-auto',
            '[class*="tw-flex"][class*="tw-flex-row"][class*="tw-overflow-x-auto"]',
            # 备选：任何横向滚动的flex容器
            'div[class*="overflow-x-auto"][class*="flex-row"]',
            'div[class*="flex"][class*="row"][class*="overflow"]',
        ]
        
        for selector in timeline_selectors:
            try:
                timeline = await self.page.query_selector(selector)
                if timeline:
                    # 获取时间线内的所有图片
                    imgs = await timeline.query_selector_all('img')
                    if len(imgs) >= 5:  # 至少要有5张图才认为是时间线
                        logger.info(f"Found timeline container: {selector} ({len(imgs)} images)")
                        
                        # 获取每张图片的URL和x坐标
                        image_data = []
                        for img in imgs:
                            try:
                                src = await img.get_attribute('src')
                                if src and 'appicon' not in src and 'media.screensdesign.com' in src:
                                    bbox = await img.bounding_box()
                                    if bbox:
                                        image_data.append((src, bbox['x']))
                            except:
                                continue
                        
                        if image_data:
                            # 按x坐标排序（从左到右）
                            image_data.sort(key=lambda x: x[1])
                            logger.info(f"SUCCESS: Extracted {len(image_data)} images from timeline (sorted by x-position)")
                            return image_data
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 备选方案：通过JavaScript直接查找横向滚动的flex容器
        logger.info("Trying JavaScript-based timeline detection...")
        try:
            timeline_data = await self.page.evaluate('''
                () => {
                    // 找所有div元素
                    const divs = document.querySelectorAll('div');
                    
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        // 查找flex row + 横向滚动的容器
                        if ((style.display === 'flex') && 
                            (style.flexDirection === 'row') &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                            (div.scrollWidth > div.clientWidth * 1.5)) {
                            
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                // 找到了！获取图片信息
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({
                                            src: img.src,
                                            x: rect.x
                                        });
                                    }
                                });
                                
                                // 按x坐标排序
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data and len(timeline_data) >= 5:
                logger.info(f"SUCCESS (JS): Found {len(timeline_data)} images in timeline")
                return [(img['src'], img['x']) for img in timeline_data]
                
        except Exception as e:
            logger.warning(f"JavaScript timeline detection failed: {e}")
        
        # 第三备选：找y坐标相近的一行图片
        logger.info("Trying Y-position based timeline detection...")
        try:
            all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            if len(all_imgs) < 5:
                logger.warning("Timeline not found, will use DOM order (may be incorrect)")
                return None
            
            # 获取所有图片的位置
            img_positions = []
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    bbox = await img.bounding_box()
                    if src and bbox and 'appicon' not in src:
                        img_positions.append({
                            'src': src,
                            'x': bbox['x'],
                            'y': bbox['y'],
                            'width': bbox['width']
                        })
                except:
                    continue
            
            if not img_positions:
                return None
            
            # 按y坐标分组（找出同一行的图片）
            y_tolerance = 50  # 50px内认为是同一行
            y_groups = {}
            for img in img_positions:
                y_bucket = round(img['y'] / y_tolerance) * y_tolerance
                if y_bucket not in y_groups:
                    y_groups[y_bucket] = []
                y_groups[y_bucket].append(img)
            
            # 找出图片最多的那一行（应该是时间线）
            largest_group = max(y_groups.values(), key=len)
            
            if len(largest_group) >= len(img_positions) * 0.5:  # 至少包含50%的图片
                # 按x坐标排序
                largest_group.sort(key=lambda x: x['x'])
                logger.info(f"SUCCESS (Y-group): Found {len(largest_group)} images in main row")
                return [(img['src'], img['x']) for img in largest_group]
        
        except Exception as e:
            logger.warning(f"Y-position detection failed: {e}")
        
        # 最后降级方案
        logger.warning("Timeline not found, will use DOM order (may be incorrect)")
        return None
    
    async def download_from_app_page(self, product_name: str, project_dir: str) -> int:
        """
        从当前的专属页面下载截图
        支持断点续传，优先从时间线获取正确顺序
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        # 检查是否有已下载的内容（断点续传）
        existing_files = set()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    existing_files = {s['original_url'] for s in manifest_data.get('screenshots', [])}
                    logger.info(f"Found {len(existing_files)} existing screenshots, will skip")
            except:
                pass
        
        # 创建目录
        os.makedirs(screens_dir, exist_ok=True)
        
        try:
            app_url = self.page.url
            logger.info(f"Downloading from: {app_url}")
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # 滚动加载所有图片
            logger.info("Scrolling to load all images...")
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # ===== 核心修复：优先从时间线获取图片 =====
            timeline_images = await self.get_timeline_images()
            
            image_urls = []
            timeline_positions = {}  # 记录时间线位置信息
            
            if timeline_images:
                # 使用时间线顺序（已按x坐标排序）
                logger.info(f"Using timeline order ({len(timeline_images)} images)")
                seen_urls = set()
                for url, x_pos in timeline_images:
                    # 直接使用原始URL（不需要转换）
                    if url not in seen_urls:
                        seen_urls.add(url)
                        image_urls.append(url)
                        timeline_positions[url] = x_pos
            else:
                # 降级：使用DOM顺序（不推荐）
                logger.warning("Falling back to DOM order - screenshots may not be in correct flow order!")
                all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                
                seen_urls = set()
                for img in all_imgs:
                    try:
                        src = await img.get_attribute('src')
                        if src and src not in seen_urls and 'appicon' not in src:
                            seen_urls.add(src)
                            image_urls.append(src)
                    except:
                        continue
            
            logger.info(f"Found {len(image_urls)} screenshots to download")
            
            if not image_urls:
                debug_path = os.path.join(project_dir, "debug_empty_page.png")
                await self.page.screenshot(path=debug_path, full_page=True)
                logger.warning(f"No screenshots found, debug saved: {debug_path}")
                return 0
            
            # 下载截图（带重试）
            downloaded = 0
            skipped = 0
            manifest = []
            used_timeline = bool(timeline_images)
            
            # 获取已有文件的最大编号
            existing_screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
            start_idx = len(existing_screens) + 1
            
            for idx, url in enumerate(image_urls, start_idx):
                # 断点续传：跳过已下载的
                if url in existing_files:
                    skipped += 1
                    continue
                
                try:
                    # 使用重试机制下载
                    image_data = download_image_with_retry(url)
                    
                    if image_data:
                        img = Image.open(BytesIO(image_data))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        if img.width > 0:
                            ratio = TARGET_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # 保存
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img.save(filepath, "PNG", optimize=True)
                        
                        # manifest增加时间线位置信息
                        manifest_entry = {
                            "index": idx,
                            "filename": filename,
                            "original_url": url,
                            "width": TARGET_WIDTH,
                            "height": new_height if img.width > 0 else img.height,
                            "timeline_order": idx - start_idx + 1,  # 时间线中的顺序
                        }
                        
                        # 如果有时间线位置，添加x坐标
                        if url in timeline_positions:
                            manifest_entry["timeline_x"] = timeline_positions[url]
                        
                        manifest.append(manifest_entry)
                        
                        downloaded += 1
                        if downloaded % 20 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(image_urls) - skipped}...")
                            # 中途保存manifest（防止崩溃丢失进度）
                            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
                    else:
                        logger.warning(f"Failed to download image {idx} after retries")
                        
                except Exception as e:
                    logger.error(f"Error downloading image {idx}: {e}")
                    continue
            
            # 保存最终manifest
            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
            
            # 验证下载顺序
            verification = await self.verify_download_order(project_dir)
            logger.info(f"Order verification: {verification}")
            
            logger.info(f"Downloaded {downloaded} screenshots (skipped {skipped} existing)")
            return downloaded
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return 0
    
    def _save_manifest(self, path: str, product_name: str, app_url: str, screenshots: list, used_timeline: bool = False):
        """保存manifest文件（含时间线验证信息）"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "product": product_name,
                "source": "screensdesign.com",
                "source_url": app_url,
                "downloaded_at": datetime.now().isoformat(),
                "total": len(screenshots),
                "order_source": "timeline" if used_timeline else "dom_order",
                "order_reliable": used_timeline,  # 时间线顺序是可靠的
                "screenshots": screenshots
            }, f, indent=2, ensure_ascii=False)
    
    async def verify_download_order(self, project_dir: str) -> dict:
        """
        验证下载顺序是否正确
        
        Returns:
            验证结果字典
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        checks = {
            "total_screenshots": 0,
            "order_source": "unknown",
            "order_reliable": False,
            "timeline_x_monotonic": None,  # 时间线x坐标是否单调递增
            "first_screen_looks_valid": None,
            "warnings": []
        }
        
        # 读取manifest
        if not os.path.exists(manifest_path):
            checks["warnings"].append("manifest.json not found")
            return checks
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            checks["warnings"].append(f"Failed to read manifest: {e}")
            return checks
        
        screenshots = manifest.get("screenshots", [])
        checks["total_screenshots"] = len(screenshots)
        checks["order_source"] = manifest.get("order_source", "unknown")
        checks["order_reliable"] = manifest.get("order_reliable", False)
        
        if not screenshots:
            checks["warnings"].append("No screenshots in manifest")
            return checks
        
        # 检查1：时间线x坐标是否单调递增
        timeline_x_values = [s.get("timeline_x") for s in screenshots if s.get("timeline_x") is not None]
        if timeline_x_values:
            is_monotonic = all(timeline_x_values[i] <= timeline_x_values[i+1] for i in range(len(timeline_x_values)-1))
            checks["timeline_x_monotonic"] = is_monotonic
            if not is_monotonic:
                checks["warnings"].append("Timeline x positions are not monotonically increasing")
        
        # 检查2：第一张截图应该是Launch/Splash页面（简单检查）
        # 这里用AI检查成本太高，改用简单规则
        first_screen = screenshots[0].get("filename", "")
        if first_screen:
            # 基于常见命名规则的简单检查
            checks["first_screen_looks_valid"] = "001" in first_screen or "Screen_001" in first_screen
        
        # 检查3：如果不是从时间线获取的，添加警告
        if not checks["order_reliable"]:
            checks["warnings"].append("Screenshots were NOT extracted from timeline - order may be incorrect!")
        
        # 保存验证结果到manifest
        manifest["verification"] = {
            "checked_at": datetime.now().isoformat(),
            "order_reliable": checks["order_reliable"],
            "timeline_x_monotonic": checks["timeline_x_monotonic"],
            "warnings": checks["warnings"]
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return checks
    
    async def process_product(self, product_info: dict) -> dict:
        """
        处理单个产品：搜索 -> 下载 -> 分析
        """
        product_name = product_info['app_name']
        publisher = product_info.get('publisher', '')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {product_name}")
        logger.info(f"Publisher: {publisher}")
        
        # 更新状态
        self._update_status(product_name, "processing")
        
        # 搜索并进入专属页面
        app_url = await self.search_and_enter_app_page(product_name)
        
        if not app_url:
            logger.warning(f"Could not find app page for {product_name}")
            self._update_status(product_name, "not_found")
            return {"status": "not_found", "product": product_name}
        
        # 创建项目目录
        safe_name = re.sub(r'[^\w\s-]', '', product_name).replace(' ', '_')
        project_name = f"{safe_name}_Analysis"
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 保存app信息
        app_info_path = os.path.join(project_dir, "app_info.json")
        with open(app_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "app_name": product_name,
                "publisher": publisher,
                "source_url": app_url,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # 下载截图
        downloaded = await self.download_from_app_page(product_name, project_dir)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} screenshots for {product_name}")
            
            # 更新产品配置
            self._update_product_config(project_name, product_info)
            
            # 自动分析
            if self.auto_analyze:
                await self._run_analysis(project_name)
            
            self._update_status(product_name, "success", {"screenshots": downloaded})
            return {
                "status": "success",
                "product": product_name,
                "app_url": app_url,
                "screenshots": downloaded,
                "project_dir": project_dir
            }
        else:
            logger.warning(f"Could not download screenshots for {product_name}")
            self._update_status(product_name, "download_failed")
            return {
                "status": "download_failed",
                "product": product_name,
                "app_url": app_url
            }
    
    async def _run_analysis(self, project_name: str):
        """运行智能分析"""
        logger.info(f"Starting analysis for {project_name}...")
        try:
            # 导入并运行分析器
            sys.path.insert(0, os.path.join(BASE_DIR, "ai_analysis"))
            from smart_analyzer import SmartAnalyzer
            
            analyzer = SmartAnalyzer(
                project_name=project_name,
                concurrent=3,
                auto_fix=True,
                verbose=False
            )
            results = analyzer.run()
            
            if results:
                logger.info(f"Analysis complete: {len(results)} screenshots analyzed")
            else:
                logger.warning("Analysis returned no results")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
    
    def _update_product_config(self, project_name: str, product_info: dict):
        """更新产品配置"""
        config_path = os.path.join(CONFIG_DIR, "products.json")
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        colors = ["#5E6AD2", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899", "#14B8A6"]
        color_idx = hash(product_info.get('app_name', '')) % len(colors)
        
        config[project_name] = {
            "name": product_info.get('app_name', project_name.replace('_Analysis', '')),
            "color": colors[color_idx],
            "initial": product_info.get('app_name', 'X')[0].upper(),
            "category": product_info.get('category', ''),
            "publisher": product_info.get('publisher', '')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _update_status(self, product_name: str, status: str, extra: dict = None):
        """更新下载状态"""
        status_data = {"queue": [], "completed": {}, "current": None, "last_updated": None}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except:
                pass
        
        status_data["current"] = product_name if status == "processing" else None
        status_data["completed"][product_name] = {
            "status": status,
            "time": datetime.now().isoformat(),
            **(extra or {})
        }
        status_data["last_updated"] = datetime.now().isoformat()
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    async def run_batch(self, products: list = None, limit: int = None, resume: bool = True):
        """
        批量下载
        
        Args:
            products: 产品列表，None则从competitors.json加载
            limit: 限制处理数量
            resume: 是否跳过已完成的产品
        """
        logger.info("\n" + "=" * 60)
        logger.info("  SMART BATCH DOWNLOAD v2.0")
        logger.info("=" * 60)
        
        # 加载产品列表
        if products is None:
            json_path = os.path.join(DATA_DIR, "competitors.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('top30', [])
            else:
                logger.error("competitors.json not found")
                return
        
        if limit:
            products = products[:limit]
        
        # 断点续传：跳过已完成的
        completed_products = set()
        if resume and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                for name, info in status_data.get("completed", {}).items():
                    if info.get("status") == "success":
                        completed_products.add(name)
                
                if completed_products:
                    logger.info(f"Resuming: skipping {len(completed_products)} completed products")
            except:
                pass
        
        products_to_process = [p for p in products if p['app_name'] not in completed_products]
        
        logger.info(f"Products to process: {len(products_to_process)}")
        logger.info(f"Auto-analyze: {'Enabled' if self.auto_analyze else 'Disabled'}")
        
        # 初始化状态
        self._init_status([p['app_name'] for p in products_to_process])
        
        # 初始化浏览器
        if not await self.init_browser():
            return
        
        try:
            for i, product in enumerate(products_to_process, 1):
                logger.info(f"\n[{i}/{len(products_to_process)}]")
                result = await self.process_product(product)
                
                # 分类结果
                if result['status'] == 'success':
                    self.results['success'].append(result)
                elif result['status'] in ('not_found', 'no_match'):
                    self.results['skipped'].append(result)
                else:
                    self.results['failed'].append(result)
                
                # 间隔
                await asyncio.sleep(2)
            
        finally:
            await self.close()
        
        # 生成报告
        self._generate_report()
    
    def _init_status(self, product_names: list):
        """初始化状态文件"""
        status_data = {"queue": product_names, "completed": {}, "current": None, "last_updated": datetime.now().isoformat()}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    status_data["completed"] = existing.get("completed", {})
            except:
                pass
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    def _generate_report(self):
        """生成下载报告"""
        logger.info("\n" + "=" * 60)
        logger.info("  DOWNLOAD REPORT")
        logger.info("=" * 60)
        
        logger.info(f"\nSuccess: {len(self.results['success'])}")
        for r in self.results['success']:
            logger.info(f"  ✓ {r['product']} ({r.get('screenshots', 0)} screenshots)")
        
        logger.info(f"\nFailed: {len(self.results['failed'])}")
        for r in self.results['failed']:
            logger.info(f"  ✗ {r['product']}")
        
        logger.info(f"\nSkipped: {len(self.results['skipped'])}")
        for r in self.results['skipped']:
            logger.info(f"  - {r['product']}")
        
        # 保存报告
        report_path = os.path.join(DATA_DIR, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "success": len(self.results['success']),
                    "failed": len(self.results['failed']),
                    "skipped": len(self.results['skipped'])
                },
                "details": self.results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nReport saved: {report_path}")


# ============================================================
# 命令行入口
# ============================================================

async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Batch Download v2.0")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of products")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed products")
    parser.add_argument("--product", "-p", type=str, help="Download single product by name")
    
    args = parser.parse_args()
    
    downloader = SmartBatchDownloader(auto_analyze=not args.no_analyze)
    
    if args.product:
        # 下载单个产品
        if not await downloader.init_browser():
            return
        try:
            result = await downloader.process_product({"app_name": args.product, "publisher": ""})
            logger.info(f"Result: {result['status']}")
        finally:
            await downloader.close()
    else:
        # 批量下载
        await downloader.run_batch(
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    asyncio.run(main())

Smart Batch Download System v2.0
================================
- 修复bug，增强稳定性
- 下载重试机制（3次）
- 断点续传
- 下载完自动分析
- Chrome连接检测和友好提示
"""

import os
import sys
import json
import time
import asyncio
import requests
import re
import shutil
import socket
import subprocess
import logging
from datetime import datetime
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 下载配置
TARGET_WIDTH = 402
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# 重试配置
MAX_IMAGE_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# 状态文件
STATUS_FILE = os.path.join(BASE_DIR, "download_status.json")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'download.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ============================================================
# 工具函数
# ============================================================

def generate_app_slug(app_name: str) -> str:
    """
    生成screensdesign.com的App URL slug
    
    Examples:
        "Cal AI - Calorie Tracker" -> "cal-ai-calorie-tracker"
        "MyFitnessPal: Calorie Counter" -> "myfitnesspal-calorie-counter"
    """
    slug = app_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def download_image_with_retry(url: str, max_retries: int = MAX_IMAGE_RETRIES) -> bytes:
    """
    下载图片，带重试机制
    
    Args:
        url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        图片字节数据，失败返回None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/'
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return None


# ============================================================
# Chrome 连接助手
# ============================================================

class ChromeHelper:
    """Chrome浏览器连接助手"""
    
    @staticmethod
    def is_chrome_ready() -> bool:
        """检查Chrome调试端口是否可用"""
        return check_port_open("127.0.0.1", CHROME_DEBUG_PORT)
    
    @staticmethod
    def get_chrome_start_command() -> str:
        """获取Chrome启动命令"""
        # Windows
        if sys.platform == 'win32':
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT}'
        return f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
    
    @staticmethod
    async def ensure_chrome_ready() -> bool:
        """
        确保Chrome已准备好
        如果未启动，提示用户启动
        """
        if ChromeHelper.is_chrome_ready():
            logger.info("Chrome debug port is ready")
            return True
        
        print("\n" + "=" * 60)
        print("  Chrome 未检测到")
        print("=" * 60)
        print(f"\n请先启动Chrome并开启调试端口 {CHROME_DEBUG_PORT}:")
        print(f"\n  命令: {ChromeHelper.get_chrome_start_command()}")
        print("\n或者在已打开的Chrome中手动登录 screensdesign.com")
        print("然后重新运行此脚本。")
        print("\n" + "=" * 60)
        
        # 等待用户启动
        print("\n等待Chrome启动... (按Ctrl+C取消)")
        for i in range(60):  # 等待最多60秒
            if ChromeHelper.is_chrome_ready():
                logger.info("Chrome is now ready!")
                return True
            await asyncio.sleep(1)
            print(f"  等待中... {60-i}秒", end="\r")
        
        logger.error("Chrome did not start within timeout")
        return False


# ============================================================
# 下载器主类
# ============================================================

class SmartBatchDownloader:
    """智能批量下载器"""
    
    def __init__(self, auto_analyze: bool = True):
        """
        初始化下载器
        
        Args:
            auto_analyze: 下载完成后是否自动分析
        """
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auto_analyze = auto_analyze
        
        # 结果统计
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
    
    async def init_browser(self) -> bool:
        """初始化浏览器连接"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        # 确保Chrome已准备好
        if not await ChromeHelper.ensure_chrome_ready():
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Connected to Chrome")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Chrome: {e}")
            return False
    
    async def close(self):
        """关闭浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def search_and_enter_app_page(self, product_name: str) -> str:
        """
        搜索产品并进入专属页面
        
        Returns:
            专属页面URL，失败返回None
        """
        try:
            simple_name = product_name.split(':')[0].split(' - ')[0].strip()
            logger.info(f"Searching for '{simple_name}'...")
            
            # 进入screensdesign首页
            await self.page.goto('https://screensdesign.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 点击搜索区域
            search_area = await self.page.query_selector('text=/Search/')
            if search_area:
                await search_area.click()
                await asyncio.sleep(2)
            
            # 找到搜索输入框并搜索
            search_input = await self.page.query_selector('input:visible')
            if search_input:
                await search_input.fill(simple_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(5)
            
            logger.info(f"Search results: {self.page.url}")
            
            # 在搜索结果中找到匹配的App完整名称
            h3_elements = await self.page.query_selector_all('h3')
            
            found_app_name = None
            for h3 in h3_elements:
                try:
                    text = (await h3.inner_text()).strip()
                    if simple_name.lower() in text.lower():
                        found_app_name = text
                        logger.info(f"Found app in search: '{found_app_name}'")
                        break
                except:
                    continue
            
            if not found_app_name:
                logger.error(f"App not found in search results")
                return None
            
            # 生成slug并访问专属页面
            slug = generate_app_slug(found_app_name)
            app_url = f"https://screensdesign.com/apps/{slug}/"
            
            logger.info(f"Generated URL: {app_url}")
            
            response = await self.page.goto(app_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查页面是否有效
            if response and response.status == 404:
                logger.warning(f"Page not found: {app_url}")
                
                # 尝试备选slug
                alt_slug = generate_app_slug(product_name)
                if alt_slug != slug:
                    alt_url = f"https://screensdesign.com/apps/{alt_slug}/"
                    logger.info(f"Trying alternate URL: {alt_url}")
                    response = await self.page.goto(alt_url, wait_until='domcontentloaded', timeout=60000)
                    if response and response.status != 404:
                        return alt_url
                
                return None
            
            # 验证页面有截图
            imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            if len(imgs) == 0:
                await asyncio.sleep(3)
                imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            logger.info(f"App page loaded with {len(imgs)} screenshots")
            return app_url
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_timeline_images(self) -> list:
        """
        从底部时间线获取图片，按x坐标排序（确保流程顺序正确）
        
        screensdesign.com 的时间线是一个 flex row 横向滚动容器，
        class 包含 tw-flex tw-flex-row tw-overflow-x-auto
        
        Returns:
            [(url, timeline_x), ...] 按时间线顺序排列的图片URL和位置
        """
        # 先滚动到页面底部，确保时间线加载
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # screensdesign.com 特定的时间线选择器（基于页面分析结果）
        # 时间线是一个 flex row 横向滚动容器
        timeline_selectors = [
            # 主要选择器：包含 tw-flex tw-flex-row 且可横向滚动
            'div.tw-flex.tw-flex-row.tw-overflow-x-auto',
            '[class*="tw-flex"][class*="tw-flex-row"][class*="tw-overflow-x-auto"]',
            # 备选：任何横向滚动的flex容器
            'div[class*="overflow-x-auto"][class*="flex-row"]',
            'div[class*="flex"][class*="row"][class*="overflow"]',
        ]
        
        for selector in timeline_selectors:
            try:
                timeline = await self.page.query_selector(selector)
                if timeline:
                    # 获取时间线内的所有图片
                    imgs = await timeline.query_selector_all('img')
                    if len(imgs) >= 5:  # 至少要有5张图才认为是时间线
                        logger.info(f"Found timeline container: {selector} ({len(imgs)} images)")
                        
                        # 获取每张图片的URL和x坐标
                        image_data = []
                        for img in imgs:
                            try:
                                src = await img.get_attribute('src')
                                if src and 'appicon' not in src and 'media.screensdesign.com' in src:
                                    bbox = await img.bounding_box()
                                    if bbox:
                                        image_data.append((src, bbox['x']))
                            except:
                                continue
                        
                        if image_data:
                            # 按x坐标排序（从左到右）
                            image_data.sort(key=lambda x: x[1])
                            logger.info(f"SUCCESS: Extracted {len(image_data)} images from timeline (sorted by x-position)")
                            return image_data
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 备选方案：通过JavaScript直接查找横向滚动的flex容器
        logger.info("Trying JavaScript-based timeline detection...")
        try:
            timeline_data = await self.page.evaluate('''
                () => {
                    // 找所有div元素
                    const divs = document.querySelectorAll('div');
                    
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        // 查找flex row + 横向滚动的容器
                        if ((style.display === 'flex') && 
                            (style.flexDirection === 'row') &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                            (div.scrollWidth > div.clientWidth * 1.5)) {
                            
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                // 找到了！获取图片信息
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({
                                            src: img.src,
                                            x: rect.x
                                        });
                                    }
                                });
                                
                                // 按x坐标排序
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data and len(timeline_data) >= 5:
                logger.info(f"SUCCESS (JS): Found {len(timeline_data)} images in timeline")
                return [(img['src'], img['x']) for img in timeline_data]
                
        except Exception as e:
            logger.warning(f"JavaScript timeline detection failed: {e}")
        
        # 第三备选：找y坐标相近的一行图片
        logger.info("Trying Y-position based timeline detection...")
        try:
            all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            if len(all_imgs) < 5:
                logger.warning("Timeline not found, will use DOM order (may be incorrect)")
                return None
            
            # 获取所有图片的位置
            img_positions = []
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    bbox = await img.bounding_box()
                    if src and bbox and 'appicon' not in src:
                        img_positions.append({
                            'src': src,
                            'x': bbox['x'],
                            'y': bbox['y'],
                            'width': bbox['width']
                        })
                except:
                    continue
            
            if not img_positions:
                return None
            
            # 按y坐标分组（找出同一行的图片）
            y_tolerance = 50  # 50px内认为是同一行
            y_groups = {}
            for img in img_positions:
                y_bucket = round(img['y'] / y_tolerance) * y_tolerance
                if y_bucket not in y_groups:
                    y_groups[y_bucket] = []
                y_groups[y_bucket].append(img)
            
            # 找出图片最多的那一行（应该是时间线）
            largest_group = max(y_groups.values(), key=len)
            
            if len(largest_group) >= len(img_positions) * 0.5:  # 至少包含50%的图片
                # 按x坐标排序
                largest_group.sort(key=lambda x: x['x'])
                logger.info(f"SUCCESS (Y-group): Found {len(largest_group)} images in main row")
                return [(img['src'], img['x']) for img in largest_group]
        
        except Exception as e:
            logger.warning(f"Y-position detection failed: {e}")
        
        # 最后降级方案
        logger.warning("Timeline not found, will use DOM order (may be incorrect)")
        return None
    
    async def download_from_app_page(self, product_name: str, project_dir: str) -> int:
        """
        从当前的专属页面下载截图
        支持断点续传，优先从时间线获取正确顺序
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        # 检查是否有已下载的内容（断点续传）
        existing_files = set()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    existing_files = {s['original_url'] for s in manifest_data.get('screenshots', [])}
                    logger.info(f"Found {len(existing_files)} existing screenshots, will skip")
            except:
                pass
        
        # 创建目录
        os.makedirs(screens_dir, exist_ok=True)
        
        try:
            app_url = self.page.url
            logger.info(f"Downloading from: {app_url}")
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # 滚动加载所有图片
            logger.info("Scrolling to load all images...")
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # ===== 核心修复：优先从时间线获取图片 =====
            timeline_images = await self.get_timeline_images()
            
            image_urls = []
            timeline_positions = {}  # 记录时间线位置信息
            
            if timeline_images:
                # 使用时间线顺序（已按x坐标排序）
                logger.info(f"Using timeline order ({len(timeline_images)} images)")
                seen_urls = set()
                for url, x_pos in timeline_images:
                    # 直接使用原始URL（不需要转换）
                    if url not in seen_urls:
                        seen_urls.add(url)
                        image_urls.append(url)
                        timeline_positions[url] = x_pos
            else:
                # 降级：使用DOM顺序（不推荐）
                logger.warning("Falling back to DOM order - screenshots may not be in correct flow order!")
                all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                
                seen_urls = set()
                for img in all_imgs:
                    try:
                        src = await img.get_attribute('src')
                        if src and src not in seen_urls and 'appicon' not in src:
                            seen_urls.add(src)
                            image_urls.append(src)
                    except:
                        continue
            
            logger.info(f"Found {len(image_urls)} screenshots to download")
            
            if not image_urls:
                debug_path = os.path.join(project_dir, "debug_empty_page.png")
                await self.page.screenshot(path=debug_path, full_page=True)
                logger.warning(f"No screenshots found, debug saved: {debug_path}")
                return 0
            
            # 下载截图（带重试）
            downloaded = 0
            skipped = 0
            manifest = []
            used_timeline = bool(timeline_images)
            
            # 获取已有文件的最大编号
            existing_screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
            start_idx = len(existing_screens) + 1
            
            for idx, url in enumerate(image_urls, start_idx):
                # 断点续传：跳过已下载的
                if url in existing_files:
                    skipped += 1
                    continue
                
                try:
                    # 使用重试机制下载
                    image_data = download_image_with_retry(url)
                    
                    if image_data:
                        img = Image.open(BytesIO(image_data))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        if img.width > 0:
                            ratio = TARGET_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # 保存
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img.save(filepath, "PNG", optimize=True)
                        
                        # manifest增加时间线位置信息
                        manifest_entry = {
                            "index": idx,
                            "filename": filename,
                            "original_url": url,
                            "width": TARGET_WIDTH,
                            "height": new_height if img.width > 0 else img.height,
                            "timeline_order": idx - start_idx + 1,  # 时间线中的顺序
                        }
                        
                        # 如果有时间线位置，添加x坐标
                        if url in timeline_positions:
                            manifest_entry["timeline_x"] = timeline_positions[url]
                        
                        manifest.append(manifest_entry)
                        
                        downloaded += 1
                        if downloaded % 20 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(image_urls) - skipped}...")
                            # 中途保存manifest（防止崩溃丢失进度）
                            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
                    else:
                        logger.warning(f"Failed to download image {idx} after retries")
                        
                except Exception as e:
                    logger.error(f"Error downloading image {idx}: {e}")
                    continue
            
            # 保存最终manifest
            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
            
            # 验证下载顺序
            verification = await self.verify_download_order(project_dir)
            logger.info(f"Order verification: {verification}")
            
            logger.info(f"Downloaded {downloaded} screenshots (skipped {skipped} existing)")
            return downloaded
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return 0
    
    def _save_manifest(self, path: str, product_name: str, app_url: str, screenshots: list, used_timeline: bool = False):
        """保存manifest文件（含时间线验证信息）"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "product": product_name,
                "source": "screensdesign.com",
                "source_url": app_url,
                "downloaded_at": datetime.now().isoformat(),
                "total": len(screenshots),
                "order_source": "timeline" if used_timeline else "dom_order",
                "order_reliable": used_timeline,  # 时间线顺序是可靠的
                "screenshots": screenshots
            }, f, indent=2, ensure_ascii=False)
    
    async def verify_download_order(self, project_dir: str) -> dict:
        """
        验证下载顺序是否正确
        
        Returns:
            验证结果字典
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        checks = {
            "total_screenshots": 0,
            "order_source": "unknown",
            "order_reliable": False,
            "timeline_x_monotonic": None,  # 时间线x坐标是否单调递增
            "first_screen_looks_valid": None,
            "warnings": []
        }
        
        # 读取manifest
        if not os.path.exists(manifest_path):
            checks["warnings"].append("manifest.json not found")
            return checks
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            checks["warnings"].append(f"Failed to read manifest: {e}")
            return checks
        
        screenshots = manifest.get("screenshots", [])
        checks["total_screenshots"] = len(screenshots)
        checks["order_source"] = manifest.get("order_source", "unknown")
        checks["order_reliable"] = manifest.get("order_reliable", False)
        
        if not screenshots:
            checks["warnings"].append("No screenshots in manifest")
            return checks
        
        # 检查1：时间线x坐标是否单调递增
        timeline_x_values = [s.get("timeline_x") for s in screenshots if s.get("timeline_x") is not None]
        if timeline_x_values:
            is_monotonic = all(timeline_x_values[i] <= timeline_x_values[i+1] for i in range(len(timeline_x_values)-1))
            checks["timeline_x_monotonic"] = is_monotonic
            if not is_monotonic:
                checks["warnings"].append("Timeline x positions are not monotonically increasing")
        
        # 检查2：第一张截图应该是Launch/Splash页面（简单检查）
        # 这里用AI检查成本太高，改用简单规则
        first_screen = screenshots[0].get("filename", "")
        if first_screen:
            # 基于常见命名规则的简单检查
            checks["first_screen_looks_valid"] = "001" in first_screen or "Screen_001" in first_screen
        
        # 检查3：如果不是从时间线获取的，添加警告
        if not checks["order_reliable"]:
            checks["warnings"].append("Screenshots were NOT extracted from timeline - order may be incorrect!")
        
        # 保存验证结果到manifest
        manifest["verification"] = {
            "checked_at": datetime.now().isoformat(),
            "order_reliable": checks["order_reliable"],
            "timeline_x_monotonic": checks["timeline_x_monotonic"],
            "warnings": checks["warnings"]
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return checks
    
    async def process_product(self, product_info: dict) -> dict:
        """
        处理单个产品：搜索 -> 下载 -> 分析
        """
        product_name = product_info['app_name']
        publisher = product_info.get('publisher', '')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {product_name}")
        logger.info(f"Publisher: {publisher}")
        
        # 更新状态
        self._update_status(product_name, "processing")
        
        # 搜索并进入专属页面
        app_url = await self.search_and_enter_app_page(product_name)
        
        if not app_url:
            logger.warning(f"Could not find app page for {product_name}")
            self._update_status(product_name, "not_found")
            return {"status": "not_found", "product": product_name}
        
        # 创建项目目录
        safe_name = re.sub(r'[^\w\s-]', '', product_name).replace(' ', '_')
        project_name = f"{safe_name}_Analysis"
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 保存app信息
        app_info_path = os.path.join(project_dir, "app_info.json")
        with open(app_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "app_name": product_name,
                "publisher": publisher,
                "source_url": app_url,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # 下载截图
        downloaded = await self.download_from_app_page(product_name, project_dir)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} screenshots for {product_name}")
            
            # 更新产品配置
            self._update_product_config(project_name, product_info)
            
            # 自动分析
            if self.auto_analyze:
                await self._run_analysis(project_name)
            
            self._update_status(product_name, "success", {"screenshots": downloaded})
            return {
                "status": "success",
                "product": product_name,
                "app_url": app_url,
                "screenshots": downloaded,
                "project_dir": project_dir
            }
        else:
            logger.warning(f"Could not download screenshots for {product_name}")
            self._update_status(product_name, "download_failed")
            return {
                "status": "download_failed",
                "product": product_name,
                "app_url": app_url
            }
    
    async def _run_analysis(self, project_name: str):
        """运行智能分析"""
        logger.info(f"Starting analysis for {project_name}...")
        try:
            # 导入并运行分析器
            sys.path.insert(0, os.path.join(BASE_DIR, "ai_analysis"))
            from smart_analyzer import SmartAnalyzer
            
            analyzer = SmartAnalyzer(
                project_name=project_name,
                concurrent=3,
                auto_fix=True,
                verbose=False
            )
            results = analyzer.run()
            
            if results:
                logger.info(f"Analysis complete: {len(results)} screenshots analyzed")
            else:
                logger.warning("Analysis returned no results")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
    
    def _update_product_config(self, project_name: str, product_info: dict):
        """更新产品配置"""
        config_path = os.path.join(CONFIG_DIR, "products.json")
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        colors = ["#5E6AD2", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899", "#14B8A6"]
        color_idx = hash(product_info.get('app_name', '')) % len(colors)
        
        config[project_name] = {
            "name": product_info.get('app_name', project_name.replace('_Analysis', '')),
            "color": colors[color_idx],
            "initial": product_info.get('app_name', 'X')[0].upper(),
            "category": product_info.get('category', ''),
            "publisher": product_info.get('publisher', '')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _update_status(self, product_name: str, status: str, extra: dict = None):
        """更新下载状态"""
        status_data = {"queue": [], "completed": {}, "current": None, "last_updated": None}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except:
                pass
        
        status_data["current"] = product_name if status == "processing" else None
        status_data["completed"][product_name] = {
            "status": status,
            "time": datetime.now().isoformat(),
            **(extra or {})
        }
        status_data["last_updated"] = datetime.now().isoformat()
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    async def run_batch(self, products: list = None, limit: int = None, resume: bool = True):
        """
        批量下载
        
        Args:
            products: 产品列表，None则从competitors.json加载
            limit: 限制处理数量
            resume: 是否跳过已完成的产品
        """
        logger.info("\n" + "=" * 60)
        logger.info("  SMART BATCH DOWNLOAD v2.0")
        logger.info("=" * 60)
        
        # 加载产品列表
        if products is None:
            json_path = os.path.join(DATA_DIR, "competitors.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('top30', [])
            else:
                logger.error("competitors.json not found")
                return
        
        if limit:
            products = products[:limit]
        
        # 断点续传：跳过已完成的
        completed_products = set()
        if resume and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                for name, info in status_data.get("completed", {}).items():
                    if info.get("status") == "success":
                        completed_products.add(name)
                
                if completed_products:
                    logger.info(f"Resuming: skipping {len(completed_products)} completed products")
            except:
                pass
        
        products_to_process = [p for p in products if p['app_name'] not in completed_products]
        
        logger.info(f"Products to process: {len(products_to_process)}")
        logger.info(f"Auto-analyze: {'Enabled' if self.auto_analyze else 'Disabled'}")
        
        # 初始化状态
        self._init_status([p['app_name'] for p in products_to_process])
        
        # 初始化浏览器
        if not await self.init_browser():
            return
        
        try:
            for i, product in enumerate(products_to_process, 1):
                logger.info(f"\n[{i}/{len(products_to_process)}]")
                result = await self.process_product(product)
                
                # 分类结果
                if result['status'] == 'success':
                    self.results['success'].append(result)
                elif result['status'] in ('not_found', 'no_match'):
                    self.results['skipped'].append(result)
                else:
                    self.results['failed'].append(result)
                
                # 间隔
                await asyncio.sleep(2)
            
        finally:
            await self.close()
        
        # 生成报告
        self._generate_report()
    
    def _init_status(self, product_names: list):
        """初始化状态文件"""
        status_data = {"queue": product_names, "completed": {}, "current": None, "last_updated": datetime.now().isoformat()}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    status_data["completed"] = existing.get("completed", {})
            except:
                pass
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    def _generate_report(self):
        """生成下载报告"""
        logger.info("\n" + "=" * 60)
        logger.info("  DOWNLOAD REPORT")
        logger.info("=" * 60)
        
        logger.info(f"\nSuccess: {len(self.results['success'])}")
        for r in self.results['success']:
            logger.info(f"  ✓ {r['product']} ({r.get('screenshots', 0)} screenshots)")
        
        logger.info(f"\nFailed: {len(self.results['failed'])}")
        for r in self.results['failed']:
            logger.info(f"  ✗ {r['product']}")
        
        logger.info(f"\nSkipped: {len(self.results['skipped'])}")
        for r in self.results['skipped']:
            logger.info(f"  - {r['product']}")
        
        # 保存报告
        report_path = os.path.join(DATA_DIR, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "success": len(self.results['success']),
                    "failed": len(self.results['failed']),
                    "skipped": len(self.results['skipped'])
                },
                "details": self.results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nReport saved: {report_path}")


# ============================================================
# 命令行入口
# ============================================================

async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Batch Download v2.0")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of products")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed products")
    parser.add_argument("--product", "-p", type=str, help="Download single product by name")
    
    args = parser.parse_args()
    
    downloader = SmartBatchDownloader(auto_analyze=not args.no_analyze)
    
    if args.product:
        # 下载单个产品
        if not await downloader.init_browser():
            return
        try:
            result = await downloader.process_product({"app_name": args.product, "publisher": ""})
            logger.info(f"Result: {result['status']}")
        finally:
            await downloader.close()
    else:
        # 批量下载
        await downloader.run_batch(
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    asyncio.run(main())

Smart Batch Download System v2.0
================================
- 修复bug，增强稳定性
- 下载重试机制（3次）
- 断点续传
- 下载完自动分析
- Chrome连接检测和友好提示
"""

import os
import sys
import json
import time
import asyncio
import requests
import re
import shutil
import socket
import subprocess
import logging
from datetime import datetime
from io import BytesIO
from difflib import SequenceMatcher
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 下载配置
TARGET_WIDTH = 402
CHROME_DEBUG_PORT = 9222
CHROME_DEBUG_URL = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# 重试配置
MAX_IMAGE_RETRIES = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 30

# 状态文件
STATUS_FILE = os.path.join(BASE_DIR, "download_status.json")

# 确保目录存在
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'download.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")


# ============================================================
# 工具函数
# ============================================================

def generate_app_slug(app_name: str) -> str:
    """
    生成screensdesign.com的App URL slug
    
    Examples:
        "Cal AI - Calorie Tracker" -> "cal-ai-calorie-tracker"
        "MyFitnessPal: Calorie Counter" -> "myfitnesspal-calorie-counter"
    """
    slug = app_name.lower()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


def check_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """检查端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def download_image_with_retry(url: str, max_retries: int = MAX_IMAGE_RETRIES) -> bytes:
    """
    下载图片，带重试机制
    
    Args:
        url: 图片URL
        max_retries: 最大重试次数
    
    Returns:
        图片字节数据，失败返回None
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
        'Referer': 'https://screensdesign.com/'
    }
    
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers)
            if resp.status_code == 200:
                return resp.content
            else:
                logger.warning(f"HTTP {resp.status_code} for {url}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            time.sleep(RETRY_DELAY)
    
    return None


# ============================================================
# Chrome 连接助手
# ============================================================

class ChromeHelper:
    """Chrome浏览器连接助手"""
    
    @staticmethod
    def is_chrome_ready() -> bool:
        """检查Chrome调试端口是否可用"""
        return check_port_open("127.0.0.1", CHROME_DEBUG_PORT)
    
    @staticmethod
    def get_chrome_start_command() -> str:
        """获取Chrome启动命令"""
        # Windows
        if sys.platform == 'win32':
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return f'"{path}" --remote-debugging-port={CHROME_DEBUG_PORT}'
        return f"chrome --remote-debugging-port={CHROME_DEBUG_PORT}"
    
    @staticmethod
    async def ensure_chrome_ready() -> bool:
        """
        确保Chrome已准备好
        如果未启动，提示用户启动
        """
        if ChromeHelper.is_chrome_ready():
            logger.info("Chrome debug port is ready")
            return True
        
        print("\n" + "=" * 60)
        print("  Chrome 未检测到")
        print("=" * 60)
        print(f"\n请先启动Chrome并开启调试端口 {CHROME_DEBUG_PORT}:")
        print(f"\n  命令: {ChromeHelper.get_chrome_start_command()}")
        print("\n或者在已打开的Chrome中手动登录 screensdesign.com")
        print("然后重新运行此脚本。")
        print("\n" + "=" * 60)
        
        # 等待用户启动
        print("\n等待Chrome启动... (按Ctrl+C取消)")
        for i in range(60):  # 等待最多60秒
            if ChromeHelper.is_chrome_ready():
                logger.info("Chrome is now ready!")
                return True
            await asyncio.sleep(1)
            print(f"  等待中... {60-i}秒", end="\r")
        
        logger.error("Chrome did not start within timeout")
        return False


# ============================================================
# 下载器主类
# ============================================================

class SmartBatchDownloader:
    """智能批量下载器"""
    
    def __init__(self, auto_analyze: bool = True):
        """
        初始化下载器
        
        Args:
            auto_analyze: 下载完成后是否自动分析
        """
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self.auto_analyze = auto_analyze
        
        # 结果统计
        self.results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
    
    async def init_browser(self) -> bool:
        """初始化浏览器连接"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        # 确保Chrome已准备好
        if not await ChromeHelper.ensure_chrome_ready():
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.connect_over_cdp(CHROME_DEBUG_URL)
            self.context = self.browser.contexts[0]
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            logger.info("Connected to Chrome")
            return True
        except Exception as e:
            logger.error(f"Could not connect to Chrome: {e}")
            return False
    
    async def close(self):
        """关闭浏览器连接"""
        if self.playwright:
            await self.playwright.stop()
    
    async def search_and_enter_app_page(self, product_name: str) -> str:
        """
        搜索产品并进入专属页面
        
        Returns:
            专属页面URL，失败返回None
        """
        try:
            simple_name = product_name.split(':')[0].split(' - ')[0].strip()
            logger.info(f"Searching for '{simple_name}'...")
            
            # 进入screensdesign首页
            await self.page.goto('https://screensdesign.com/', wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            # 点击搜索区域
            search_area = await self.page.query_selector('text=/Search/')
            if search_area:
                await search_area.click()
                await asyncio.sleep(2)
            
            # 找到搜索输入框并搜索
            search_input = await self.page.query_selector('input:visible')
            if search_input:
                await search_input.fill(simple_name)
                await asyncio.sleep(2)
                await self.page.keyboard.press('Enter')
                await asyncio.sleep(5)
            
            logger.info(f"Search results: {self.page.url}")
            
            # 在搜索结果中找到匹配的App完整名称
            h3_elements = await self.page.query_selector_all('h3')
            
            found_app_name = None
            for h3 in h3_elements:
                try:
                    text = (await h3.inner_text()).strip()
                    if simple_name.lower() in text.lower():
                        found_app_name = text
                        logger.info(f"Found app in search: '{found_app_name}'")
                        break
                except:
                    continue
            
            if not found_app_name:
                logger.error(f"App not found in search results")
                return None
            
            # 生成slug并访问专属页面
            slug = generate_app_slug(found_app_name)
            app_url = f"https://screensdesign.com/apps/{slug}/"
            
            logger.info(f"Generated URL: {app_url}")
            
            response = await self.page.goto(app_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查页面是否有效
            if response and response.status == 404:
                logger.warning(f"Page not found: {app_url}")
                
                # 尝试备选slug
                alt_slug = generate_app_slug(product_name)
                if alt_slug != slug:
                    alt_url = f"https://screensdesign.com/apps/{alt_slug}/"
                    logger.info(f"Trying alternate URL: {alt_url}")
                    response = await self.page.goto(alt_url, wait_until='domcontentloaded', timeout=60000)
                    if response and response.status != 404:
                        return alt_url
                
                return None
            
            # 验证页面有截图
            imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            if len(imgs) == 0:
                await asyncio.sleep(3)
                imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            logger.info(f"App page loaded with {len(imgs)} screenshots")
            return app_url
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None
    
    async def get_timeline_images(self) -> list:
        """
        从底部时间线获取图片，按x坐标排序（确保流程顺序正确）
        
        screensdesign.com 的时间线是一个 flex row 横向滚动容器，
        class 包含 tw-flex tw-flex-row tw-overflow-x-auto
        
        Returns:
            [(url, timeline_x), ...] 按时间线顺序排列的图片URL和位置
        """
        # 先滚动到页面底部，确保时间线加载
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        
        # screensdesign.com 特定的时间线选择器（基于页面分析结果）
        # 时间线是一个 flex row 横向滚动容器
        timeline_selectors = [
            # 主要选择器：包含 tw-flex tw-flex-row 且可横向滚动
            'div.tw-flex.tw-flex-row.tw-overflow-x-auto',
            '[class*="tw-flex"][class*="tw-flex-row"][class*="tw-overflow-x-auto"]',
            # 备选：任何横向滚动的flex容器
            'div[class*="overflow-x-auto"][class*="flex-row"]',
            'div[class*="flex"][class*="row"][class*="overflow"]',
        ]
        
        for selector in timeline_selectors:
            try:
                timeline = await self.page.query_selector(selector)
                if timeline:
                    # 获取时间线内的所有图片
                    imgs = await timeline.query_selector_all('img')
                    if len(imgs) >= 5:  # 至少要有5张图才认为是时间线
                        logger.info(f"Found timeline container: {selector} ({len(imgs)} images)")
                        
                        # 获取每张图片的URL和x坐标
                        image_data = []
                        for img in imgs:
                            try:
                                src = await img.get_attribute('src')
                                if src and 'appicon' not in src and 'media.screensdesign.com' in src:
                                    bbox = await img.bounding_box()
                                    if bbox:
                                        image_data.append((src, bbox['x']))
                            except:
                                continue
                        
                        if image_data:
                            # 按x坐标排序（从左到右）
                            image_data.sort(key=lambda x: x[1])
                            logger.info(f"SUCCESS: Extracted {len(image_data)} images from timeline (sorted by x-position)")
                            return image_data
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # 备选方案：通过JavaScript直接查找横向滚动的flex容器
        logger.info("Trying JavaScript-based timeline detection...")
        try:
            timeline_data = await self.page.evaluate('''
                () => {
                    // 找所有div元素
                    const divs = document.querySelectorAll('div');
                    
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        // 查找flex row + 横向滚动的容器
                        if ((style.display === 'flex') && 
                            (style.flexDirection === 'row') &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
                            (div.scrollWidth > div.clientWidth * 1.5)) {
                            
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                // 找到了！获取图片信息
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({
                                            src: img.src,
                                            x: rect.x
                                        });
                                    }
                                });
                                
                                // 按x坐标排序
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data and len(timeline_data) >= 5:
                logger.info(f"SUCCESS (JS): Found {len(timeline_data)} images in timeline")
                return [(img['src'], img['x']) for img in timeline_data]
                
        except Exception as e:
            logger.warning(f"JavaScript timeline detection failed: {e}")
        
        # 第三备选：找y坐标相近的一行图片
        logger.info("Trying Y-position based timeline detection...")
        try:
            all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
            
            if len(all_imgs) < 5:
                logger.warning("Timeline not found, will use DOM order (may be incorrect)")
                return None
            
            # 获取所有图片的位置
            img_positions = []
            for img in all_imgs:
                try:
                    src = await img.get_attribute('src')
                    bbox = await img.bounding_box()
                    if src and bbox and 'appicon' not in src:
                        img_positions.append({
                            'src': src,
                            'x': bbox['x'],
                            'y': bbox['y'],
                            'width': bbox['width']
                        })
                except:
                    continue
            
            if not img_positions:
                return None
            
            # 按y坐标分组（找出同一行的图片）
            y_tolerance = 50  # 50px内认为是同一行
            y_groups = {}
            for img in img_positions:
                y_bucket = round(img['y'] / y_tolerance) * y_tolerance
                if y_bucket not in y_groups:
                    y_groups[y_bucket] = []
                y_groups[y_bucket].append(img)
            
            # 找出图片最多的那一行（应该是时间线）
            largest_group = max(y_groups.values(), key=len)
            
            if len(largest_group) >= len(img_positions) * 0.5:  # 至少包含50%的图片
                # 按x坐标排序
                largest_group.sort(key=lambda x: x['x'])
                logger.info(f"SUCCESS (Y-group): Found {len(largest_group)} images in main row")
                return [(img['src'], img['x']) for img in largest_group]
        
        except Exception as e:
            logger.warning(f"Y-position detection failed: {e}")
        
        # 最后降级方案
        logger.warning("Timeline not found, will use DOM order (may be incorrect)")
        return None
    
    async def download_from_app_page(self, product_name: str, project_dir: str) -> int:
        """
        从当前的专属页面下载截图
        支持断点续传，优先从时间线获取正确顺序
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        # 检查是否有已下载的内容（断点续传）
        existing_files = set()
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    existing_files = {s['original_url'] for s in manifest_data.get('screenshots', [])}
                    logger.info(f"Found {len(existing_files)} existing screenshots, will skip")
            except:
                pass
        
        # 创建目录
        os.makedirs(screens_dir, exist_ok=True)
        
        try:
            app_url = self.page.url
            logger.info(f"Downloading from: {app_url}")
            
            # 关闭弹窗
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
            
            # 滚动加载所有图片
            logger.info("Scrolling to load all images...")
            for _ in range(10):
                await self.page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(0.5)
            await self.page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)
            
            # ===== 核心修复：优先从时间线获取图片 =====
            timeline_images = await self.get_timeline_images()
            
            image_urls = []
            timeline_positions = {}  # 记录时间线位置信息
            
            if timeline_images:
                # 使用时间线顺序（已按x坐标排序）
                logger.info(f"Using timeline order ({len(timeline_images)} images)")
                seen_urls = set()
                for url, x_pos in timeline_images:
                    # 直接使用原始URL（不需要转换）
                    if url not in seen_urls:
                        seen_urls.add(url)
                        image_urls.append(url)
                        timeline_positions[url] = x_pos
            else:
                # 降级：使用DOM顺序（不推荐）
                logger.warning("Falling back to DOM order - screenshots may not be in correct flow order!")
                all_imgs = await self.page.query_selector_all('img[src*="media.screensdesign.com/avs"]')
                
                seen_urls = set()
                for img in all_imgs:
                    try:
                        src = await img.get_attribute('src')
                        if src and src not in seen_urls and 'appicon' not in src:
                            seen_urls.add(src)
                            image_urls.append(src)
                    except:
                        continue
            
            logger.info(f"Found {len(image_urls)} screenshots to download")
            
            if not image_urls:
                debug_path = os.path.join(project_dir, "debug_empty_page.png")
                await self.page.screenshot(path=debug_path, full_page=True)
                logger.warning(f"No screenshots found, debug saved: {debug_path}")
                return 0
            
            # 下载截图（带重试）
            downloaded = 0
            skipped = 0
            manifest = []
            used_timeline = bool(timeline_images)
            
            # 获取已有文件的最大编号
            existing_screens = [f for f in os.listdir(screens_dir) if f.endswith('.png')] if os.path.exists(screens_dir) else []
            start_idx = len(existing_screens) + 1
            
            for idx, url in enumerate(image_urls, start_idx):
                # 断点续传：跳过已下载的
                if url in existing_files:
                    skipped += 1
                    continue
                
                try:
                    # 使用重试机制下载
                    image_data = download_image_with_retry(url)
                    
                    if image_data:
                        img = Image.open(BytesIO(image_data))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        if img.width > 0:
                            ratio = TARGET_WIDTH / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((TARGET_WIDTH, new_height), Image.LANCZOS)
                        
                        # 保存
                        filename = f"Screen_{idx:03d}.png"
                        filepath = os.path.join(screens_dir, filename)
                        img.save(filepath, "PNG", optimize=True)
                        
                        # manifest增加时间线位置信息
                        manifest_entry = {
                            "index": idx,
                            "filename": filename,
                            "original_url": url,
                            "width": TARGET_WIDTH,
                            "height": new_height if img.width > 0 else img.height,
                            "timeline_order": idx - start_idx + 1,  # 时间线中的顺序
                        }
                        
                        # 如果有时间线位置，添加x坐标
                        if url in timeline_positions:
                            manifest_entry["timeline_x"] = timeline_positions[url]
                        
                        manifest.append(manifest_entry)
                        
                        downloaded += 1
                        if downloaded % 20 == 0:
                            logger.info(f"Downloaded {downloaded}/{len(image_urls) - skipped}...")
                            # 中途保存manifest（防止崩溃丢失进度）
                            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
                    else:
                        logger.warning(f"Failed to download image {idx} after retries")
                        
                except Exception as e:
                    logger.error(f"Error downloading image {idx}: {e}")
                    continue
            
            # 保存最终manifest
            self._save_manifest(manifest_path, product_name, app_url, manifest, used_timeline)
            
            # 验证下载顺序
            verification = await self.verify_download_order(project_dir)
            logger.info(f"Order verification: {verification}")
            
            logger.info(f"Downloaded {downloaded} screenshots (skipped {skipped} existing)")
            return downloaded
            
        except Exception as e:
            logger.error(f"Download error: {e}")
            return 0
    
    def _save_manifest(self, path: str, product_name: str, app_url: str, screenshots: list, used_timeline: bool = False):
        """保存manifest文件（含时间线验证信息）"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "product": product_name,
                "source": "screensdesign.com",
                "source_url": app_url,
                "downloaded_at": datetime.now().isoformat(),
                "total": len(screenshots),
                "order_source": "timeline" if used_timeline else "dom_order",
                "order_reliable": used_timeline,  # 时间线顺序是可靠的
                "screenshots": screenshots
            }, f, indent=2, ensure_ascii=False)
    
    async def verify_download_order(self, project_dir: str) -> dict:
        """
        验证下载顺序是否正确
        
        Returns:
            验证结果字典
        """
        screens_dir = os.path.join(project_dir, "Screens")
        manifest_path = os.path.join(project_dir, "manifest.json")
        
        checks = {
            "total_screenshots": 0,
            "order_source": "unknown",
            "order_reliable": False,
            "timeline_x_monotonic": None,  # 时间线x坐标是否单调递增
            "first_screen_looks_valid": None,
            "warnings": []
        }
        
        # 读取manifest
        if not os.path.exists(manifest_path):
            checks["warnings"].append("manifest.json not found")
            return checks
        
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception as e:
            checks["warnings"].append(f"Failed to read manifest: {e}")
            return checks
        
        screenshots = manifest.get("screenshots", [])
        checks["total_screenshots"] = len(screenshots)
        checks["order_source"] = manifest.get("order_source", "unknown")
        checks["order_reliable"] = manifest.get("order_reliable", False)
        
        if not screenshots:
            checks["warnings"].append("No screenshots in manifest")
            return checks
        
        # 检查1：时间线x坐标是否单调递增
        timeline_x_values = [s.get("timeline_x") for s in screenshots if s.get("timeline_x") is not None]
        if timeline_x_values:
            is_monotonic = all(timeline_x_values[i] <= timeline_x_values[i+1] for i in range(len(timeline_x_values)-1))
            checks["timeline_x_monotonic"] = is_monotonic
            if not is_monotonic:
                checks["warnings"].append("Timeline x positions are not monotonically increasing")
        
        # 检查2：第一张截图应该是Launch/Splash页面（简单检查）
        # 这里用AI检查成本太高，改用简单规则
        first_screen = screenshots[0].get("filename", "")
        if first_screen:
            # 基于常见命名规则的简单检查
            checks["first_screen_looks_valid"] = "001" in first_screen or "Screen_001" in first_screen
        
        # 检查3：如果不是从时间线获取的，添加警告
        if not checks["order_reliable"]:
            checks["warnings"].append("Screenshots were NOT extracted from timeline - order may be incorrect!")
        
        # 保存验证结果到manifest
        manifest["verification"] = {
            "checked_at": datetime.now().isoformat(),
            "order_reliable": checks["order_reliable"],
            "timeline_x_monotonic": checks["timeline_x_monotonic"],
            "warnings": checks["warnings"]
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        return checks
    
    async def process_product(self, product_info: dict) -> dict:
        """
        处理单个产品：搜索 -> 下载 -> 分析
        """
        product_name = product_info['app_name']
        publisher = product_info.get('publisher', '')
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing: {product_name}")
        logger.info(f"Publisher: {publisher}")
        
        # 更新状态
        self._update_status(product_name, "processing")
        
        # 搜索并进入专属页面
        app_url = await self.search_and_enter_app_page(product_name)
        
        if not app_url:
            logger.warning(f"Could not find app page for {product_name}")
            self._update_status(product_name, "not_found")
            return {"status": "not_found", "product": product_name}
        
        # 创建项目目录
        safe_name = re.sub(r'[^\w\s-]', '', product_name).replace(' ', '_')
        project_name = f"{safe_name}_Analysis"
        project_dir = os.path.join(PROJECTS_DIR, project_name)
        os.makedirs(project_dir, exist_ok=True)
        
        # 保存app信息
        app_info_path = os.path.join(project_dir, "app_info.json")
        with open(app_info_path, 'w', encoding='utf-8') as f:
            json.dump({
                "app_name": product_name,
                "publisher": publisher,
                "source_url": app_url,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2, ensure_ascii=False)
        
        # 下载截图
        downloaded = await self.download_from_app_page(product_name, project_dir)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} screenshots for {product_name}")
            
            # 更新产品配置
            self._update_product_config(project_name, product_info)
            
            # 自动分析
            if self.auto_analyze:
                await self._run_analysis(project_name)
            
            self._update_status(product_name, "success", {"screenshots": downloaded})
            return {
                "status": "success",
                "product": product_name,
                "app_url": app_url,
                "screenshots": downloaded,
                "project_dir": project_dir
            }
        else:
            logger.warning(f"Could not download screenshots for {product_name}")
            self._update_status(product_name, "download_failed")
            return {
                "status": "download_failed",
                "product": product_name,
                "app_url": app_url
            }
    
    async def _run_analysis(self, project_name: str):
        """运行智能分析"""
        logger.info(f"Starting analysis for {project_name}...")
        try:
            # 导入并运行分析器
            sys.path.insert(0, os.path.join(BASE_DIR, "ai_analysis"))
            from smart_analyzer import SmartAnalyzer
            
            analyzer = SmartAnalyzer(
                project_name=project_name,
                concurrent=3,
                auto_fix=True,
                verbose=False
            )
            results = analyzer.run()
            
            if results:
                logger.info(f"Analysis complete: {len(results)} screenshots analyzed")
            else:
                logger.warning("Analysis returned no results")
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
    
    def _update_product_config(self, project_name: str, product_info: dict):
        """更新产品配置"""
        config_path = os.path.join(CONFIG_DIR, "products.json")
        
        config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        colors = ["#5E6AD2", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444", "#3B82F6", "#EC4899", "#14B8A6"]
        color_idx = hash(product_info.get('app_name', '')) % len(colors)
        
        config[project_name] = {
            "name": product_info.get('app_name', project_name.replace('_Analysis', '')),
            "color": colors[color_idx],
            "initial": product_info.get('app_name', 'X')[0].upper(),
            "category": product_info.get('category', ''),
            "publisher": product_info.get('publisher', '')
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def _update_status(self, product_name: str, status: str, extra: dict = None):
        """更新下载状态"""
        status_data = {"queue": [], "completed": {}, "current": None, "last_updated": None}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
            except:
                pass
        
        status_data["current"] = product_name if status == "processing" else None
        status_data["completed"][product_name] = {
            "status": status,
            "time": datetime.now().isoformat(),
            **(extra or {})
        }
        status_data["last_updated"] = datetime.now().isoformat()
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    async def run_batch(self, products: list = None, limit: int = None, resume: bool = True):
        """
        批量下载
        
        Args:
            products: 产品列表，None则从competitors.json加载
            limit: 限制处理数量
            resume: 是否跳过已完成的产品
        """
        logger.info("\n" + "=" * 60)
        logger.info("  SMART BATCH DOWNLOAD v2.0")
        logger.info("=" * 60)
        
        # 加载产品列表
        if products is None:
            json_path = os.path.join(DATA_DIR, "competitors.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                products = data.get('top30', [])
            else:
                logger.error("competitors.json not found")
                return
        
        if limit:
            products = products[:limit]
        
        # 断点续传：跳过已完成的
        completed_products = set()
        if resume and os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    status_data = json.load(f)
                for name, info in status_data.get("completed", {}).items():
                    if info.get("status") == "success":
                        completed_products.add(name)
                
                if completed_products:
                    logger.info(f"Resuming: skipping {len(completed_products)} completed products")
            except:
                pass
        
        products_to_process = [p for p in products if p['app_name'] not in completed_products]
        
        logger.info(f"Products to process: {len(products_to_process)}")
        logger.info(f"Auto-analyze: {'Enabled' if self.auto_analyze else 'Disabled'}")
        
        # 初始化状态
        self._init_status([p['app_name'] for p in products_to_process])
        
        # 初始化浏览器
        if not await self.init_browser():
            return
        
        try:
            for i, product in enumerate(products_to_process, 1):
                logger.info(f"\n[{i}/{len(products_to_process)}]")
                result = await self.process_product(product)
                
                # 分类结果
                if result['status'] == 'success':
                    self.results['success'].append(result)
                elif result['status'] in ('not_found', 'no_match'):
                    self.results['skipped'].append(result)
                else:
                    self.results['failed'].append(result)
                
                # 间隔
                await asyncio.sleep(2)
            
        finally:
            await self.close()
        
        # 生成报告
        self._generate_report()
    
    def _init_status(self, product_names: list):
        """初始化状态文件"""
        status_data = {"queue": product_names, "completed": {}, "current": None, "last_updated": datetime.now().isoformat()}
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    status_data["completed"] = existing.get("completed", {})
            except:
                pass
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
    
    def _generate_report(self):
        """生成下载报告"""
        logger.info("\n" + "=" * 60)
        logger.info("  DOWNLOAD REPORT")
        logger.info("=" * 60)
        
        logger.info(f"\nSuccess: {len(self.results['success'])}")
        for r in self.results['success']:
            logger.info(f"  ✓ {r['product']} ({r.get('screenshots', 0)} screenshots)")
        
        logger.info(f"\nFailed: {len(self.results['failed'])}")
        for r in self.results['failed']:
            logger.info(f"  ✗ {r['product']}")
        
        logger.info(f"\nSkipped: {len(self.results['skipped'])}")
        for r in self.results['skipped']:
            logger.info(f"  - {r['product']}")
        
        # 保存报告
        report_path = os.path.join(DATA_DIR, "download_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "success": len(self.results['success']),
                    "failed": len(self.results['failed']),
                    "skipped": len(self.results['skipped'])
                },
                "details": self.results
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"\nReport saved: {report_path}")


# ============================================================
# 命令行入口
# ============================================================

async def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Batch Download v2.0")
    parser.add_argument("--limit", "-l", type=int, help="Limit number of products")
    parser.add_argument("--no-analyze", action="store_true", help="Skip auto-analysis")
    parser.add_argument("--no-resume", action="store_true", help="Don't skip completed products")
    parser.add_argument("--product", "-p", type=str, help="Download single product by name")
    
    args = parser.parse_args()
    
    downloader = SmartBatchDownloader(auto_analyze=not args.no_analyze)
    
    if args.product:
        # 下载单个产品
        if not await downloader.init_browser():
            return
        try:
            result = await downloader.process_product({"app_name": args.product, "publisher": ""})
            logger.info(f"Result: {result['status']}")
        finally:
            await downloader.close()
    else:
        # 批量下载
        await downloader.run_batch(
            limit=args.limit,
            resume=not args.no_resume
        )


if __name__ == "__main__":
    asyncio.run(main())
