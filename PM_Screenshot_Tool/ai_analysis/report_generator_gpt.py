# -*- coding: utf-8 -*-
"""
GPT 报告生成器
利用 GPT 的大上下文窗口（400K tokens）生成竞品分析汇总报告
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("警告: openai 库未安装，请运行: pip install openai")


# ============================================================
# 报告生成 Prompt 模板
# ============================================================

SUMMARY_REPORT_PROMPT = """你是一位资深产品经理，正在为团队生成竞品分析汇总报告。

我会给你一个App的所有截图分析结果（JSON格式），请基于这些数据生成一份结构化的竞品分析报告。

## 分析数据：
{analysis_data}

## 输出要求：
请生成一份专业的竞品分析报告，包含以下部分：

```json
{{
  "app_name": "App名称",
  "analysis_date": "分析日期",
  "executive_summary": {{
    "cn": "执行摘要（100-200字，概述这个App的核心设计策略）",
    "en": "Executive summary in English (50-100 words)"
  }},
  
  "flow_analysis": {{
    "onboarding": {{
      "total_steps": 数字,
      "step_breakdown": [
        {{"step": 1, "type": "类型", "purpose": "目的"}},
        ...
      ],
      "incentive_placement": "激励点位置描述",
      "paywall_position": "付费墙位置（第几步）",
      "personalization_level": "高/中/低",
      "highlights": ["亮点1", "亮点2", "亮点3"]
    }},
    "paywall": {{
      "type": "软/硬付费墙",
      "trial_offer": "试用优惠描述",
      "pricing_display": "价格展示策略",
      "social_proof": "社交证明元素",
      "urgency_tactics": "紧迫感策略"
    }}
  }},
  
  "design_patterns": {{
    "visual_style": "视觉风格描述",
    "color_scheme": "配色方案",
    "top_patterns": [
      {{"pattern": "模式名", "usage": "使用场景", "effectiveness": "高/中/低"}}
    ]
  }},
  
  "key_insights": [
    {{
      "category": "onboarding/paywall/ux/conversion",
      "insight_cn": "洞察中文描述",
      "insight_en": "Insight in English",
      "recommendation": "建议借鉴之处"
    }}
  ],
  
  "competitive_advantages": [
    "竞争优势1",
    "竞争优势2"
  ],
  
  "areas_for_improvement": [
    "可改进之处1",
    "可改进之处2"
  ],
  
  "takeaways_for_our_product": [
    {{
      "priority": "高/中/低",
      "takeaway_cn": "可借鉴点中文",
      "takeaway_en": "Takeaway in English",
      "implementation_difficulty": "易/中/难"
    }}
  ]
}}
```

请确保：
1. 报告基于实际的截图分析数据，不要编造
2. 洞察要有深度，不要泛泛而谈
3. 建议要可操作，具体到可以直接应用
4. 双语输出，中英文都要专业准确

只输出JSON，不要其他内容。"""


MULTI_APP_COMPARISON_PROMPT = """你是一位资深产品经理，正在对比分析多个竞品App。

我会给你多个App的分析数据，请生成一份对比分析报告。

## 分析数据：
{analysis_data}

## 输出要求：

```json
{{
  "comparison_title": "竞品对比分析报告",
  "apps_analyzed": ["App1", "App2", ...],
  "analysis_date": "日期",
  
  "comparison_matrix": {{
    "onboarding_steps": {{
      "App1": 数字,
      "App2": 数字,
      ...
    }},
    "paywall_position": {{
      "App1": "位置描述",
      "App2": "位置描述"
    }},
    "trial_offer": {{
      "App1": "有/无 + 描述",
      "App2": "有/无 + 描述"
    }},
    "personalization": {{
      "App1": "高/中/低",
      "App2": "高/中/低"
    }}
  }},
  
  "best_practices": [
    {{
      "practice": "最佳实践名称",
      "found_in": ["App1", "App2"],
      "description_cn": "描述",
      "description_en": "Description"
    }}
  ],
  
  "differentiation_opportunities": [
    {{
      "opportunity_cn": "差异化机会",
      "opportunity_en": "Opportunity",
      "rationale": "理由"
    }}
  ],
  
  "recommended_approach": {{
    "onboarding": "推荐的Onboarding策略",
    "paywall": "推荐的付费策略",
    "key_features": ["推荐包含的关键功能"]
  }}
}}
```

