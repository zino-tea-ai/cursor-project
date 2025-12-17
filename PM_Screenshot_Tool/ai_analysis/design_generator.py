# -*- coding: utf-8 -*-
"""
设计生成器 - 基于竞品分析生成产品设计方案
利用 GPT 的大上下文窗口，整合多个竞品的分析结果，生成定制化的设计方案
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


# ============================================================
# 设计生成 Prompt 模板
# ============================================================

ONBOARDING_DESIGN_PROMPT = """你是一位资深产品设计师和UX专家。

我会给你多个竞品App的Onboarding流程分析数据，请基于这些最佳实践，为我的产品设计一套Onboarding流程。

## 竞品分析数据：
{analysis_data}

## 我的产品信息：
{product_info}

## 设计要求：
{requirements}

## 输出要求：
请设计一套完整的Onboarding流程，输出以下JSON格式：

```json
{{
  "design_name": "设计方案名称",
  "target_product": "目标产品",
  "design_philosophy": {{
    "cn": "设计理念（50-100字）",
    "en": "Design philosophy (30-50 words)"
  }},
  
  "flow_overview": {{
    "total_steps": 数字,
    "estimated_completion_time": "预计完成时间（秒）",
    "key_strategy": "核心策略描述"
  }},
  
  "screens": [
    {{
      "step": 1,
      "screen_type": "类型（Welcome/Onboarding/Permission/Paywall等）",
      "name": {{
        "cn": "页面中文名",
        "en": "Page Name"
      }},
      "purpose": {{
        "cn": "页面目的",
        "en": "Page purpose"
      }},
      "layout": {{
        "structure": "布局结构描述",
        "header": "顶部区域内容",
        "body": "主体区域内容",
        "footer": "底部区域内容"
      }},
      "copy": {{
        "headline_cn": "主标题中文",
        "headline_en": "Headline English",
        "subheadline_cn": "副标题中文",
        "subheadline_en": "Subheadline English",
        "cta_cn": "按钮文案中文",
        "cta_en": "CTA English"
      }},
      "ui_elements": ["UI元素1", "UI元素2"],
      "interaction": {{
        "primary_action": "主要操作",
        "secondary_action": "次要操作（可选）",
        "skip_option": true或false
      }},
      "design_rationale": {{
        "cn": "设计依据（参考了哪个竞品的什么设计）",
        "en": "Design rationale"
      }},
      "reference_screenshots": ["参考的竞品截图文件名"]
    }}
  ],
  
  "incentive_strategy": {{
    "placement": "激励点位置策略",
    "types": ["激励类型1", "激励类型2"],
    "psychology": "心理学原理"
  }},
  
  "paywall_strategy": {{
    "position": "付费墙位置（第几步后）",
    "type": "软付费墙/硬付费墙",
    "trial_offer": {{
      "enabled": true,
      "duration": "试用时长",
      "messaging": "试用文案策略"
    }},
    "pricing_display": "价格展示策略",
    "social_proof": ["社交证明元素"]
  }},
  
  "personalization": {{
    "level": "高/中/低",
    "data_collected": ["收集的数据类型"],
    "personalization_points": ["个性化应用点"]
  }},
  
  "success_metrics": [
    {{
      "metric": "指标名称",
      "target": "目标值",
      "measurement": "测量方式"
    }}
  ],
  
  "ab_test_suggestions": [
    {{
      "test_name": "测试名称",
      "variable": "测试变量",
      "hypothesis": "假设"
    }}
  ]
}}
```

请确保：
1. 设计基于竞品分析的最佳实践
2. 每个页面都有清晰的目的和设计依据
3. 文案要专业且有吸引力
4. 标注参考的竞品截图便于查证

只输出JSON，不要其他内容。"""


FEATURE_DESIGN_PROMPT = """你是一位资深产品设计师。

基于以下竞品的功能设计分析，为我的产品设计一个新功能。

## 竞品分析数据：
{analysis_data}

## 我的产品信息：
{product_info}

## 功能需求：
{feature_requirements}

## 输出要求：

