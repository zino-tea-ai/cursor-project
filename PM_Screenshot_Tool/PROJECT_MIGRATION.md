# 项目迁移文档 - PM Screenshot Tool

## 项目路径
```
C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool
```

---

## 一、项目目标
产品经理竞品分析工具，主要功能：
1. 从 ScreensDesign.com 下载竞品 App 截图
2. 按正确的用户流程顺序排列截图
3. AI 自动分类（Stage/Module/Feature 三层结构）
4. Web 界面展示和对比分析

---

## 二、核心设计原则

### ⚠️ 最重要的原则：截图绝对排序
- 截图必须按 Screen_001 → Screen_002 → Screen_003... 的绝对流程顺序展示
- 这个顺序反映视频播放/下载的原始顺序，不能被任何分类逻辑打乱
- 分类（Stage/Module/Feature）只是标签，不能改变展示顺序

### 三层分类体系
- **Stage**：Onboarding（引导）/ Core（核心）
- **Module**：Welcome, Profile, Goal, Paywall, Permission, Dashboard, Tracking...
- **Feature**：具体页面功能

---

## 三、已完成的功能

### Web 界面
- 主页：http://localhost:5000
- 排序工具：http://localhost:5000/sort
- 分类调整：http://localhost:5000/quick-classify

### 核心文件
- `app.py` - Flask 后端
- `templates/index.html` - 主界面
- `templates/sort_screens.html` - 拖拽排序工具
- `config/taxonomy.json` - 分类词库
- `data/competitors.json` - Sensor Tower Top 30 竞品列表

---

## 四、竞品列表（Sensor Tower Top 30）

### 已下载（6个）
| 产品 | 状态 |
|------|------|
| Cal AI | ✅ 已下载 93 张 |
| Calm | ✅ 已下载 120 张 |
| Flo | ✅ 已下载 198 张 |
| MyFitnessPal | ✅ 已下载 200 张 |
| Runna | ✅ 已下载 200 张 |
| Strava | ✅ 已下载 200 张 |

### 待下载（24个）
1. Peloton - https://screensdesign.com/apps/peloton-fitness-workouts/
2. WeightWatchers
3. Zwift
4. LADDER
5. Fitbit
6. Carbon
7. Headspace
8. MacroFactor
9. Calorie Counter +
10. Noom
11. Lose It!
12. Yazio
13. AllTrails
14. MyNetDiary
15. Yuka
16. Zero
17. Foodvisor
18. RP Diet
19. Lifesum
20. Fastic
21. Carb Manager
22. BitePal
23. Calorie Counter (Municorn)
24. HitMeal

---

## 五、当前工作流程

### 下载截图流程
1. 用户提供 ScreensDesign URL
2. 启动 Chrome 调试模式：
   ```
   chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\.chrome_debug"
   ```
3. 登录 ScreensDesign
4. 运行下载脚本，保存到 `projects/[产品名]_Analysis/screens/`

### 排序流程
1. 用户在 http://localhost:5000/sort 手动排序
2. 拖拽调整顺序，只有被拖动的卡片显示黄色
3. 点击"应用排序"重命名文件

### 分析流程
1. 排序完成后运行 AI 分析
2. 结果保存到 `ai_analysis.json`
3. 在主页展示，按 Stage 分组

---

## 六、已知问题

1. **截图顺序问题**：ScreensDesign 下载的截图顺序可能与视频不一致，需要用户手动在排序工具中调整

2. **Worktree 问题**：Cursor 的 worktree 功能不稳定，建议直接打开主项目文件夹

---

## 七、启动命令

### 启动 Web 服务
```bash
cd "C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool"
python app.py
```

### 启动 Chrome 调试模式
```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\.chrome_debug"
```

---

## 八、下一步任务

1. 下载剩余 24 个竞品的截图（用户逐个提供 URL）
2. 用户在排序工具中统一调整所有截图顺序
3. 运行 AI 分析
4. 开始竞品 Onboarding 对比分析

---

**迁移方式**：
1. 在 Cursor 中打开文件夹：`C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool`
2. 把这个文件内容发给新窗口的 AI
3. 继续工作












