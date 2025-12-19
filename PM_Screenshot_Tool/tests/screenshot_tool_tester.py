# -*- coding: utf-8 -*-
"""
PM Screenshot Tool - 全面自动化测试框架
=====================================

功能覆盖：
1. 项目管理测试
2. 截图显示测试
3. 截图操作测试（导入、删除、排序）
4. 数据同步测试
5. 性能测试
6. 回归测试

使用方法：
    python screenshot_tool_tester.py                    # 运行所有测试
    python screenshot_tool_tester.py --suite display    # 只运行显示测试
    python screenshot_tool_tester.py --project MyApp    # 指定测试项目
    python screenshot_tool_tester.py --loop 5           # 循环测试5次
    python screenshot_tool_tester.py --fix              # 发现问题自动修复
"""

import asyncio
import sys

# Windows 控制台编码修复
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import argparse
import json
import os
import re
import sys
import time
import requests
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Callable
from playwright.async_api import async_playwright, Page, Browser, Locator

# ============================================================
# 配置
# ============================================================

@dataclass
class TestConfig:
    """测试配置"""
    base_url: str = "http://localhost:5000"
    default_project: str = "downloads_2024/WeightWatchers"
    headless: bool = False
    timeout: int = 30000
    screenshot_on_failure: bool = True
    auto_fix: bool = False
    loop_count: int = 1
    
CONFIG = TestConfig()


# ============================================================
# 测试结果
# ============================================================

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """单个测试结果"""
    name: str
    status: TestStatus
    duration: float
    message: str = ""
    details: Dict = field(default_factory=dict)
    screenshot: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass  
class TestSuiteResult:
    """测试套件结果"""
    name: str
    results: List[TestResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAILED)
    
    @property
    def total(self) -> int:
        return len(self.results)


# ============================================================
# 页面操作封装
# ============================================================