```json
{{
  "feature_name": {{
    "cn": "功能名称",
    "en": "Feature Name"
  }},
  "feature_description": {{
    "cn": "功能描述",
    "en": "Feature description"
  }},
  
  "user_stories": [
    {{
      "as_a": "用户角色",
      "i_want": "想要做什么",
      "so_that": "为了什么目的"
    }}
  ],
  
  "screens": [
    {{
      "screen_name": "页面名称",
      "purpose": "页面目的",
      "layout": "布局描述",
      "key_elements": ["关键UI元素"],
      "interactions": ["交互说明"],
      "reference_competitors": ["参考的竞品"]
    }}
  ],
  
  "user_flow": [
    {{
      "step": 1,
      "action": "用户操作",
      "system_response": "系统响应",
      "screen": "所在页面"
    }}
  ],
  
  "design_highlights": [
    {{
      "highlight_cn": "设计亮点",
      "highlight_en": "Design highlight",
      "source": "灵感来源竞品"
    }}
  ],
  
  "technical_considerations": [
    "技术注意事项"
  ],
  
  "success_metrics": [
    "成功指标"
  ]
}}
```

只输出JSON，不要其他内容。"""


class DesignGenerator:
    """设计生成器"""
    
    def __init__(self, model: str = "gpt-4o"):
        """
        初始化
        
        Args:
            model: 使用的模型（推荐gpt-4o以获得大上下文）
        """
        self.model = model
        self.api_key = self._load_api_key()
        self.client = None
        
        if self.api_key and OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=self.api_key)
            print(f"[OK] Design Generator initialized (model: {self.model})")
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
    
    def _load_project_analysis(self, project_path: str) -> Optional[Dict]:
        """加载项目分析数据"""
        possible_files = [
            "ai_analysis.json",
            "analysis_claude.json",
            "analysis_openai.json"
        ]
        
        for filename in possible_files:
            filepath = os.path.join(project_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        return None
    
    def _filter_screens_by_type(
        self, 
        analysis_data: Dict, 
        screen_types: List[str]
    ) -> List[Dict]:
        """按类型筛选截图"""
        results = analysis_data.get('results', {})
        filtered = []
        
        for filename, data in results.items():
            if data.get('screen_type') in screen_types:
                filtered.append({
                    'filename': filename,
                    'screen_type': data.get('screen_type'),
                    'sub_type': data.get('sub_type', ''),
                    'naming': data.get('naming', {}),
                    'core_function': data.get('core_function', {}),
                    'design_highlights': data.get('design_highlights', []),
                    'tags': data.get('tags', []),
                    'product_insight': data.get('product_insight', {})
                })
        
        return filtered
    
    def generate_onboarding_design(
        self,
        reference_projects: List[str],
        product_info: Dict,
        requirements: Optional[Dict] = None,
        output_file: Optional[str] = None
    ) -> Dict:
        """
        生成Onboarding设计方案
        
        Args:
            reference_projects: 参考的竞品项目路径列表
            product_info: 产品信息
            requirements: 设计要求
            output_file: 输出文件路径
        
        Returns:
            设计方案字典
        """
        print(f"\n[DESIGN] Generating Onboarding design...")
        print(f"  References: {len(reference_projects)} projects")
        
        # 收集所有Onboarding相关的截图分析
        all_onboarding_screens = {}
        onboarding_types = ['Welcome', 'Onboarding', 'Permission', 'Paywall', 'SignUp']
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for project in reference_projects:
            if not os.path.isabs(project):
                project_path = os.path.join(base_dir, "projects", project)
            else:
                project_path = project
            
            analysis = self._load_project_analysis(project_path)
            if analysis:
                project_name = analysis.get('project_name', os.path.basename(project_path))
                screens = self._filter_screens_by_type(analysis, onboarding_types)
                all_onboarding_screens[project_name] = screens
                print(f"    {project_name}: {len(screens)} onboarding screens")
        
        if not all_onboarding_screens:
            return {"error": "No onboarding screens found in reference projects"}
        
        # 准备数据
        analysis_data = json.dumps(all_onboarding_screens, ensure_ascii=False, indent=2)
        product_info_str = json.dumps(product_info, ensure_ascii=False, indent=2)
        requirements_str = json.dumps(requirements or {}, ensure_ascii=False, indent=2)
        
        # 构建prompt
        prompt = ONBOARDING_DESIGN_PROMPT.format(
            analysis_data=analysis_data,
            product_info=product_info_str,
            requirements=requirements_str
        )
        
        print(f"  Generating design with {self.model}...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=6000,
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
                design = json.loads(json_match.group(0))
            else:
                design = {"raw_response": raw_response, "error": "Failed to parse"}
            
            # 添加元数据
            design["_meta"] = {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "reference_projects": list(all_onboarding_screens.keys()),
                "product_info": product_info,
                "design_type": "onboarding"
            }
            
            # 保存
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(design, f, ensure_ascii=False, indent=2)
                print(f"  [OK] Design saved: {output_file}")
                
                # 生成Markdown版本
                md_file = output_file.replace('.json', '.md')
                self._generate_onboarding_markdown(design, md_file)
            
            return design
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {"error": str(e)}
    
    def generate_feature_design(
        self,
        reference_projects: List[str],
        product_info: Dict,
        feature_requirements: Dict,
        screen_types: List[str] = None,
        output_file: Optional[str] = None
    ) -> Dict:
        """
        生成功能设计方案
        
        Args:
            reference_projects: 参考的竞品项目路径列表
            product_info: 产品信息
            feature_requirements: 功能需求
            screen_types: 要参考的页面类型
            output_file: 输出文件路径
        
        Returns:
            设计方案字典
        """
        print(f"\n[DESIGN] Generating feature design...")
        
        # 默认参考所有功能相关页面
        if screen_types is None:
            screen_types = ['Feature', 'Tracking', 'Progress', 'Content', 'Home']
        
        # 收集相关截图
        all_screens = {}
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        for project in reference_projects:
            if not os.path.isabs(project):
                project_path = os.path.join(base_dir, "projects", project)
            else:
                project_path = project
            
            analysis = self._load_project_analysis(project_path)
            if analysis:
                project_name = analysis.get('project_name', os.path.basename(project_path))
                screens = self._filter_screens_by_type(analysis, screen_types)
                all_screens[project_name] = screens
        
        if not all_screens:
            return {"error": "No relevant screens found"}
        
        # 准备数据
        analysis_data = json.dumps(all_screens, ensure_ascii=False, indent=2)
        product_info_str = json.dumps(product_info, ensure_ascii=False, indent=2)
        feature_req_str = json.dumps(feature_requirements, ensure_ascii=False, indent=2)
        
        # 构建prompt
        prompt = FEATURE_DESIGN_PROMPT.format(
            analysis_data=analysis_data,
            product_info=product_info_str,
            feature_requirements=feature_req_str
        )
        
        print(f"  Generating with {self.model}...")
        
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
                design = json.loads(json_match.group(0))
            else:
                design = {"raw_response": raw_response}
            
            design["_meta"] = {
                "generated_at": datetime.now().isoformat(),
                "model": self.model,
                "reference_projects": list(all_screens.keys()),
                "design_type": "feature"
            }
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(design, f, ensure_ascii=False, indent=2)
                print(f"  [OK] Design saved: {output_file}")
            
            return design
            
        except Exception as e:
            print(f"  [ERROR] {e}")
            return {"error": str(e)}
    
    def _generate_onboarding_markdown(self, design: Dict, output_file: str):
        """生成Onboarding设计的Markdown文档"""
        lines = []
        
        # 标题
        lines.append(f"# {design.get('design_name', 'Onboarding Design')}\n")
        lines.append(f"*目标产品: {design.get('target_product', 'N/A')}*\n")
        lines.append(f"*生成时间: {design.get('_meta', {}).get('generated_at', 'N/A')}*\n")
        
        # 设计理念
        philosophy = design.get('design_philosophy', {})
        lines.append("\n## 设计理念\n")
        lines.append(f"{philosophy.get('cn', 'N/A')}\n")
        lines.append(f"*{philosophy.get('en', '')}*\n")
        
        # 流程概览
        overview = design.get('flow_overview', {})
        lines.append("\n## 流程概览\n")
        lines.append(f"- **总步骤数**: {overview.get('total_steps', 'N/A')}\n")
        lines.append(f"- **预计完成时间**: {overview.get('estimated_completion_time', 'N/A')}\n")
        lines.append(f"- **核心策略**: {overview.get('key_strategy', 'N/A')}\n")
        
        # 页面设计
        screens = design.get('screens', [])
        lines.append("\n## 页面设计\n")
        
        for screen in screens:
            step = screen.get('step', '?')
            name = screen.get('name', {})
            lines.append(f"\n### Step {step}: {name.get('cn', 'N/A')} ({name.get('en', '')})\n")
            
            lines.append(f"**类型**: {screen.get('screen_type', 'N/A')}\n")
            
            purpose = screen.get('purpose', {})
            lines.append(f"\n**目的**: {purpose.get('cn', 'N/A')}\n")
            
            # 布局
            layout = screen.get('layout', {})
            if layout:
                lines.append("\n**布局**:\n")
                lines.append(f"- 结构: {layout.get('structure', 'N/A')}\n")
                lines.append(f"- 顶部: {layout.get('header', 'N/A')}\n")
                lines.append(f"- 主体: {layout.get('body', 'N/A')}\n")
                lines.append(f"- 底部: {layout.get('footer', 'N/A')}\n")
            
            # 文案
            copy = screen.get('copy', {})
            if copy:
                lines.append("\n**文案**:\n")
                lines.append(f"- 主标题: {copy.get('headline_cn', 'N/A')}\n")
                lines.append(f"- 副标题: {copy.get('subheadline_cn', 'N/A')}\n")
                lines.append(f"- CTA: {copy.get('cta_cn', 'N/A')}\n")
            
            # 设计依据
            rationale = screen.get('design_rationale', {})
            if rationale:
                lines.append(f"\n**设计依据**: {rationale.get('cn', 'N/A')}\n")
            
            # 参考截图
            refs = screen.get('reference_screenshots', [])
            if refs:
                lines.append(f"\n**参考截图**: {', '.join(refs)}\n")
        
        # 激励策略
        incentive = design.get('incentive_strategy', {})
        if incentive:
            lines.append("\n## 激励策略\n")
            lines.append(f"- **位置**: {incentive.get('placement', 'N/A')}\n")
            lines.append(f"- **类型**: {', '.join(incentive.get('types', []))}\n")
            lines.append(f"- **心理学原理**: {incentive.get('psychology', 'N/A')}\n")
        
        # 付费墙策略
        paywall = design.get('paywall_strategy', {})
        if paywall:
            lines.append("\n## 付费墙策略\n")
            lines.append(f"- **位置**: {paywall.get('position', 'N/A')}\n")
            lines.append(f"- **类型**: {paywall.get('type', 'N/A')}\n")
            trial = paywall.get('trial_offer', {})
            if trial.get('enabled'):
                lines.append(f"- **试用**: {trial.get('duration', 'N/A')} - {trial.get('messaging', '')}\n")
        
        # A/B测试建议
        ab_tests = design.get('ab_test_suggestions', [])
        if ab_tests:
            lines.append("\n## A/B测试建议\n")
            for test in ab_tests:
                lines.append(f"- **{test.get('test_name', 'N/A')}**: {test.get('hypothesis', '')}\n")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        print(f"  [OK] Markdown: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="设计生成器 - 基于竞品生成设计方案")
    parser.add_argument("--type", type=str, default="onboarding",
                        choices=['onboarding', 'feature'],
                        help="设计类型")
    parser.add_argument("--refs", type=str, required=True,
                        help="参考的竞品项目，逗号分隔")
    parser.add_argument("--product", type=str, required=True,
                        help="产品名称")
    parser.add_argument("--category", type=str, default="health",
                        help="产品类别")
    parser.add_argument("--target-users", type=str, default="18-35岁健康关注者",
                        help="目标用户")
    parser.add_argument("--feature-name", type=str,
                        help="功能名称（功能设计时必填）")
    parser.add_argument("--model", type=str, default="gpt-4o",
                        help="使用的模型")
    parser.add_argument("--output", "-o", type=str,
                        help="输出文件路径")
    
    args = parser.parse_args()
    
    generator = DesignGenerator(model=args.model)
    
    # 产品信息
    product_info = {
        "name": args.product,
        "category": args.category,
        "target_users": args.target_users
    }
    
    # 参考项目
    ref_projects = [p.strip() for p in args.refs.split(',')]
    
    # 输出路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_file = args.output or os.path.join(
        base_dir, 
        f"designs/{args.product}_{args.type}_design.json"
    )
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if args.type == 'onboarding':
        generator.generate_onboarding_design(
            reference_projects=ref_projects,
            product_info=product_info,
            output_file=output_file
        )
    
    elif args.type == 'feature':
        if not args.feature_name:
            print("[ERROR] --feature-name is required for feature design")
        else:
            feature_req = {
                "name": args.feature_name,
                "description": f"设计{args.feature_name}功能"
            }
            generator.generate_feature_design(
                reference_projects=ref_projects,
                product_info=product_info,
                feature_requirements=feature_req,
                output_file=output_file
            )
    
    print("\n示例用法:")
    print("  # 生成Onboarding设计")
    print('  python design_generator.py --type onboarding --refs "Calm,Headspace" --product "MyApp"')
    print("")
    print("  # 生成功能设计")
    print('  python design_generator.py --type feature --refs "MFP,Noom" --product "MyApp" --feature-name "每日追踪"')

















