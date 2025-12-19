# -*- coding: utf-8 -*-
"""
自动诊断脚本
发现问题后生成详细诊断报告和修复建议
"""
import asyncio
import json
import requests
import os
from datetime import datetime
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:5000"
PROJECT = "downloads_2024/WeightWatchers"


class AutoDiagnoser:
    """自动诊断器"""
    
    def __init__(self):
        self.issues = []
        self.browser = None
        self.page = None
        
    async def setup(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        
    async def teardown(self):
        if self.browser:
            await self.browser.close()
    
    def check_api(self):
        """检查 API 返回的数据"""
        print("\n[1] 检查 API 数据...")
        
        try:
            resp = requests.get(f"{BASE_URL}/api/screenshots/{PROJECT}", timeout=10)
            data = resp.json()
            screens = data.get("screens", [])
            
            print(f"    API 返回 {len(screens)} 个文件")
            
            # 检查连续性
            expected = set(f"{i:04d}.png" for i in range(1, len(screens) + 1))
            actual = set(screens)
            
            missing = expected - actual
            extra = actual - expected
            
            if missing:
                self.issues.append({
                    "type": "api_missing_files",
                    "severity": "high",
                    "message": f"API 缺少文件: {sorted(missing)[:5]}...",
                    "fix": "文件可能被删除但编号未重排，需要重新下载或重命名"
                })
                print(f"    ⚠ 缺少: {sorted(missing)[:5]}")
            
            if extra:
                self.issues.append({
                    "type": "api_extra_files", 
                    "severity": "medium",
                    "message": f"API 有额外文件: {sorted(extra)[:5]}",
                    "fix": "文件编号超出预期范围"
                })
                print(f"    ⚠ 额外: {sorted(extra)[:5]}")
            
            if not missing and not extra:
                print("    ✓ 文件列表连续完整")
                
            return screens
            
        except Exception as e:
            self.issues.append({
                "type": "api_error",
                "severity": "critical",
                "message": str(e),
                "fix": "检查服务器是否运行"
            })
            print(f"    ✗ API 错误: {e}")
            return []
    
    def check_filesystem(self):
        """检查文件系统"""
        print("\n[2] 检查文件系统...")
        
        base_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "downloads_2024", "WeightWatchers"
        )
        
        # 检查主图
        main_files = [f for f in os.listdir(base_path) 
                      if f.endswith('.png') and not f.startswith('thumb')]
        main_files = sorted(main_files)
        print(f"    主图: {len(main_files)} 个")
        
        # 检查缩略图
        thumb_path = os.path.join(base_path, "thumbs_small")
        if os.path.exists(thumb_path):
            thumb_files = [f for f in os.listdir(thumb_path) if f.endswith('.png')]
            thumb_files = sorted(thumb_files)
            print(f"    缩略图: {len(thumb_files)} 个")
            
            # 检查孤立缩略图
            main_set = set(main_files)
            thumb_set = set(thumb_files)
            
            orphan_thumbs = thumb_set - main_set
            if orphan_thumbs:
                self.issues.append({
                    "type": "orphan_thumbnails",
                    "severity": "high",
                    "message": f"发现 {len(orphan_thumbs)} 个孤立缩略图",
                    "details": sorted(orphan_thumbs)[:10],
                    "fix": "删除孤立缩略图: rm thumbs_small/{" + ",".join(sorted(orphan_thumbs)[:3]) + "}"
                })
                print(f"    ⚠ 孤立缩略图: {sorted(orphan_thumbs)[:5]}")
            
            missing_thumbs = main_set - thumb_set
            if missing_thumbs:
                print(f"    ℹ 缺少缩略图: {len(missing_thumbs)} 个 (会自动生成)")
        else:
            print("    ℹ 缩略图目录不存在 (会自动生成)")
            
        return main_files
    
    async def check_ui_consistency(self, api_files):
        """检查 UI 显示一致性"""
        print("\n[3] 检查 UI 显示...")
        
        await self.page.goto(f"{BASE_URL}/#sort")
        await self.page.wait_for_timeout(2000)
        
        # 选择项目
        frame = self.page.frame_locator("#frame-sort")
        select = frame.locator("#projectSelect")
        options = await select.locator("option").all_text_contents()
        
        for opt in options:
            if "WeightWatchers" in opt:
                await select.select_option(label=opt)
                break
        
        await self.page.wait_for_timeout(2000)
        
        # 获取卡片数量
        cards = frame.locator("#grid .card")
        card_count = await cards.count()
        print(f"    UI 显示 {card_count} 张卡片")
        
        if card_count != len(api_files):
            self.issues.append({
                "type": "ui_count_mismatch",
                "severity": "high",
                "message": f"UI 显示 {card_count} 张，API 返回 {len(api_files)} 张",
                "fix": "刷新页面或检查前端渲染逻辑"
            })
            print(f"    ⚠ 数量不匹配!")
        
        # 抽样检查前10个卡片
        mismatches = []
        for i in range(min(10, card_count)):
            card = cards.nth(i)
            thumb_img = card.locator("img")
            thumb_src = await thumb_img.get_attribute("src")
            data_file = await card.get_attribute("data-file")
            
            # 点击查看预览
            await card.click()
            await self.page.wait_for_timeout(300)
            
            preview_img = frame.locator("#previewImage img")
            if await preview_img.count() > 0:
                preview_src = await preview_img.get_attribute("src")
                
                # 提取文件名比较
                thumb_file = thumb_src.split("/")[-1].split("?")[0] if thumb_src else None
                preview_file = preview_src.split("/")[-1].split("?")[0] if preview_src else None
                
                if thumb_file != preview_file:
                    mismatches.append({
                        "position": i + 1,
                        "data_file": data_file,
                        "thumb": thumb_file,
                        "preview": preview_file
                    })
        
        if mismatches:
            self.issues.append({
                "type": "thumbnail_preview_mismatch",
                "severity": "critical",
                "message": f"发现 {len(mismatches)} 个缩略图与预览不匹配",
                "details": mismatches,
                "fix": "清除缩略图缓存: rm -rf thumbs_small/ 并刷新页面"
            })
            print(f"    ⚠ {len(mismatches)} 个位置缩略图与预览不匹配")
        else:
            print("    ✓ 前10个位置缩略图与预览一致")
    
    def generate_report(self):
        """生成诊断报告"""
        print("\n" + "="*60)
        print("  诊断报告")
        print("="*60)
        
        if not self.issues:
            print("\n  ✓ 未发现问题!")
            return
        
        # 按严重程度分组
        critical = [i for i in self.issues if i["severity"] == "critical"]
        high = [i for i in self.issues if i["severity"] == "high"]
        medium = [i for i in self.issues if i["severity"] == "medium"]
        
        if critical:
            print("\n  🔴 严重问题:")
            for issue in critical:
                print(f"     - {issue['message']}")
                print(f"       修复: {issue['fix']}")
        
        if high:
            print("\n  🟠 重要问题:")
            for issue in high:
                print(f"     - {issue['message']}")
                print(f"       修复: {issue['fix']}")
        
        if medium:
            print("\n  🟡 一般问题:")
            for issue in medium:
                print(f"     - {issue['message']}")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "issues": self.issues,
            "summary": {
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium)
            }
        }
        
        with open("diagnosis_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n  报告已保存: diagnosis_report.json")
    
    async def run(self):
        """运行诊断"""
        print("\n" + "="*60)
        print("  截图工具自动诊断")
        print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        await self.setup()
        
        try:
            # 1. 检查 API
            api_files = self.check_api()
            
            # 2. 检查文件系统
            self.check_filesystem()
            
            # 3. 检查 UI
            if api_files:
                await self.check_ui_consistency(api_files)
            
            # 4. 生成报告
            self.generate_report()
            
        finally:
            await self.teardown()


async def main():
    diagnoser = AutoDiagnoser()
    await diagnoser.run()


if __name__ == "__main__":
    asyncio.run(main())
