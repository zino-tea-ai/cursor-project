# -*- coding: utf-8 -*-
"""
截图重新分类
使用新的三层分类体系重新分析所有截图
"""

import os
import sys
import json
import base64
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("[WARN] Anthropic not available")

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 加载API Key
API_KEYS_FILE = os.path.join(CONFIG_DIR, "api_keys.json")
if os.path.exists(API_KEYS_FILE):
    with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
        api_keys = json.load(f)
        for key, value in api_keys.items():
            if value and not os.environ.get(key):
                os.environ[key] = value

# 加载分类词表
def load_taxonomy():
    taxonomy_file = os.path.join(CONFIG_DIR, "taxonomy.json")
    if os.path.exists(taxonomy_file):
        with open(taxonomy_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

TAXONOMY = load_taxonomy()

# 构建分类提示词
def build_classification_prompt(taxonomy):
    """根据词表动态构建分类提示词"""
    
    stages_info = []
    for stage_name, stage_data in taxonomy.get("stages", {}).items():
        modules = ", ".join(stage_data.get("modules", []))
        stages_info.append(f"- **{stage_name}**: {stage_data.get('description_cn', '')} (模块: {modules})")
    
    modules_info = []
    for module_name, module_data in taxonomy.get("modules", {}).items():
        features = ", ".join(module_data.get("features", []))
        modules_info.append(f"- **{module_name}** ({module_data.get('stage', '')}): {module_data.get('description_cn', '')} → Features: {features}")
    
    prompt = f"""你是一个专业的产品分析师，专注于移动应用UI/UX分析。

请分析这个App截图，按照以下三层分类体系进行分类：

## 分类框架

### Stage（阶段）
{chr(10).join(stages_info)}

### Module（模块）及其Feature
{chr(10).join(modules_info[:15])}

## 判断规则
1. **Onboarding vs Core**: 
   - 如果页面没有底部Tab栏，通常是Onboarding
   - 如果是在收集用户信息、展示价值、请求权限、付费，是Onboarding
   - 如果已经进入核心功能（有Tab栏、可以记录数据），是Core

2. **Feature命名**: 使用PascalCase，如 GenderSelect, FoodSearch, PlanSelect

3. **page_role**: 
   - Information: 展示信息（价值主张、结果展示）
   - Collection: 收集信息（表单、选择）
   - Action: 执行动作（拍照、记录）
   - Confirmation: 确认（支付确认、完成提示）
   - Navigation: 导航（列表、Tab）

## 输出格式
请以JSON格式输出：
```json
{{
  "stage": "Onboarding或Core",
  "module": "模块名称",
  "feature": "功能点名称（PascalCase）",
  "page_role": "Information/Collection/Action/Confirmation/Navigation",
  "description_cn": "中文描述（20字以内）",
  "description_en": "English description (within 20 words)",
  "ui_elements": ["识别到的UI元素"],
  "has_tab_bar": false,
  "confidence": 0.95
}}
```

请只输出JSON，不要其他内容。"""
    
    return prompt

CLASSIFICATION_PROMPT = build_classification_prompt(TAXONOMY)


def analyze_screenshot(image_path, client, context=None):
    """分析单个截图"""
    
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    # 添加上下文信息
    prompt = CLASSIFICATION_PROMPT
    if context:
        prompt += f"\n\n## 上下文信息\n{context}"
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        result_text = response.content[0].text.strip()
        
        # 提取JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(result_text)
        
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {e}", "raw": result_text if 'result_text' in locals() else ""}
    except Exception as e:
        return {"error": str(e)}


def reclassify_project(project_name, start_from=0, limit=None):
    """重新分类项目中的所有截图"""
    
    if not ANTHROPIC_AVAILABLE:
        print("[ERROR] Anthropic not available")
        return
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        return
    
    client = anthropic.Anthropic(api_key=api_key)
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    ai_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(screens_dir):
        print(f"[ERROR] Screens directory not found: {screens_dir}")
        return
    
    # 加载现有分析结果
    existing_data = {}
    if os.path.exists(ai_file):
        with open(ai_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    
    results = existing_data.get("results", {})
    
    # 获取所有截图
    screenshots = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')])
    
    if limit:
        screenshots = screenshots[start_from:start_from + limit]
    else:
        screenshots = screenshots[start_from:]
    
    print(f"[RECLASSIFY] Starting analysis of {len(screenshots)} screenshots...")
    print(f"[RECLASSIFY] Using 3-layer classification: Stage / Module / Feature")
    
    for i, filename in enumerate(screenshots):
        filepath = os.path.join(screens_dir, filename)
        
        # 构建上下文（前一张截图的分类结果）
        context = None
        if i > 0:
            prev_file = screenshots[i-1]
            if prev_file in results:
                prev_result = results[prev_file]
                context = f"前一张截图: {prev_result.get('stage', '?')}/{prev_result.get('module', '?')}/{prev_result.get('feature', '?')}"
        
        print(f"[{i+1+start_from}/{len(screenshots)+start_from}] Analyzing {filename}...")
        
        result = analyze_screenshot(filepath, client, context)
        result["filename"] = filename
        result["index"] = i + start_from
        result["reclassified_at"] = datetime.now().isoformat()
        
        # 保留旧的描述信息
        if filename in results:
            old = results[filename]
            if "naming" in old:
                result["naming"] = old["naming"]
            if "core_function" in old:
                result["core_function"] = old["core_function"]
            if "design_highlights" in old:
                result["design_highlights"] = old["design_highlights"]
            if "product_insight" in old:
                result["product_insight"] = old["product_insight"]
            if "tags" in old:
                result["tags"] = old["tags"]
        
        results[filename] = result
        
        # 每5个保存一次
        if (i + 1) % 5 == 0:
            save_data = {
                **existing_data,
                "results": results,
                "classification_version": "3-layer",
                "last_updated": datetime.now().isoformat()
            }
            with open(ai_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            print(f"[SAVE] Progress saved ({i+1+start_from}/{len(screenshots)+start_from})")
    
    # 最终保存
    save_data = {
        **existing_data,
        "results": results,
        "classification_version": "3-layer",
        "last_updated": datetime.now().isoformat()
    }
    with open(ai_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    
    # 统计结果
    stages = {}
    modules = {}
    for v in results.values():
        s = v.get("stage", "Unknown")
        m = v.get("module", "Unknown")
        stages[s] = stages.get(s, 0) + 1
        modules[m] = modules.get(m, 0) + 1
    
    print(f"\n[DONE] Reclassification complete!")
    print(f"[STATS] Stages: {stages}")
    print(f"[STATS] Top Modules: {dict(sorted(modules.items(), key=lambda x: -x[1])[:10])}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="截图重新分类")
    parser.add_argument("--project", default="Cal_AI_-_Calorie_Tracker_Analysis", help="项目名称")
    parser.add_argument("--start", type=int, default=0, help="从第几张开始")
    parser.add_argument("--limit", type=int, default=None, help="限制分析数量")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("截图重新分类 - 三层分类体系")
    print("=" * 60)
    print(f"项目: {args.project}")
    print(f"开始位置: {args.start}")
    print(f"限制数量: {args.limit or '无限制'}")
    print("=" * 60)
    
    reclassify_project(args.project, args.start, args.limit)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    main()












