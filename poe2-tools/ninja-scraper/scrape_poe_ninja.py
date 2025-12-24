"""
使用 Playwright 抓取 poe.ninja POE2 萨满构建数据
"""
import asyncio
import json
from playwright.async_api import async_playwright


async def scrape_poe_ninja():
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://poe.ninja/poe2/builds/vaal?class=Shaman"
        print(f"正在访问: {url}")
        
        try:
            # 访问页面，等待网络空闲
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待页面加载完成
            await page.wait_for_timeout(3000)
            
            # 获取页面标题
            title = await page.title()
            print(f"页面标题: {title}")
            
            # 尝试获取构建数据
            data = {}
            
            # 1. 获取技能使用统计
            print("\n=== 技能使用统计 ===")
            try:
                # 查找技能统计区域
                skill_elements = await page.query_selector_all('[class*="skill"], [class*="Skill"]')
                print(f"找到 {len(skill_elements)} 个技能相关元素")
                
                # 尝试获取热门技能列表
                skills_data = await page.evaluate('''() => {
                    const skills = [];
                    // 查找所有带有技能图标和百分比的元素
                    const items = document.querySelectorAll('[class*="item"], [class*="row"], [class*="skill"]');
                    items.forEach(item => {
                        const text = item.innerText;
                        if (text && text.includes('%')) {
                            skills.push(text.trim());
                        }
                    });
                    return skills.slice(0, 50);
                }''')
                if skills_data:
                    for skill in skills_data[:20]:
                        print(f"  - {skill}")
            except Exception as e:
                print(f"获取技能数据出错: {e}")
            
            # 2. 获取页面主要内容
            print("\n=== 页面主要文本内容 ===")
            try:
                # 获取页面所有可见文本
                page_text = await page.evaluate('''() => {
                    return document.body.innerText;
                }''')
                # 打印前5000字符
                print(page_text[:5000] if page_text else "无内容")
                data['page_text'] = page_text
            except Exception as e:
                print(f"获取页面文本出错: {e}")
            
            # 3. 截图保存
            screenshot_path = "poe_ninja_shaman.png"
            await page.screenshot(path=screenshot_path, full_page=False)
            print(f"\n截图已保存: {screenshot_path}")
            
            # 4. 尝试获取表格数据
            print("\n=== 尝试获取表格/列表数据 ===")
            try:
                table_data = await page.evaluate('''() => {
                    const tables = document.querySelectorAll('table');
                    const result = [];
                    tables.forEach((table, idx) => {
                        const rows = table.querySelectorAll('tr');
                        const tableData = [];
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, th');
                            const rowData = [];
                            cells.forEach(cell => {
                                rowData.push(cell.innerText.trim());
                            });
                            if (rowData.length > 0) {
                                tableData.push(rowData);
                            }
                        });
                        if (tableData.length > 0) {
                            result.push({table_index: idx, data: tableData});
                        }
                    });
                    return result;
                }''')
                if table_data:
                    for table in table_data:
                        print(f"\n表格 {table['table_index']}:")
                        for row in table['data'][:10]:
                            print(f"  {row}")
                else:
                    print("未找到表格数据")
            except Exception as e:
                print(f"获取表格数据出错: {e}")
            
            # 5. 获取所有链接和统计信息
            print("\n=== 统计数据元素 ===")
            try:
                stats = await page.evaluate('''() => {
                    const elements = document.querySelectorAll('[class*="stat"], [class*="percent"], [class*="value"], [class*="count"]');
                    const stats = [];
                    elements.forEach(el => {
                        const text = el.innerText.trim();
                        if (text && text.length < 100) {
                            stats.push(text);
                        }
                    });
                    return [...new Set(stats)].slice(0, 30);
                }''')
                for stat in stats:
                    print(f"  - {stat}")
            except Exception as e:
                print(f"获取统计数据出错: {e}")
            
            # 保存完整HTML以便分析
            html_content = await page.content()
            with open("poe_ninja_shaman.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("\nHTML已保存: poe_ninja_shaman.html")
            
        except Exception as e:
            print(f"抓取过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(scrape_poe_ninja())









































