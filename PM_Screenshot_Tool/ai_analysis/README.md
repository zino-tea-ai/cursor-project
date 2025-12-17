# AI Screenshot Analysis System / AI截图分析系统

## 功能特点

- **单张精准分析**: 每次只分析一张图片，避免上下文污染
- **结构化输出**: 强制JSON格式，确保输出一致性
- **三层自动验证**: 关键词验证 + 位置验证 + 序列验证
- **置信度评分**: 自动标记需要人工审核的结果
- **多格式报告**: 终端、Markdown、CSV、JSON

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 设置API Key

**Windows:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. 运行分析

```bash
cd PM_Screenshot_Tool/ai_analysis
python batch_ai_analyze.py --project Calm_Analysis
```

## 命令行用法

```bash
# 分析单个项目
python batch_ai_analyze.py --project Calm_Analysis

# 使用指定API Key
python batch_ai_analyze.py --project Calm_Analysis --api-key sk-xxx

# 查看所有项目状态
python batch_ai_analyze.py --status

# 跳过分析，只验证已有结果
python batch_ai_analyze.py --project Calm_Analysis --skip-analysis

# 分析所有项目
python batch_ai_analyze.py --all
```

## 输出文件

分析完成后会在项目文件夹生成：

| 文件 | 说明 |
|------|------|
| `ai_analysis.json` | AI分析原始结果 |
| `validation_report.json` | 验证报告 |
| `{项目名}_AI_Report.md` | 可读的Markdown报告 |
| `{项目名}_AI_ScreenList.csv` | Excel兼容的CSV清单 |
| `descriptions_ai.json` | 与Web UI兼容的描述文件 |

## 验证机制

### 置信度等级

| 等级 | 置信度范围 | 处理方式 |
|------|-----------|----------|
| PASS | >= 90% | 自动通过 |
| REVIEW | 70-90% | 建议复查 |
| FAIL | < 70% | 需要人工审核 |

### 验证规则

1. **关键词验证**: 检查AI识别的关键词是否符合该类型的预期
2. **位置验证**: 检查截图在序列中的位置是否合理（如Launch应该在前面）
3. **序列验证**: 检查整体流程顺序是否合理（如Onboarding应该在Home之前）

## 屏幕类型

| Type | 中文名 | 说明 |
|------|--------|------|
| Launch | 启动页 | 应用启动时的品牌展示 |
| Welcome | 欢迎页 | 产品价值主张引导 |
| Permission | 权限请求 | 系统权限弹窗 |
| SignUp | 注册登录 | 用户注册/登录流程 |
| Onboarding | 引导问卷 | 收集用户信息的问卷 |
| Paywall | 付费墙 | 订阅付费相关页面 |
| Home | 首页 | 应用主页/仪表盘 |
| Feature | 功能页 | 具体功能页面 |
| Content | 内容页 | 内容展示/播放 |
| Profile | 个人中心 | 用户账户页面 |
| Settings | 设置 | 应用设置 |
| Social | 社交 | 社交互动页面 |
| Tracking | 追踪记录 | 数据记录页面 |
| Progress | 进度统计 | 图表/数据展示 |

## 成本估算

使用 Claude Sonnet 模型：

| 截图数量 | 预估成本 | 预估时间 |
|----------|----------|----------|
| 100 张 | ~$0.50 | ~3分钟 |
| 200 张 | ~$1.00 | ~6分钟 |
| 500 张 | ~$2.50 | ~15分钟 |

## 模块说明

| 文件 | 功能 |
|------|------|
| `ai_analyzer.py` | AI分析核心，调用Claude Vision API |
| `validator.py` | 结果验证和回测 |
| `validation_rules.py` | 验证规则配置 |
| `report_generator.py` | 报告生成器 |
| `batch_ai_analyze.py` | 主入口脚本 |

## 获取API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在API Keys页面创建新Key
4. 复制Key并设置为环境变量

## 常见问题

**Q: 为什么要单张分析？**
A: 一次性给AI太多图片会导致后面的分析质量下降（上下文污染）

**Q: 可以用其他模型吗？**
A: 可以通过 `--model` 参数指定，如 `claude-3-5-sonnet-20241022`