class PageHelper:
    """页面操作助手 - 封装常用操作"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = CONFIG.base_url
        
    async def goto_home(self):
        """导航到首页"""
        await self.page.goto(f"{self.base_url}/")
        await self.page.wait_for_load_state("networkidle")
        
    async def goto_sort(self):
        """导航到排序页面"""
        await self.page.goto(f"{self.base_url}/#sort")
        await self.page.wait_for_timeout(2000)
        
    async def goto_onboarding(self):
        """导航到引导流程页面"""
        await self.page.goto(f"{self.base_url}/#onboarding")
        await self.page.wait_for_timeout(2000)
        
    async def goto_store(self):
        """导航到商城对比页面"""
        await self.page.goto(f"{self.base_url}/#store")
        await self.page.wait_for_timeout(2000)
    
    def get_frame(self, frame_id: str) -> Locator:
        """获取 iframe 的 frame locator"""
        return self.page.frame_locator(f"#{frame_id}")
    
    async def select_project(self, project_name: str, frame_id: str = "frame-sort") -> bool:
        """选择项目"""
        frame = self.get_frame(frame_id)
        select = frame.locator("#projectSelect")
        
        options = await select.locator("option").all_text_contents()
        
        for opt in options:
            # 支持部分匹配
            if project_name in opt or project_name.split("/")[-1] in opt:
                await select.select_option(label=opt)
                await self.page.wait_for_timeout(2000)
                return True
        return False
    
    async def get_cards(self, frame_id: str = "frame-sort") -> Locator:
        """获取所有卡片"""
        frame = self.get_frame(frame_id)
        return frame.locator("#grid .card")
    
    async def get_card_count(self, frame_id: str = "frame-sort") -> int:
        """获取卡片数量"""
        cards = await self.get_cards(frame_id)
        return await cards.count()
    
    async def click_card(self, index: int, frame_id: str = "frame-sort"):
        """点击指定索引的卡片"""
        cards = await self.get_cards(frame_id)
        await cards.nth(index).click()
        await self.page.wait_for_timeout(300)
    
    async def get_card_info(self, index: int, frame_id: str = "frame-sort") -> Dict:
        """获取卡片信息"""
        frame = self.get_frame(frame_id)
        cards = frame.locator("#grid .card")
        card = cards.nth(index)
        
        return {
            "data_file": await card.get_attribute("data-file"),
            "thumb_src": await card.locator("img").get_attribute("src"),
            "position": await card.locator(".card-index").text_content(),
        }
    
    async def get_preview_info(self, frame_id: str = "frame-sort") -> Dict:
        """获取预览区信息"""
        frame = self.get_frame(frame_id)
        
        preview_img = frame.locator("#previewImage img")
        preview_info = frame.locator("#previewInfo")
        
        return {
            "src": await preview_img.get_attribute("src") if await preview_img.count() > 0 else None,
            "info": await preview_info.text_content() if await preview_info.count() > 0 else "",
        }
    
    async def delete_selected(self, frame_id: str = "frame-sort"):
        """删除选中的截图"""
        frame = self.get_frame(frame_id)
        delete_btn = frame.locator("#deleteBtn")
        if await delete_btn.is_enabled():
            await delete_btn.click()
            await self.page.wait_for_timeout(1000)
            return True
        return False
    
    async def screenshot(self, name: str) -> str:
        """截取页面截图"""
        path = f"test_screenshots/{name}_{int(time.time())}.png"
        os.makedirs("test_screenshots", exist_ok=True)
        await self.page.screenshot(path=path)
        return path


# ============================================================
# API 助手
# ============================================================

class APIHelper:
    """API 操作助手"""
    
    def __init__(self):
        self.base_url = CONFIG.base_url
        
    def get_projects(self) -> List[Dict]:
        """获取项目列表"""
        resp = requests.get(f"{self.base_url}/api/sort-projects", timeout=10)
        return resp.json().get("projects", [])
    
    def get_screenshots(self, project: str) -> List[str]:
        """获取项目截图列表"""
        resp = requests.get(f"{self.base_url}/api/screenshots/{project}", timeout=10)
        return resp.json().get("screens", [])
    
    def get_project_info(self, project: str) -> Dict:
        """获取项目详情"""
        resp = requests.get(f"{self.base_url}/api/screenshots/{project}", timeout=10)
        return resp.json()
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            resp = requests.get(f"{self.base_url}/", timeout=5)
            return resp.status_code == 200
        except:
            return False


# ============================================================
# 文件系统助手
# ============================================================

class FileSystemHelper:
    """文件系统操作助手"""
    
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
            )
        self.base_path = base_path
    
    def get_project_path(self, project: str) -> str:
        """获取项目路径"""
        return os.path.join(self.base_path, project)
    
    def get_screenshots(self, project: str) -> List[str]:
        """获取项目截图文件列表"""
        path = self.get_project_path(project)
        if not os.path.exists(path):
            return []
        return sorted([f for f in os.listdir(path) 
                      if f.endswith('.png') and not f.startswith('thumb')])
    
    def get_thumbnails(self, project: str) -> List[str]:
        """获取缩略图列表"""
        path = os.path.join(self.get_project_path(project), "thumbs_small")
        if not os.path.exists(path):
            return []
        return sorted([f for f in os.listdir(path) if f.endswith('.png')])
    
    def find_orphan_thumbnails(self, project: str) -> List[str]:
        """查找孤立的缩略图"""
        main = set(self.get_screenshots(project))
        thumbs = set(self.get_thumbnails(project))
        return sorted(thumbs - main)
    
    def clean_orphan_thumbnails(self, project: str) -> int:
        """清理孤立缩略图"""
        orphans = self.find_orphan_thumbnails(project)
        thumb_path = os.path.join(self.get_project_path(project), "thumbs_small")
        
        for f in orphans:
            path = os.path.join(thumb_path, f)
            if os.path.exists(path):
                os.remove(path)
            # 同时删除 webp 版本
            webp_path = path.replace('.png', '.webp')
            if os.path.exists(webp_path):
                os.remove(webp_path)
        
        return len(orphans)


# ============================================================
# 测试基类
# ============================================================

class BaseTest(ABC):
    """测试基类"""
    
    name: str = "未命名测试"
    description: str = ""
    
    def __init__(self, helper: PageHelper, api: APIHelper, fs: FileSystemHelper):
        self.helper = helper
        self.api = api
        self.fs = fs
        
    @abstractmethod
    async def run(self) -> TestResult:
        """执行测试"""
        pass
    
    def passed(self, message: str = "", **details) -> TestResult:
        return TestResult(
            name=self.name,
            status=TestStatus.PASSED,
            duration=0,
            message=message,
            details=details
        )
    
    def failed(self, message: str, fix: str = None, **details) -> TestResult:
        return TestResult(
            name=self.name,
            status=TestStatus.FAILED,
            duration=0,
            message=message,
            details=details,
            fix_suggestion=fix
        )
    
    def error(self, message: str) -> TestResult:
        return TestResult(
            name=self.name,
            status=TestStatus.ERROR,
            duration=0,
            message=message
        )


# ============================================================
# 具体测试类
# ============================================================

class TestServerHealth(BaseTest):
    """服务器健康检查"""
    name = "服务器健康检查"
    
    async def run(self) -> TestResult:
        if self.api.health_check():
            return self.passed("服务器运行正常")
        return self.failed(
            "服务器无响应",
            fix="启动服务器: python app.py"
        )


class TestProjectList(BaseTest):
    """项目列表测试"""
    name = "项目列表加载"
    
    async def run(self) -> TestResult:
        try:
            projects = self.api.get_projects()
            if len(projects) > 0:
                return self.passed(f"找到 {len(projects)} 个项目", count=len(projects))
            return self.failed("未找到任何项目")
        except Exception as e:
            return self.error(str(e))


class TestProjectSelect(BaseTest):
    """项目选择测试"""
    name = "项目选择功能"
    
    async def run(self) -> TestResult:
        await self.helper.goto_sort()
        
        if await self.helper.select_project(CONFIG.default_project):
            count = await self.helper.get_card_count()
            return self.passed(f"成功选择项目，{count} 张截图", count=count)
        return self.failed(
            f"无法选择项目: {CONFIG.default_project}",
            fix="检查项目是否存在"
        )


class TestFileSystemConsistency(BaseTest):
    """文件系统一致性测试"""
    name = "文件系统一致性"
    
    async def run(self) -> TestResult:
        project = CONFIG.default_project
        
        # API 数据
        api_files = self.api.get_screenshots(project)
        
        # 文件系统数据
        fs_files = self.fs.get_screenshots(project)
        
        api_set = set(api_files)
        fs_set = set(fs_files)
        
        if api_set == fs_set:
            return self.passed(f"{len(api_files)} 个文件一致")
        
        missing_in_api = fs_set - api_set
        missing_in_fs = api_set - fs_set
        
        return self.failed(
            f"API 与文件系统不一致",
            details={
                "missing_in_api": list(missing_in_api)[:5],
                "missing_in_fs": list(missing_in_fs)[:5]
            },
            fix="检查文件扫描逻辑"
        )


class TestThumbnailOrphans(BaseTest):
    """孤立缩略图检测"""
    name = "孤立缩略图检测"
    
    async def run(self) -> TestResult:
        orphans = self.fs.find_orphan_thumbnails(CONFIG.default_project)
        
        if not orphans:
            return self.passed("无孤立缩略图")
        
        if CONFIG.auto_fix:
            cleaned = self.fs.clean_orphan_thumbnails(CONFIG.default_project)
            return self.passed(f"已自动清理 {cleaned} 个孤立缩略图")
        
        return self.failed(
            f"发现 {len(orphans)} 个孤立缩略图",
            details={"orphans": orphans[:10]},
            fix=f"删除孤立缩略图或启用 --fix 自动修复"
        )


class TestThumbnailPreviewMatch(BaseTest):
    """缩略图与预览一致性"""
    name = "缩略图与预览一致性"
    
    async def run(self) -> TestResult:
        await self.helper.goto_sort()
        
        if not await self.helper.select_project(CONFIG.default_project):
            return self.error("无法选择项目")
        
        mismatches = []
        sample_size = 10
        
        for i in range(sample_size):
            card_info = await self.helper.get_card_info(i)
            await self.helper.click_card(i)
            preview_info = await self.helper.get_preview_info()
            
            # 提取文件名
            thumb_file = self._extract_filename(card_info["thumb_src"])
            preview_file = self._extract_filename(preview_info["src"])
            
            if thumb_file != preview_file:
                mismatches.append({
                    "position": i + 1,
                    "thumb": thumb_file,
                    "preview": preview_file
                })
        
        if not mismatches:
            return self.passed(f"前 {sample_size} 个位置一致")
        
        return self.failed(
            f"{len(mismatches)} 个位置不一致",
            details={"mismatches": mismatches},
            fix="清除缩略图缓存: rm -rf thumbs_small/"
        )
    
    def _extract_filename(self, url: str) -> Optional[str]:
        if not url:
            return None
        match = re.search(r'/([^/?]+\.png)', url)
        return match.group(1) if match else None


class TestPositionContinuity(BaseTest):
    """位置索引连续性"""
    name = "位置索引连续性"
    
    async def run(self) -> TestResult:
        await self.helper.goto_sort()
        
        if not await self.helper.select_project(CONFIG.default_project):
            return self.error("无法选择项目")
        
        count = await self.helper.get_card_count()
        errors = []
        
        for i in range(min(count, 20)):
            card_info = await self.helper.get_card_info(i)
            expected = str(i + 1).zfill(4)
            actual = card_info["position"]
            
            if expected != actual:
                errors.append({"index": i, "expected": expected, "actual": actual})
        
        if not errors:
            return self.passed(f"前 {min(count, 20)} 个位置连续")
        
        return self.failed(
            f"{len(errors)} 个位置不连续",
            details={"errors": errors[:5]}
        )


class TestRefreshConsistency(BaseTest):
    """刷新一致性测试"""
    name = "刷新后数据一致性"
    
    async def run(self) -> TestResult:
        await self.helper.goto_sort()
        
        if not await self.helper.select_project(CONFIG.default_project):
            return self.error("无法选择项目")
        
        # 记录刷新前状态
        before_count = await self.helper.get_card_count()
        before_files = []
        for i in range(min(5, before_count)):
            info = await self.helper.get_card_info(i)
            before_files.append(info["data_file"])
        
        # 刷新页面
        await self.helper.page.reload()
        await self.helper.page.wait_for_timeout(2000)
        await self.helper.select_project(CONFIG.default_project)
        
        # 记录刷新后状态
        after_count = await self.helper.get_card_count()
        after_files = []
        for i in range(min(5, after_count)):
            info = await self.helper.get_card_info(i)
            after_files.append(info["data_file"])
        
        if before_count == after_count and before_files == after_files:
            return self.passed("刷新后数据一致")
        
        return self.failed(
            "刷新后数据不一致",
            details={
                "before": {"count": before_count, "files": before_files},
                "after": {"count": after_count, "files": after_files}
            }
        )


class TestDeleteOperation(BaseTest):
    """删除操作测试"""
    name = "删除操作"
    
    async def run(self) -> TestResult:
        await self.helper.goto_sort()
        
        if not await self.helper.select_project(CONFIG.default_project):
            return self.error("无法选择项目")
        
        before_count = await self.helper.get_card_count()
        
        if before_count == 0:
            return self.passed("项目为空，跳过删除测试")
        
        # 选中第一个卡片
        await self.helper.click_card(0)
        
        # 执行删除
        if await self.helper.delete_selected():
            await self.helper.page.wait_for_timeout(1000)
            after_count = await self.helper.get_card_count()
            
            if after_count == before_count - 1:
                return self.passed(f"删除成功: {before_count} -> {after_count}")
            return self.failed(f"删除后数量异常: 期望 {before_count-1}, 实际 {after_count}")
        
        return self.failed("删除按钮不可用")


class TestPageNavigation(BaseTest):
    """页面导航测试"""
    name = "页面导航"
    
    async def run(self) -> TestResult:
        pages = [
            ("home", "/"),
            ("sort", "/#sort"),
            ("onboarding", "/#onboarding"),
            ("store", "/#store"),
        ]
        
        errors = []
        for name, path in pages:
            try:
                await self.helper.page.goto(f"{CONFIG.base_url}{path}")
                await self.helper.page.wait_for_timeout(1000)
                
                # 检查页面是否加载
                title = await self.helper.page.title()
                if not title:
                    errors.append(f"{name}: 无标题")
            except Exception as e:
                errors.append(f"{name}: {str(e)}")
        
        if not errors:
            return self.passed(f"所有 {len(pages)} 个页面正常")
        
        return self.failed(
            f"{len(errors)} 个页面异常",
            details={"errors": errors}
        )


class TestLoadPerformance(BaseTest):
    """加载性能测试"""
    name = "加载性能"
    
    async def run(self) -> TestResult:
        start = time.time()
        
        await self.helper.goto_sort()
        await self.helper.select_project(CONFIG.default_project)
        
        # 等待所有卡片加载
        cards = await self.helper.get_cards()
        count = await cards.count()
        
        duration = time.time() - start
        
        if duration < 5:
            return self.passed(f"{count} 张截图加载耗时 {duration:.2f}s")
        elif duration < 10:
            return self.passed(f"加载较慢: {duration:.2f}s", warn=True)
        else:
            return self.failed(f"加载过慢: {duration:.2f}s")


# ============================================================
# 测试套件
# ============================================================

class TestSuite:
    """测试套件"""
    
    SUITES = {
        "health": [TestServerHealth],
        "project": [TestProjectList, TestProjectSelect],
        "display": [
            TestThumbnailPreviewMatch,
            TestPositionContinuity,
        ],
        "filesystem": [
            TestFileSystemConsistency,
            TestThumbnailOrphans,
        ],
        "operation": [
            TestDeleteOperation,
        ],
        "sync": [
            TestRefreshConsistency,
        ],
        "navigation": [
            TestPageNavigation,
        ],
        "performance": [
            TestLoadPerformance,
        ],
    }
    
    ALL_TESTS = [
        TestServerHealth,
        TestProjectList,
        TestProjectSelect,
        TestFileSystemConsistency,
        TestThumbnailOrphans,
        TestThumbnailPreviewMatch,
        TestPositionContinuity,
        TestRefreshConsistency,
        TestPageNavigation,
        TestLoadPerformance,
    ]
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.helper: Optional[PageHelper] = None
        self.api = APIHelper()
        self.fs = FileSystemHelper()
        self.results: List[TestSuiteResult] = []
        
    async def setup(self):
        """初始化"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=CONFIG.headless)
        self.page = await self.browser.new_page()
        self.helper = PageHelper(self.page)
        print("✓ 浏览器已启动")
        
    async def teardown(self):
        """清理"""
        if self.browser:
            await self.browser.close()
        print("✓ 浏览器已关闭")
    
    async def run_tests(self, test_classes: List[type]) -> TestSuiteResult:
        """运行指定的测试"""
        result = TestSuiteResult(name="测试")
        
        for test_class in test_classes:
            test = test_class(self.helper, self.api, self.fs)
            print(f"\n  运行: {test.name}...", end=" ")
            
            start = time.time()
            try:
                test_result = await test.run()
                test_result.duration = time.time() - start
                
                if test_result.status == TestStatus.PASSED:
                    print(f"✓ {test_result.message}")
                elif test_result.status == TestStatus.FAILED:
                    print(f"✗ {test_result.message}")
                    if test_result.fix_suggestion:
                        print(f"    修复建议: {test_result.fix_suggestion}")
                else:
                    print(f"! {test_result.message}")
                    
            except Exception as e:
                test_result = TestResult(
                    name=test.name,
                    status=TestStatus.ERROR,
                    duration=time.time() - start,
                    message=str(e)
                )
                print(f"! 错误: {e}")
            
            result.results.append(test_result)
        
        result.end_time = datetime.now()
        return result
    
    async def run_suite(self, suite_name: str = None):
        """运行测试套件"""
        if suite_name and suite_name in self.SUITES:
            tests = self.SUITES[suite_name]
            name = f"{suite_name} 套件"
        else:
            tests = self.ALL_TESTS
            name = "完整测试"
        
        print(f"\n{'='*60}")
        print(f"  PM Screenshot Tool - {name}")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  项目: {CONFIG.default_project}")
        print(f"{'='*60}")
        
        await self.setup()
        
        try:
            for i in range(CONFIG.loop_count):
                if CONFIG.loop_count > 1:
                    print(f"\n--- 第 {i+1}/{CONFIG.loop_count} 轮 ---")
                
                result = await self.run_tests(tests)
                self.results.append(result)
                
        finally:
            await self.teardown()
        
        self._print_summary()
        self._save_report()
    
    def _print_summary(self):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("  测试摘要")
        print(f"{'='*60}")
        
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total = sum(r.total for r in self.results)
        
        print(f"\n  通过: {total_passed}/{total}")
        print(f"  失败: {total_failed}/{total}")
        
        if total_failed > 0:
            print("\n  失败的测试:")
            for result in self.results:
                for r in result.results:
                    if r.status == TestStatus.FAILED:
                        print(f"    - {r.name}: {r.message}")
    
    def _save_report(self):
        """保存报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "project": CONFIG.default_project,
                "loop_count": CONFIG.loop_count,
                "auto_fix": CONFIG.auto_fix,
            },
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "duration": r.duration,
                    "message": r.message,
                    "details": r.details,
                    "fix_suggestion": r.fix_suggestion,
                }
                for suite in self.results
                for r in suite.results
            ],
        }
        
        os.makedirs("test_reports", exist_ok=True)
        filename = f"test_reports/report_{int(time.time())}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n  报告已保存: {filename}")


# ============================================================
# 主程序
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="PM Screenshot Tool 测试框架")
    parser.add_argument("--suite", choices=list(TestSuite.SUITES.keys()),
                        help="运行指定测试套件")
    parser.add_argument("--project", help="指定测试项目")
    parser.add_argument("--loop", type=int, default=1, help="循环测试次数")
    parser.add_argument("--fix", action="store_true", help="自动修复发现的问题")
    parser.add_argument("--headless", action="store_true", help="无头模式运行")
    
    args = parser.parse_args()
    
    if args.project:
        CONFIG.default_project = args.project
    if args.loop:
        CONFIG.loop_count = args.loop
    if args.fix:
        CONFIG.auto_fix = True
    if args.headless:
        CONFIG.headless = True
    
    suite = TestSuite()
    await suite.run_suite(args.suite)


if __name__ == "__main__":
    asyncio.run(main())
