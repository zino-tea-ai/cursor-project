# PM Tool V1 → V2 完整复刻指南

## 🖼️ 视觉对比

### V1 排序页面
![V1](./screenshots/v1_sort_page.png)

**V1 特点**：
- ✅ 待处理区（显示 11 张傲软截图）
- ✅ 双语导航（首页 Home、排序 Sort）
- ✅ 操作栏（删除、标记 Onboarding）
- ✅ 右侧预览区
- ✅ 快捷键面板
- ✅ 导入/配置按钮

### V2 排序页面
![V2](./screenshots/v2_sort_page.png)

**V2 特点**：
- ✅ 更简洁的侧边栏
- ✅ 项目列表更清晰（带数量）
- ✅ 设置入口
- ❌ 缺少待处理区
- ❌ 缺少预览区
- ❌ 缺少操作按钮

---

## 📊 版本对比

| 项目 | V1 (Flask) | V2 (FastAPI + Next.js) |
|------|------------|------------------------|
| 前端 | http://localhost:5000 | http://localhost:3001 |
| 后端 | Flask (同一端口) | http://localhost:8001 |
| API 文档 | 无 | http://localhost:8001/docs |
| 技术栈 | Flask + Jinja2 + Socket.IO | FastAPI + Next.js 15 |

---

## 🔴 V2 缺失的核心功能（需要复刻）

### 1. 待处理区（傲软截图导入）⚠️ 重要
**V1 功能**：
- 侧边栏 "待处理 Pending" 区域
- 自动监控傲软投屏截图目录
- 实时显示待处理截图数量
- 拖拽导入到项目任意位置
- WebSocket 实时更新

**V2 状态**：❌ 完全缺失

**需要实现**：
```
后端 API:
- GET /api/pending-screenshots       # 获取待处理截图列表
- POST /api/import-screenshot        # 导入截图到项目
- GET /api/apowersoft-config         # 获取傲软配置
- POST /api/apowersoft-config        # 保存傲软配置
- WebSocket: screenshot_imported     # 实时推送

前端组件:
- PendingPanel 组件（侧边栏）
- 拖拽上传功能
- 配置弹窗
```

---

### 2. 右侧预览面板 ⚠️ 重要
**V1 功能**：
- 固定在右侧的大图预览区
- 点击卡片显示大图
- 显示当前选中截图信息

**V2 状态**：❌ 缺失

**需要实现**：
```jsx
// 三栏布局：侧边栏 | 网格区 | 预览区
<div className="flex h-screen">
  <Sidebar />           {/* 240px */}
  <main className="flex-1">
    <ScreenGrid />      {/* 截图网格 */}
  </main>
  <PreviewPanel />      {/* 300px 预览区 */}
</div>
```

---

### 3. 快捷键系统
**V1 功能**：
| 快捷键 | 功能 |
|--------|------|
| Ctrl+A | 全选 |
| Delete | 删除选中 |
| Ctrl+Z | 撤销 |
| ← → | 导航 |
| Esc | 取消选择 |
| 拖拽 | 排序/插入 |

**V2 状态**：❌ 无快捷键提示面板

**需要实现**：
```jsx
// 右下角快捷键提示组件
<ShortcutHints>
  <kbd>Ctrl+A</kbd> 全选
  <kbd>Delete</kbd> 删除选中
  ...
</ShortcutHints>
```

---

### 4. 操作按钮栏
**V1 功能**：
- 🗑️ 删除 (选中数量)
- 🎯 标记 Onboarding
- 信息栏（总数、选中、已移动）

**V2 状态**：⚠️ 部分缺失
- ✅ 有全选按钮
- ❌ 无删除按钮
- ❌ 无标记 Onboarding 按钮
- ❌ 无信息栏

---

### 5. 拖拽排序 + 撤销
**V1 功能**：
- Sortable.js 拖拽排序
- 拖动的卡片显示黄色高亮
- 撤销历史（支持删除、排序撤销）
- 自动保存排序

**V2 状态**：⚠️ 需验证
- 需要检查是否实现了完整的拖拽排序
- 需要检查撤销功能

---

## ✅ V2 已实现的功能

### API 对比

