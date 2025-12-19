# 🚀 AI分析系统升级说明

## 新增功能

### 1. 多模型支持
现在支持 **Claude** 和 **OpenAI GPT** 双引擎：

| 模块 | 说明 |
|------|------|
| `openai_analyzer.py` | OpenAI GPT Vision 分析器 |
| `unified_analyzer.py` | 统一分析器，支持模型切换 |
| `report_generator_gpt.py` | GPT 报告生成器 |
| `design_generator.py` | 设计方案生成器 |

---

## 快速开始

### 安装依赖
```bash
pip install openai anthropic
```

### 1. 使用统一分析器

```python
from unified_analyzer import UnifiedAnalyzer

# 使用 Claude（默认）
analyzer = UnifiedAnalyzer(provider='claude', tier='standard')
result = analyzer.analyze_single('screenshot.png')

# 使用 OpenAI
analyzer = UnifiedAnalyzer(provider='openai', tier='standard')
result = analyzer.analyze_single('screenshot.png')

# 按任务类型自动选择
analyzer = UnifiedAnalyzer(task='batch_classify')  # 自动用Claude Haiku
analyzer = UnifiedAnalyzer(task='report_summary')  # 自动用GPT
```

### 2. 命令行使用

```bash
# 单图分析（Claude）
python unified_analyzer.py --image screenshot.png

# 单图分析（OpenAI）
python unified_analyzer.py --image screenshot.png -p openai

# 对比两个提供商
python unified_analyzer.py --image screenshot.png --compare

# 批量分析项目
python unified_analyzer.py --project Calm -p claude -t fast -c 5

# 按任务类型自动选择
python unified_analyzer.py --project Calm --task batch_classify
```

---

## 模型配置

### 模型层级
| 层级 | Claude | OpenAI | 适用场景 |
|------|--------|--------|----------|
| fast | claude-3-5-haiku | gpt-4o-mini | 批量初筛，成本低 |
| standard | claude-sonnet-4 | gpt-4o | 常规分析 |
| deep | claude-opus-4-5 | gpt-4o | 深度分析，最高质量 |

### 任务推荐配置
| 任务 | 推荐配置 |
|------|----------|
| batch_classify | Claude Haiku |
| deep_analysis | Claude Sonnet |
| verification | Claude Opus |
| report_summary | OpenAI GPT |
| design_generation | OpenAI GPT |

---

## 报告生成

```bash
# 单App报告
python report_generator_gpt.py --project Calm

# 多App对比报告
python report_generator_gpt.py --projects Calm,Headspace,MFP

# 输出文件：
# - competitive_report.json (JSON格式)
# - competitive_report.md (Markdown格式)
```

---

## 设计生成

```bash
# 生成Onboarding设计
python design_generator.py \
  --type onboarding \
  --refs "Calm,Headspace" \
  --product "我的App" \
  --category "健康" \
  --target-users "18-35岁健康关注者"

# 生成功能设计
python design_generator.py \
  --type feature \
  --refs "MFP,Noom" \
  --product "我的App" \
  --feature-name "每日追踪"

# 输出文件：
# - designs/我的App_onboarding_design.json
# - designs/我的App_onboarding_design.md
```

---

## API Keys 配置

API Keys 存储在 `config/api_keys.json`：

```json
{
  "ANTHROPIC_API_KEY": "sk-ant-xxx",
  "OPENAI_API_KEY": "sk-proj-xxx"
}
```

⚠️ **安全提醒**：请将此文件加入 `.gitignore`

---

## 完整工作流示例

```python
# 1. 批量分析截图（使用Claude Haiku节省成本）
from unified_analyzer import batch_analyze
batch_analyze('Calm', provider='claude', tier='fast', concurrent=5)

# 2. 生成竞品报告（使用GPT大上下文）
from report_generator_gpt import GPTReportGenerator
generator = GPTReportGenerator()
generator.generate_single_app_report('./projects/Calm')

# 3. 生成设计方案
from design_generator import DesignGenerator
designer = DesignGenerator()
designer.generate_onboarding_design(
    reference_projects=['Calm', 'Headspace'],
    product_info={
        'name': '我的健康App',
        'category': '健康',
        'target_users': '18-35岁'
    },
    output_file='./designs/my_onboarding.json'
)
```

---

## 文件结构

```
ai_analysis/
├── ai_analyzer.py           # Claude 分析器（原有）
├── openai_analyzer.py       # OpenAI GPT 分析器（新增）
├── unified_analyzer.py      # 统一分析器（新增）
├── report_generator_gpt.py  # GPT 报告生成器（新增）
├── design_generator.py      # 设计方案生成器（新增）
├── fast_analyze.py          # 高速并行分析
└── README_UPGRADE.md        # 本文档
```

---

## 常见问题

### Q: 什么时候用 Claude，什么时候用 GPT？
- **Claude**: 截图分析（Vision能力强）、深度推理
- **GPT**: 大量文本汇总（400K上下文）、设计生成

### Q: 如何降低成本？
- 批量初筛用 `fast` 层级（Haiku / gpt-4o-mini）
- 只对关键截图用 `deep` 层级

### Q: 报告生成失败怎么办？
- 检查是否已运行截图分析（需要 `ai_analysis.json`）
- 确认 OpenAI API Key 有效









































