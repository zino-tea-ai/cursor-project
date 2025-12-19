# -*- coding: utf-8 -*-
"""
使用 Playwright 抓取 poe.ninja POE2 萨满构建完整统计数据
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
            await page.wait_for_timeout(5000)
            
            # 获取页面总角色数
            total_chars = await page.evaluate('''() => {
                const el = document.body.innerText.match(/Found (\\d+) characters/);
                return el ? el[1] : 'unknown';
            }''')
            print(f"\n总计角色数: {total_chars}")
            
            # 获取左侧面板的所有统计数据
            print("\n" + "="*70)
            print("=== 从左侧面板抓取完整统计数据 ===")
            print("="*70)
            
            # 抓取左侧面板中的所有分类数据
            sidebar_data = await page.evaluate('''() => {
                const result = {};
                
                // 查找左侧面板
                const sidebar = document.querySelector('[class*="sidebar"]') || 
                               document.querySelector('[class*="filter"]') ||
                               document.querySelector('[class*="left"]');
                
                if (!sidebar) {
                    // 尝试获取所有带百分比的行
                    const allRows = [];
                    document.querySelectorAll('*').forEach(el => {
                        const text = el.innerText?.trim();
                        if (text && text.match(/^[\\w\\s]+\\s+\\d+%$/) && text.length < 50) {
                            allRows.push(text);
                        }
                    });
                    result['all'] = [...new Set(allRows)];
                    return result;
                }
                
                // 获取所有分类标题和对应的列表项
                let currentCategory = 'UNKNOWN';
                const categories = {};
                
                sidebar.querySelectorAll('*').forEach(el => {
                    const text = el.innerText?.trim();
                    if (!text) return;
                    
                    // 检测分类标题（通常是大写的文字）
                    if (text.match(/^[A-Z\\s]+$/) && text.length < 30) {
                        currentCategory = text;
                        if (!categories[currentCategory]) {
                            categories[currentCategory] = [];
                        }
                    }
                    
                    // 检测带百分比的项目
                    const match = text.match(/^(.+?)\\s+(\\d+)%$/);
                    if (match && !text.includes('\\n')) {
                        const name = match[1].trim();
                        const percent = parseInt(match[2]);
                        if (!categories[currentCategory]) {
                            categories[currentCategory] = [];
                        }
                        categories[currentCategory].push({name, percent});
                    }
                });
                
                return categories;
            }''')
            
            # 使用更精确的方法获取数据
            precise_data = await page.evaluate('''() => {
                const data = {
                    items: [],
                    main_skills: [],
                    keystones: [],
                    ascendancy: [],
                    support_skills: [],
                    auras: [],
                    weapons: []
                };
                
                // 获取页面所有文本内容
                const pageText = document.body.innerText;
                
                // 解析 ITEMS 部分
                const itemsMatch = pageText.match(/ITEMS[\\s\\S]*?(?=MAIN SKILLS|KEYSTONES|$)/i);
                if (itemsMatch) {
                    const itemLines = itemsMatch[0].split('\\n').filter(l => l.match(/\\d+%/));
                    itemLines.forEach(line => {
                        const m = line.match(/^(.+?)\\s+(\\d+)%$/);
                        if (m) data.items.push({name: m[1].trim(), percent: parseInt(m[2])});
                    });
                }
                
                // 解析 MAIN SKILLS 部分  
                const skillsMatch = pageText.match(/MAIN SKILLS[\\s\\S]*?(?=KEYSTONES|SUPPORT|AURAS|WEAPONS|$)/i);
                if (skillsMatch) {
                    const skillLines = skillsMatch[0].split('\\n').filter(l => l.match(/\\d+%/));
                    skillLines.forEach(line => {
                        const m = line.match(/^(.+?)\\s+(\\d+)%$/);
                        if (m) data.main_skills.push({name: m[1].trim(), percent: parseInt(m[2])});
                    });
                }
                
                return data;
            }''')
            
            print("\n【ITEMS 装备使用率】")
            for item in precise_data.get('items', []):
                print(f"  {item['name']}: {item['percent']}%")
            
            print("\n【MAIN SKILLS 主要技能使用率】")
            for skill in precise_data.get('main_skills', []):
                print(f"  {skill['name']}: {skill['percent']}%")
            
            # 滚动左侧面板以加载更多数据
            await page.evaluate('''() => {
                const sidebar = document.querySelector('[class*="sidebar"]') || 
                               document.querySelector('[class*="filter"]');
                if (sidebar) {
                    sidebar.scrollTop = sidebar.scrollHeight;
                }
            }''')
            await page.wait_for_timeout(1000)
            
            # 直接获取完整的左侧面板文本
            print("\n" + "="*70)
            print("=== 左侧面板完整文本 ===")
            print("="*70)
            
            left_panel_text = await page.evaluate('''() => {
                // 查找包含 ITEMS 和 MAIN SKILLS 的区域
                const body = document.body.innerText;
                const match = body.match(/(ITEMS[\\s\\S]*?)(?=Name\\s+Level|Found \\d+ characters|$)/);
                if (match) {
                    return match[1];
                }
                return body.substring(0, 3000);
            }''')
            
            print(left_panel_text[:2000])
            
            # 获取构建列表的详细数据
            print("\n" + "="*70)
            print("=== 前20名萨满构建详情 ===")
            print("="*70)
            
            builds = await page.evaluate('''() => {
                const builds = [];
                const rows = document.querySelectorAll('table tbody tr');
                rows.forEach((row, idx) => {
                    if (idx >= 20) return;
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 6) {
                        builds.push({
                            rank: idx + 1,
                            name: cells[0]?.innerText?.trim(),
                            level: cells[1]?.innerText?.trim(),
                            life: cells[2]?.innerText?.trim(),
                            es: cells[3]?.innerText?.trim(),
                            ehp: cells[4]?.innerText?.trim(),
                            dps: cells[5]?.innerText?.trim()
                        });
                    }
                });
                return builds;
            }''')
            
            print("\n排名 | 玩家 | 等级 | 生命 | ES | EHP | DPS")
            print("-" * 70)
            for b in builds:
                print(f"{b['rank']:2} | {b['name'][:20]:20} | {b['level']:3} | {b['life']:5} | {b['es']:5} | {b['ehp']:5} | {b['dps']:5}")
            
            # 点击 "Show passive heatmap" 查看天赋热力图
            print("\n" + "="*70)
            print("=== 尝试获取天赋热力图数据 ===")
            print("="*70)
            
            try:
                heatmap_btn = await page.query_selector('button:has-text("Show passive heatmap")')
                if heatmap_btn:
                    await heatmap_btn.click()
                    await page.wait_for_timeout(3000)
                    await page.screenshot(path="poe_ninja_heatmap.png")
                    print("天赋热力图截图已保存: poe_ninja_heatmap.png")
            except Exception as e:
                print(f"获取热力图失败: {e}")
            
            # 保存最终数据
            final_data = {
                'total_characters': total_chars,
                'sidebar_data': sidebar_data,
                'precise_data': precise_data,
                'builds': builds,
                'left_panel_text': left_panel_text
            }
            
            with open("poe_ninja_shaman_complete.json", "w", encoding="utf-8") as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)
            print("\n完整数据已保存: poe_ninja_shaman_complete.json")
            
        except Exception as e:
            print(f"抓取过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_poe_ninja())