| V1 API | V2 API | 状态 |
|--------|--------|------|
| `/api/projects` | `/api/projects` | ✅ |
| `/api/screens/<project>` | `/api/project-screenshots/{project_name}` | ✅ |
| `/api/thumb/<project>/<folder>/<file>` | `/api/thumbnails/{project_name}/{filename}` | ✅ |
| `/api/reorder-screens` | `/api/save-sort-order` + `/api/apply-sort-order` | ✅ |
| `/api/delete-screens` | `/api/delete-screens` | ✅ |
| `/api/restore-screens` | `/api/restore-screens` | ✅ |
| `/api/onboarding-range` | `/api/onboarding-range/{project_name}` | ✅ |
| `/api/store-comparison` | `/api/store-comparison` | ✅ |
| `/api/pending-screenshots` | ❌ 未实现 | ❌ |
| `/api/import-screenshot` | ❌ 未实现 | ❌ |
| `/api/apowersoft-config` | ❌ 未实现 | ❌ |

---

## 🎨 UI/UX 差异

### 设计系统

**V1 设计变量** (`common.css`):
```css
:root {
    --bg-primary: #0a0a0a;
    --bg-secondary: #111111;
    --bg-card: #1a1a1a;
    --text-primary: #ffffff;
    --text-muted: #6b7280;
    --border-default: rgba(255, 255, 255, 0.06);
    --font-family: 'Urbanist', -apple-system, sans-serif;
}
```

**V2 需要匹配的样式**：
- 侧边栏宽度：240px
- 白色左边框高亮导航项
- Urbanist 字体
- 深色主题 (#0a0a0a 背景)

### 导航结构

**V1**:
```
导航 Navigation
├── 首页 Home
├── 排序 Sort  
├── 引导流程 Onboarding
└── 商城对比 Store

项目 Project
└── [下拉选择器]

待处理 Pending (数量)
├── [截图缩略图列表]
└── [导入/配置按钮]
```

**V2**:
```
导航
└── 全部项目

工具
├── Onboarding
├── 排序
├── 分类
└── 商店对比

项目 (数量)
├── [项目列表...]
```

---

## 📋 复刻优先级

### P0 - 必须复刻（核心功能）
1. [ ] 待处理区（傲软截图导入）
2. [ ] 右侧预览面板
3. [ ] 删除/标记 Onboarding 按钮
4. [ ] 信息栏（总数、选中、已移动）
5. [ ] 完整的拖拽排序+撤销

### P1 - 重要功能
1. [ ] 快捷键系统
2. [ ] 导航双语显示（中英文）
3. [ ] Toast 提示样式统一
4. [ ] View Transition 动画

### P2 - 样式细节
1. [ ] 卡片左上角序号样式
2. [ ] 选中状态边框样式
3. [ ] 滚动条样式
4. [ ] 项目选择器下拉样式

---

## 🔧 具体实现建议

### 待处理区实现

**后端 (FastAPI)**:
```python
# api/pending.py
from fastapi import APIRouter
from watchdog.observers import Observer

router = APIRouter()

@router.get("/api/pending-screenshots")
async def list_pending():
    """列出待处理截图"""
    pass

@router.post("/api/import-screenshot")
async def import_screenshot(project: str, filename: str, position: int):
    """导入截图到项目指定位置"""
    pass

@router.get("/api/apowersoft-config")
async def get_config():
    """获取傲软配置"""
    pass
```

**前端 (Next.js)**:
```tsx
// components/PendingPanel.tsx
export function PendingPanel() {
  const [pending, setPending] = useState([]);
  
  // 使用 WebSocket 或轮询获取待处理截图
  useEffect(() => {
    fetchPending();
    const interval = setInterval(fetchPending, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="sidebar-section">
      <h3>待处理 Pending <span>{pending.length}</span></h3>
      <div className="pending-grid">
        {pending.map(img => (
          <PendingItem key={img} draggable />
        ))}
      </div>
    </div>
  );
}
```

---

## 📁 V1 核心文件参考

需要复刻的关键代码来自：

| 文件 | 行数 | 说明 |
|------|------|------|
| `app.py` | ~2600 | Flask 后端，所有 API |
| `templates/sort_screens.html` | ~3500 | 排序页面，最复杂 |
| `static/css/common.css` | ~780 | 统一设计系统 |
| `templates/onboarding.html` | ~1500 | Onboarding 页面 |
| `templates/store_comparison.html` | ~800 | 商店对比页面 |

---

## 🚀 快速复刻步骤

1. **阅读 V1 代码**：重点看 `sort_screens.html` 的 JavaScript
2. **对比 API**：确保 V2 后端实现了所有 V1 的 API
3. **实现待处理区**：这是最大的差异
4. **添加预览面板**：右侧固定区域
5. **完善操作栏**：删除、标记按钮
6. **添加快捷键**：全局键盘监听
7. **样式微调**：确保颜色、字体一致

---

*文档生成时间: 2024-12-19*
*生成者: Claude (基于 Playwright 分析)*

