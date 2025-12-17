# -*- coding: utf-8 -*-
"""
健壮下载系统 v1.0
==================
- 断点续传：任何时候中断都能继续
- 自动重试：网络问题自动恢复
- 独立任务：一个失败不影响其他
- 进度持久化：实时保存到文件
- 详细日志：便于排查问题

使用方式:
    python robust_download.py              # 执行所有待完成任务
    python robust_download.py --status     # 查看进度
    python robust_download.py --retry      # 重试失败的任务
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
PROGRESS_FILE = BASE_DIR / "task_progress.json"
ERROR_FILE = BASE_DIR / "task_errors.json"
LOG_FILE = BASE_DIR / "logs" / "robust_download.log"

# 确保目录存在
(BASE_DIR / "logs").mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

# 任务配置
TASKS = {
    "Calm": {
        "url": "https://screensdesign.com/apps/calm/",
        "project_name": "Calm_Analysis"
    },
    "Flo": {
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/",
        "project_name": "Flo_Period_Pregnancy_Tracker_Analysis"
    },
    "Runna": {
        "url": "https://screensdesign.com/apps/runna-running-training-plans/",
        "project_name": "Runna_Running_Training_Plans_Analysis"
    },
    "Strava": {
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/",
        "project_name": "Strava_Run_Bike_Hike_Analysis"
    }
}

# 重试配置
MAX_TASK_RETRIES = 3          # 每个任务最大重试次数
MAX_PAGE_RETRIES = 5          # 页面加载最大重试次数
MAX_IMAGE_RETRIES = 3         # 图片下载最大重试次数
RETRY_WAIT_BASE = 10          # 重试等待基础秒数
CHROME_RECONNECT_WAIT = 30    # Chrome重连等待秒数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# 进度管理
# ============================================================

def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 初始化进度
    return {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tasks": {name: {"status": "pending", "retry_count": 0} for name in TASKS}
    }


def save_progress(progress: dict):
    """保存进度文件"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def log_error(task_name: str, error: str):
    """记录错误"""
    errors = {}
    if ERROR_FILE.exists():
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except:
            pass
    
    if task_name not in errors:
        errors[task_name] = []
    
    errors[task_name].append({
        "time": datetime.now().isoformat(),
        "error": str(error)[:500]
    })
    
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


# ============================================================
# 浏览器管理
# ============================================================

