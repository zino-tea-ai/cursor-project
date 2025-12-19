# -*- coding: utf-8 -*-
"""
使用 Playwright 抓取 poe.ninja POE2 萨满构建数据 - V3
"""
import asyncio
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def scrape_poe_ninja():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        url = "https://poe.ninja/poe2/builds/vaal?class=Shaman"
        print(f"正在访问: {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)
            
            title = await page.title()
            print(f"页面标题: {title}")
            
            # 截图看当前页面状态
            await page.screenshot(path="poe_ninja_step1.png")
            print("Step1 截图已保存")
            
            # 检查是否有弹窗需要关闭
            try:
                close_btn = await page.query_selector('button:has-text("Close")')
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # 等待表格加载
            await page.wait_for_selector('table', timeout=10000)
            
            # 获取构建列表数据
            print("\n" + "="*60)
            print("=== 萨满玩家构建数据（前20名）===")
            print("="*60)
            
            builds_data = await page.evaluate('''() => {
                const builds = [];
                const rows = document.querySelectorAll('table tbody tr');
                rows.forEach((row, idx) => {
                    if (idx >= 20) return;
                    const cells = row.querySelectorAll('td');
                    if (cells.length > 0) {
                        const build = {
                            name: cells[0]?.innerText?.trim() || '',
                            level: cells[1]?.innerText?.trim() || '',
                            life: cells[2]?.innerText?.trim() || '',
                            es: cells[3]?.innerText?.trim() || '',
                            ehp: cells[4]?.innerText?.trim() || '',
                            dps: cells[5]?.innerText?.trim() || '',
                        };
                        // 获取技能图标的alt文本
                        const imgs = row.querySelectorAll('img[alt]');
                        const skills = [];
                        imgs.forEach(img => {
                            const alt = img.alt || '';
                            if (alt && !skills.includes(alt)) {
                                skills.push(alt);
                            }
                        });
                        build.skills = skills;
                        builds.push(build);
                    }
                });
                return builds;
            }''')
            
            for i, build in enumerate(builds_data):
                print(f"\n[{i+1}] {build['name']}")
                print(f"    Lv.{build['level']} | HP:{build['life']} | ES:{build['es']} | EHP:{build['ehp']} | DPS:{build['dps']}")
                if build['skills']:
                    print(f"    升华/关键点: {', '.join(build['skills'])}")
            
            # 点击第一个构建查看详情
            print("\n" + "="*60)
            print("=== 查看第一个构建的详细技能配置 ===")
            print("="*60)
            
            first_row = await page.query_selector('table tbody tr')
            if first_row:
                await first_row.click()
                await page.wait_for_timeout(3000)
                await page.screenshot(path="poe_ninja_build_detail.png")
                print("构建详情截图已保存")
                
                # 获取详情面板中的技能信息
                detail_data = await page.evaluate('''() => {
                    const result = {
                        skills: [],
                        keystones: [],
                        gear: [],
                        all_text: ''
                    };
                    
                    // 获取所有文本
                    const panels = document.querySelectorAll('[class*="panel"], [class*="sidebar"], [class*="detail"]');
                    panels.forEach(panel => {
                        result.all_text += panel.innerText + '\\n';
                    });
                    
                    // 获取所有图片alt作为技能/物品名
                    const imgs = document.querySelectorAll('img[alt]');
                    imgs.forEach(img => {
                        const alt = img.alt;
                        if (alt && alt.length > 2 && alt.length < 50) {
                            result.skills.push(alt);
                        }
                    });
                    
                    return result;
                }''')
                
                # 去重并显示
                unique_skills = list(dict.fromkeys(detail_data['skills']))
                print(f"\n发现的技能/物品/天赋 ({len(unique_skills)} 个):")
                for skill in unique_skills[:30]:
                    print(f"  - {skill}")
            
            # 返回列表页获取统计信息
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)
            
            # 尝试找到并点击 "Skill" 或 "Stats" 标签
            print("\n" + "="*60)
            print("=== 查找统计面板 ===")
            print("="*60)
            
            # 获取页面上所有按钮和标签
            tabs = await page.evaluate('''() => {
                const tabs = [];
                const elements = document.querySelectorAll('button, a, [role="tab"], [class*="tab"]');
                elements.forEach(el => {
                    const text = el.innerText?.trim();
                    if (text && text.length < 30) {
                        tabs.push(text);
                    }
                });
                return [...new Set(tabs)];
            }''')
            
            print(f"页面上的标签/按钮: {tabs}")
            
            # 获取右侧面板的统计数据
            stats_data = await page.evaluate('''() => {
                const stats = {
                    skills: [],
                    keystones: [],
                    ascendancy: [],
                    items: []
                };
                
                // 查找包含使用率的元素
                const allElements = document.body.querySelectorAll('*');
                allElements.forEach(el => {
                    if (el.children.length === 0) {  // 只看叶子节点
                        const text = el.innerText?.trim();
                        if (text && text.match(/\\d+%/)) {
                            stats.skills.push(text);
                        }
                    }
                });
                
                return stats;
            }''')
            
            if stats_data['skills']:
                print("\n带百分比的数据:")
                for s in stats_data['skills'][:50]:
                    print(f"  {s}")
            
            # 最终截图
            await page.screenshot(path="poe_ninja_final.png", full_page=True)
            print("\n最终截图已保存: poe_ninja_final.png")
            
            # 保存所有数据
            all_data = {
                'builds': builds_data,
                'stats': stats_data,
            }
            with open("poe_ninja_shaman_full.json", "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print("完整数据已保存: poe_ninja_shaman_full.json")
            
        except Exception as e:
            print(f"抓取过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_poe_ninja())













