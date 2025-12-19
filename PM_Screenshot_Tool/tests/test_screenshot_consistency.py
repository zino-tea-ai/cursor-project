# -*- coding: utf-8 -*-
"""
截图工具一致性自动化测试脚本
使用 Playwright 自动测试导入、删除、刷新后的缩略图与大图一致性
"""
import asyncio
import json
import re
import sys
from datetime import datetime
from playwright.async_api import async_playwright

# 配置
BASE_URL = "http://localhost:5000"
TEST_PROJECT = "downloads_2024/WeightWatchers"


class ScreenshotConsistencyTester:
    """截图一致性测试器"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.errors = []
        self.test_results = []
        
    async def setup(self):
        """初始化浏览器"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)  # 可视化运行
        self.page = await self.browser.new_page()
        print("✓ 浏览器已启动")
        
    async def teardown(self):
        """清理"""
        if self.browser:
            await self.browser.close()
        print("✓ 浏览器已关闭")
    
    async def navigate_to_sort(self):
        """导航到排序页面"""
        await self.page.goto(f"{BASE_URL}/#sort")
        await self.page.wait_for_timeout(2000)
        print("✓ 已导航到排序页面")
        
    async def select_project(self, project_name=TEST_PROJECT):
        """选择项目"""
        frame = self.page.frame_locator("#frame-sort")
        select = frame.locator("#projectSelect")
        
        # 获取所有选项
        options = await select.locator("option").all_text_contents()
        
        # 查找匹配的选项
        target_option = None
        for opt in options:
            if project_name.split("/")[-1] in opt:
                target_option = opt
                break
        
        if target_option:
            await select.select_option(label=target_option)
            await self.page.wait_for_timeout(2000)
            print(f"✓ 已选择项目: {target_option}")
            return True
        else:
            print(f"✗ 未找到项目: {project_name}")
            return False
    
    async def get_card_info(self, card_index: int):
        """获取指定位置卡片的信息"""
        frame = self.page.frame_locator("#frame-sort")
        cards = frame.locator("#grid .card")
        
        count = await cards.count()
        if card_index >= count:
            return None
            
        card = cards.nth(card_index)
        
        # 获取缩略图 URL
        thumb_img = card.locator("img")
        thumb_src = await thumb_img.get_attribute("src")
        
        # 获取位置索引
        index_span = card.locator(".card-index")
        position = await index_span.text_content()
        
        # 获取文件名 (从 data-file 属性)
        data_file = await card.get_attribute("data-file")
        
        return {
            "position": position,
            "data_file": data_file,
            "thumb_src": thumb_src
        }
    
    async def click_card_and_get_preview(self, card_index: int):
        """点击卡片并获取预览信息"""
        frame = self.page.frame_locator("#frame-sort")
        cards = frame.locator("#grid .card")
        
        card = cards.nth(card_index)
        await card.click()
        await self.page.wait_for_timeout(500)
        
        # 获取预览图 URL
        preview_img = frame.locator("#previewImage img")
        preview_src = await preview_img.get_attribute("src") if await preview_img.count() > 0 else None
        
        # 获取预览信息
        preview_info = frame.locator("#previewInfo")
        info_text = await preview_info.text_content() if await preview_info.count() > 0 else ""
        
        return {
            "preview_src": preview_src,
            "info_text": info_text
        }
    
    def extract_filename_from_url(self, url: str) -> str:
        """从 URL 中提取文件名"""
        if not url:
            return None
        # 匹配 /screens/XXXX.png 或类似模式
        match = re.search(r'/screens/([^?]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/([0-9]+\.png)', url)
        if match:
            return match.group(1)
        return None
    
    async def test_thumbnail_preview_consistency(self, sample_size=10):
        """测试缩略图与预览大图的一致性"""
        print("\n" + "="*60)
        print("测试: 缩略图与预览大图一致性")
        print("="*60)
        
        frame = self.page.frame_locator("#frame-sort")
        cards = frame.locator("#grid .card")
        total = await cards.count()
        
        errors = []
        tested = 0
        
        # 测试前 sample_size 个卡片
        for i in range(min(sample_size, total)):
            card_info = await self.get_card_info(i)
            if not card_info:
                continue
                
            preview_info = await self.click_card_and_get_preview(i)
            
            # 提取文件名
            thumb_file = self.extract_filename_from_url(card_info["thumb_src"])
            preview_file = self.extract_filename_from_url(preview_info["preview_src"])
            
            tested += 1
            
            # 验证文件名一致
            if thumb_file != preview_file:
                error = f"位置 {card_info['position']}: 缩略图={thumb_file}, 预览={preview_file}"
                errors.append(error)
                print(f"  ✗ {error}")
            else:
                print(f"  ✓ 位置 {card_info['position']}: {thumb_file} 一致")
        
        result = {
            "test": "thumbnail_preview_consistency",
            "tested": tested,
            "errors": len(errors),
            "details": errors
        }
        self.test_results.append(result)
        
        if errors:
            print(f"\n结果: {len(errors)}/{tested} 个位置不一致")
        else:
            print(f"\n结果: 全部 {tested} 个位置一致 ✓")
            
        return len(errors) == 0
    
    async def test_position_continuity(self):
        """测试位置索引连续性"""
        print("\n" + "="*60)
        print("测试: 位置索引连续性")
        print("="*60)
        
        frame = self.page.frame_locator("#frame-sort")
        cards = frame.locator("#grid .card")
        total = await cards.count()
        
        errors = []
        
        for i in range(total):
            card_info = await self.get_card_info(i)
            if not card_info:
                continue
            
            expected_position = str(i + 1).zfill(4)
            actual_position = card_info["position"]
            
            if expected_position != actual_position:
                error = f"索引 {i}: 期望={expected_position}, 实际={actual_position}"
                errors.append(error)
                if len(errors) <= 5:  # 只打印前5个错误
                    print(f"  ✗ {error}")
        
        result = {
            "test": "position_continuity",
            "total": total,
            "errors": len(errors),
            "details": errors[:10]  # 只保存前10个
        }
        self.test_results.append(result)
        
        if errors:
            print(f"\n结果: {len(errors)}/{total} 个位置不连续")
        else:
            print(f"\n结果: 全部 {total} 个位置连续 ✓")
            
        return len(errors) == 0
    
    async def test_refresh_consistency(self):
        """测试刷新后数据一致性"""
        print("\n" + "="*60)
        print("测试: 刷新后数据一致性")
        print("="*60)
        
        # 获取刷新前的状态
        frame = self.page.frame_locator("#frame-sort")
        cards = frame.locator("#grid .card")
        before_count = await cards.count()
        
        before_files = []
        for i in range(min(5, before_count)):
            info = await self.get_card_info(i)
            if info:
                before_files.append(info["data_file"])
        
        print(f"  刷新前: {before_count} 张, 前5个: {before_files}")
        
        # 刷新页面
        await self.page.reload()
        await self.page.wait_for_timeout(2000)
        await self.select_project()
        
        # 获取刷新后的状态
        cards = frame.locator("#grid .card")
        after_count = await cards.count()
        
        after_files = []
        for i in range(min(5, after_count)):
            info = await self.get_card_info(i)
            if info:
                after_files.append(info["data_file"])
        
        print(f"  刷新后: {after_count} 张, 前5个: {after_files}")
        
        # 验证
        count_match = before_count == after_count
        files_match = before_files == after_files
        
        result = {
            "test": "refresh_consistency",
            "before_count": before_count,
            "after_count": after_count,
            "count_match": count_match,
            "files_match": files_match
        }
        self.test_results.append(result)
        
        if count_match and files_match:
            print(f"\n结果: 刷新后数据一致 ✓")
            return True
        else:
            print(f"\n结果: 刷新后数据不一致 ✗")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*60)
        print("  截图工具一致性测试")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        await self.setup()
        
        try:
            await self.navigate_to_sort()
            
            if not await self.select_project():
                print("无法选择项目，测试终止")
                return
            
            # 运行测试
            results = {
                "position_continuity": await self.test_position_continuity(),
                "thumbnail_preview": await self.test_thumbnail_preview_consistency(),
                "refresh_consistency": await self.test_refresh_consistency(),
            }
            
            # 总结
            print("\n" + "="*60)
            print("  测试总结")
            print("="*60)
            
            passed = sum(1 for v in results.values() if v)
            total = len(results)
            
            for name, passed_test in results.items():
                status = "✓ 通过" if passed_test else "✗ 失败"
                print(f"  {name}: {status}")
            
            print(f"\n  总计: {passed}/{total} 通过")
            
            # 保存结果
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": results,
                "details": self.test_results
            }
            
            with open("test_report.json", "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n  报告已保存: test_report.json")
            
        finally:
            await self.teardown()


async def main():
    tester = ScreenshotConsistencyTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