class BrowserManager:
    """浏览器连接管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def connect(self) -> bool:
        """连接到Chrome"""
        from playwright.async_api import async_playwright
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9222"
                )
                self.page = self.browser.contexts[0].pages[0]
                logger.info("Connected to Chrome")
                return True
                
            except Exception as e:
                logger.warning(f"Chrome connection attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = CHROME_RECONNECT_WAIT * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Could not connect to Chrome after all retries")
        return False
    
    async def ensure_connected(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser and self.browser.is_connected():
                return True
        except:
            pass
        
        logger.info("Browser disconnected, reconnecting...")
        return await self.connect()
    
    async def close(self):
        """关闭连接"""
        if self.playwright:
            await self.playwright.stop()


# ============================================================
# 下载器
# ============================================================

class RobustDownloader:
    """健壮下载器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager
        self.current_task = None
    
    async def download_product(self, task_name: str, url: str, project_name: str, progress: dict) -> bool:
        """
        下载单个产品
        
        Returns:
            True=成功, False=失败
        """
        self.current_task = task_name
        project_dir = PROJECTS_DIR / project_name
        screens_dir = project_dir / "Screens"
        manifest_path = project_dir / "manifest.json"
        
        project_dir.mkdir(exist_ok=True)
        screens_dir.mkdir(exist_ok=True)
        
        # 检查已下载的进度
        existing_count = len(list(screens_dir.glob("*.png")))
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing screenshots, will continue from there")
        
        # 加载页面
        logger.info(f"Loading page: {url}")
        page_loaded = await self._load_page_with_retry(url)
        if not page_loaded:
            return False
        
        # 获取时间线图片
        logger.info("Extracting timeline images...")
        images = await self._get_timeline_images()
        if not images:
            logger.error("No images found in timeline")
            return False
        
        logger.info(f"Found {len(images)} images in timeline")
        
        # 更新进度
        progress["tasks"][task_name]["total_images"] = len(images)
        progress["tasks"][task_name]["status"] = "downloading"
        save_progress(progress)
        
        # 下载图片
        downloaded = await self._download_images(images, screens_dir, manifest_path, url, task_name, progress)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} images for {task_name}")
            
            # 保存manifest
            self._save_manifest(manifest_path, task_name, url, screens_dir)
            
            # 运行AI分析
            progress["tasks"][task_name]["status"] = "analyzing"
            save_progress(progress)
            
            analysis_success = await self._run_analysis(project_name)
            
            if analysis_success:
                progress["tasks"][task_name]["status"] = "completed"
                progress["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
            else:
                progress["tasks"][task_name]["status"] = "analysis_failed"
            
            save_progress(progress)
            return analysis_success
        
        return False
    
    async def _load_page_with_retry(self, url: str) -> bool:
        """带重试的页面加载"""
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                # 确保浏览器连接
                if not await self.bm.ensure_connected():
                    continue
                
                await self.bm.page.goto(url, timeout=90000, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # 滚动加载
                await self.bm.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                return True
                
            except Exception as e:
                logger.warning(f"Page load attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = RETRY_WAIT_BASE * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def _get_timeline_images(self) -> list:
        """获取时间线图片"""
        try:
            # 查找时间线容器
            timeline = await self.bm.page.query_selector('div.tw-flex.tw-flex-row.tw-overflow-x-auto')
            
            if timeline:
                imgs = await timeline.query_selector_all('img')
                if len(imgs) >= 5:
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
                    
                    # 按x坐标排序
                    image_data.sort(key=lambda x: x[1])
                    return image_data
            
            # 备选：JavaScript方式
            timeline_data = await self.bm.page.evaluate('''
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        if (style.display === 'flex' && style.flexDirection === 'row' &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({src: img.src, x: rect.x});
                                    }
                                });
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data:
                return [(img['src'], img['x']) for img in timeline_data]
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
        
        return []
    
    async def _download_images(self, images: list, screens_dir: Path, manifest_path: Path, 
                                url: str, task_name: str, progress: dict) -> int:
        """下载图片（带断点续传）"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        # 检查已下载的
        existing_files = set(f.name for f in screens_dir.glob("*.png"))
        
        downloaded = 0
        total = len(images)
        
        for idx, (img_url, x_pos) in enumerate(images, 1):
            filename = f"Screen_{idx:03d}.png"
            
            # 跳过已下载的
            if filename in existing_files:
                downloaded += 1
                continue
            
            # 下载图片（带重试）
            for attempt in range(MAX_IMAGE_RETRIES):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                        'Referer': 'https://screensdesign.com/'
                    }
                    resp = requests.get(img_url, timeout=30, headers=headers)
                    
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        target_width = 402
                        if img.width > 0:
                            ratio = target_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # 保存
                        filepath = screens_dir / filename
                        img.save(filepath, "PNG", optimize=True)
                        downloaded += 1
                        break
                    else:
                        logger.warning(f"HTTP {resp.status_code} for image {idx}")
                        
                except Exception as e:
                    logger.warning(f"Image {idx} download attempt {attempt + 1} failed: {e}")
                    if attempt < MAX_IMAGE_RETRIES - 1:
                        await asyncio.sleep(2)
            
            # 每20张保存一次进度
            if downloaded % 20 == 0:
                progress["tasks"][task_name]["downloaded"] = downloaded
                save_progress(progress)
                logger.info(f"Progress: {downloaded}/{total}")
        
        return downloaded
    
    def _save_manifest(self, manifest_path: Path, task_name: str, url: str, screens_dir: Path):
        """保存manifest"""
        screenshots = []
        for f in sorted(screens_dir.glob("*.png")):
            screenshots.append({
                "index": int(f.stem.split("_")[1]),
                "filename": f.name
            })
        
        manifest = {
            "product": task_name,
            "source": "screensdesign.com",
            "source_url": url,
            "downloaded_at": datetime.now().isoformat(),
            "total": len(screenshots),
            "order_source": "timeline",
            "order_reliable": True,
            "screenshots": screenshots
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _run_analysis(self, project_name: str) -> bool:
        """运行AI分析"""
        logger.info(f"Starting AI analysis for {project_name}...")
        
        try:
            sys.path.insert(0, str(BASE_DIR / "ai_analysis"))
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
                return True
            else:
                logger.warning("Analysis returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            log_error(project_name, str(e))
            return False


# ============================================================
# 主流程
# ============================================================

async def run_all_tasks():
    """运行所有任务"""
    progress = load_progress()
    
    # 显示当前状态
    print("\n" + "=" * 60)
    print("  ROBUST DOWNLOAD SYSTEM v1.0")
    print("=" * 60)
    print(f"\nTasks:")
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        print(f"  - {name}: {status}")
    print()
    
    # 找到待处理的任务
    pending_tasks = [
        name for name, info in progress["tasks"].items()
        if info.get("status") not in ("completed", "skipped")
    ]
    
    if not pending_tasks:
        print("All tasks completed!")
        return
    
    print(f"Tasks to process: {len(pending_tasks)}")
    print()
    
    # 连接浏览器
    bm = BrowserManager()
    if not await bm.connect():
        print("\nERROR: Could not connect to Chrome.")
        print("Please make sure Chrome is running with: --remote-debugging-port=9222")
        return
    
    downloader = RobustDownloader(bm)
    
    try:
        for task_name in pending_tasks:
            task_config = TASKS[task_name]
            task_info = progress["tasks"][task_name]
            
            print(f"\n{'=' * 50}")
            print(f"  Processing: {task_name}")
            print(f"  Retry count: {task_info.get('retry_count', 0)}")
            print(f"{'=' * 50}")
            
            # 检查重试次数
            if task_info.get("retry_count", 0) >= MAX_TASK_RETRIES:
                logger.warning(f"Task {task_name} exceeded max retries, skipping")
                task_info["status"] = "max_retries_exceeded"
                save_progress(progress)
                continue
            
            # 执行任务
            success = await downloader.download_product(
                task_name,
                task_config["url"],
                task_config["project_name"],
                progress
            )
            
            if not success:
                task_info["retry_count"] = task_info.get("retry_count", 0) + 1
                task_info["status"] = "failed"
                save_progress(progress)
                
                # 等待后继续下一个任务
                logger.info("Task failed, waiting before next task...")
                await asyncio.sleep(RETRY_WAIT_BASE)
            
            # 任务间隔
            await asyncio.sleep(3)
    
    finally:
        await bm.close()
    
    # 生成报告
    generate_report(progress)


def generate_report(progress: dict):
    """生成最终报告"""
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    
    completed = []
    failed = []
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        if status == "completed":
            completed.append(name)
        elif status not in ("pending",):
            failed.append((name, status))
    
    print(f"\nCompleted: {len(completed)}/{len(TASKS)}")
    for name in completed:
        print(f"  ✓ {name}")
    
    if failed:
        print(f"\nFailed/Incomplete: {len(failed)}")
        for name, status in failed:
            print(f"  ✗ {name} ({status})")
        print(f"\nCheck {ERROR_FILE} for error details")
        print("Run again to retry failed tasks")
    else:
        print("\nAll tasks completed successfully!")
    
    print("\n" + "=" * 60)


def show_status():
    """显示当前状态"""
    progress = load_progress()
    
    print("\n" + "=" * 60)
    print("  TASK STATUS")
    print("=" * 60)
    print(f"\nLast updated: {progress.get('last_updated', 'N/A')}")
    print("\nTasks:")
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        downloaded = info.get("downloaded", 0)
        total = info.get("total_images", "?")
        retries = info.get("retry_count", 0)
        
        status_icon = "✓" if status == "completed" else "○" if status == "pending" else "✗"
        print(f"  {status_icon} {name}: {status}")
        if downloaded:
            print(f"      Downloaded: {downloaded}/{total}")
        if retries > 0:
            print(f"      Retries: {retries}")
    
    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Download System")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--retry", action="store_true", help="Reset failed tasks and retry")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.retry:
        progress = load_progress()
        for name, info in progress["tasks"].items():
            if info.get("status") not in ("completed",):
                info["status"] = "pending"
                info["retry_count"] = 0
        save_progress(progress)
        print("Failed tasks reset. Run again to retry.")
    else:
        asyncio.run(run_all_tasks())


"""
健壮下载系统 v1.0
==================
- 断点续传：任何时候中断都能继续
- 自动重试：网络问题自动恢复
- 独立任务：一个失败不影响其他
- 进度持久化：实时保存到文件
- 详细日志：便于排查问题

使用方式:
    python robust_download.py              # 执行所有待完成任务
    python robust_download.py --status     # 查看进度
    python robust_download.py --retry      # 重试失败的任务
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
PROGRESS_FILE = BASE_DIR / "task_progress.json"
ERROR_FILE = BASE_DIR / "task_errors.json"
LOG_FILE = BASE_DIR / "logs" / "robust_download.log"

# 确保目录存在
(BASE_DIR / "logs").mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

# 任务配置
TASKS = {
    "Calm": {
        "url": "https://screensdesign.com/apps/calm/",
        "project_name": "Calm_Analysis"
    },
    "Flo": {
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/",
        "project_name": "Flo_Period_Pregnancy_Tracker_Analysis"
    },
    "Runna": {
        "url": "https://screensdesign.com/apps/runna-running-training-plans/",
        "project_name": "Runna_Running_Training_Plans_Analysis"
    },
    "Strava": {
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/",
        "project_name": "Strava_Run_Bike_Hike_Analysis"
    }
}

# 重试配置
MAX_TASK_RETRIES = 3          # 每个任务最大重试次数
MAX_PAGE_RETRIES = 5          # 页面加载最大重试次数
MAX_IMAGE_RETRIES = 3         # 图片下载最大重试次数
RETRY_WAIT_BASE = 10          # 重试等待基础秒数
CHROME_RECONNECT_WAIT = 30    # Chrome重连等待秒数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# 进度管理
# ============================================================

def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 初始化进度
    return {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tasks": {name: {"status": "pending", "retry_count": 0} for name in TASKS}
    }


def save_progress(progress: dict):
    """保存进度文件"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def log_error(task_name: str, error: str):
    """记录错误"""
    errors = {}
    if ERROR_FILE.exists():
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except:
            pass
    
    if task_name not in errors:
        errors[task_name] = []
    
    errors[task_name].append({
        "time": datetime.now().isoformat(),
        "error": str(error)[:500]
    })
    
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


# ============================================================
# 浏览器管理
# ============================================================

class BrowserManager:
    """浏览器连接管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def connect(self) -> bool:
        """连接到Chrome"""
        from playwright.async_api import async_playwright
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9222"
                )
                self.page = self.browser.contexts[0].pages[0]
                logger.info("Connected to Chrome")
                return True
                
            except Exception as e:
                logger.warning(f"Chrome connection attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = CHROME_RECONNECT_WAIT * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Could not connect to Chrome after all retries")
        return False
    
    async def ensure_connected(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser and self.browser.is_connected():
                return True
        except:
            pass
        
        logger.info("Browser disconnected, reconnecting...")
        return await self.connect()
    
    async def close(self):
        """关闭连接"""
        if self.playwright:
            await self.playwright.stop()


# ============================================================
# 下载器
# ============================================================

class RobustDownloader:
    """健壮下载器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager
        self.current_task = None
    
    async def download_product(self, task_name: str, url: str, project_name: str, progress: dict) -> bool:
        """
        下载单个产品
        
        Returns:
            True=成功, False=失败
        """
        self.current_task = task_name
        project_dir = PROJECTS_DIR / project_name
        screens_dir = project_dir / "Screens"
        manifest_path = project_dir / "manifest.json"
        
        project_dir.mkdir(exist_ok=True)
        screens_dir.mkdir(exist_ok=True)
        
        # 检查已下载的进度
        existing_count = len(list(screens_dir.glob("*.png")))
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing screenshots, will continue from there")
        
        # 加载页面
        logger.info(f"Loading page: {url}")
        page_loaded = await self._load_page_with_retry(url)
        if not page_loaded:
            return False
        
        # 获取时间线图片
        logger.info("Extracting timeline images...")
        images = await self._get_timeline_images()
        if not images:
            logger.error("No images found in timeline")
            return False
        
        logger.info(f"Found {len(images)} images in timeline")
        
        # 更新进度
        progress["tasks"][task_name]["total_images"] = len(images)
        progress["tasks"][task_name]["status"] = "downloading"
        save_progress(progress)
        
        # 下载图片
        downloaded = await self._download_images(images, screens_dir, manifest_path, url, task_name, progress)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} images for {task_name}")
            
            # 保存manifest
            self._save_manifest(manifest_path, task_name, url, screens_dir)
            
            # 运行AI分析
            progress["tasks"][task_name]["status"] = "analyzing"
            save_progress(progress)
            
            analysis_success = await self._run_analysis(project_name)
            
            if analysis_success:
                progress["tasks"][task_name]["status"] = "completed"
                progress["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
            else:
                progress["tasks"][task_name]["status"] = "analysis_failed"
            
            save_progress(progress)
            return analysis_success
        
        return False
    
    async def _load_page_with_retry(self, url: str) -> bool:
        """带重试的页面加载"""
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                # 确保浏览器连接
                if not await self.bm.ensure_connected():
                    continue
                
                await self.bm.page.goto(url, timeout=90000, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # 滚动加载
                await self.bm.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                return True
                
            except Exception as e:
                logger.warning(f"Page load attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = RETRY_WAIT_BASE * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def _get_timeline_images(self) -> list:
        """获取时间线图片"""
        try:
            # 查找时间线容器
            timeline = await self.bm.page.query_selector('div.tw-flex.tw-flex-row.tw-overflow-x-auto')
            
            if timeline:
                imgs = await timeline.query_selector_all('img')
                if len(imgs) >= 5:
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
                    
                    # 按x坐标排序
                    image_data.sort(key=lambda x: x[1])
                    return image_data
            
            # 备选：JavaScript方式
            timeline_data = await self.bm.page.evaluate('''
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        if (style.display === 'flex' && style.flexDirection === 'row' &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({src: img.src, x: rect.x});
                                    }
                                });
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data:
                return [(img['src'], img['x']) for img in timeline_data]
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
        
        return []
    
    async def _download_images(self, images: list, screens_dir: Path, manifest_path: Path, 
                                url: str, task_name: str, progress: dict) -> int:
        """下载图片（带断点续传）"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        # 检查已下载的
        existing_files = set(f.name for f in screens_dir.glob("*.png"))
        
        downloaded = 0
        total = len(images)
        
        for idx, (img_url, x_pos) in enumerate(images, 1):
            filename = f"Screen_{idx:03d}.png"
            
            # 跳过已下载的
            if filename in existing_files:
                downloaded += 1
                continue
            
            # 下载图片（带重试）
            for attempt in range(MAX_IMAGE_RETRIES):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                        'Referer': 'https://screensdesign.com/'
                    }
                    resp = requests.get(img_url, timeout=30, headers=headers)
                    
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        target_width = 402
                        if img.width > 0:
                            ratio = target_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # 保存
                        filepath = screens_dir / filename
                        img.save(filepath, "PNG", optimize=True)
                        downloaded += 1
                        break
                    else:
                        logger.warning(f"HTTP {resp.status_code} for image {idx}")
                        
                except Exception as e:
                    logger.warning(f"Image {idx} download attempt {attempt + 1} failed: {e}")
                    if attempt < MAX_IMAGE_RETRIES - 1:
                        await asyncio.sleep(2)
            
            # 每20张保存一次进度
            if downloaded % 20 == 0:
                progress["tasks"][task_name]["downloaded"] = downloaded
                save_progress(progress)
                logger.info(f"Progress: {downloaded}/{total}")
        
        return downloaded
    
    def _save_manifest(self, manifest_path: Path, task_name: str, url: str, screens_dir: Path):
        """保存manifest"""
        screenshots = []
        for f in sorted(screens_dir.glob("*.png")):
            screenshots.append({
                "index": int(f.stem.split("_")[1]),
                "filename": f.name
            })
        
        manifest = {
            "product": task_name,
            "source": "screensdesign.com",
            "source_url": url,
            "downloaded_at": datetime.now().isoformat(),
            "total": len(screenshots),
            "order_source": "timeline",
            "order_reliable": True,
            "screenshots": screenshots
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _run_analysis(self, project_name: str) -> bool:
        """运行AI分析"""
        logger.info(f"Starting AI analysis for {project_name}...")
        
        try:
            sys.path.insert(0, str(BASE_DIR / "ai_analysis"))
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
                return True
            else:
                logger.warning("Analysis returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            log_error(project_name, str(e))
            return False


# ============================================================
# 主流程
# ============================================================

async def run_all_tasks():
    """运行所有任务"""
    progress = load_progress()
    
    # 显示当前状态
    print("\n" + "=" * 60)
    print("  ROBUST DOWNLOAD SYSTEM v1.0")
    print("=" * 60)
    print(f"\nTasks:")
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        print(f"  - {name}: {status}")
    print()
    
    # 找到待处理的任务
    pending_tasks = [
        name for name, info in progress["tasks"].items()
        if info.get("status") not in ("completed", "skipped")
    ]
    
    if not pending_tasks:
        print("All tasks completed!")
        return
    
    print(f"Tasks to process: {len(pending_tasks)}")
    print()
    
    # 连接浏览器
    bm = BrowserManager()
    if not await bm.connect():
        print("\nERROR: Could not connect to Chrome.")
        print("Please make sure Chrome is running with: --remote-debugging-port=9222")
        return
    
    downloader = RobustDownloader(bm)
    
    try:
        for task_name in pending_tasks:
            task_config = TASKS[task_name]
            task_info = progress["tasks"][task_name]
            
            print(f"\n{'=' * 50}")
            print(f"  Processing: {task_name}")
            print(f"  Retry count: {task_info.get('retry_count', 0)}")
            print(f"{'=' * 50}")
            
            # 检查重试次数
            if task_info.get("retry_count", 0) >= MAX_TASK_RETRIES:
                logger.warning(f"Task {task_name} exceeded max retries, skipping")
                task_info["status"] = "max_retries_exceeded"
                save_progress(progress)
                continue
            
            # 执行任务
            success = await downloader.download_product(
                task_name,
                task_config["url"],
                task_config["project_name"],
                progress
            )
            
            if not success:
                task_info["retry_count"] = task_info.get("retry_count", 0) + 1
                task_info["status"] = "failed"
                save_progress(progress)
                
                # 等待后继续下一个任务
                logger.info("Task failed, waiting before next task...")
                await asyncio.sleep(RETRY_WAIT_BASE)
            
            # 任务间隔
            await asyncio.sleep(3)
    
    finally:
        await bm.close()
    
    # 生成报告
    generate_report(progress)


def generate_report(progress: dict):
    """生成最终报告"""
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    
    completed = []
    failed = []
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        if status == "completed":
            completed.append(name)
        elif status not in ("pending",):
            failed.append((name, status))
    
    print(f"\nCompleted: {len(completed)}/{len(TASKS)}")
    for name in completed:
        print(f"  ✓ {name}")
    
    if failed:
        print(f"\nFailed/Incomplete: {len(failed)}")
        for name, status in failed:
            print(f"  ✗ {name} ({status})")
        print(f"\nCheck {ERROR_FILE} for error details")
        print("Run again to retry failed tasks")
    else:
        print("\nAll tasks completed successfully!")
    
    print("\n" + "=" * 60)


def show_status():
    """显示当前状态"""
    progress = load_progress()
    
    print("\n" + "=" * 60)
    print("  TASK STATUS")
    print("=" * 60)
    print(f"\nLast updated: {progress.get('last_updated', 'N/A')}")
    print("\nTasks:")
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        downloaded = info.get("downloaded", 0)
        total = info.get("total_images", "?")
        retries = info.get("retry_count", 0)
        
        status_icon = "✓" if status == "completed" else "○" if status == "pending" else "✗"
        print(f"  {status_icon} {name}: {status}")
        if downloaded:
            print(f"      Downloaded: {downloaded}/{total}")
        if retries > 0:
            print(f"      Retries: {retries}")
    
    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Download System")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--retry", action="store_true", help="Reset failed tasks and retry")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.retry:
        progress = load_progress()
        for name, info in progress["tasks"].items():
            if info.get("status") not in ("completed",):
                info["status"] = "pending"
                info["retry_count"] = 0
        save_progress(progress)
        print("Failed tasks reset. Run again to retry.")
    else:
        asyncio.run(run_all_tasks())


"""
健壮下载系统 v1.0
==================
- 断点续传：任何时候中断都能继续
- 自动重试：网络问题自动恢复
- 独立任务：一个失败不影响其他
- 进度持久化：实时保存到文件
- 详细日志：便于排查问题

使用方式:
    python robust_download.py              # 执行所有待完成任务
    python robust_download.py --status     # 查看进度
    python robust_download.py --retry      # 重试失败的任务
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
PROGRESS_FILE = BASE_DIR / "task_progress.json"
ERROR_FILE = BASE_DIR / "task_errors.json"
LOG_FILE = BASE_DIR / "logs" / "robust_download.log"

# 确保目录存在
(BASE_DIR / "logs").mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

# 任务配置
TASKS = {
    "Calm": {
        "url": "https://screensdesign.com/apps/calm/",
        "project_name": "Calm_Analysis"
    },
    "Flo": {
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/",
        "project_name": "Flo_Period_Pregnancy_Tracker_Analysis"
    },
    "Runna": {
        "url": "https://screensdesign.com/apps/runna-running-training-plans/",
        "project_name": "Runna_Running_Training_Plans_Analysis"
    },
    "Strava": {
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/",
        "project_name": "Strava_Run_Bike_Hike_Analysis"
    }
}

# 重试配置
MAX_TASK_RETRIES = 3          # 每个任务最大重试次数
MAX_PAGE_RETRIES = 5          # 页面加载最大重试次数
MAX_IMAGE_RETRIES = 3         # 图片下载最大重试次数
RETRY_WAIT_BASE = 10          # 重试等待基础秒数
CHROME_RECONNECT_WAIT = 30    # Chrome重连等待秒数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# 进度管理
# ============================================================

def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 初始化进度
    return {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tasks": {name: {"status": "pending", "retry_count": 0} for name in TASKS}
    }


def save_progress(progress: dict):
    """保存进度文件"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def log_error(task_name: str, error: str):
    """记录错误"""
    errors = {}
    if ERROR_FILE.exists():
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except:
            pass
    
    if task_name not in errors:
        errors[task_name] = []
    
    errors[task_name].append({
        "time": datetime.now().isoformat(),
        "error": str(error)[:500]
    })
    
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


# ============================================================
# 浏览器管理
# ============================================================

class BrowserManager:
    """浏览器连接管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def connect(self) -> bool:
        """连接到Chrome"""
        from playwright.async_api import async_playwright
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9222"
                )
                self.page = self.browser.contexts[0].pages[0]
                logger.info("Connected to Chrome")
                return True
                
            except Exception as e:
                logger.warning(f"Chrome connection attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = CHROME_RECONNECT_WAIT * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Could not connect to Chrome after all retries")
        return False
    
    async def ensure_connected(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser and self.browser.is_connected():
                return True
        except:
            pass
        
        logger.info("Browser disconnected, reconnecting...")
        return await self.connect()
    
    async def close(self):
        """关闭连接"""
        if self.playwright:
            await self.playwright.stop()


# ============================================================
# 下载器
# ============================================================

class RobustDownloader:
    """健壮下载器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager
        self.current_task = None
    
    async def download_product(self, task_name: str, url: str, project_name: str, progress: dict) -> bool:
        """
        下载单个产品
        
        Returns:
            True=成功, False=失败
        """
        self.current_task = task_name
        project_dir = PROJECTS_DIR / project_name
        screens_dir = project_dir / "Screens"
        manifest_path = project_dir / "manifest.json"
        
        project_dir.mkdir(exist_ok=True)
        screens_dir.mkdir(exist_ok=True)
        
        # 检查已下载的进度
        existing_count = len(list(screens_dir.glob("*.png")))
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing screenshots, will continue from there")
        
        # 加载页面
        logger.info(f"Loading page: {url}")
        page_loaded = await self._load_page_with_retry(url)
        if not page_loaded:
            return False
        
        # 获取时间线图片
        logger.info("Extracting timeline images...")
        images = await self._get_timeline_images()
        if not images:
            logger.error("No images found in timeline")
            return False
        
        logger.info(f"Found {len(images)} images in timeline")
        
        # 更新进度
        progress["tasks"][task_name]["total_images"] = len(images)
        progress["tasks"][task_name]["status"] = "downloading"
        save_progress(progress)
        
        # 下载图片
        downloaded = await self._download_images(images, screens_dir, manifest_path, url, task_name, progress)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} images for {task_name}")
            
            # 保存manifest
            self._save_manifest(manifest_path, task_name, url, screens_dir)
            
            # 运行AI分析
            progress["tasks"][task_name]["status"] = "analyzing"
            save_progress(progress)
            
            analysis_success = await self._run_analysis(project_name)
            
            if analysis_success:
                progress["tasks"][task_name]["status"] = "completed"
                progress["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
            else:
                progress["tasks"][task_name]["status"] = "analysis_failed"
            
            save_progress(progress)
            return analysis_success
        
        return False
    
    async def _load_page_with_retry(self, url: str) -> bool:
        """带重试的页面加载"""
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                # 确保浏览器连接
                if not await self.bm.ensure_connected():
                    continue
                
                await self.bm.page.goto(url, timeout=90000, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # 滚动加载
                await self.bm.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                return True
                
            except Exception as e:
                logger.warning(f"Page load attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = RETRY_WAIT_BASE * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def _get_timeline_images(self) -> list:
        """获取时间线图片"""
        try:
            # 查找时间线容器
            timeline = await self.bm.page.query_selector('div.tw-flex.tw-flex-row.tw-overflow-x-auto')
            
            if timeline:
                imgs = await timeline.query_selector_all('img')
                if len(imgs) >= 5:
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
                    
                    # 按x坐标排序
                    image_data.sort(key=lambda x: x[1])
                    return image_data
            
            # 备选：JavaScript方式
            timeline_data = await self.bm.page.evaluate('''
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        if (style.display === 'flex' && style.flexDirection === 'row' &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({src: img.src, x: rect.x});
                                    }
                                });
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data:
                return [(img['src'], img['x']) for img in timeline_data]
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
        
        return []
    
    async def _download_images(self, images: list, screens_dir: Path, manifest_path: Path, 
                                url: str, task_name: str, progress: dict) -> int:
        """下载图片（带断点续传）"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        # 检查已下载的
        existing_files = set(f.name for f in screens_dir.glob("*.png"))
        
        downloaded = 0
        total = len(images)
        
        for idx, (img_url, x_pos) in enumerate(images, 1):
            filename = f"Screen_{idx:03d}.png"
            
            # 跳过已下载的
            if filename in existing_files:
                downloaded += 1
                continue
            
            # 下载图片（带重试）
            for attempt in range(MAX_IMAGE_RETRIES):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                        'Referer': 'https://screensdesign.com/'
                    }
                    resp = requests.get(img_url, timeout=30, headers=headers)
                    
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        target_width = 402
                        if img.width > 0:
                            ratio = target_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # 保存
                        filepath = screens_dir / filename
                        img.save(filepath, "PNG", optimize=True)
                        downloaded += 1
                        break
                    else:
                        logger.warning(f"HTTP {resp.status_code} for image {idx}")
                        
                except Exception as e:
                    logger.warning(f"Image {idx} download attempt {attempt + 1} failed: {e}")
                    if attempt < MAX_IMAGE_RETRIES - 1:
                        await asyncio.sleep(2)
            
            # 每20张保存一次进度
            if downloaded % 20 == 0:
                progress["tasks"][task_name]["downloaded"] = downloaded
                save_progress(progress)
                logger.info(f"Progress: {downloaded}/{total}")
        
        return downloaded
    
    def _save_manifest(self, manifest_path: Path, task_name: str, url: str, screens_dir: Path):
        """保存manifest"""
        screenshots = []
        for f in sorted(screens_dir.glob("*.png")):
            screenshots.append({
                "index": int(f.stem.split("_")[1]),
                "filename": f.name
            })
        
        manifest = {
            "product": task_name,
            "source": "screensdesign.com",
            "source_url": url,
            "downloaded_at": datetime.now().isoformat(),
            "total": len(screenshots),
            "order_source": "timeline",
            "order_reliable": True,
            "screenshots": screenshots
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _run_analysis(self, project_name: str) -> bool:
        """运行AI分析"""
        logger.info(f"Starting AI analysis for {project_name}...")
        
        try:
            sys.path.insert(0, str(BASE_DIR / "ai_analysis"))
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
                return True
            else:
                logger.warning("Analysis returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            log_error(project_name, str(e))
            return False


# ============================================================
# 主流程
# ============================================================

async def run_all_tasks():
    """运行所有任务"""
    progress = load_progress()
    
    # 显示当前状态
    print("\n" + "=" * 60)
    print("  ROBUST DOWNLOAD SYSTEM v1.0")
    print("=" * 60)
    print(f"\nTasks:")
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        print(f"  - {name}: {status}")
    print()
    
    # 找到待处理的任务
    pending_tasks = [
        name for name, info in progress["tasks"].items()
        if info.get("status") not in ("completed", "skipped")
    ]
    
    if not pending_tasks:
        print("All tasks completed!")
        return
    
    print(f"Tasks to process: {len(pending_tasks)}")
    print()
    
    # 连接浏览器
    bm = BrowserManager()
    if not await bm.connect():
        print("\nERROR: Could not connect to Chrome.")
        print("Please make sure Chrome is running with: --remote-debugging-port=9222")
        return
    
    downloader = RobustDownloader(bm)
    
    try:
        for task_name in pending_tasks:
            task_config = TASKS[task_name]
            task_info = progress["tasks"][task_name]
            
            print(f"\n{'=' * 50}")
            print(f"  Processing: {task_name}")
            print(f"  Retry count: {task_info.get('retry_count', 0)}")
            print(f"{'=' * 50}")
            
            # 检查重试次数
            if task_info.get("retry_count", 0) >= MAX_TASK_RETRIES:
                logger.warning(f"Task {task_name} exceeded max retries, skipping")
                task_info["status"] = "max_retries_exceeded"
                save_progress(progress)
                continue
            
            # 执行任务
            success = await downloader.download_product(
                task_name,
                task_config["url"],
                task_config["project_name"],
                progress
            )
            
            if not success:
                task_info["retry_count"] = task_info.get("retry_count", 0) + 1
                task_info["status"] = "failed"
                save_progress(progress)
                
                # 等待后继续下一个任务
                logger.info("Task failed, waiting before next task...")
                await asyncio.sleep(RETRY_WAIT_BASE)
            
            # 任务间隔
            await asyncio.sleep(3)
    
    finally:
        await bm.close()
    
    # 生成报告
    generate_report(progress)


def generate_report(progress: dict):
    """生成最终报告"""
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    
    completed = []
    failed = []
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        if status == "completed":
            completed.append(name)
        elif status not in ("pending",):
            failed.append((name, status))
    
    print(f"\nCompleted: {len(completed)}/{len(TASKS)}")
    for name in completed:
        print(f"  ✓ {name}")
    
    if failed:
        print(f"\nFailed/Incomplete: {len(failed)}")
        for name, status in failed:
            print(f"  ✗ {name} ({status})")
        print(f"\nCheck {ERROR_FILE} for error details")
        print("Run again to retry failed tasks")
    else:
        print("\nAll tasks completed successfully!")
    
    print("\n" + "=" * 60)


def show_status():
    """显示当前状态"""
    progress = load_progress()
    
    print("\n" + "=" * 60)
    print("  TASK STATUS")
    print("=" * 60)
    print(f"\nLast updated: {progress.get('last_updated', 'N/A')}")
    print("\nTasks:")
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        downloaded = info.get("downloaded", 0)
        total = info.get("total_images", "?")
        retries = info.get("retry_count", 0)
        
        status_icon = "✓" if status == "completed" else "○" if status == "pending" else "✗"
        print(f"  {status_icon} {name}: {status}")
        if downloaded:
            print(f"      Downloaded: {downloaded}/{total}")
        if retries > 0:
            print(f"      Retries: {retries}")
    
    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Download System")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--retry", action="store_true", help="Reset failed tasks and retry")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.retry:
        progress = load_progress()
        for name, info in progress["tasks"].items():
            if info.get("status") not in ("completed",):
                info["status"] = "pending"
                info["retry_count"] = 0
        save_progress(progress)
        print("Failed tasks reset. Run again to retry.")
    else:
        asyncio.run(run_all_tasks())


"""
健壮下载系统 v1.0
==================
- 断点续传：任何时候中断都能继续
- 自动重试：网络问题自动恢复
- 独立任务：一个失败不影响其他
- 进度持久化：实时保存到文件
- 详细日志：便于排查问题

使用方式:
    python robust_download.py              # 执行所有待完成任务
    python robust_download.py --status     # 查看进度
    python robust_download.py --retry      # 重试失败的任务
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
PROGRESS_FILE = BASE_DIR / "task_progress.json"
ERROR_FILE = BASE_DIR / "task_errors.json"
LOG_FILE = BASE_DIR / "logs" / "robust_download.log"

# 确保目录存在
(BASE_DIR / "logs").mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

# 任务配置
TASKS = {
    "Calm": {
        "url": "https://screensdesign.com/apps/calm/",
        "project_name": "Calm_Analysis"
    },
    "Flo": {
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/",
        "project_name": "Flo_Period_Pregnancy_Tracker_Analysis"
    },
    "Runna": {
        "url": "https://screensdesign.com/apps/runna-running-training-plans/",
        "project_name": "Runna_Running_Training_Plans_Analysis"
    },
    "Strava": {
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/",
        "project_name": "Strava_Run_Bike_Hike_Analysis"
    }
}

# 重试配置
MAX_TASK_RETRIES = 3          # 每个任务最大重试次数
MAX_PAGE_RETRIES = 5          # 页面加载最大重试次数
MAX_IMAGE_RETRIES = 3         # 图片下载最大重试次数
RETRY_WAIT_BASE = 10          # 重试等待基础秒数
CHROME_RECONNECT_WAIT = 30    # Chrome重连等待秒数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# 进度管理
# ============================================================

def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 初始化进度
    return {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tasks": {name: {"status": "pending", "retry_count": 0} for name in TASKS}
    }


def save_progress(progress: dict):
    """保存进度文件"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def log_error(task_name: str, error: str):
    """记录错误"""
    errors = {}
    if ERROR_FILE.exists():
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except:
            pass
    
    if task_name not in errors:
        errors[task_name] = []
    
    errors[task_name].append({
        "time": datetime.now().isoformat(),
        "error": str(error)[:500]
    })
    
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


# ============================================================
# 浏览器管理
# ============================================================

class BrowserManager:
    """浏览器连接管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def connect(self) -> bool:
        """连接到Chrome"""
        from playwright.async_api import async_playwright
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9222"
                )
                self.page = self.browser.contexts[0].pages[0]
                logger.info("Connected to Chrome")
                return True
                
            except Exception as e:
                logger.warning(f"Chrome connection attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = CHROME_RECONNECT_WAIT * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Could not connect to Chrome after all retries")
        return False
    
    async def ensure_connected(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser and self.browser.is_connected():
                return True
        except:
            pass
        
        logger.info("Browser disconnected, reconnecting...")
        return await self.connect()
    
    async def close(self):
        """关闭连接"""
        if self.playwright:
            await self.playwright.stop()


# ============================================================
# 下载器
# ============================================================

class RobustDownloader:
    """健壮下载器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager
        self.current_task = None
    
    async def download_product(self, task_name: str, url: str, project_name: str, progress: dict) -> bool:
        """
        下载单个产品
        
        Returns:
            True=成功, False=失败
        """
        self.current_task = task_name
        project_dir = PROJECTS_DIR / project_name
        screens_dir = project_dir / "Screens"
        manifest_path = project_dir / "manifest.json"
        
        project_dir.mkdir(exist_ok=True)
        screens_dir.mkdir(exist_ok=True)
        
        # 检查已下载的进度
        existing_count = len(list(screens_dir.glob("*.png")))
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing screenshots, will continue from there")
        
        # 加载页面
        logger.info(f"Loading page: {url}")
        page_loaded = await self._load_page_with_retry(url)
        if not page_loaded:
            return False
        
        # 获取时间线图片
        logger.info("Extracting timeline images...")
        images = await self._get_timeline_images()
        if not images:
            logger.error("No images found in timeline")
            return False
        
        logger.info(f"Found {len(images)} images in timeline")
        
        # 更新进度
        progress["tasks"][task_name]["total_images"] = len(images)
        progress["tasks"][task_name]["status"] = "downloading"
        save_progress(progress)
        
        # 下载图片
        downloaded = await self._download_images(images, screens_dir, manifest_path, url, task_name, progress)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} images for {task_name}")
            
            # 保存manifest
            self._save_manifest(manifest_path, task_name, url, screens_dir)
            
            # 运行AI分析
            progress["tasks"][task_name]["status"] = "analyzing"
            save_progress(progress)
            
            analysis_success = await self._run_analysis(project_name)
            
            if analysis_success:
                progress["tasks"][task_name]["status"] = "completed"
                progress["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
            else:
                progress["tasks"][task_name]["status"] = "analysis_failed"
            
            save_progress(progress)
            return analysis_success
        
        return False
    
    async def _load_page_with_retry(self, url: str) -> bool:
        """带重试的页面加载"""
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                # 确保浏览器连接
                if not await self.bm.ensure_connected():
                    continue
                
                await self.bm.page.goto(url, timeout=90000, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # 滚动加载
                await self.bm.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                return True
                
            except Exception as e:
                logger.warning(f"Page load attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = RETRY_WAIT_BASE * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def _get_timeline_images(self) -> list:
        """获取时间线图片"""
        try:
            # 查找时间线容器
            timeline = await self.bm.page.query_selector('div.tw-flex.tw-flex-row.tw-overflow-x-auto')
            
            if timeline:
                imgs = await timeline.query_selector_all('img')
                if len(imgs) >= 5:
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
                    
                    # 按x坐标排序
                    image_data.sort(key=lambda x: x[1])
                    return image_data
            
            # 备选：JavaScript方式
            timeline_data = await self.bm.page.evaluate('''
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        if (style.display === 'flex' && style.flexDirection === 'row' &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({src: img.src, x: rect.x});
                                    }
                                });
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data:
                return [(img['src'], img['x']) for img in timeline_data]
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
        
        return []
    
    async def _download_images(self, images: list, screens_dir: Path, manifest_path: Path, 
                                url: str, task_name: str, progress: dict) -> int:
        """下载图片（带断点续传）"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        # 检查已下载的
        existing_files = set(f.name for f in screens_dir.glob("*.png"))
        
        downloaded = 0
        total = len(images)
        
        for idx, (img_url, x_pos) in enumerate(images, 1):
            filename = f"Screen_{idx:03d}.png"
            
            # 跳过已下载的
            if filename in existing_files:
                downloaded += 1
                continue
            
            # 下载图片（带重试）
            for attempt in range(MAX_IMAGE_RETRIES):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                        'Referer': 'https://screensdesign.com/'
                    }
                    resp = requests.get(img_url, timeout=30, headers=headers)
                    
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        target_width = 402
                        if img.width > 0:
                            ratio = target_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # 保存
                        filepath = screens_dir / filename
                        img.save(filepath, "PNG", optimize=True)
                        downloaded += 1
                        break
                    else:
                        logger.warning(f"HTTP {resp.status_code} for image {idx}")
                        
                except Exception as e:
                    logger.warning(f"Image {idx} download attempt {attempt + 1} failed: {e}")
                    if attempt < MAX_IMAGE_RETRIES - 1:
                        await asyncio.sleep(2)
            
            # 每20张保存一次进度
            if downloaded % 20 == 0:
                progress["tasks"][task_name]["downloaded"] = downloaded
                save_progress(progress)
                logger.info(f"Progress: {downloaded}/{total}")
        
        return downloaded
    
    def _save_manifest(self, manifest_path: Path, task_name: str, url: str, screens_dir: Path):
        """保存manifest"""
        screenshots = []
        for f in sorted(screens_dir.glob("*.png")):
            screenshots.append({
                "index": int(f.stem.split("_")[1]),
                "filename": f.name
            })
        
        manifest = {
            "product": task_name,
            "source": "screensdesign.com",
            "source_url": url,
            "downloaded_at": datetime.now().isoformat(),
            "total": len(screenshots),
            "order_source": "timeline",
            "order_reliable": True,
            "screenshots": screenshots
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _run_analysis(self, project_name: str) -> bool:
        """运行AI分析"""
        logger.info(f"Starting AI analysis for {project_name}...")
        
        try:
            sys.path.insert(0, str(BASE_DIR / "ai_analysis"))
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
                return True
            else:
                logger.warning("Analysis returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            log_error(project_name, str(e))
            return False


# ============================================================
# 主流程
# ============================================================

async def run_all_tasks():
    """运行所有任务"""
    progress = load_progress()
    
    # 显示当前状态
    print("\n" + "=" * 60)
    print("  ROBUST DOWNLOAD SYSTEM v1.0")
    print("=" * 60)
    print(f"\nTasks:")
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        print(f"  - {name}: {status}")
    print()
    
    # 找到待处理的任务
    pending_tasks = [
        name for name, info in progress["tasks"].items()
        if info.get("status") not in ("completed", "skipped")
    ]
    
    if not pending_tasks:
        print("All tasks completed!")
        return
    
    print(f"Tasks to process: {len(pending_tasks)}")
    print()
    
    # 连接浏览器
    bm = BrowserManager()
    if not await bm.connect():
        print("\nERROR: Could not connect to Chrome.")
        print("Please make sure Chrome is running with: --remote-debugging-port=9222")
        return
    
    downloader = RobustDownloader(bm)
    
    try:
        for task_name in pending_tasks:
            task_config = TASKS[task_name]
            task_info = progress["tasks"][task_name]
            
            print(f"\n{'=' * 50}")
            print(f"  Processing: {task_name}")
            print(f"  Retry count: {task_info.get('retry_count', 0)}")
            print(f"{'=' * 50}")
            
            # 检查重试次数
            if task_info.get("retry_count", 0) >= MAX_TASK_RETRIES:
                logger.warning(f"Task {task_name} exceeded max retries, skipping")
                task_info["status"] = "max_retries_exceeded"
                save_progress(progress)
                continue
            
            # 执行任务
            success = await downloader.download_product(
                task_name,
                task_config["url"],
                task_config["project_name"],
                progress
            )
            
            if not success:
                task_info["retry_count"] = task_info.get("retry_count", 0) + 1
                task_info["status"] = "failed"
                save_progress(progress)
                
                # 等待后继续下一个任务
                logger.info("Task failed, waiting before next task...")
                await asyncio.sleep(RETRY_WAIT_BASE)
            
            # 任务间隔
            await asyncio.sleep(3)
    
    finally:
        await bm.close()
    
    # 生成报告
    generate_report(progress)


def generate_report(progress: dict):
    """生成最终报告"""
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    
    completed = []
    failed = []
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        if status == "completed":
            completed.append(name)
        elif status not in ("pending",):
            failed.append((name, status))
    
    print(f"\nCompleted: {len(completed)}/{len(TASKS)}")
    for name in completed:
        print(f"  ✓ {name}")
    
    if failed:
        print(f"\nFailed/Incomplete: {len(failed)}")
        for name, status in failed:
            print(f"  ✗ {name} ({status})")
        print(f"\nCheck {ERROR_FILE} for error details")
        print("Run again to retry failed tasks")
    else:
        print("\nAll tasks completed successfully!")
    
    print("\n" + "=" * 60)


def show_status():
    """显示当前状态"""
    progress = load_progress()
    
    print("\n" + "=" * 60)
    print("  TASK STATUS")
    print("=" * 60)
    print(f"\nLast updated: {progress.get('last_updated', 'N/A')}")
    print("\nTasks:")
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        downloaded = info.get("downloaded", 0)
        total = info.get("total_images", "?")
        retries = info.get("retry_count", 0)
        
        status_icon = "✓" if status == "completed" else "○" if status == "pending" else "✗"
        print(f"  {status_icon} {name}: {status}")
        if downloaded:
            print(f"      Downloaded: {downloaded}/{total}")
        if retries > 0:
            print(f"      Retries: {retries}")
    
    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Download System")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--retry", action="store_true", help="Reset failed tasks and retry")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.retry:
        progress = load_progress()
        for name, info in progress["tasks"].items():
            if info.get("status") not in ("completed",):
                info["status"] = "pending"
                info["retry_count"] = 0
        save_progress(progress)
        print("Failed tasks reset. Run again to retry.")
    else:
        asyncio.run(run_all_tasks())



"""
健壮下载系统 v1.0
==================
- 断点续传：任何时候中断都能继续
- 自动重试：网络问题自动恢复
- 独立任务：一个失败不影响其他
- 进度持久化：实时保存到文件
- 详细日志：便于排查问题

使用方式:
    python robust_download.py              # 执行所有待完成任务
    python robust_download.py --status     # 查看进度
    python robust_download.py --retry      # 重试失败的任务
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
PROGRESS_FILE = BASE_DIR / "task_progress.json"
ERROR_FILE = BASE_DIR / "task_errors.json"
LOG_FILE = BASE_DIR / "logs" / "robust_download.log"

# 确保目录存在
(BASE_DIR / "logs").mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

# 任务配置
TASKS = {
    "Calm": {
        "url": "https://screensdesign.com/apps/calm/",
        "project_name": "Calm_Analysis"
    },
    "Flo": {
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/",
        "project_name": "Flo_Period_Pregnancy_Tracker_Analysis"
    },
    "Runna": {
        "url": "https://screensdesign.com/apps/runna-running-training-plans/",
        "project_name": "Runna_Running_Training_Plans_Analysis"
    },
    "Strava": {
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/",
        "project_name": "Strava_Run_Bike_Hike_Analysis"
    }
}

# 重试配置
MAX_TASK_RETRIES = 3          # 每个任务最大重试次数
MAX_PAGE_RETRIES = 5          # 页面加载最大重试次数
MAX_IMAGE_RETRIES = 3         # 图片下载最大重试次数
RETRY_WAIT_BASE = 10          # 重试等待基础秒数
CHROME_RECONNECT_WAIT = 30    # Chrome重连等待秒数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# 进度管理
# ============================================================

def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 初始化进度
    return {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tasks": {name: {"status": "pending", "retry_count": 0} for name in TASKS}
    }


def save_progress(progress: dict):
    """保存进度文件"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def log_error(task_name: str, error: str):
    """记录错误"""
    errors = {}
    if ERROR_FILE.exists():
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except:
            pass
    
    if task_name not in errors:
        errors[task_name] = []
    
    errors[task_name].append({
        "time": datetime.now().isoformat(),
        "error": str(error)[:500]
    })
    
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


# ============================================================
# 浏览器管理
# ============================================================

class BrowserManager:
    """浏览器连接管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def connect(self) -> bool:
        """连接到Chrome"""
        from playwright.async_api import async_playwright
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9222"
                )
                self.page = self.browser.contexts[0].pages[0]
                logger.info("Connected to Chrome")
                return True
                
            except Exception as e:
                logger.warning(f"Chrome connection attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = CHROME_RECONNECT_WAIT * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Could not connect to Chrome after all retries")
        return False
    
    async def ensure_connected(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser and self.browser.is_connected():
                return True
        except:
            pass
        
        logger.info("Browser disconnected, reconnecting...")
        return await self.connect()
    
    async def close(self):
        """关闭连接"""
        if self.playwright:
            await self.playwright.stop()


# ============================================================
# 下载器
# ============================================================

class RobustDownloader:
    """健壮下载器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager
        self.current_task = None
    
    async def download_product(self, task_name: str, url: str, project_name: str, progress: dict) -> bool:
        """
        下载单个产品
        
        Returns:
            True=成功, False=失败
        """
        self.current_task = task_name
        project_dir = PROJECTS_DIR / project_name
        screens_dir = project_dir / "Screens"
        manifest_path = project_dir / "manifest.json"
        
        project_dir.mkdir(exist_ok=True)
        screens_dir.mkdir(exist_ok=True)
        
        # 检查已下载的进度
        existing_count = len(list(screens_dir.glob("*.png")))
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing screenshots, will continue from there")
        
        # 加载页面
        logger.info(f"Loading page: {url}")
        page_loaded = await self._load_page_with_retry(url)
        if not page_loaded:
            return False
        
        # 获取时间线图片
        logger.info("Extracting timeline images...")
        images = await self._get_timeline_images()
        if not images:
            logger.error("No images found in timeline")
            return False
        
        logger.info(f"Found {len(images)} images in timeline")
        
        # 更新进度
        progress["tasks"][task_name]["total_images"] = len(images)
        progress["tasks"][task_name]["status"] = "downloading"
        save_progress(progress)
        
        # 下载图片
        downloaded = await self._download_images(images, screens_dir, manifest_path, url, task_name, progress)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} images for {task_name}")
            
            # 保存manifest
            self._save_manifest(manifest_path, task_name, url, screens_dir)
            
            # 运行AI分析
            progress["tasks"][task_name]["status"] = "analyzing"
            save_progress(progress)
            
            analysis_success = await self._run_analysis(project_name)
            
            if analysis_success:
                progress["tasks"][task_name]["status"] = "completed"
                progress["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
            else:
                progress["tasks"][task_name]["status"] = "analysis_failed"
            
            save_progress(progress)
            return analysis_success
        
        return False
    
    async def _load_page_with_retry(self, url: str) -> bool:
        """带重试的页面加载"""
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                # 确保浏览器连接
                if not await self.bm.ensure_connected():
                    continue
                
                await self.bm.page.goto(url, timeout=90000, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # 滚动加载
                await self.bm.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                return True
                
            except Exception as e:
                logger.warning(f"Page load attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = RETRY_WAIT_BASE * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def _get_timeline_images(self) -> list:
        """获取时间线图片"""
        try:
            # 查找时间线容器
            timeline = await self.bm.page.query_selector('div.tw-flex.tw-flex-row.tw-overflow-x-auto')
            
            if timeline:
                imgs = await timeline.query_selector_all('img')
                if len(imgs) >= 5:
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
                    
                    # 按x坐标排序
                    image_data.sort(key=lambda x: x[1])
                    return image_data
            
            # 备选：JavaScript方式
            timeline_data = await self.bm.page.evaluate('''
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        if (style.display === 'flex' && style.flexDirection === 'row' &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({src: img.src, x: rect.x});
                                    }
                                });
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data:
                return [(img['src'], img['x']) for img in timeline_data]
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
        
        return []
    
    async def _download_images(self, images: list, screens_dir: Path, manifest_path: Path, 
                                url: str, task_name: str, progress: dict) -> int:
        """下载图片（带断点续传）"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        # 检查已下载的
        existing_files = set(f.name for f in screens_dir.glob("*.png"))
        
        downloaded = 0
        total = len(images)
        
        for idx, (img_url, x_pos) in enumerate(images, 1):
            filename = f"Screen_{idx:03d}.png"
            
            # 跳过已下载的
            if filename in existing_files:
                downloaded += 1
                continue
            
            # 下载图片（带重试）
            for attempt in range(MAX_IMAGE_RETRIES):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                        'Referer': 'https://screensdesign.com/'
                    }
                    resp = requests.get(img_url, timeout=30, headers=headers)
                    
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        target_width = 402
                        if img.width > 0:
                            ratio = target_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # 保存
                        filepath = screens_dir / filename
                        img.save(filepath, "PNG", optimize=True)
                        downloaded += 1
                        break
                    else:
                        logger.warning(f"HTTP {resp.status_code} for image {idx}")
                        
                except Exception as e:
                    logger.warning(f"Image {idx} download attempt {attempt + 1} failed: {e}")
                    if attempt < MAX_IMAGE_RETRIES - 1:
                        await asyncio.sleep(2)
            
            # 每20张保存一次进度
            if downloaded % 20 == 0:
                progress["tasks"][task_name]["downloaded"] = downloaded
                save_progress(progress)
                logger.info(f"Progress: {downloaded}/{total}")
        
        return downloaded
    
    def _save_manifest(self, manifest_path: Path, task_name: str, url: str, screens_dir: Path):
        """保存manifest"""
        screenshots = []
        for f in sorted(screens_dir.glob("*.png")):
            screenshots.append({
                "index": int(f.stem.split("_")[1]),
                "filename": f.name
            })
        
        manifest = {
            "product": task_name,
            "source": "screensdesign.com",
            "source_url": url,
            "downloaded_at": datetime.now().isoformat(),
            "total": len(screenshots),
            "order_source": "timeline",
            "order_reliable": True,
            "screenshots": screenshots
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _run_analysis(self, project_name: str) -> bool:
        """运行AI分析"""
        logger.info(f"Starting AI analysis for {project_name}...")
        
        try:
            sys.path.insert(0, str(BASE_DIR / "ai_analysis"))
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
                return True
            else:
                logger.warning("Analysis returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            log_error(project_name, str(e))
            return False


# ============================================================
# 主流程
# ============================================================

async def run_all_tasks():
    """运行所有任务"""
    progress = load_progress()
    
    # 显示当前状态
    print("\n" + "=" * 60)
    print("  ROBUST DOWNLOAD SYSTEM v1.0")
    print("=" * 60)
    print(f"\nTasks:")
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        print(f"  - {name}: {status}")
    print()
    
    # 找到待处理的任务
    pending_tasks = [
        name for name, info in progress["tasks"].items()
        if info.get("status") not in ("completed", "skipped")
    ]
    
    if not pending_tasks:
        print("All tasks completed!")
        return
    
    print(f"Tasks to process: {len(pending_tasks)}")
    print()
    
    # 连接浏览器
    bm = BrowserManager()
    if not await bm.connect():
        print("\nERROR: Could not connect to Chrome.")
        print("Please make sure Chrome is running with: --remote-debugging-port=9222")
        return
    
    downloader = RobustDownloader(bm)
    
    try:
        for task_name in pending_tasks:
            task_config = TASKS[task_name]
            task_info = progress["tasks"][task_name]
            
            print(f"\n{'=' * 50}")
            print(f"  Processing: {task_name}")
            print(f"  Retry count: {task_info.get('retry_count', 0)}")
            print(f"{'=' * 50}")
            
            # 检查重试次数
            if task_info.get("retry_count", 0) >= MAX_TASK_RETRIES:
                logger.warning(f"Task {task_name} exceeded max retries, skipping")
                task_info["status"] = "max_retries_exceeded"
                save_progress(progress)
                continue
            
            # 执行任务
            success = await downloader.download_product(
                task_name,
                task_config["url"],
                task_config["project_name"],
                progress
            )
            
            if not success:
                task_info["retry_count"] = task_info.get("retry_count", 0) + 1
                task_info["status"] = "failed"
                save_progress(progress)
                
                # 等待后继续下一个任务
                logger.info("Task failed, waiting before next task...")
                await asyncio.sleep(RETRY_WAIT_BASE)
            
            # 任务间隔
            await asyncio.sleep(3)
    
    finally:
        await bm.close()
    
    # 生成报告
    generate_report(progress)


def generate_report(progress: dict):
    """生成最终报告"""
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    
    completed = []
    failed = []
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        if status == "completed":
            completed.append(name)
        elif status not in ("pending",):
            failed.append((name, status))
    
    print(f"\nCompleted: {len(completed)}/{len(TASKS)}")
    for name in completed:
        print(f"  ✓ {name}")
    
    if failed:
        print(f"\nFailed/Incomplete: {len(failed)}")
        for name, status in failed:
            print(f"  ✗ {name} ({status})")
        print(f"\nCheck {ERROR_FILE} for error details")
        print("Run again to retry failed tasks")
    else:
        print("\nAll tasks completed successfully!")
    
    print("\n" + "=" * 60)


def show_status():
    """显示当前状态"""
    progress = load_progress()
    
    print("\n" + "=" * 60)
    print("  TASK STATUS")
    print("=" * 60)
    print(f"\nLast updated: {progress.get('last_updated', 'N/A')}")
    print("\nTasks:")
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        downloaded = info.get("downloaded", 0)
        total = info.get("total_images", "?")
        retries = info.get("retry_count", 0)
        
        status_icon = "✓" if status == "completed" else "○" if status == "pending" else "✗"
        print(f"  {status_icon} {name}: {status}")
        if downloaded:
            print(f"      Downloaded: {downloaded}/{total}")
        if retries > 0:
            print(f"      Retries: {retries}")
    
    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Download System")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--retry", action="store_true", help="Reset failed tasks and retry")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.retry:
        progress = load_progress()
        for name, info in progress["tasks"].items():
            if info.get("status") not in ("completed",):
                info["status"] = "pending"
                info["retry_count"] = 0
        save_progress(progress)
        print("Failed tasks reset. Run again to retry.")
    else:
        asyncio.run(run_all_tasks())


"""
健壮下载系统 v1.0
==================
- 断点续传：任何时候中断都能继续
- 自动重试：网络问题自动恢复
- 独立任务：一个失败不影响其他
- 进度持久化：实时保存到文件
- 详细日志：便于排查问题

使用方式:
    python robust_download.py              # 执行所有待完成任务
    python robust_download.py --status     # 查看进度
    python robust_download.py --retry      # 重试失败的任务
"""

import os
import sys
import json
import time
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 确保UTF-8输出
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 配置
# ============================================================

BASE_DIR = Path(__file__).parent
PROJECTS_DIR = BASE_DIR / "projects"
PROGRESS_FILE = BASE_DIR / "task_progress.json"
ERROR_FILE = BASE_DIR / "task_errors.json"
LOG_FILE = BASE_DIR / "logs" / "robust_download.log"

# 确保目录存在
(BASE_DIR / "logs").mkdir(exist_ok=True)
PROJECTS_DIR.mkdir(exist_ok=True)

# 任务配置
TASKS = {
    "Calm": {
        "url": "https://screensdesign.com/apps/calm/",
        "project_name": "Calm_Analysis"
    },
    "Flo": {
        "url": "https://screensdesign.com/apps/flo-period-pregnancy-tracker/",
        "project_name": "Flo_Period_Pregnancy_Tracker_Analysis"
    },
    "Runna": {
        "url": "https://screensdesign.com/apps/runna-running-training-plans/",
        "project_name": "Runna_Running_Training_Plans_Analysis"
    },
    "Strava": {
        "url": "https://screensdesign.com/apps/strava-run-bike-hike/",
        "project_name": "Strava_Run_Bike_Hike_Analysis"
    }
}

# 重试配置
MAX_TASK_RETRIES = 3          # 每个任务最大重试次数
MAX_PAGE_RETRIES = 5          # 页面加载最大重试次数
MAX_IMAGE_RETRIES = 3         # 图片下载最大重试次数
RETRY_WAIT_BASE = 10          # 重试等待基础秒数
CHROME_RECONNECT_WAIT = 30    # Chrome重连等待秒数

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ============================================================
# 进度管理
# ============================================================

def load_progress() -> dict:
    """加载进度文件"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 初始化进度
    return {
        "created_at": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
        "tasks": {name: {"status": "pending", "retry_count": 0} for name in TASKS}
    }


def save_progress(progress: dict):
    """保存进度文件"""
    progress["last_updated"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def log_error(task_name: str, error: str):
    """记录错误"""
    errors = {}
    if ERROR_FILE.exists():
        try:
            with open(ERROR_FILE, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except:
            pass
    
    if task_name not in errors:
        errors[task_name] = []
    
    errors[task_name].append({
        "time": datetime.now().isoformat(),
        "error": str(error)[:500]
    })
    
    with open(ERROR_FILE, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)


# ============================================================
# 浏览器管理
# ============================================================

class BrowserManager:
    """浏览器连接管理"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
    
    async def connect(self) -> bool:
        """连接到Chrome"""
        from playwright.async_api import async_playwright
        
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                if self.playwright is None:
                    self.playwright = await async_playwright().start()
                
                self.browser = await self.playwright.chromium.connect_over_cdp(
                    "http://127.0.0.1:9222"
                )
                self.page = self.browser.contexts[0].pages[0]
                logger.info("Connected to Chrome")
                return True
                
            except Exception as e:
                logger.warning(f"Chrome connection attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = CHROME_RECONNECT_WAIT * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        logger.error("Could not connect to Chrome after all retries")
        return False
    
    async def ensure_connected(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser and self.browser.is_connected():
                return True
        except:
            pass
        
        logger.info("Browser disconnected, reconnecting...")
        return await self.connect()
    
    async def close(self):
        """关闭连接"""
        if self.playwright:
            await self.playwright.stop()


# ============================================================
# 下载器
# ============================================================

class RobustDownloader:
    """健壮下载器"""
    
    def __init__(self, browser_manager: BrowserManager):
        self.bm = browser_manager
        self.current_task = None
    
    async def download_product(self, task_name: str, url: str, project_name: str, progress: dict) -> bool:
        """
        下载单个产品
        
        Returns:
            True=成功, False=失败
        """
        self.current_task = task_name
        project_dir = PROJECTS_DIR / project_name
        screens_dir = project_dir / "Screens"
        manifest_path = project_dir / "manifest.json"
        
        project_dir.mkdir(exist_ok=True)
        screens_dir.mkdir(exist_ok=True)
        
        # 检查已下载的进度
        existing_count = len(list(screens_dir.glob("*.png")))
        if existing_count > 0:
            logger.info(f"Found {existing_count} existing screenshots, will continue from there")
        
        # 加载页面
        logger.info(f"Loading page: {url}")
        page_loaded = await self._load_page_with_retry(url)
        if not page_loaded:
            return False
        
        # 获取时间线图片
        logger.info("Extracting timeline images...")
        images = await self._get_timeline_images()
        if not images:
            logger.error("No images found in timeline")
            return False
        
        logger.info(f"Found {len(images)} images in timeline")
        
        # 更新进度
        progress["tasks"][task_name]["total_images"] = len(images)
        progress["tasks"][task_name]["status"] = "downloading"
        save_progress(progress)
        
        # 下载图片
        downloaded = await self._download_images(images, screens_dir, manifest_path, url, task_name, progress)
        
        if downloaded > 0:
            logger.info(f"Downloaded {downloaded} images for {task_name}")
            
            # 保存manifest
            self._save_manifest(manifest_path, task_name, url, screens_dir)
            
            # 运行AI分析
            progress["tasks"][task_name]["status"] = "analyzing"
            save_progress(progress)
            
            analysis_success = await self._run_analysis(project_name)
            
            if analysis_success:
                progress["tasks"][task_name]["status"] = "completed"
                progress["tasks"][task_name]["completed_at"] = datetime.now().isoformat()
            else:
                progress["tasks"][task_name]["status"] = "analysis_failed"
            
            save_progress(progress)
            return analysis_success
        
        return False
    
    async def _load_page_with_retry(self, url: str) -> bool:
        """带重试的页面加载"""
        for attempt in range(MAX_PAGE_RETRIES):
            try:
                # 确保浏览器连接
                if not await self.bm.ensure_connected():
                    continue
                
                await self.bm.page.goto(url, timeout=90000, wait_until='domcontentloaded')
                await asyncio.sleep(3)
                
                # 滚动加载
                await self.bm.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)
                
                return True
                
            except Exception as e:
                logger.warning(f"Page load attempt {attempt + 1} failed: {e}")
                if attempt < MAX_PAGE_RETRIES - 1:
                    wait_time = RETRY_WAIT_BASE * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        return False
    
    async def _get_timeline_images(self) -> list:
        """获取时间线图片"""
        try:
            # 查找时间线容器
            timeline = await self.bm.page.query_selector('div.tw-flex.tw-flex-row.tw-overflow-x-auto')
            
            if timeline:
                imgs = await timeline.query_selector_all('img')
                if len(imgs) >= 5:
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
                    
                    # 按x坐标排序
                    image_data.sort(key=lambda x: x[1])
                    return image_data
            
            # 备选：JavaScript方式
            timeline_data = await self.bm.page.evaluate('''
                () => {
                    const divs = document.querySelectorAll('div');
                    for (const div of divs) {
                        const style = getComputedStyle(div);
                        if (style.display === 'flex' && style.flexDirection === 'row' &&
                            (style.overflowX === 'auto' || style.overflowX === 'scroll')) {
                            const imgs = div.querySelectorAll('img[src*="media.screensdesign.com/avs"]');
                            if (imgs.length >= 10) {
                                const imageData = [];
                                imgs.forEach(img => {
                                    const rect = img.getBoundingClientRect();
                                    if (!img.src.includes('appicon')) {
                                        imageData.push({src: img.src, x: rect.x});
                                    }
                                });
                                imageData.sort((a, b) => a.x - b.x);
                                return imageData;
                            }
                        }
                    }
                    return null;
                }
            ''')
            
            if timeline_data:
                return [(img['src'], img['x']) for img in timeline_data]
            
        except Exception as e:
            logger.error(f"Timeline extraction error: {e}")
        
        return []
    
    async def _download_images(self, images: list, screens_dir: Path, manifest_path: Path, 
                                url: str, task_name: str, progress: dict) -> int:
        """下载图片（带断点续传）"""
        import requests
        from PIL import Image
        from io import BytesIO
        
        # 检查已下载的
        existing_files = set(f.name for f in screens_dir.glob("*.png"))
        
        downloaded = 0
        total = len(images)
        
        for idx, (img_url, x_pos) in enumerate(images, 1):
            filename = f"Screen_{idx:03d}.png"
            
            # 跳过已下载的
            if filename in existing_files:
                downloaded += 1
                continue
            
            # 下载图片（带重试）
            for attempt in range(MAX_IMAGE_RETRIES):
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
                        'Referer': 'https://screensdesign.com/'
                    }
                    resp = requests.get(img_url, timeout=30, headers=headers)
                    
                    if resp.status_code == 200:
                        img = Image.open(BytesIO(resp.content))
                        
                        # 转换颜色模式
                        if img.mode in ('RGBA', 'P', 'LA'):
                            img = img.convert('RGB')
                        
                        # 调整大小
                        target_width = 402
                        if img.width > 0:
                            ratio = target_width / img.width
                            new_height = int(img.height * ratio)
                            img = img.resize((target_width, new_height), Image.LANCZOS)
                        
                        # 保存
                        filepath = screens_dir / filename
                        img.save(filepath, "PNG", optimize=True)
                        downloaded += 1
                        break
                    else:
                        logger.warning(f"HTTP {resp.status_code} for image {idx}")
                        
                except Exception as e:
                    logger.warning(f"Image {idx} download attempt {attempt + 1} failed: {e}")
                    if attempt < MAX_IMAGE_RETRIES - 1:
                        await asyncio.sleep(2)
            
            # 每20张保存一次进度
            if downloaded % 20 == 0:
                progress["tasks"][task_name]["downloaded"] = downloaded
                save_progress(progress)
                logger.info(f"Progress: {downloaded}/{total}")
        
        return downloaded
    
    def _save_manifest(self, manifest_path: Path, task_name: str, url: str, screens_dir: Path):
        """保存manifest"""
        screenshots = []
        for f in sorted(screens_dir.glob("*.png")):
            screenshots.append({
                "index": int(f.stem.split("_")[1]),
                "filename": f.name
            })
        
        manifest = {
            "product": task_name,
            "source": "screensdesign.com",
            "source_url": url,
            "downloaded_at": datetime.now().isoformat(),
            "total": len(screenshots),
            "order_source": "timeline",
            "order_reliable": True,
            "screenshots": screenshots
        }
        
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    async def _run_analysis(self, project_name: str) -> bool:
        """运行AI分析"""
        logger.info(f"Starting AI analysis for {project_name}...")
        
        try:
            sys.path.insert(0, str(BASE_DIR / "ai_analysis"))
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
                return True
            else:
                logger.warning("Analysis returned no results")
                return False
                
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            log_error(project_name, str(e))
            return False


# ============================================================
# 主流程
# ============================================================

async def run_all_tasks():
    """运行所有任务"""
    progress = load_progress()
    
    # 显示当前状态
    print("\n" + "=" * 60)
    print("  ROBUST DOWNLOAD SYSTEM v1.0")
    print("=" * 60)
    print(f"\nTasks:")
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        print(f"  - {name}: {status}")
    print()
    
    # 找到待处理的任务
    pending_tasks = [
        name for name, info in progress["tasks"].items()
        if info.get("status") not in ("completed", "skipped")
    ]
    
    if not pending_tasks:
        print("All tasks completed!")
        return
    
    print(f"Tasks to process: {len(pending_tasks)}")
    print()
    
    # 连接浏览器
    bm = BrowserManager()
    if not await bm.connect():
        print("\nERROR: Could not connect to Chrome.")
        print("Please make sure Chrome is running with: --remote-debugging-port=9222")
        return
    
    downloader = RobustDownloader(bm)
    
    try:
        for task_name in pending_tasks:
            task_config = TASKS[task_name]
            task_info = progress["tasks"][task_name]
            
            print(f"\n{'=' * 50}")
            print(f"  Processing: {task_name}")
            print(f"  Retry count: {task_info.get('retry_count', 0)}")
            print(f"{'=' * 50}")
            
            # 检查重试次数
            if task_info.get("retry_count", 0) >= MAX_TASK_RETRIES:
                logger.warning(f"Task {task_name} exceeded max retries, skipping")
                task_info["status"] = "max_retries_exceeded"
                save_progress(progress)
                continue
            
            # 执行任务
            success = await downloader.download_product(
                task_name,
                task_config["url"],
                task_config["project_name"],
                progress
            )
            
            if not success:
                task_info["retry_count"] = task_info.get("retry_count", 0) + 1
                task_info["status"] = "failed"
                save_progress(progress)
                
                # 等待后继续下一个任务
                logger.info("Task failed, waiting before next task...")
                await asyncio.sleep(RETRY_WAIT_BASE)
            
            # 任务间隔
            await asyncio.sleep(3)
    
    finally:
        await bm.close()
    
    # 生成报告
    generate_report(progress)


def generate_report(progress: dict):
    """生成最终报告"""
    print("\n" + "=" * 60)
    print("  FINAL REPORT")
    print("=" * 60)
    
    completed = []
    failed = []
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        if status == "completed":
            completed.append(name)
        elif status not in ("pending",):
            failed.append((name, status))
    
    print(f"\nCompleted: {len(completed)}/{len(TASKS)}")
    for name in completed:
        print(f"  ✓ {name}")
    
    if failed:
        print(f"\nFailed/Incomplete: {len(failed)}")
        for name, status in failed:
            print(f"  ✗ {name} ({status})")
        print(f"\nCheck {ERROR_FILE} for error details")
        print("Run again to retry failed tasks")
    else:
        print("\nAll tasks completed successfully!")
    
    print("\n" + "=" * 60)


def show_status():
    """显示当前状态"""
    progress = load_progress()
    
    print("\n" + "=" * 60)
    print("  TASK STATUS")
    print("=" * 60)
    print(f"\nLast updated: {progress.get('last_updated', 'N/A')}")
    print("\nTasks:")
    
    for name, info in progress["tasks"].items():
        status = info.get("status", "pending")
        downloaded = info.get("downloaded", 0)
        total = info.get("total_images", "?")
        retries = info.get("retry_count", 0)
        
        status_icon = "✓" if status == "completed" else "○" if status == "pending" else "✗"
        print(f"  {status_icon} {name}: {status}")
        if downloaded:
            print(f"      Downloaded: {downloaded}/{total}")
        if retries > 0:
            print(f"      Retries: {retries}")
    
    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Robust Download System")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--retry", action="store_true", help="Reset failed tasks and retry")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.retry:
        progress = load_progress()
        for name, info in progress["tasks"].items():
            if info.get("status") not in ("completed",):
                info["status"] = "pending"
                info["retry_count"] = 0
        save_progress(progress)
        print("Failed tasks reset. Run again to retry.")
    else:
        asyncio.run(run_all_tasks())


















