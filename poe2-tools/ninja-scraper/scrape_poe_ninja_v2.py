# -*- coding: utf-8 -*-
"""
使用 Playwright 抓取 poe.ninja POE2 萨满构建数据 - 改进版
"""
import asyncio
import json
import sys
import io

# 设置输出编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright


async def scrape_poe_ninja():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://poe.ninja/poe2/builds/vaal?class=Shaman"
        print(f"正在访问: {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000)
            
            title = await page.title()
            print(f"页面标题: {title}")
            
            # 1. 获取玩家构建列表
            print("\n" + "="*60)
            print("=== 萨满玩家构建数据 ===")
            print("="*60)
            
            builds_data = await page.evaluate('''() => {
                const builds = [];
                const rows = document.querySelectorAll('table tbody tr');
                rows.forEach((row, idx) => {
                    if (idx >= 30) return;  // 只取前30个
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
                        // 获取技能图标
                        const skillImgs = row.querySelectorAll('img');
                        const skills = [];
                        skillImgs.forEach(img => {
                            const alt = img.alt || img.title || '';
                            if (alt) skills.push(alt);
                        });
                        build.skills = skills;
                        builds.push(build);
                    }
                });
                return builds;
            }''')
            
            print(f"\n找到 {len(builds_data)} 个构建")
            for i, build in enumerate(builds_data[:15]):
                print(f"\n[{i+1}] {build['name']}")
                print(f"    等级: {build['level']}, 生命: {build['life']}, ES: {build['es']}, EHP: {build['ehp']}, DPS: {build['dps']}")
                if build['skills']:
                    print(f"    技能: {', '.join(build['skills'][:10])}")
            
            # 2. 尝试点击技能统计标签获取技能使用率
            print("\n" + "="*60)
            print("=== 查找技能使用统计 ===")
            print("="*60)
            
            # 点击 "Skill" 标签页（如果存在）
            try:
                skill_tab = await page.query_selector('text=Skill')
                if skill_tab:
                    await skill_tab.click()
                    await page.wait_for_timeout(2000)
            except:
                pass
            
            # 获取侧边栏或统计区域的技能数据
            skill_stats = await page.evaluate('''() => {
                const stats = [];
                // 查找所有带有百分比的元素
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const text = el.innerText || '';
                    // 匹配类似 "Skill Name 85%" 的模式
                    if (text.match(/\\d+(\\.\\d+)?%/) && text.length < 200 && !text.includes('\\n\\n')) {
                        const cleaned = text.replace(/\\s+/g, ' ').trim();
                        if (cleaned.length > 0 && cleaned.length < 100) {
                            stats.push(cleaned);
                        }
                    }
                });
                return [...new Set(stats)].slice(0, 50);
            }''')
            
            print("\n带百分比的统计数据:")
            for stat in skill_stats:
                print(f"  {stat}")
            
            # 3. 获取页面右侧的统计面板
            print("\n" + "="*60)
            print("=== 技能/天赋热度图数据 ===")
            print("="*60)
            
            heatmap_data = await page.evaluate('''() => {
                const data = {skills: [], keystones: [], ascendancy: []};
                
                // 查找所有列表项
                const listItems = document.querySelectorAll('li, div[class*="item"], div[class*="row"]');
                listItems.forEach(item => {
                    const text = item.innerText || '';
                    if (text.includes('%') && text.length < 150) {
                        data.skills.push(text.trim());
                    }
                });
                
                return data;
            }''')
            
            if heatmap_data['skills']:
                print("\n技能/物品统计:")
                for skill in heatmap_data['skills'][:30]:
                    if skill.strip():
                        print(f"  {skill}")
            
            # 4. 查看页面的完整结构
            print("\n" + "="*60)
            print("=== 页面主要区域文本 ===")
            print("="*60)
            
            main_content = await page.evaluate('''() => {
                const main = document.querySelector('main') || document.querySelector('[class*="content"]') || document.body;
                return main.innerText.substring(0, 8000);
            }''')
            
            print(main_content)
            
            # 5. 截图
            await page.screenshot(path="poe_ninja_shaman_v2.png", full_page=True)
            print("\n截图已保存: poe_ninja_shaman_v2.png")
            
            # 6. 保存JSON数据
            result = {
                'builds': builds_data,
                'skill_stats': skill_stats,
            }
            with open("poe_ninja_shaman_data.json", "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print("数据已保存: poe_ninja_shaman_data.json")
            
        except Exception as e:
            print(f"抓取过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_poe_ninja())









