**Q: 如何提高准确度？**
A: 
1. 确保截图清晰
2. 使用更强的模型（如 claude-sonnet-4）
3. 人工审核FAIL状态的结果





## 功能特点

- **单张精准分析**: 每次只分析一张图片，避免上下文污染
- **结构化输出**: 强制JSON格式，确保输出一致性
- **三层自动验证**: 关键词验证 + 位置验证 + 序列验证
- **置信度评分**: 自动标记需要人工审核的结果
- **多格式报告**: 终端、Markdown、CSV、JSON

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 设置API Key

**Windows:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. 运行分析

```bash
cd PM_Screenshot_Tool/ai_analysis
python batch_ai_analyze.py --project Calm_Analysis
```

## 命令行用法

```bash
# 分析单个项目
python batch_ai_analyze.py --project Calm_Analysis

# 使用指定API Key
python batch_ai_analyze.py --project Calm_Analysis --api-key sk-xxx

# 查看所有项目状态
python batch_ai_analyze.py --status

# 跳过分析，只验证已有结果
python batch_ai_analyze.py --project Calm_Analysis --skip-analysis

# 分析所有项目
python batch_ai_analyze.py --all
```

## 输出文件

分析完成后会在项目文件夹生成：

| 文件 | 说明 |
|------|------|
| `ai_analysis.json` | AI分析原始结果 |
| `validation_report.json` | 验证报告 |
| `{项目名}_AI_Report.md` | 可读的Markdown报告 |
| `{项目名}_AI_ScreenList.csv` | Excel兼容的CSV清单 |
| `descriptions_ai.json` | 与Web UI兼容的描述文件 |

## 验证机制

### 置信度等级

| 等级 | 置信度范围 | 处理方式 |
|------|-----------|----------|
| PASS | >= 90% | 自动通过 |
| REVIEW | 70-90% | 建议复查 |
| FAIL | < 70% | 需要人工审核 |

### 验证规则

1. **关键词验证**: 检查AI识别的关键词是否符合该类型的预期
2. **位置验证**: 检查截图在序列中的位置是否合理（如Launch应该在前面）
3. **序列验证**: 检查整体流程顺序是否合理（如Onboarding应该在Home之前）

## 屏幕类型

| Type | 中文名 | 说明 |
|------|--------|------|
| Launch | 启动页 | 应用启动时的品牌展示 |
| Welcome | 欢迎页 | 产品价值主张引导 |
| Permission | 权限请求 | 系统权限弹窗 |
| SignUp | 注册登录 | 用户注册/登录流程 |
| Onboarding | 引导问卷 | 收集用户信息的问卷 |
| Paywall | 付费墙 | 订阅付费相关页面 |
| Home | 首页 | 应用主页/仪表盘 |
| Feature | 功能页 | 具体功能页面 |
| Content | 内容页 | 内容展示/播放 |
| Profile | 个人中心 | 用户账户页面 |
| Settings | 设置 | 应用设置 |
| Social | 社交 | 社交互动页面 |
| Tracking | 追踪记录 | 数据记录页面 |
| Progress | 进度统计 | 图表/数据展示 |

## 成本估算

使用 Claude Sonnet 模型：

| 截图数量 | 预估成本 | 预估时间 |
|----------|----------|----------|
| 100 张 | ~$0.50 | ~3分钟 |
| 200 张 | ~$1.00 | ~6分钟 |
| 500 张 | ~$2.50 | ~15分钟 |

## 模块说明

| 文件 | 功能 |
|------|------|
| `ai_analyzer.py` | AI分析核心，调用Claude Vision API |
| `validator.py` | 结果验证和回测 |
| `validation_rules.py` | 验证规则配置 |
| `report_generator.py` | 报告生成器 |
| `batch_ai_analyze.py` | 主入口脚本 |

## 获取API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在API Keys页面创建新Key
4. 复制Key并设置为环境变量

## 常见问题

**Q: 为什么要单张分析？**
A: 一次性给AI太多图片会导致后面的分析质量下降（上下文污染）

**Q: 可以用其他模型吗？**
A: 可以通过 `--model` 参数指定，如 `claude-3-5-sonnet-20241022`

**Q: 如何提高准确度？**
A: 
1. 确保截图清晰
2. 使用更强的模型（如 claude-sonnet-4）
3. 人工审核FAIL状态的结果