只输出JSON，不要其他内容。"""


class GPTReportGenerator:
    """GPT 报告生成器"""
    
    def __init__(self, model: str = "gpt-4o"):
        """
        初始化
        
        Args:
            model: 使用的模型（推荐gpt-4o或更高版本以获得大上下文）
        """
        self.model = model
        self.api_key = self._load_api_key()
        self.client = None
        
        if self.api_key and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=self.api_key)
            print(f"[OK] GPT Report Generator initialized (model: {self.model})")
        else:
            print("[ERROR] OpenAI API not available")
    
    def _load_api_key(self) -> Optional[str]:
        """加载API Key"""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("OPENAI_API_KEY")
            except Exception:
                pass
        return None
    
    def _load_analysis_data(self, project_path: str) -> Optional[Dict]:
        """加载项目的分析数据"""
        # 尝试多个可能的分析文件
        possible_files = [
            "ai_analysis.json",
            "analysis_claude.json",
            "analysis_openai.json",
            "descriptions_structured.json"
        ]
        
        for filename in possible_files:
            filepath = os.path.join(project_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        return None
    
    def _prepare_analysis_summary(self, analysis_data: Dict) -> str:
        """准备分析数据摘要（控制token数量）"""
        results = analysis_data.get('results', {})
        
        summary = {
            "project_name": analysis_data.get('project_name', 'Unknown'),
            "total_screenshots": len(results),
            "screens": []
        }
        
        # 按screen_type分组统计
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        summary["type_distribution"] = type_counts
        
        # 提取每个截图的关键信息
        for filename, data in results.items():
            screen_info = {
                "filename": filename,
                "screen_type": data.get('screen_type', 'Unknown'),
                "sub_type": data.get('sub_type', ''),
                "naming": data.get('naming', {}),
                "core_function": data.get('core_function', {}),
                "design_highlights": data.get('design_highlights', [])[:2],  # 只取前2个亮点
                "tags": data.get('tags', [])[:3],  # 只取前3个标签
                "confidence": data.get('confidence', 0)
            }
            summary["screens"].append(screen_info)
        
        return json.dumps(summary, ensure_ascii=False, indent=2)
    
    def generate_single_app_report(
        self,
        project_path: str,
        output_file: Optional[str] = None
    ) -> Dict:
        """
        生成单个App的分析报告
        
        Args:
            project_path: 项目路径
            output_file: 输出文件路径
        
        Returns:
            报告字典
        """
        print(f"\n[REPORT] Generating report for: {project_path}")
        
        # 加载分析数据
        analysis_data = self._load_analysis_data(project_path)
        if not analysis_data:
            return {"error": "No analysis data found"}
        
        # 准备数据摘要
        data_summary = self._prepare_analysis_summary(analysis_data)
        
        # 构建prompt
        prompt = SUMMARY_REPORT_PROMPT.format(analysis_data=data_summary)
        
        print(f"  Data size: {len(data_summary)} chars")
        print(f"  Generating report with {self.model}...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            raw_response = response.choices[0].message.content
            
            # 解析JSON
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                report = json.loads(json_match.group(0))
            else:
                report = {"raw_response": raw_response, "error": "Failed to parse JSON"}
            
            # 添加元数据
            report["_meta"] = {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "source_project": os.path.basename(project_path)
            }
            
            # 保存报告
            if output_file is None:
                output_file = os.path.join(project_path, "competitive_report.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"  [OK] Report saved: {output_file}")
            
            # 同时生成Markdown版本
            md_file = output_file.replace('.json', '.md')
            self._generate_markdown_report(report, md_file)
            
            return report
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {"error": str(e)}
    
    def generate_comparison_report(
        self,
        project_paths: List[str],
        output_file: Optional[str] = None
    ) -> Dict:
        """
        生成多App对比报告
        
        Args:
            project_paths: 项目路径列表
            output_file: 输出文件路径
        
        Returns:
            对比报告字典
        """
        print(f"\n[COMPARE] Generating comparison report for {len(project_paths)} apps")
        
        # 加载所有项目的分析数据
        all_data = {}
        for path in project_paths:
            data = self._load_analysis_data(path)
            if data:
                project_name = data.get('project_name', os.path.basename(path))
                all_data[project_name] = self._prepare_analysis_summary(data)
        
        if not all_data:
            return {"error": "No analysis data found"}
        
        # 构建prompt
        combined_data = json.dumps(all_data, ensure_ascii=False)
        prompt = MULTI_APP_COMPARISON_PROMPT.format(analysis_data=combined_data)
        
        print(f"  Apps: {list(all_data.keys())}")
        print(f"  Generating comparison with {self.model}...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            raw_response = response.choices[0].message.content
            
            import re
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                report = json.loads(json_match.group(0))
            else:
                report = {"raw_response": raw_response}
            
            report["_meta"] = {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "apps_compared": list(all_data.keys())
            }
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                print(f"  [OK] Report saved: {output_file}")
            
            return report
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {"error": str(e)}
    
    def _generate_markdown_report(self, report: Dict, output_file: str):
        """生成Markdown格式的报告"""
        lines = []
        
        # 标题
        app_name = report.get('app_name', 'Unknown App')
        lines.append(f"# {app_name} 竞品分析报告\n")
        lines.append(f"*生成时间: {report.get('_meta', {}).get('generated_at', 'N/A')}*\n")
        
        # 执行摘要
        summary = report.get('executive_summary', {})
        lines.append("## 执行摘要\n")
        lines.append(f"{summary.get('cn', 'N/A')}\n")
        lines.append(f"*{summary.get('en', '')}*\n")
        
        # 流程分析
        flow = report.get('flow_analysis', {})
        if flow:
            lines.append("## 流程分析\n")
            
            onboarding = flow.get('onboarding', {})
            if onboarding:
                lines.append("### Onboarding\n")
                lines.append(f"- **总步骤数**: {onboarding.get('total_steps', 'N/A')}\n")
                lines.append(f"- **个性化程度**: {onboarding.get('personalization_level', 'N/A')}\n")
                lines.append(f"- **付费墙位置**: {onboarding.get('paywall_position', 'N/A')}\n")
                
                highlights = onboarding.get('highlights', [])
                if highlights:
                    lines.append("\n**亮点**:\n")
                    for h in highlights:
                        lines.append(f"- {h}\n")
            
            paywall = flow.get('paywall', {})
            if paywall:
                lines.append("\n### 付费墙\n")
                lines.append(f"- **类型**: {paywall.get('type', 'N/A')}\n")
                lines.append(f"- **试用优惠**: {paywall.get('trial_offer', 'N/A')}\n")
                lines.append(f"- **社交证明**: {paywall.get('social_proof', 'N/A')}\n")
        
        # 关键洞察
        insights = report.get('key_insights', [])
        if insights:
            lines.append("\n## 关键洞察\n")
            for i, insight in enumerate(insights, 1):
                lines.append(f"### {i}. {insight.get('category', '').upper()}\n")
                lines.append(f"{insight.get('insight_cn', 'N/A')}\n")
                lines.append(f"*{insight.get('insight_en', '')}*\n")
                lines.append(f"\n**建议**: {insight.get('recommendation', 'N/A')}\n")
        
        # 可借鉴点
        takeaways = report.get('takeaways_for_our_product', [])
        if takeaways:
            lines.append("\n## 可借鉴点\n")
            lines.append("| 优先级 | 借鉴点 | 实施难度 |\n")
            lines.append("|--------|--------|----------|\n")
            for t in takeaways:
                lines.append(f"| {t.get('priority', 'N/A')} | {t.get('takeaway_cn', 'N/A')} | {t.get('implementation_difficulty', 'N/A')} |\n")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"  [OK] Markdown report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GPT 报告生成器")
    parser.add_argument("--project", type=str, help="项目名称或路径")
    parser.add_argument("--projects", type=str, help="多个项目名称，逗号分隔（用于对比）")
    parser.add_argument("--model", type=str, default="gpt-4o", help="使用的模型")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    
    args = parser.parse_args()
    
    generator = GPTReportGenerator(model=args.model)
    
    if args.project:
        # 单App报告
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if os.path.isabs(args.project):
            project_path = args.project
        else:
            project_path = os.path.join(base_dir, "projects", args.project)
        
        generator.generate_single_app_report(project_path, args.output)
    
    elif args.projects:
        # 多App对比
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_names = [p.strip() for p in args.projects.split(',')]
        project_paths = [os.path.join(base_dir, "projects", p) for p in project_names]
        
        output = args.output or os.path.join(base_dir, "comparison_report.json")
        generator.generate_comparison_report(project_paths, output)
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  # 生成单App报告")
        print("  python report_generator_gpt.py --project Calm")
        print("")
        print("  # 生成多App对比报告")
        print("  python report_generator_gpt.py --projects Calm,Headspace,MFP")









































