# PM Screenshot Tool 开发者日志
> 更新时间：2025-12-14
> 保存此文件，重新开始对话时粘贴给AI即可恢复上下文

---

## 一、项目概述

**项目名称**：PM_Screenshot_Tool（产品经理竞品分析工具）
**项目路径**：`C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool`
**目标**：从 screensdesign.com 下载竞品截图，自动AI分类分析，生成竞品报告

---

## 二、用户背景

- **角色**：产品经理
- **核心需求**：分析竞品的 Onboarding 流程、Paywall 设计
- **工作流偏好**：
  - 截图宽度：402px，PNG格式
  - 扁平文件夹结构（方便导入Figma）
  - 命名格式：`[阶段编号]_[阶段名]_[步骤编号]_[描述].png`
  - 生成CSV清单 + Markdown分析文档
- **技术环境**：Windows 10, PowerShell, Python 3.14+

---

## 三、分析的产品（6个）

| 产品 | URL | 状态 |
|------|-----|------|
| Cal AI | https://screensdesign.com/apps/cal-ai-calorie-tracker/ | ✅ 视频分析完成 |
| Calm | https://screensdesign.com/apps/calm/ | ⏳ 待处理 |
| Flo | https://screensdesign.com/apps/flo-period-pregnancy-tracker/ | ⏳ 待处理 |
| MyFitnessPal | https://screensdesign.com/apps/myfitnesspal-calorie-counter/ | ⏳ 待处理 |
| Runna | https://screensdesign.com/apps/runna-running-training-plans/ | ⏳ 待处理 |
| Strava | https://screensdesign.com/apps/strava-run-bike-hike/ | ⏳ 待处理 |

---

## 四、新分类框架（核心！）

### 4.1 三层分类结构

```
Stage（阶段）/ Module（模块）/ Feature（功能）
```

### 4.2 Stage 标准词库

| Stage | 说明 |
|-------|------|
| Onboarding | 首次启动到进入主界面前的所有步骤 |
| Paywall | 付费墙/订阅页面（可能在Onboarding内或独立） |
| Core | 产品核心功能区 |
| Settings | 设置相关 |
| Profile | 用户资料相关 |

### 4.3 Module 标准词库

| Module | 说明 |
|--------|------|
| Welcome | 欢迎/启动 |
| Permission | 权限请求 |
| Personalization | 个性化设置/问卷 |
| GoalSetting | 目标设定 |
| AccountSetup | 账号注册/登录 |
| Tutorial | 教程/引导 |
| Subscription | 订阅/付费 |
| Dashboard | 主页/仪表盘 |
| Tracking | 记录/追踪 |
| Analytics | 数据分析/报告 |
| Social | 社交功能 |
| Content | 内容浏览 |
| Search | 搜索 |
| Notification | 通知 |
| Account | 账户管理 |
| Preferences | 偏好设置 |
| Help | 帮助/支持 |

### 4.4 页面层级（Domain/Role）

| 层级 | 说明 |
|------|------|
| Domain | 页面所属领域（如：Onboarding、Core、Settings） |
| Role | 页面角色（如：Entry入口、Detail详情、Action操作、Result结果） |

### 4.5 转场类型

| Transition | 说明 |
|------------|------|
| push | 前进到新页面（右滑入） |
| pop | 返回上一页（左滑出） |
| modal | 弹窗/底部弹出 |
| tab | Tab切换 |
| replace | 页面替换 |

---

## 五、已完成的工作

### 5.1 基础设施
- ✅ 截图下载器（timeline顺序提取）
- ✅ Web展示界面（Flask + 前端）
- ✅ AI分析模块（Claude/GPT）
- ✅ 手动分类调整工具（/quick-classify）

### 5.2 Cal AI 视频分析
- ✅ 视频下载：`C:\Users\WIN\Desktop\calai.mp4`
- ✅ 帧提取：1473帧 → `video_analysis/calai_frames/`
- ✅ 去重处理：417张关键帧 → `video_analysis/calai_keyframes/`
- ✅ AI分析完成 → `video_analysis/calai_analysis.json`

---

## 六、待完成任务

### Phase 1：基础设施（当前）
1. ⏳ 创建 `config/taxonomy.json`（标准化词库文件）
2. ⏳ 更新 `ai_analysis/analyze_keyframes.py` 的prompt