## 功能特点

- **单张精准分析**: 每次只分析一张图片，避免上下文污染
- **结构化输出**: 强制JSON格式，确保输出一致性
- **三层自动验证**: 关键词验证 + 位置验证 + 序列验证
- **置信度评分**: 自动标记需要人工审核的结果
- **多格式报告**: 终端、Markdown、CSV、JSON

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 设置API Key

**Windows:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. 运行分析

```bash
cd PM_Screenshot_Tool/ai_analysis
python batch_ai_analyze.py --project Calm_Analysis
```

## 命令行用法

```bash
# 分析单个项目
python batch_ai_analyze.py --project Calm_Analysis

# 使用指定API Key
python batch_ai_analyze.py --project Calm_Analysis --api-key sk-xxx

# 查看所有项目状态
python batch_ai_analyze.py --status

# 跳过分析，只验证已有结果
python batch_ai_analyze.py --project Calm_Analysis --skip-analysis

# 分析所有项目
python batch_ai_analyze.py --all
```

## 输出文件

分析完成后会在项目文件夹生成：

| 文件 | 说明 |
|------|------|
| `ai_analysis.json` | AI分析原始结果 |
| `validation_report.json` | 验证报告 |
| `{项目名}_AI_Report.md` | 可读的Markdown报告 |
| `{项目名}_AI_ScreenList.csv` | Excel兼容的CSV清单 |
| `descriptions_ai.json` | 与Web UI兼容的描述文件 |

## 验证机制

### 置信度等级

| 等级 | 置信度范围 | 处理方式 |
|------|-----------|----------|
| PASS | >= 90% | 自动通过 |
| REVIEW | 70-90% | 建议复查 |
| FAIL | < 70% | 需要人工审核 |

### 验证规则

1. **关键词验证**: 检查AI识别的关键词是否符合该类型的预期
2. **位置验证**: 检查截图在序列中的位置是否合理（如Launch应该在前面）
3. **序列验证**: 检查整体流程顺序是否合理（如Onboarding应该在Home之前）

## 屏幕类型

| Type | 中文名 | 说明 |
|------|--------|------|
| Launch | 启动页 | 应用启动时的品牌展示 |
| Welcome | 欢迎页 | 产品价值主张引导 |
| Permission | 权限请求 | 系统权限弹窗 |
| SignUp | 注册登录 | 用户注册/登录流程 |
| Onboarding | 引导问卷 | 收集用户信息的问卷 |
| Paywall | 付费墙 | 订阅付费相关页面 |
| Home | 首页 | 应用主页/仪表盘 |
| Feature | 功能页 | 具体功能页面 |
| Content | 内容页 | 内容展示/播放 |
| Profile | 个人中心 | 用户账户页面 |
| Settings | 设置 | 应用设置 |
| Social | 社交 | 社交互动页面 |
| Tracking | 追踪记录 | 数据记录页面 |
| Progress | 进度统计 | 图表/数据展示 |

## 成本估算

使用 Claude Sonnet 模型：

| 截图数量 | 预估成本 | 预估时间 |
|----------|----------|----------|
| 100 张 | ~$0.50 | ~3分钟 |
| 200 张 | ~$1.00 | ~6分钟 |
| 500 张 | ~$2.50 | ~15分钟 |

## 模块说明

| 文件 | 功能 |
|------|------|
| `ai_analyzer.py` | AI分析核心，调用Claude Vision API |
| `validator.py` | 结果验证和回测 |
| `validation_rules.py` | 验证规则配置 |
| `report_generator.py` | 报告生成器 |
| `batch_ai_analyze.py` | 主入口脚本 |

## 获取API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在API Keys页面创建新Key
4. 复制Key并设置为环境变量

## 常见问题

**Q: 为什么要单张分析？**
A: 一次性给AI太多图片会导致后面的分析质量下降（上下文污染）

**Q: 可以用其他模型吗？**
A: 可以通过 `--model` 参数指定，如 `claude-3-5-sonnet-20241022`

**Q: 如何提高准确度？**
A: 
1. 确保截图清晰
2. 使用更强的模型（如 claude-sonnet-4）
3. 人工审核FAIL状态的结果





## 功能特点

