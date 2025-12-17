# -*- coding: utf-8 -*-
"""
产品流程分析器
=============
给AI看整个产品的截图网格，让它识别Onboarding流程
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import base64
from PIL import Image
import io
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def load_api_key():
    paths = [
        os.path.join(BASE_DIR, "config", "api_keys.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                return data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    return None


def create_thumbnail_grid(screens_dir: str, cols: int = 10, thumb_size: int = 80) -> Image.Image:
    """创建缩略图网格"""
    files = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')],
                   key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    total = len(files)
    rows = (total + cols - 1) // cols
    
    grid_width = cols * thumb_size
    grid_height = rows * thumb_size
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    
    for idx, f in enumerate(files):
        try:
            with Image.open(os.path.join(screens_dir, f)) as img:
                img = img.convert('RGB')
                # 保持比例缩放
                ratio = thumb_size / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                thumb = img.resize(new_size, Image.LANCZOS)
                
                # 计算位置
                row = idx // cols
                col = idx % cols
                x = col * thumb_size + (thumb_size - new_size[0]) // 2
                y = row * thumb_size + (thumb_size - new_size[1]) // 2
                
                grid.paste(thumb, (x, y))
        except:
            pass
    
    return grid, total


def analyze_product_flow(project_name: str):
    """分析产品流程"""
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    
    if not os.path.exists(screens_dir):
        return None
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    # 创建缩略图网格
    print("  Creating thumbnail grid...")
    grid, total = create_thumbnail_grid(screens_dir)
    
    # 转base64
    buffer = io.BytesIO()
    grid.save(buffer, format='JPEG', quality=85)
    grid_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # API调用
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""这是一个App的{total}张截图组成的缩略图网格（从左到右，从上到下排列）。

请分析这个App的用户流程，特别是：

1. **Onboarding流程**（从App启动到进入主界面）
   - 大约在第几张到第几张？（例如：1-35）
   - 包含哪些步骤？（简要列举）

2. **Paywall位置**
   - 在第几张左右？
   - 是否在Onboarding流程中？

3. **Core功能开始**
   - 从第几张开始出现有Tab栏的主界面？

请用JSON格式回答：
{{
  "app_type": "App类型",
  "onboarding": {{
    "start": 1,
    "end": 截止页码,
    "steps": ["步骤1", "步骤2", ...]
  }},
  "paywall": {{
    "position": 页码或null,
    "in_onboarding": true/false
  }},
  "core_start": 开始页码,
  "summary": "一句话总结这个App的引导设计特点"
}}"""
    
    print("  Analyzing with AI...")
    
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': grid_data}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    
    text = response.content[0].text
    
    # 解析JSON
    if '```' in text:
        text = text.split('```')[1] if '```json' in text else text.split('```')[1]
        text = text.replace('json', '').strip()
    
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        result = json.loads(text[json_start:json_end])
    else:
        result = {"error": "Parse failed", "raw": text}
    
    result["project"] = project_name
    result["total_screenshots"] = total
    result["analyzed_at"] = datetime.now().isoformat()
    
    # 打印结果
    if "onboarding" in result:
        onb = result["onboarding"]
        print(f"\n  App Type: {result.get('app_type', 'N/A')}")
        print(f"  Onboarding: #{onb.get('start', '?')} - #{onb.get('end', '?')} ({onb.get('end', 0) - onb.get('start', 0) + 1} screens)")
        print(f"  Steps: {', '.join(onb.get('steps', [])[:5])}...")
        
        paywall = result.get("paywall", {})
        if paywall.get("position"):
            loc = "在Onboarding中" if paywall.get("in_onboarding") else "在Core功能区"
            print(f"  Paywall: #{paywall.get('position')} ({loc})")
        
        print(f"  Core Start: #{result.get('core_start', '?')}")
        print(f"\n  Summary: {result.get('summary', 'N/A')}")
    
    # 保存
    output_path = os.path.join(project_dir, "flow_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def analyze_all():
    """分析所有产品"""
    products = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    all_results = {}
    
    for product in products:
        try:
            result = analyze_product_flow(product)
            if result:
                all_results[product] = result
        except Exception as e:
            print(f"  Error: {e}")
    
    # 汇总表
    print("\n" + "=" * 80)
    print("  ONBOARDING COMPARISON")
    print("=" * 80)
    print(f"\n{'Product':<35} {'Total':>6} {'Onb Range':>12} {'Paywall':>10} {'Core':>8}")
    print("-" * 80)
    
    for name, r in all_results.items():
        short_name = name.replace("_Analysis", "").replace("_", " ")[:30]
        total = r.get("total_screenshots", 0)
        
        onb = r.get("onboarding", {})
        onb_range = f"{onb.get('start', '?')}-{onb.get('end', '?')}"
        
        paywall = r.get("paywall", {})
        paywall_pos = paywall.get("position", "-")
        
        core = r.get("core_start", "?")
        
        print(f"{short_name:<35} {total:>6} {onb_range:>12} {str(paywall_pos):>10} {str(core):>8}")
    
    # 保存汇总
    summary_path = os.path.join(BASE_DIR, "flow_comparison.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {summary_path}")
    
    return all_results


if __name__ == "__main__":
    analyze_all()


"""
产品流程分析器
=============
给AI看整个产品的截图网格，让它识别Onboarding流程
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import base64
from PIL import Image
import io
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def load_api_key():
    paths = [
        os.path.join(BASE_DIR, "config", "api_keys.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                return data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    return None


def create_thumbnail_grid(screens_dir: str, cols: int = 10, thumb_size: int = 80) -> Image.Image:
    """创建缩略图网格"""
    files = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')],
                   key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    total = len(files)
    rows = (total + cols - 1) // cols
    
    grid_width = cols * thumb_size
    grid_height = rows * thumb_size
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    
    for idx, f in enumerate(files):
        try:
            with Image.open(os.path.join(screens_dir, f)) as img:
                img = img.convert('RGB')
                # 保持比例缩放
                ratio = thumb_size / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                thumb = img.resize(new_size, Image.LANCZOS)
                
                # 计算位置
                row = idx // cols
                col = idx % cols
                x = col * thumb_size + (thumb_size - new_size[0]) // 2
                y = row * thumb_size + (thumb_size - new_size[1]) // 2
                
                grid.paste(thumb, (x, y))
        except:
            pass
    
    return grid, total


def analyze_product_flow(project_name: str):
    """分析产品流程"""
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    
    if not os.path.exists(screens_dir):
        return None
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    # 创建缩略图网格
    print("  Creating thumbnail grid...")
    grid, total = create_thumbnail_grid(screens_dir)
    
    # 转base64
    buffer = io.BytesIO()
    grid.save(buffer, format='JPEG', quality=85)
    grid_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # API调用
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""这是一个App的{total}张截图组成的缩略图网格（从左到右，从上到下排列）。

请分析这个App的用户流程，特别是：

1. **Onboarding流程**（从App启动到进入主界面）
   - 大约在第几张到第几张？（例如：1-35）
   - 包含哪些步骤？（简要列举）

2. **Paywall位置**
   - 在第几张左右？
   - 是否在Onboarding流程中？

3. **Core功能开始**
   - 从第几张开始出现有Tab栏的主界面？

请用JSON格式回答：
{{
  "app_type": "App类型",
  "onboarding": {{
    "start": 1,
    "end": 截止页码,
    "steps": ["步骤1", "步骤2", ...]
  }},
  "paywall": {{
    "position": 页码或null,
    "in_onboarding": true/false
  }},
  "core_start": 开始页码,
  "summary": "一句话总结这个App的引导设计特点"
}}"""
    
    print("  Analyzing with AI...")
    
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': grid_data}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    
    text = response.content[0].text
    
    # 解析JSON
    if '```' in text:
        text = text.split('```')[1] if '```json' in text else text.split('```')[1]
        text = text.replace('json', '').strip()
    
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        result = json.loads(text[json_start:json_end])
    else:
        result = {"error": "Parse failed", "raw": text}
    
    result["project"] = project_name
    result["total_screenshots"] = total
    result["analyzed_at"] = datetime.now().isoformat()
    
    # 打印结果
    if "onboarding" in result:
        onb = result["onboarding"]
        print(f"\n  App Type: {result.get('app_type', 'N/A')}")
        print(f"  Onboarding: #{onb.get('start', '?')} - #{onb.get('end', '?')} ({onb.get('end', 0) - onb.get('start', 0) + 1} screens)")
        print(f"  Steps: {', '.join(onb.get('steps', [])[:5])}...")
        
        paywall = result.get("paywall", {})
        if paywall.get("position"):
            loc = "在Onboarding中" if paywall.get("in_onboarding") else "在Core功能区"
            print(f"  Paywall: #{paywall.get('position')} ({loc})")
        
        print(f"  Core Start: #{result.get('core_start', '?')}")
        print(f"\n  Summary: {result.get('summary', 'N/A')}")
    
    # 保存
    output_path = os.path.join(project_dir, "flow_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def analyze_all():
    """分析所有产品"""
    products = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    all_results = {}
    
    for product in products:
        try:
            result = analyze_product_flow(product)
            if result:
                all_results[product] = result
        except Exception as e:
            print(f"  Error: {e}")
    
    # 汇总表
    print("\n" + "=" * 80)
    print("  ONBOARDING COMPARISON")
    print("=" * 80)
    print(f"\n{'Product':<35} {'Total':>6} {'Onb Range':>12} {'Paywall':>10} {'Core':>8}")
    print("-" * 80)
    
    for name, r in all_results.items():
        short_name = name.replace("_Analysis", "").replace("_", " ")[:30]
        total = r.get("total_screenshots", 0)
        
        onb = r.get("onboarding", {})
        onb_range = f"{onb.get('start', '?')}-{onb.get('end', '?')}"
        
        paywall = r.get("paywall", {})
        paywall_pos = paywall.get("position", "-")
        
        core = r.get("core_start", "?")
        
        print(f"{short_name:<35} {total:>6} {onb_range:>12} {str(paywall_pos):>10} {str(core):>8}")
    
    # 保存汇总
    summary_path = os.path.join(BASE_DIR, "flow_comparison.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {summary_path}")
    
    return all_results


if __name__ == "__main__":
    analyze_all()


"""
产品流程分析器
=============
给AI看整个产品的截图网格，让它识别Onboarding流程
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import base64
from PIL import Image
import io
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def load_api_key():
    paths = [
        os.path.join(BASE_DIR, "config", "api_keys.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                return data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    return None


def create_thumbnail_grid(screens_dir: str, cols: int = 10, thumb_size: int = 80) -> Image.Image:
    """创建缩略图网格"""
    files = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')],
                   key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    total = len(files)
    rows = (total + cols - 1) // cols
    
    grid_width = cols * thumb_size
    grid_height = rows * thumb_size
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    
    for idx, f in enumerate(files):
        try:
            with Image.open(os.path.join(screens_dir, f)) as img:
                img = img.convert('RGB')
                # 保持比例缩放
                ratio = thumb_size / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                thumb = img.resize(new_size, Image.LANCZOS)
                
                # 计算位置
                row = idx // cols
                col = idx % cols
                x = col * thumb_size + (thumb_size - new_size[0]) // 2
                y = row * thumb_size + (thumb_size - new_size[1]) // 2
                
                grid.paste(thumb, (x, y))
        except:
            pass
    
    return grid, total


def analyze_product_flow(project_name: str):
    """分析产品流程"""
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    
    if not os.path.exists(screens_dir):
        return None
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    # 创建缩略图网格
    print("  Creating thumbnail grid...")
    grid, total = create_thumbnail_grid(screens_dir)
    
    # 转base64
    buffer = io.BytesIO()
    grid.save(buffer, format='JPEG', quality=85)
    grid_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # API调用
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""这是一个App的{total}张截图组成的缩略图网格（从左到右，从上到下排列）。

请分析这个App的用户流程，特别是：

1. **Onboarding流程**（从App启动到进入主界面）
   - 大约在第几张到第几张？（例如：1-35）
   - 包含哪些步骤？（简要列举）

2. **Paywall位置**
   - 在第几张左右？
   - 是否在Onboarding流程中？

3. **Core功能开始**
   - 从第几张开始出现有Tab栏的主界面？

请用JSON格式回答：
{{
  "app_type": "App类型",
  "onboarding": {{
    "start": 1,
    "end": 截止页码,
    "steps": ["步骤1", "步骤2", ...]
  }},
  "paywall": {{
    "position": 页码或null,
    "in_onboarding": true/false
  }},
  "core_start": 开始页码,
  "summary": "一句话总结这个App的引导设计特点"
}}"""
    
    print("  Analyzing with AI...")
    
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': grid_data}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    
    text = response.content[0].text
    
    # 解析JSON
    if '```' in text:
        text = text.split('```')[1] if '```json' in text else text.split('```')[1]
        text = text.replace('json', '').strip()
    
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        result = json.loads(text[json_start:json_end])
    else:
        result = {"error": "Parse failed", "raw": text}
    
    result["project"] = project_name
    result["total_screenshots"] = total
    result["analyzed_at"] = datetime.now().isoformat()
    
    # 打印结果
    if "onboarding" in result:
        onb = result["onboarding"]
        print(f"\n  App Type: {result.get('app_type', 'N/A')}")
        print(f"  Onboarding: #{onb.get('start', '?')} - #{onb.get('end', '?')} ({onb.get('end', 0) - onb.get('start', 0) + 1} screens)")
        print(f"  Steps: {', '.join(onb.get('steps', [])[:5])}...")
        
        paywall = result.get("paywall", {})
        if paywall.get("position"):
            loc = "在Onboarding中" if paywall.get("in_onboarding") else "在Core功能区"
            print(f"  Paywall: #{paywall.get('position')} ({loc})")
        
        print(f"  Core Start: #{result.get('core_start', '?')}")
        print(f"\n  Summary: {result.get('summary', 'N/A')}")
    
    # 保存
    output_path = os.path.join(project_dir, "flow_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def analyze_all():
    """分析所有产品"""
    products = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    all_results = {}
    
    for product in products:
        try:
            result = analyze_product_flow(product)
            if result:
                all_results[product] = result
        except Exception as e:
            print(f"  Error: {e}")
    
    # 汇总表
    print("\n" + "=" * 80)
    print("  ONBOARDING COMPARISON")
    print("=" * 80)
    print(f"\n{'Product':<35} {'Total':>6} {'Onb Range':>12} {'Paywall':>10} {'Core':>8}")
    print("-" * 80)
    
    for name, r in all_results.items():
        short_name = name.replace("_Analysis", "").replace("_", " ")[:30]
        total = r.get("total_screenshots", 0)
        
        onb = r.get("onboarding", {})
        onb_range = f"{onb.get('start', '?')}-{onb.get('end', '?')}"
        
        paywall = r.get("paywall", {})
        paywall_pos = paywall.get("position", "-")
        
        core = r.get("core_start", "?")
        
        print(f"{short_name:<35} {total:>6} {onb_range:>12} {str(paywall_pos):>10} {str(core):>8}")
    
    # 保存汇总
    summary_path = os.path.join(BASE_DIR, "flow_comparison.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {summary_path}")
    
    return all_results


if __name__ == "__main__":
    analyze_all()


"""
产品流程分析器
=============
给AI看整个产品的截图网格，让它识别Onboarding流程
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import base64
from PIL import Image
import io
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def load_api_key():
    paths = [
        os.path.join(BASE_DIR, "config", "api_keys.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                return data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    return None


def create_thumbnail_grid(screens_dir: str, cols: int = 10, thumb_size: int = 80) -> Image.Image:
    """创建缩略图网格"""
    files = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')],
                   key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    total = len(files)
    rows = (total + cols - 1) // cols
    
    grid_width = cols * thumb_size
    grid_height = rows * thumb_size
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    
    for idx, f in enumerate(files):
        try:
            with Image.open(os.path.join(screens_dir, f)) as img:
                img = img.convert('RGB')
                # 保持比例缩放
                ratio = thumb_size / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                thumb = img.resize(new_size, Image.LANCZOS)
                
                # 计算位置
                row = idx // cols
                col = idx % cols
                x = col * thumb_size + (thumb_size - new_size[0]) // 2
                y = row * thumb_size + (thumb_size - new_size[1]) // 2
                
                grid.paste(thumb, (x, y))
        except:
            pass
    
    return grid, total


def analyze_product_flow(project_name: str):
    """分析产品流程"""
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    
    if not os.path.exists(screens_dir):
        return None
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    # 创建缩略图网格
    print("  Creating thumbnail grid...")
    grid, total = create_thumbnail_grid(screens_dir)
    
    # 转base64
    buffer = io.BytesIO()
    grid.save(buffer, format='JPEG', quality=85)
    grid_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # API调用
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""这是一个App的{total}张截图组成的缩略图网格（从左到右，从上到下排列）。

请分析这个App的用户流程，特别是：

1. **Onboarding流程**（从App启动到进入主界面）
   - 大约在第几张到第几张？（例如：1-35）
   - 包含哪些步骤？（简要列举）

2. **Paywall位置**
   - 在第几张左右？
   - 是否在Onboarding流程中？

3. **Core功能开始**
   - 从第几张开始出现有Tab栏的主界面？

请用JSON格式回答：
{{
  "app_type": "App类型",
  "onboarding": {{
    "start": 1,
    "end": 截止页码,
    "steps": ["步骤1", "步骤2", ...]
  }},
  "paywall": {{
    "position": 页码或null,
    "in_onboarding": true/false
  }},
  "core_start": 开始页码,
  "summary": "一句话总结这个App的引导设计特点"
}}"""
    
    print("  Analyzing with AI...")
    
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': grid_data}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    
    text = response.content[0].text
    
    # 解析JSON
    if '```' in text:
        text = text.split('```')[1] if '```json' in text else text.split('```')[1]
        text = text.replace('json', '').strip()
    
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        result = json.loads(text[json_start:json_end])
    else:
        result = {"error": "Parse failed", "raw": text}
    
    result["project"] = project_name
    result["total_screenshots"] = total
    result["analyzed_at"] = datetime.now().isoformat()
    
    # 打印结果
    if "onboarding" in result:
        onb = result["onboarding"]
        print(f"\n  App Type: {result.get('app_type', 'N/A')}")
        print(f"  Onboarding: #{onb.get('start', '?')} - #{onb.get('end', '?')} ({onb.get('end', 0) - onb.get('start', 0) + 1} screens)")
        print(f"  Steps: {', '.join(onb.get('steps', [])[:5])}...")
        
        paywall = result.get("paywall", {})
        if paywall.get("position"):
            loc = "在Onboarding中" if paywall.get("in_onboarding") else "在Core功能区"
            print(f"  Paywall: #{paywall.get('position')} ({loc})")
        
        print(f"  Core Start: #{result.get('core_start', '?')}")
        print(f"\n  Summary: {result.get('summary', 'N/A')}")
    
    # 保存
    output_path = os.path.join(project_dir, "flow_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def analyze_all():
    """分析所有产品"""
    products = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    all_results = {}
    
    for product in products:
        try:
            result = analyze_product_flow(product)
            if result:
                all_results[product] = result
        except Exception as e:
            print(f"  Error: {e}")
    
    # 汇总表
    print("\n" + "=" * 80)
    print("  ONBOARDING COMPARISON")
    print("=" * 80)
    print(f"\n{'Product':<35} {'Total':>6} {'Onb Range':>12} {'Paywall':>10} {'Core':>8}")
    print("-" * 80)
    
    for name, r in all_results.items():
        short_name = name.replace("_Analysis", "").replace("_", " ")[:30]
        total = r.get("total_screenshots", 0)
        
        onb = r.get("onboarding", {})
        onb_range = f"{onb.get('start', '?')}-{onb.get('end', '?')}"
        
        paywall = r.get("paywall", {})
        paywall_pos = paywall.get("position", "-")
        
        core = r.get("core_start", "?")
        
        print(f"{short_name:<35} {total:>6} {onb_range:>12} {str(paywall_pos):>10} {str(core):>8}")
    
    # 保存汇总
    summary_path = os.path.join(BASE_DIR, "flow_comparison.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {summary_path}")
    
    return all_results


if __name__ == "__main__":
    analyze_all()



"""
产品流程分析器
=============
给AI看整个产品的截图网格，让它识别Onboarding流程
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import base64
from PIL import Image
import io
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def load_api_key():
    paths = [
        os.path.join(BASE_DIR, "config", "api_keys.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                return data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    return None


def create_thumbnail_grid(screens_dir: str, cols: int = 10, thumb_size: int = 80) -> Image.Image:
    """创建缩略图网格"""
    files = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')],
                   key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    total = len(files)
    rows = (total + cols - 1) // cols
    
    grid_width = cols * thumb_size
    grid_height = rows * thumb_size
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    
    for idx, f in enumerate(files):
        try:
            with Image.open(os.path.join(screens_dir, f)) as img:
                img = img.convert('RGB')
                # 保持比例缩放
                ratio = thumb_size / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                thumb = img.resize(new_size, Image.LANCZOS)
                
                # 计算位置
                row = idx // cols
                col = idx % cols
                x = col * thumb_size + (thumb_size - new_size[0]) // 2
                y = row * thumb_size + (thumb_size - new_size[1]) // 2
                
                grid.paste(thumb, (x, y))
        except:
            pass
    
    return grid, total


def analyze_product_flow(project_name: str):
    """分析产品流程"""
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    
    if not os.path.exists(screens_dir):
        return None
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    # 创建缩略图网格
    print("  Creating thumbnail grid...")
    grid, total = create_thumbnail_grid(screens_dir)
    
    # 转base64
    buffer = io.BytesIO()
    grid.save(buffer, format='JPEG', quality=85)
    grid_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # API调用
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""这是一个App的{total}张截图组成的缩略图网格（从左到右，从上到下排列）。

请分析这个App的用户流程，特别是：

1. **Onboarding流程**（从App启动到进入主界面）
   - 大约在第几张到第几张？（例如：1-35）
   - 包含哪些步骤？（简要列举）

2. **Paywall位置**
   - 在第几张左右？
   - 是否在Onboarding流程中？

3. **Core功能开始**
   - 从第几张开始出现有Tab栏的主界面？

请用JSON格式回答：
{{
  "app_type": "App类型",
  "onboarding": {{
    "start": 1,
    "end": 截止页码,
    "steps": ["步骤1", "步骤2", ...]
  }},
  "paywall": {{
    "position": 页码或null,
    "in_onboarding": true/false
  }},
  "core_start": 开始页码,
  "summary": "一句话总结这个App的引导设计特点"
}}"""
    
    print("  Analyzing with AI...")
    
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': grid_data}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    
    text = response.content[0].text
    
    # 解析JSON
    if '```' in text:
        text = text.split('```')[1] if '```json' in text else text.split('```')[1]
        text = text.replace('json', '').strip()
    
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        result = json.loads(text[json_start:json_end])
    else:
        result = {"error": "Parse failed", "raw": text}
    
    result["project"] = project_name
    result["total_screenshots"] = total
    result["analyzed_at"] = datetime.now().isoformat()
    
    # 打印结果
    if "onboarding" in result:
        onb = result["onboarding"]
        print(f"\n  App Type: {result.get('app_type', 'N/A')}")
        print(f"  Onboarding: #{onb.get('start', '?')} - #{onb.get('end', '?')} ({onb.get('end', 0) - onb.get('start', 0) + 1} screens)")
        print(f"  Steps: {', '.join(onb.get('steps', [])[:5])}...")
        
        paywall = result.get("paywall", {})
        if paywall.get("position"):
            loc = "在Onboarding中" if paywall.get("in_onboarding") else "在Core功能区"
            print(f"  Paywall: #{paywall.get('position')} ({loc})")
        
        print(f"  Core Start: #{result.get('core_start', '?')}")
        print(f"\n  Summary: {result.get('summary', 'N/A')}")
    
    # 保存
    output_path = os.path.join(project_dir, "flow_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def analyze_all():
    """分析所有产品"""
    products = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    all_results = {}
    
    for product in products:
        try:
            result = analyze_product_flow(product)
            if result:
                all_results[product] = result
        except Exception as e:
            print(f"  Error: {e}")
    
    # 汇总表
    print("\n" + "=" * 80)
    print("  ONBOARDING COMPARISON")
    print("=" * 80)
    print(f"\n{'Product':<35} {'Total':>6} {'Onb Range':>12} {'Paywall':>10} {'Core':>8}")
    print("-" * 80)
    
    for name, r in all_results.items():
        short_name = name.replace("_Analysis", "").replace("_", " ")[:30]
        total = r.get("total_screenshots", 0)
        
        onb = r.get("onboarding", {})
        onb_range = f"{onb.get('start', '?')}-{onb.get('end', '?')}"
        
        paywall = r.get("paywall", {})
        paywall_pos = paywall.get("position", "-")
        
        core = r.get("core_start", "?")
        
        print(f"{short_name:<35} {total:>6} {onb_range:>12} {str(paywall_pos):>10} {str(core):>8}")
    
    # 保存汇总
    summary_path = os.path.join(BASE_DIR, "flow_comparison.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {summary_path}")
    
    return all_results


if __name__ == "__main__":
    analyze_all()


"""
产品流程分析器
=============
给AI看整个产品的截图网格，让它识别Onboarding流程
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import base64
from PIL import Image
import io
from datetime import datetime

try:
    import anthropic
except ImportError:
    print("Please install anthropic: pip install anthropic")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def load_api_key():
    paths = [
        os.path.join(BASE_DIR, "config", "api_keys.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r') as f:
                data = json.load(f)
                return data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    return None


def create_thumbnail_grid(screens_dir: str, cols: int = 10, thumb_size: int = 80) -> Image.Image:
    """创建缩略图网格"""
    files = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')],
                   key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    
    total = len(files)
    rows = (total + cols - 1) // cols
    
    grid_width = cols * thumb_size
    grid_height = rows * thumb_size
    
    grid = Image.new('RGB', (grid_width, grid_height), 'white')
    
    for idx, f in enumerate(files):
        try:
            with Image.open(os.path.join(screens_dir, f)) as img:
                img = img.convert('RGB')
                # 保持比例缩放
                ratio = thumb_size / max(img.width, img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                thumb = img.resize(new_size, Image.LANCZOS)
                
                # 计算位置
                row = idx // cols
                col = idx % cols
                x = col * thumb_size + (thumb_size - new_size[0]) // 2
                y = row * thumb_size + (thumb_size - new_size[1]) // 2
                
                grid.paste(thumb, (x, y))
        except:
            pass
    
    return grid, total


def analyze_product_flow(project_name: str):
    """分析产品流程"""
    
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    screens_dir = os.path.join(project_dir, "Screens")
    
    if not os.path.exists(screens_dir):
        return None
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    # 创建缩略图网格
    print("  Creating thumbnail grid...")
    grid, total = create_thumbnail_grid(screens_dir)
    
    # 转base64
    buffer = io.BytesIO()
    grid.save(buffer, format='JPEG', quality=85)
    grid_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # API调用
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = f"""这是一个App的{total}张截图组成的缩略图网格（从左到右，从上到下排列）。

请分析这个App的用户流程，特别是：

1. **Onboarding流程**（从App启动到进入主界面）
   - 大约在第几张到第几张？（例如：1-35）
   - 包含哪些步骤？（简要列举）

2. **Paywall位置**
   - 在第几张左右？
   - 是否在Onboarding流程中？

3. **Core功能开始**
   - 从第几张开始出现有Tab栏的主界面？

请用JSON格式回答：
{{
  "app_type": "App类型",
  "onboarding": {{
    "start": 1,
    "end": 截止页码,
    "steps": ["步骤1", "步骤2", ...]
  }},
  "paywall": {{
    "position": 页码或null,
    "in_onboarding": true/false
  }},
  "core_start": 开始页码,
  "summary": "一句话总结这个App的引导设计特点"
}}"""
    
    print("  Analyzing with AI...")
    
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1000,
        messages=[{
            'role': 'user',
            'content': [
                {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': grid_data}},
                {'type': 'text', 'text': prompt}
            ]
        }]
    )
    
    text = response.content[0].text
    
    # 解析JSON
    if '```' in text:
        text = text.split('```')[1] if '```json' in text else text.split('```')[1]
        text = text.replace('json', '').strip()
    
    json_start = text.find('{')
    json_end = text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        result = json.loads(text[json_start:json_end])
    else:
        result = {"error": "Parse failed", "raw": text}
    
    result["project"] = project_name
    result["total_screenshots"] = total
    result["analyzed_at"] = datetime.now().isoformat()
    
    # 打印结果
    if "onboarding" in result:
        onb = result["onboarding"]
        print(f"\n  App Type: {result.get('app_type', 'N/A')}")
        print(f"  Onboarding: #{onb.get('start', '?')} - #{onb.get('end', '?')} ({onb.get('end', 0) - onb.get('start', 0) + 1} screens)")
        print(f"  Steps: {', '.join(onb.get('steps', [])[:5])}...")
        
        paywall = result.get("paywall", {})
        if paywall.get("position"):
            loc = "在Onboarding中" if paywall.get("in_onboarding") else "在Core功能区"
            print(f"  Paywall: #{paywall.get('position')} ({loc})")
        
        print(f"  Core Start: #{result.get('core_start', '?')}")
        print(f"\n  Summary: {result.get('summary', 'N/A')}")
    
    # 保存
    output_path = os.path.join(project_dir, "flow_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    return result


def analyze_all():
    """分析所有产品"""
    products = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    all_results = {}
    
    for product in products:
        try:
            result = analyze_product_flow(product)
            if result:
                all_results[product] = result
        except Exception as e:
            print(f"  Error: {e}")
    
    # 汇总表
    print("\n" + "=" * 80)
    print("  ONBOARDING COMPARISON")
    print("=" * 80)
    print(f"\n{'Product':<35} {'Total':>6} {'Onb Range':>12} {'Paywall':>10} {'Core':>8}")
    print("-" * 80)
    
    for name, r in all_results.items():
        short_name = name.replace("_Analysis", "").replace("_", " ")[:30]
        total = r.get("total_screenshots", 0)
        
        onb = r.get("onboarding", {})
        onb_range = f"{onb.get('start', '?')}-{onb.get('end', '?')}"
        
        paywall = r.get("paywall", {})
        paywall_pos = paywall.get("position", "-")
        
        core = r.get("core_start", "?")
        
        print(f"{short_name:<35} {total:>6} {onb_range:>12} {str(paywall_pos):>10} {str(core):>8}")
    
    # 保存汇总
    summary_path = os.path.join(BASE_DIR, "flow_comparison.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved to: {summary_path}")
    
    return all_results


if __name__ == "__main__":
    analyze_all()


