### Phase 2：Cal AI 完整流程
3. ⏳ 用新框架重新分析视频帧
4. ⏳ 下载Cal AI静态截图
5. ⏳ AI对齐：视频帧 ↔ 静态截图
6. ⏳ 生成最终 `analysis.json`
7. ⏳ 更新前端展示

### Phase 3：全局推广
8. ⏳ 其他5个产品重复上述流程
9. ⏳ 收集"Other"类型，扩展词库
10. ⏳ 优化AI准确率

---

## 七、关键文件路径

```
PM_Screenshot_Tool/
├── config/
│   ├── taxonomy.json          # [待创建] 标准化分类词库
│   ├── api_keys.json          # API密钥配置
│   └── products.json          # 产品列表
├── ai_analysis/
│   ├── analyze_keyframes.py   # 视频帧分析脚本
│   ├── smart_analyzer.py      # 主AI分析模块
│   └── onboarding_classifier.py # Onboarding专用分类器
├── projects/
│   └── Cal_AI_*/              # Cal AI分析结果
├── templates/
│   ├── index.html             # 主页面
│   └── quick_classify.html    # 手动分类工具
└── app.py                     # Flask后端

video_analysis/
├── calai_frames/              # 原始提取帧(1473张)
├── calai_keyframes/           # 去重后关键帧(417张)
├── calai_analysis.json        # 视频分析结果
├── dedupe_frames.py           # 去重脚本
└── analyze_keyframes.py       # 分析脚本
```

---

## 八、重要技术决策

### 8.1 视频+截图混合方案
- **视频用于**：分析流程逻辑、页面层级、转场关系
- **截图用于**：高清展示（AI语义匹配对齐）

### 8.2 排序策略
- **绝对排序**：保持视频/timeline原始顺序
- **原因**：用户流程是线性的，特别是Onboarding

### 8.3 分类粒度
- **三层结构**：Stage → Module → Feature
- **标准化词库**：确保跨产品一致性
- **兜底机制**："Other"类型 + 定期扩展词库

---

## 九、遇到的问题和解决方案

| 问题 | 解决方案 |
|------|----------|
| URL转换错误导致404 | 使用原始URL，不做转换 |
| 长周期任务中断 | 设计断点续传+重试机制 |
| AI分类不准确 | 改进prompt + 三层分类框架 |
| Web排序错误 | 改为基于首次出现位置排序 |
| Onboarding定义模糊 | 明确边界：启动→进入主界面 |

---

## 十、API配置

```json
// config/api_keys.json
{
  "anthropic": "sk-ant-...",
  "openai": "sk-..."
}
```

---

## 十一、常用命令

```powershell
# 启动Web服务
cd "C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool"
python app.py

# 运行视频分析
cd "C:\Users\WIN\Desktop\Cursor Project\video_analysis"
python analyze_keyframes.py

# 提取视频帧
cd "C:\Users\WIN\Desktop\Cursor Project"
.\ffmpeg.exe -i calai.mp4 -vf "fps=2" video_analysis/calai_frames/frame_%04d.jpg

# 去重
python video_analysis/dedupe_frames.py
```

---

## 十二、下一步行动

**立即执行**：
1. 创建 `taxonomy.json` 文件
2. 内容包含所有标准化的 Stage、Module、Feature、Transition 词库

**文件内容预览**：
```json
{
  "version": "1.0",
  "stages": ["Onboarding", "Paywall", "Core", "Settings", "Profile"],
  "modules": {
    "Onboarding": ["Welcome", "Permission", "Personalization", ...],
    "Core": ["Dashboard", "Tracking", "Analytics", ...],
    ...
  },
  "features": { ... },
  "transitions": ["push", "pop", "modal", "tab", "replace"],
  "roles": ["Entry", "Detail", "Action", "Result", "List", "Form"]
}
```

---

## 十三、Cursor 多模型策略

### 推荐配置
| 任务类型 | 推荐模型 | 原因 |
|----------|----------|------|
| 复杂架构设计 | Opus 4.5 | 深度推理能力强 |
| 代码编写/修改 | Sonnet 4 | 平衡速度和质量 |
| 快速问答 | GPT-4o | 响应快 |
| 创意/文案 | GPT-5.2 | 创造力强 |

### 并行模式建议
- **2x 同模型**：适合需要一致性的任务
- **2x 不同模型**：适合需要多角度验证的任务

---

**恢复对话时，粘贴此文档即可！**