- **单张精准分析**: 每次只分析一张图片，避免上下文污染
- **结构化输出**: 强制JSON格式，确保输出一致性
- **三层自动验证**: 关键词验证 + 位置验证 + 序列验证
- **置信度评分**: 自动标记需要人工审核的结果
- **多格式报告**: 终端、Markdown、CSV、JSON

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 设置API Key

**Windows:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. 运行分析

```bash
cd PM_Screenshot_Tool/ai_analysis
python batch_ai_analyze.py --project Calm_Analysis
```

## 命令行用法

```bash
# 分析单个项目
python batch_ai_analyze.py --project Calm_Analysis

# 使用指定API Key
python batch_ai_analyze.py --project Calm_Analysis --api-key sk-xxx

# 查看所有项目状态
python batch_ai_analyze.py --status

# 跳过分析，只验证已有结果
python batch_ai_analyze.py --project Calm_Analysis --skip-analysis

# 分析所有项目
python batch_ai_analyze.py --all
```

## 输出文件

分析完成后会在项目文件夹生成：

| 文件 | 说明 |
|------|------|
| `ai_analysis.json` | AI分析原始结果 |
| `validation_report.json` | 验证报告 |
| `{项目名}_AI_Report.md` | 可读的Markdown报告 |
| `{项目名}_AI_ScreenList.csv` | Excel兼容的CSV清单 |
| `descriptions_ai.json` | 与Web UI兼容的描述文件 |

## 验证机制

### 置信度等级

| 等级 | 置信度范围 | 处理方式 |
|------|-----------|----------|
| PASS | >= 90% | 自动通过 |
| REVIEW | 70-90% | 建议复查 |
| FAIL | < 70% | 需要人工审核 |

### 验证规则

1. **关键词验证**: 检查AI识别的关键词是否符合该类型的预期
2. **位置验证**: 检查截图在序列中的位置是否合理（如Launch应该在前面）
3. **序列验证**: 检查整体流程顺序是否合理（如Onboarding应该在Home之前）

## 屏幕类型

| Type | 中文名 | 说明 |
|------|--------|------|
| Launch | 启动页 | 应用启动时的品牌展示 |
| Welcome | 欢迎页 | 产品价值主张引导 |
| Permission | 权限请求 | 系统权限弹窗 |
| SignUp | 注册登录 | 用户注册/登录流程 |
| Onboarding | 引导问卷 | 收集用户信息的问卷 |
| Paywall | 付费墙 | 订阅付费相关页面 |
| Home | 首页 | 应用主页/仪表盘 |
| Feature | 功能页 | 具体功能页面 |
| Content | 内容页 | 内容展示/播放 |
| Profile | 个人中心 | 用户账户页面 |
| Settings | 设置 | 应用设置 |
| Social | 社交 | 社交互动页面 |
| Tracking | 追踪记录 | 数据记录页面 |
| Progress | 进度统计 | 图表/数据展示 |

## 成本估算

使用 Claude Sonnet 模型：

| 截图数量 | 预估成本 | 预估时间 |
|----------|----------|----------|
| 100 张 | ~$0.50 | ~3分钟 |
| 200 张 | ~$1.00 | ~6分钟 |
| 500 张 | ~$2.50 | ~15分钟 |

## 模块说明

| 文件 | 功能 |
|------|------|
| `ai_analyzer.py` | AI分析核心，调用Claude Vision API |
| `validator.py` | 结果验证和回测 |
| `validation_rules.py` | 验证规则配置 |
| `report_generator.py` | 报告生成器 |
| `batch_ai_analyze.py` | 主入口脚本 |

## 获取API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在API Keys页面创建新Key
4. 复制Key并设置为环境变量

## 常见问题

**Q: 为什么要单张分析？**
A: 一次性给AI太多图片会导致后面的分析质量下降（上下文污染）

**Q: 可以用其他模型吗？**
A: 可以通过 `--model` 参数指定，如 `claude-3-5-sonnet-20241022`

**Q: 如何提高准确度？**
A: 
1. 确保截图清晰
2. 使用更强的模型（如 claude-sonnet-4）
3. 人工审核FAIL状态的结果






## 功能特点

- **单张精准分析**: 每次只分析一张图片，避免上下文污染
- **结构化输出**: 强制JSON格式，确保输出一致性
- **三层自动验证**: 关键词验证 + 位置验证 + 序列验证
- **置信度评分**: 自动标记需要人工审核的结果
- **多格式报告**: 终端、Markdown、CSV、JSON

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 设置API Key

**Windows:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. 运行分析

```bash
cd PM_Screenshot_Tool/ai_analysis
python batch_ai_analyze.py --project Calm_Analysis
```

## 命令行用法

```bash
# 分析单个项目
python batch_ai_analyze.py --project Calm_Analysis

# 使用指定API Key
python batch_ai_analyze.py --project Calm_Analysis --api-key sk-xxx

# 查看所有项目状态
python batch_ai_analyze.py --status

# 跳过分析，只验证已有结果
python batch_ai_analyze.py --project Calm_Analysis --skip-analysis

# 分析所有项目
python batch_ai_analyze.py --all
```

## 输出文件

分析完成后会在项目文件夹生成：

| 文件 | 说明 |
|------|------|
| `ai_analysis.json` | AI分析原始结果 |
| `validation_report.json` | 验证报告 |
| `{项目名}_AI_Report.md` | 可读的Markdown报告 |
| `{项目名}_AI_ScreenList.csv` | Excel兼容的CSV清单 |
| `descriptions_ai.json` | 与Web UI兼容的描述文件 |

## 验证机制

### 置信度等级

| 等级 | 置信度范围 | 处理方式 |
|------|-----------|----------|
| PASS | >= 90% | 自动通过 |
| REVIEW | 70-90% | 建议复查 |
| FAIL | < 70% | 需要人工审核 |

### 验证规则

1. **关键词验证**: 检查AI识别的关键词是否符合该类型的预期
2. **位置验证**: 检查截图在序列中的位置是否合理（如Launch应该在前面）
3. **序列验证**: 检查整体流程顺序是否合理（如Onboarding应该在Home之前）

## 屏幕类型

| Type | 中文名 | 说明 |
|------|--------|------|
| Launch | 启动页 | 应用启动时的品牌展示 |
| Welcome | 欢迎页 | 产品价值主张引导 |
| Permission | 权限请求 | 系统权限弹窗 |
| SignUp | 注册登录 | 用户注册/登录流程 |
| Onboarding | 引导问卷 | 收集用户信息的问卷 |
| Paywall | 付费墙 | 订阅付费相关页面 |
| Home | 首页 | 应用主页/仪表盘 |
| Feature | 功能页 | 具体功能页面 |
| Content | 内容页 | 内容展示/播放 |
| Profile | 个人中心 | 用户账户页面 |
| Settings | 设置 | 应用设置 |
| Social | 社交 | 社交互动页面 |
| Tracking | 追踪记录 | 数据记录页面 |
| Progress | 进度统计 | 图表/数据展示 |

## 成本估算

使用 Claude Sonnet 模型：

| 截图数量 | 预估成本 | 预估时间 |
|----------|----------|----------|
| 100 张 | ~$0.50 | ~3分钟 |
| 200 张 | ~$1.00 | ~6分钟 |
| 500 张 | ~$2.50 | ~15分钟 |

## 模块说明

| 文件 | 功能 |
|------|------|
| `ai_analyzer.py` | AI分析核心，调用Claude Vision API |
| `validator.py` | 结果验证和回测 |
| `validation_rules.py` | 验证规则配置 |
| `report_generator.py` | 报告生成器 |
| `batch_ai_analyze.py` | 主入口脚本 |

## 获取API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在API Keys页面创建新Key
4. 复制Key并设置为环境变量

## 常见问题

**Q: 为什么要单张分析？**
A: 一次性给AI太多图片会导致后面的分析质量下降（上下文污染）

**Q: 可以用其他模型吗？**
A: 可以通过 `--model` 参数指定，如 `claude-3-5-sonnet-20241022`

**Q: 如何提高准确度？**
A: 
1. 确保截图清晰
2. 使用更强的模型（如 claude-sonnet-4）
3. 人工审核FAIL状态的结果





## 功能特点

- **单张精准分析**: 每次只分析一张图片，避免上下文污染
- **结构化输出**: 强制JSON格式，确保输出一致性
- **三层自动验证**: 关键词验证 + 位置验证 + 序列验证
- **置信度评分**: 自动标记需要人工审核的结果
- **多格式报告**: 终端、Markdown、CSV、JSON

## 快速开始

### 1. 安装依赖

```bash
pip install anthropic
```

### 2. 设置API Key

**Windows:**
```cmd
set ANTHROPIC_API_KEY=your_key_here
```

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. 运行分析

```bash
cd PM_Screenshot_Tool/ai_analysis
python batch_ai_analyze.py --project Calm_Analysis
```

## 命令行用法

```bash
# 分析单个项目
python batch_ai_analyze.py --project Calm_Analysis

# 使用指定API Key
python batch_ai_analyze.py --project Calm_Analysis --api-key sk-xxx

# 查看所有项目状态
python batch_ai_analyze.py --status

# 跳过分析，只验证已有结果
python batch_ai_analyze.py --project Calm_Analysis --skip-analysis

# 分析所有项目
python batch_ai_analyze.py --all
```

## 输出文件

分析完成后会在项目文件夹生成：

| 文件 | 说明 |
|------|------|
| `ai_analysis.json` | AI分析原始结果 |
| `validation_report.json` | 验证报告 |
| `{项目名}_AI_Report.md` | 可读的Markdown报告 |
| `{项目名}_AI_ScreenList.csv` | Excel兼容的CSV清单 |
| `descriptions_ai.json` | 与Web UI兼容的描述文件 |

## 验证机制

### 置信度等级

| 等级 | 置信度范围 | 处理方式 |
|------|-----------|----------|
| PASS | >= 90% | 自动通过 |
| REVIEW | 70-90% | 建议复查 |
| FAIL | < 70% | 需要人工审核 |

### 验证规则

1. **关键词验证**: 检查AI识别的关键词是否符合该类型的预期
2. **位置验证**: 检查截图在序列中的位置是否合理（如Launch应该在前面）
3. **序列验证**: 检查整体流程顺序是否合理（如Onboarding应该在Home之前）

## 屏幕类型

| Type | 中文名 | 说明 |
|------|--------|------|
| Launch | 启动页 | 应用启动时的品牌展示 |
| Welcome | 欢迎页 | 产品价值主张引导 |
| Permission | 权限请求 | 系统权限弹窗 |
| SignUp | 注册登录 | 用户注册/登录流程 |
| Onboarding | 引导问卷 | 收集用户信息的问卷 |
| Paywall | 付费墙 | 订阅付费相关页面 |
| Home | 首页 | 应用主页/仪表盘 |
| Feature | 功能页 | 具体功能页面 |
| Content | 内容页 | 内容展示/播放 |
| Profile | 个人中心 | 用户账户页面 |
| Settings | 设置 | 应用设置 |
| Social | 社交 | 社交互动页面 |
| Tracking | 追踪记录 | 数据记录页面 |
| Progress | 进度统计 | 图表/数据展示 |

## 成本估算

使用 Claude Sonnet 模型：

| 截图数量 | 预估成本 | 预估时间 |
|----------|----------|----------|
| 100 张 | ~$0.50 | ~3分钟 |
| 200 张 | ~$1.00 | ~6分钟 |
| 500 张 | ~$2.50 | ~15分钟 |

## 模块说明

| 文件 | 功能 |
|------|------|
| `ai_analyzer.py` | AI分析核心，调用Claude Vision API |
| `validator.py` | 结果验证和回测 |
| `validation_rules.py` | 验证规则配置 |
| `report_generator.py` | 报告生成器 |
| `batch_ai_analyze.py` | 主入口脚本 |

## 获取API Key

1. 访问 https://console.anthropic.com/
2. 注册/登录账户
3. 在API Keys页面创建新Key
4. 复制Key并设置为环境变量

## 常见问题

**Q: 为什么要单张分析？**
A: 一次性给AI太多图片会导致后面的分析质量下降（上下文污染）

**Q: 可以用其他模型吗？**
A: 可以通过 `--model` 参数指定，如 `claude-3-5-sonnet-20241022`

**Q: 如何提高准确度？**
A: 
1. 确保截图清晰
2. 使用更强的模型（如 claude-sonnet-4）
3. 人工审核FAIL状态的结果




















