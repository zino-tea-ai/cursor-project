#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将 ai_analysis.json 转换为 structured_descriptions.json
供前端使用的结构化描述文件
"""

import os
import json
import sys

# 页面类型映射 - 用于生成更好的命名
SCREEN_TYPE_NAMES = {
    "Launch": {"cn": "启动页", "en": "Launch Screen"},
    "Welcome": {"cn": "欢迎页", "en": "Welcome"},
    "Onboarding": {"cn": "引导流程", "en": "Onboarding"},
    "Registration": {"cn": "注册页", "en": "Registration"},
    "Login": {"cn": "登录页", "en": "Login"},
    "Goal": {"cn": "目标设置", "en": "Goal Setting"},
    "Profile": {"cn": "个人资料", "en": "Profile"},
    "Paywall": {"cn": "付费墙", "en": "Paywall"},
    "Home": {"cn": "首页", "en": "Home"},
    "Dashboard": {"cn": "仪表盘", "en": "Dashboard"},
    "Settings": {"cn": "设置", "en": "Settings"},
    "Notification": {"cn": "通知", "en": "Notification"},
    "Search": {"cn": "搜索", "en": "Search"},
    "Detail": {"cn": "详情页", "en": "Detail"},
    "List": {"cn": "列表页", "en": "List"},
    "Modal": {"cn": "弹窗", "en": "Modal"},
    "Loading": {"cn": "加载页", "en": "Loading"},
    "Error": {"cn": "错误页", "en": "Error"},
    "Success": {"cn": "成功页", "en": "Success"},
    "Empty": {"cn": "空状态", "en": "Empty State"},
    "Logging": {"cn": "记录页", "en": "Logging"},
    "Progress": {"cn": "进度页", "en": "Progress"},
    "Activity": {"cn": "活动页", "en": "Activity"},
    "Social": {"cn": "社交", "en": "Social"},
    "Content": {"cn": "内容页", "en": "Content"},
}


def convert_analysis_to_structured(ai_result):
    """将单个AI分析结果转换为结构化描述 - 优先使用AI返回的结构化数据"""
    
    screen_type = ai_result.get("screen_type", "Unknown")
    sub_type = ai_result.get("sub_type", "")
    confidence = ai_result.get("confidence", 0.8)
    
    # 获取类型名称（用于fallback）
    type_names = SCREEN_TYPE_NAMES.get(screen_type, {"cn": screen_type, "en": screen_type})
    
    # === 优先使用AI返回的结构化数据 ===
    
    # 1. naming - 优先使用AI返回的
    ai_naming = ai_result.get("naming", {})
    if isinstance(ai_naming, dict) and ai_naming.get("cn"):
        naming = ai_naming
    else:
        # Fallback: 从screen_type生成
        naming = {"cn": type_names['cn'], "en": type_names['en']}
        if sub_type:
            sub_display = sub_type.replace("_", " ").title()
            naming["cn"] = f"{type_names['cn']} - {sub_display}"
            naming["en"] = f"{type_names['en']} - {sub_display}"
    
    # 2. core_function - 优先使用AI返回的
    ai_core = ai_result.get("core_function", {})
    if isinstance(ai_core, dict) and ai_core.get("cn"):
        core_function = ai_core
    else:
        # Fallback: 使用description
        core_function = {
            "cn": ai_result.get("description_cn", ""),
            "en": ai_result.get("description_en", "")
        }
    
    # 3. design_highlights - 优先使用AI返回的
    ai_highlights = ai_result.get("design_highlights", [])
    if isinstance(ai_highlights, list) and len(ai_highlights) > 0:
        design_highlights = ai_highlights
    else:
        # Fallback: 从ui_elements生成
        ui_elements = ai_result.get("ui_elements", [])
        design_highlights = []
        if ui_elements:
            visual_elements = [e for e in ui_elements if any(k in e.lower() for k in ['image', 'icon', 'logo', 'color', 'background', 'chart', 'graph'])]
            if visual_elements:
                design_highlights.append({
                    "category": "visual",
                    "cn": f"包含{len(visual_elements)}个视觉元素: {', '.join(visual_elements[:3])}",
                    "en": f"Contains {len(visual_elements)} visual elements: {', '.join(visual_elements[:3])}"
                })
            interactive_elements = [e for e in ui_elements if any(k in e.lower() for k in ['button', 'input', 'toggle', 'slider', 'picker', 'selector'])]
            if interactive_elements:
                design_highlights.append({
                    "category": "interaction",
                    "cn": f"交互组件: {', '.join(interactive_elements[:3])}",
                    "en": f"Interactive components: {', '.join(interactive_elements[:3])}"
                })
        if not design_highlights:
            design_highlights.append({"category": "general", "cn": "标准页面布局", "en": "Standard page layout"})
    
    # 4. product_insight - 优先使用AI返回的
    ai_insight = ai_result.get("product_insight", {})
    if isinstance(ai_insight, dict) and ai_insight.get("cn"):
        product_insight = ai_insight
    else:
        # Fallback: 自动生成
        desc_cn = ai_result.get("description_cn", "")
        desc_en = ai_result.get("description_en", "")
        product_insight = {
            "cn": f"{screen_type}类型页面，{desc_cn[:30]}..." if len(desc_cn) > 30 else desc_cn,
            "en": f"{screen_type} page type. {desc_en[:50]}..." if len(desc_en) > 50 else desc_en
        }
    
    # 5. tags - 优先使用AI返回的
    ai_tags = ai_result.get("tags", [])
    if isinstance(ai_tags, list) and len(ai_tags) > 0:
        tags = ai_tags
    else:
        # Fallback: 从keywords生成
        keywords = ai_result.get("keywords_found", [])
        tags = [{"cn": type_names["cn"], "en": type_names["en"]}]
        for kw in keywords[:5]:
            if len(kw) < 20:
                tags.append({"cn": kw, "en": kw})
    
    return {
        "screen_type": screen_type,
        "naming": naming,
        "core_function": core_function,
        "design_highlights": design_highlights,
        "product_insight": product_insight,
        "tags": tags,
        "confidence": confidence
    }


def process_project(project_path):
    """处理单个项目"""
    ai_analysis_file = os.path.join(project_path, "ai_analysis.json")
    structured_file = os.path.join(project_path, "structured_descriptions.json")
    
    if not os.path.exists(ai_analysis_file):
        print(f"  [SKIP] No ai_analysis.json found")
        return False
    
    # 读取AI分析结果
    with open(ai_analysis_file, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    if not results:
        print(f"  [SKIP] No results in ai_analysis.json")
        return False
    
    # 转换每个截图的分析结果
    structured = {}
    for filename, ai_result in results.items():
        structured[filename] = convert_analysis_to_structured(ai_result)
    
    # 写入结构化描述文件
    with open(structured_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Generated {len(structured)} structured descriptions")
    return True


def main():
    # 获取项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(os.path.dirname(script_dir), "projects")
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    print("=" * 60)
    print("Generating structured_descriptions.json for all projects")
    print("=" * 60)
    
    # 如果指定了项目名，只处理该项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
        else:
            print(f"Project not found: {project_name}")
        return
    
    # 处理所有项目
    for project_name in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_name)
        if os.path.isdir(project_path) and project_name != "null":
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
将 ai_analysis.json 转换为 structured_descriptions.json
供前端使用的结构化描述文件
"""

import os
import json
import sys

# 页面类型映射 - 用于生成更好的命名
SCREEN_TYPE_NAMES = {
    "Launch": {"cn": "启动页", "en": "Launch Screen"},
    "Welcome": {"cn": "欢迎页", "en": "Welcome"},
    "Onboarding": {"cn": "引导流程", "en": "Onboarding"},
    "Registration": {"cn": "注册页", "en": "Registration"},
    "Login": {"cn": "登录页", "en": "Login"},
    "Goal": {"cn": "目标设置", "en": "Goal Setting"},
    "Profile": {"cn": "个人资料", "en": "Profile"},
    "Paywall": {"cn": "付费墙", "en": "Paywall"},
    "Home": {"cn": "首页", "en": "Home"},
    "Dashboard": {"cn": "仪表盘", "en": "Dashboard"},
    "Settings": {"cn": "设置", "en": "Settings"},
    "Notification": {"cn": "通知", "en": "Notification"},
    "Search": {"cn": "搜索", "en": "Search"},
    "Detail": {"cn": "详情页", "en": "Detail"},
    "List": {"cn": "列表页", "en": "List"},
    "Modal": {"cn": "弹窗", "en": "Modal"},
    "Loading": {"cn": "加载页", "en": "Loading"},
    "Error": {"cn": "错误页", "en": "Error"},
    "Success": {"cn": "成功页", "en": "Success"},
    "Empty": {"cn": "空状态", "en": "Empty State"},
    "Logging": {"cn": "记录页", "en": "Logging"},
    "Progress": {"cn": "进度页", "en": "Progress"},
    "Activity": {"cn": "活动页", "en": "Activity"},
    "Social": {"cn": "社交", "en": "Social"},
    "Content": {"cn": "内容页", "en": "Content"},
}


def convert_analysis_to_structured(ai_result):
    """将单个AI分析结果转换为结构化描述 - 优先使用AI返回的结构化数据"""
    
    screen_type = ai_result.get("screen_type", "Unknown")
    sub_type = ai_result.get("sub_type", "")
    confidence = ai_result.get("confidence", 0.8)
    
    # 获取类型名称（用于fallback）
    type_names = SCREEN_TYPE_NAMES.get(screen_type, {"cn": screen_type, "en": screen_type})
    
    # === 优先使用AI返回的结构化数据 ===
    
    # 1. naming - 优先使用AI返回的
    ai_naming = ai_result.get("naming", {})
    if isinstance(ai_naming, dict) and ai_naming.get("cn"):
        naming = ai_naming
    else:
        # Fallback: 从screen_type生成
        naming = {"cn": type_names['cn'], "en": type_names['en']}
        if sub_type:
            sub_display = sub_type.replace("_", " ").title()
            naming["cn"] = f"{type_names['cn']} - {sub_display}"
            naming["en"] = f"{type_names['en']} - {sub_display}"
    
    # 2. core_function - 优先使用AI返回的
    ai_core = ai_result.get("core_function", {})
    if isinstance(ai_core, dict) and ai_core.get("cn"):
        core_function = ai_core
    else:
        # Fallback: 使用description
        core_function = {
            "cn": ai_result.get("description_cn", ""),
            "en": ai_result.get("description_en", "")
        }
    
    # 3. design_highlights - 优先使用AI返回的
    ai_highlights = ai_result.get("design_highlights", [])
    if isinstance(ai_highlights, list) and len(ai_highlights) > 0:
        design_highlights = ai_highlights
    else:
        # Fallback: 从ui_elements生成
        ui_elements = ai_result.get("ui_elements", [])
        design_highlights = []
        if ui_elements:
            visual_elements = [e for e in ui_elements if any(k in e.lower() for k in ['image', 'icon', 'logo', 'color', 'background', 'chart', 'graph'])]
            if visual_elements:
                design_highlights.append({
                    "category": "visual",
                    "cn": f"包含{len(visual_elements)}个视觉元素: {', '.join(visual_elements[:3])}",
                    "en": f"Contains {len(visual_elements)} visual elements: {', '.join(visual_elements[:3])}"
                })
            interactive_elements = [e for e in ui_elements if any(k in e.lower() for k in ['button', 'input', 'toggle', 'slider', 'picker', 'selector'])]
            if interactive_elements:
                design_highlights.append({
                    "category": "interaction",
                    "cn": f"交互组件: {', '.join(interactive_elements[:3])}",
                    "en": f"Interactive components: {', '.join(interactive_elements[:3])}"
                })
        if not design_highlights:
            design_highlights.append({"category": "general", "cn": "标准页面布局", "en": "Standard page layout"})
    
    # 4. product_insight - 优先使用AI返回的
    ai_insight = ai_result.get("product_insight", {})
    if isinstance(ai_insight, dict) and ai_insight.get("cn"):
        product_insight = ai_insight
    else:
        # Fallback: 自动生成
        desc_cn = ai_result.get("description_cn", "")
        desc_en = ai_result.get("description_en", "")
        product_insight = {
            "cn": f"{screen_type}类型页面，{desc_cn[:30]}..." if len(desc_cn) > 30 else desc_cn,
            "en": f"{screen_type} page type. {desc_en[:50]}..." if len(desc_en) > 50 else desc_en
        }
    
    # 5. tags - 优先使用AI返回的
    ai_tags = ai_result.get("tags", [])
    if isinstance(ai_tags, list) and len(ai_tags) > 0:
        tags = ai_tags
    else:
        # Fallback: 从keywords生成
        keywords = ai_result.get("keywords_found", [])
        tags = [{"cn": type_names["cn"], "en": type_names["en"]}]
        for kw in keywords[:5]:
            if len(kw) < 20:
                tags.append({"cn": kw, "en": kw})
    
    return {
        "screen_type": screen_type,
        "naming": naming,
        "core_function": core_function,
        "design_highlights": design_highlights,
        "product_insight": product_insight,
        "tags": tags,
        "confidence": confidence
    }


def process_project(project_path):
    """处理单个项目"""
    ai_analysis_file = os.path.join(project_path, "ai_analysis.json")
    structured_file = os.path.join(project_path, "structured_descriptions.json")
    
    if not os.path.exists(ai_analysis_file):
        print(f"  [SKIP] No ai_analysis.json found")
        return False
    
    # 读取AI分析结果
    with open(ai_analysis_file, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    if not results:
        print(f"  [SKIP] No results in ai_analysis.json")
        return False
    
    # 转换每个截图的分析结果
    structured = {}
    for filename, ai_result in results.items():
        structured[filename] = convert_analysis_to_structured(ai_result)
    
    # 写入结构化描述文件
    with open(structured_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Generated {len(structured)} structured descriptions")
    return True


def main():
    # 获取项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(os.path.dirname(script_dir), "projects")
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    print("=" * 60)
    print("Generating structured_descriptions.json for all projects")
    print("=" * 60)
    
    # 如果指定了项目名，只处理该项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
        else:
            print(f"Project not found: {project_name}")
        return
    
    # 处理所有项目
    for project_name in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_name)
        if os.path.isdir(project_path) and project_name != "null":
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
将 ai_analysis.json 转换为 structured_descriptions.json
供前端使用的结构化描述文件
"""

import os
import json
import sys

# 页面类型映射 - 用于生成更好的命名
SCREEN_TYPE_NAMES = {
    "Launch": {"cn": "启动页", "en": "Launch Screen"},
    "Welcome": {"cn": "欢迎页", "en": "Welcome"},
    "Onboarding": {"cn": "引导流程", "en": "Onboarding"},
    "Registration": {"cn": "注册页", "en": "Registration"},
    "Login": {"cn": "登录页", "en": "Login"},
    "Goal": {"cn": "目标设置", "en": "Goal Setting"},
    "Profile": {"cn": "个人资料", "en": "Profile"},
    "Paywall": {"cn": "付费墙", "en": "Paywall"},
    "Home": {"cn": "首页", "en": "Home"},
    "Dashboard": {"cn": "仪表盘", "en": "Dashboard"},
    "Settings": {"cn": "设置", "en": "Settings"},
    "Notification": {"cn": "通知", "en": "Notification"},
    "Search": {"cn": "搜索", "en": "Search"},
    "Detail": {"cn": "详情页", "en": "Detail"},
    "List": {"cn": "列表页", "en": "List"},
    "Modal": {"cn": "弹窗", "en": "Modal"},
    "Loading": {"cn": "加载页", "en": "Loading"},
    "Error": {"cn": "错误页", "en": "Error"},
    "Success": {"cn": "成功页", "en": "Success"},
    "Empty": {"cn": "空状态", "en": "Empty State"},
    "Logging": {"cn": "记录页", "en": "Logging"},
    "Progress": {"cn": "进度页", "en": "Progress"},
    "Activity": {"cn": "活动页", "en": "Activity"},
    "Social": {"cn": "社交", "en": "Social"},
    "Content": {"cn": "内容页", "en": "Content"},
}


def convert_analysis_to_structured(ai_result):
    """将单个AI分析结果转换为结构化描述 - 优先使用AI返回的结构化数据"""
    
    screen_type = ai_result.get("screen_type", "Unknown")
    sub_type = ai_result.get("sub_type", "")
    confidence = ai_result.get("confidence", 0.8)
    
    # 获取类型名称（用于fallback）
    type_names = SCREEN_TYPE_NAMES.get(screen_type, {"cn": screen_type, "en": screen_type})
    
    # === 优先使用AI返回的结构化数据 ===
    
    # 1. naming - 优先使用AI返回的
    ai_naming = ai_result.get("naming", {})
    if isinstance(ai_naming, dict) and ai_naming.get("cn"):
        naming = ai_naming
    else:
        # Fallback: 从screen_type生成
        naming = {"cn": type_names['cn'], "en": type_names['en']}
        if sub_type:
            sub_display = sub_type.replace("_", " ").title()
            naming["cn"] = f"{type_names['cn']} - {sub_display}"
            naming["en"] = f"{type_names['en']} - {sub_display}"
    
    # 2. core_function - 优先使用AI返回的
    ai_core = ai_result.get("core_function", {})
    if isinstance(ai_core, dict) and ai_core.get("cn"):
        core_function = ai_core
    else:
        # Fallback: 使用description
        core_function = {
            "cn": ai_result.get("description_cn", ""),
            "en": ai_result.get("description_en", "")
        }
    
    # 3. design_highlights - 优先使用AI返回的
    ai_highlights = ai_result.get("design_highlights", [])
    if isinstance(ai_highlights, list) and len(ai_highlights) > 0:
        design_highlights = ai_highlights
    else:
        # Fallback: 从ui_elements生成
        ui_elements = ai_result.get("ui_elements", [])
        design_highlights = []
        if ui_elements:
            visual_elements = [e for e in ui_elements if any(k in e.lower() for k in ['image', 'icon', 'logo', 'color', 'background', 'chart', 'graph'])]
            if visual_elements:
                design_highlights.append({
                    "category": "visual",
                    "cn": f"包含{len(visual_elements)}个视觉元素: {', '.join(visual_elements[:3])}",
                    "en": f"Contains {len(visual_elements)} visual elements: {', '.join(visual_elements[:3])}"
                })
            interactive_elements = [e for e in ui_elements if any(k in e.lower() for k in ['button', 'input', 'toggle', 'slider', 'picker', 'selector'])]
            if interactive_elements:
                design_highlights.append({
                    "category": "interaction",
                    "cn": f"交互组件: {', '.join(interactive_elements[:3])}",
                    "en": f"Interactive components: {', '.join(interactive_elements[:3])}"
                })
        if not design_highlights:
            design_highlights.append({"category": "general", "cn": "标准页面布局", "en": "Standard page layout"})
    
    # 4. product_insight - 优先使用AI返回的
    ai_insight = ai_result.get("product_insight", {})
    if isinstance(ai_insight, dict) and ai_insight.get("cn"):
        product_insight = ai_insight
    else:
        # Fallback: 自动生成
        desc_cn = ai_result.get("description_cn", "")
        desc_en = ai_result.get("description_en", "")
        product_insight = {
            "cn": f"{screen_type}类型页面，{desc_cn[:30]}..." if len(desc_cn) > 30 else desc_cn,
            "en": f"{screen_type} page type. {desc_en[:50]}..." if len(desc_en) > 50 else desc_en
        }
    
    # 5. tags - 优先使用AI返回的
    ai_tags = ai_result.get("tags", [])
    if isinstance(ai_tags, list) and len(ai_tags) > 0:
        tags = ai_tags
    else:
        # Fallback: 从keywords生成
        keywords = ai_result.get("keywords_found", [])
        tags = [{"cn": type_names["cn"], "en": type_names["en"]}]
        for kw in keywords[:5]:
            if len(kw) < 20:
                tags.append({"cn": kw, "en": kw})
    
    return {
        "screen_type": screen_type,
        "naming": naming,
        "core_function": core_function,
        "design_highlights": design_highlights,
        "product_insight": product_insight,
        "tags": tags,
        "confidence": confidence
    }


def process_project(project_path):
    """处理单个项目"""
    ai_analysis_file = os.path.join(project_path, "ai_analysis.json")
    structured_file = os.path.join(project_path, "structured_descriptions.json")
    
    if not os.path.exists(ai_analysis_file):
        print(f"  [SKIP] No ai_analysis.json found")
        return False
    
    # 读取AI分析结果
    with open(ai_analysis_file, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    if not results:
        print(f"  [SKIP] No results in ai_analysis.json")
        return False
    
    # 转换每个截图的分析结果
    structured = {}
    for filename, ai_result in results.items():
        structured[filename] = convert_analysis_to_structured(ai_result)
    
    # 写入结构化描述文件
    with open(structured_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Generated {len(structured)} structured descriptions")
    return True


def main():
    # 获取项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(os.path.dirname(script_dir), "projects")
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    print("=" * 60)
    print("Generating structured_descriptions.json for all projects")
    print("=" * 60)
    
    # 如果指定了项目名，只处理该项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
        else:
            print(f"Project not found: {project_name}")
        return
    
    # 处理所有项目
    for project_name in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_name)
        if os.path.isdir(project_path) and project_name != "null":
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
将 ai_analysis.json 转换为 structured_descriptions.json
供前端使用的结构化描述文件
"""

import os
import json
import sys

# 页面类型映射 - 用于生成更好的命名
SCREEN_TYPE_NAMES = {
    "Launch": {"cn": "启动页", "en": "Launch Screen"},
    "Welcome": {"cn": "欢迎页", "en": "Welcome"},
    "Onboarding": {"cn": "引导流程", "en": "Onboarding"},
    "Registration": {"cn": "注册页", "en": "Registration"},
    "Login": {"cn": "登录页", "en": "Login"},
    "Goal": {"cn": "目标设置", "en": "Goal Setting"},
    "Profile": {"cn": "个人资料", "en": "Profile"},
    "Paywall": {"cn": "付费墙", "en": "Paywall"},
    "Home": {"cn": "首页", "en": "Home"},
    "Dashboard": {"cn": "仪表盘", "en": "Dashboard"},
    "Settings": {"cn": "设置", "en": "Settings"},
    "Notification": {"cn": "通知", "en": "Notification"},
    "Search": {"cn": "搜索", "en": "Search"},
    "Detail": {"cn": "详情页", "en": "Detail"},
    "List": {"cn": "列表页", "en": "List"},
    "Modal": {"cn": "弹窗", "en": "Modal"},
    "Loading": {"cn": "加载页", "en": "Loading"},
    "Error": {"cn": "错误页", "en": "Error"},
    "Success": {"cn": "成功页", "en": "Success"},
    "Empty": {"cn": "空状态", "en": "Empty State"},
    "Logging": {"cn": "记录页", "en": "Logging"},
    "Progress": {"cn": "进度页", "en": "Progress"},
    "Activity": {"cn": "活动页", "en": "Activity"},
    "Social": {"cn": "社交", "en": "Social"},
    "Content": {"cn": "内容页", "en": "Content"},
}


def convert_analysis_to_structured(ai_result):
    """将单个AI分析结果转换为结构化描述 - 优先使用AI返回的结构化数据"""
    
    screen_type = ai_result.get("screen_type", "Unknown")
    sub_type = ai_result.get("sub_type", "")
    confidence = ai_result.get("confidence", 0.8)
    
    # 获取类型名称（用于fallback）
    type_names = SCREEN_TYPE_NAMES.get(screen_type, {"cn": screen_type, "en": screen_type})
    
    # === 优先使用AI返回的结构化数据 ===
    
    # 1. naming - 优先使用AI返回的
    ai_naming = ai_result.get("naming", {})
    if isinstance(ai_naming, dict) and ai_naming.get("cn"):
        naming = ai_naming
    else:
        # Fallback: 从screen_type生成
        naming = {"cn": type_names['cn'], "en": type_names['en']}
        if sub_type:
            sub_display = sub_type.replace("_", " ").title()
            naming["cn"] = f"{type_names['cn']} - {sub_display}"
            naming["en"] = f"{type_names['en']} - {sub_display}"
    
    # 2. core_function - 优先使用AI返回的
    ai_core = ai_result.get("core_function", {})
    if isinstance(ai_core, dict) and ai_core.get("cn"):
        core_function = ai_core
    else:
        # Fallback: 使用description
        core_function = {
            "cn": ai_result.get("description_cn", ""),
            "en": ai_result.get("description_en", "")
        }
    
    # 3. design_highlights - 优先使用AI返回的
    ai_highlights = ai_result.get("design_highlights", [])
    if isinstance(ai_highlights, list) and len(ai_highlights) > 0:
        design_highlights = ai_highlights
    else:
        # Fallback: 从ui_elements生成
        ui_elements = ai_result.get("ui_elements", [])
        design_highlights = []
        if ui_elements:
            visual_elements = [e for e in ui_elements if any(k in e.lower() for k in ['image', 'icon', 'logo', 'color', 'background', 'chart', 'graph'])]
            if visual_elements:
                design_highlights.append({
                    "category": "visual",
                    "cn": f"包含{len(visual_elements)}个视觉元素: {', '.join(visual_elements[:3])}",
                    "en": f"Contains {len(visual_elements)} visual elements: {', '.join(visual_elements[:3])}"
                })
            interactive_elements = [e for e in ui_elements if any(k in e.lower() for k in ['button', 'input', 'toggle', 'slider', 'picker', 'selector'])]
            if interactive_elements:
                design_highlights.append({
                    "category": "interaction",
                    "cn": f"交互组件: {', '.join(interactive_elements[:3])}",
                    "en": f"Interactive components: {', '.join(interactive_elements[:3])}"
                })
        if not design_highlights:
            design_highlights.append({"category": "general", "cn": "标准页面布局", "en": "Standard page layout"})
    
    # 4. product_insight - 优先使用AI返回的
    ai_insight = ai_result.get("product_insight", {})
    if isinstance(ai_insight, dict) and ai_insight.get("cn"):
        product_insight = ai_insight
    else:
        # Fallback: 自动生成
        desc_cn = ai_result.get("description_cn", "")
        desc_en = ai_result.get("description_en", "")
        product_insight = {
            "cn": f"{screen_type}类型页面，{desc_cn[:30]}..." if len(desc_cn) > 30 else desc_cn,
            "en": f"{screen_type} page type. {desc_en[:50]}..." if len(desc_en) > 50 else desc_en
        }
    
    # 5. tags - 优先使用AI返回的
    ai_tags = ai_result.get("tags", [])
    if isinstance(ai_tags, list) and len(ai_tags) > 0:
        tags = ai_tags
    else:
        # Fallback: 从keywords生成
        keywords = ai_result.get("keywords_found", [])
        tags = [{"cn": type_names["cn"], "en": type_names["en"]}]
        for kw in keywords[:5]:
            if len(kw) < 20:
                tags.append({"cn": kw, "en": kw})
    
    return {
        "screen_type": screen_type,
        "naming": naming,
        "core_function": core_function,
        "design_highlights": design_highlights,
        "product_insight": product_insight,
        "tags": tags,
        "confidence": confidence
    }


def process_project(project_path):
    """处理单个项目"""
    ai_analysis_file = os.path.join(project_path, "ai_analysis.json")
    structured_file = os.path.join(project_path, "structured_descriptions.json")
    
    if not os.path.exists(ai_analysis_file):
        print(f"  [SKIP] No ai_analysis.json found")
        return False
    
    # 读取AI分析结果
    with open(ai_analysis_file, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    if not results:
        print(f"  [SKIP] No results in ai_analysis.json")
        return False
    
    # 转换每个截图的分析结果
    structured = {}
    for filename, ai_result in results.items():
        structured[filename] = convert_analysis_to_structured(ai_result)
    
    # 写入结构化描述文件
    with open(structured_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Generated {len(structured)} structured descriptions")
    return True


def main():
    # 获取项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(os.path.dirname(script_dir), "projects")
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    print("=" * 60)
    print("Generating structured_descriptions.json for all projects")
    print("=" * 60)
    
    # 如果指定了项目名，只处理该项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
        else:
            print(f"Project not found: {project_name}")
        return
    
    # 处理所有项目
    for project_name in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_name)
        if os.path.isdir(project_path) and project_name != "null":
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
将 ai_analysis.json 转换为 structured_descriptions.json
供前端使用的结构化描述文件
"""

import os
import json
import sys

# 页面类型映射 - 用于生成更好的命名
SCREEN_TYPE_NAMES = {
    "Launch": {"cn": "启动页", "en": "Launch Screen"},
    "Welcome": {"cn": "欢迎页", "en": "Welcome"},
    "Onboarding": {"cn": "引导流程", "en": "Onboarding"},
    "Registration": {"cn": "注册页", "en": "Registration"},
    "Login": {"cn": "登录页", "en": "Login"},
    "Goal": {"cn": "目标设置", "en": "Goal Setting"},
    "Profile": {"cn": "个人资料", "en": "Profile"},
    "Paywall": {"cn": "付费墙", "en": "Paywall"},
    "Home": {"cn": "首页", "en": "Home"},
    "Dashboard": {"cn": "仪表盘", "en": "Dashboard"},
    "Settings": {"cn": "设置", "en": "Settings"},
    "Notification": {"cn": "通知", "en": "Notification"},
    "Search": {"cn": "搜索", "en": "Search"},
    "Detail": {"cn": "详情页", "en": "Detail"},
    "List": {"cn": "列表页", "en": "List"},
    "Modal": {"cn": "弹窗", "en": "Modal"},
    "Loading": {"cn": "加载页", "en": "Loading"},
    "Error": {"cn": "错误页", "en": "Error"},
    "Success": {"cn": "成功页", "en": "Success"},
    "Empty": {"cn": "空状态", "en": "Empty State"},
    "Logging": {"cn": "记录页", "en": "Logging"},
    "Progress": {"cn": "进度页", "en": "Progress"},
    "Activity": {"cn": "活动页", "en": "Activity"},
    "Social": {"cn": "社交", "en": "Social"},
    "Content": {"cn": "内容页", "en": "Content"},
}


def convert_analysis_to_structured(ai_result):
    """将单个AI分析结果转换为结构化描述 - 优先使用AI返回的结构化数据"""
    
    screen_type = ai_result.get("screen_type", "Unknown")
    sub_type = ai_result.get("sub_type", "")
    confidence = ai_result.get("confidence", 0.8)
    
    # 获取类型名称（用于fallback）
    type_names = SCREEN_TYPE_NAMES.get(screen_type, {"cn": screen_type, "en": screen_type})
    
    # === 优先使用AI返回的结构化数据 ===
    
    # 1. naming - 优先使用AI返回的
    ai_naming = ai_result.get("naming", {})
    if isinstance(ai_naming, dict) and ai_naming.get("cn"):
        naming = ai_naming
    else:
        # Fallback: 从screen_type生成
        naming = {"cn": type_names['cn'], "en": type_names['en']}
        if sub_type:
            sub_display = sub_type.replace("_", " ").title()
            naming["cn"] = f"{type_names['cn']} - {sub_display}"
            naming["en"] = f"{type_names['en']} - {sub_display}"
    
    # 2. core_function - 优先使用AI返回的
    ai_core = ai_result.get("core_function", {})
    if isinstance(ai_core, dict) and ai_core.get("cn"):
        core_function = ai_core
    else:
        # Fallback: 使用description
        core_function = {
            "cn": ai_result.get("description_cn", ""),
            "en": ai_result.get("description_en", "")
        }
    
    # 3. design_highlights - 优先使用AI返回的
    ai_highlights = ai_result.get("design_highlights", [])
    if isinstance(ai_highlights, list) and len(ai_highlights) > 0:
        design_highlights = ai_highlights
    else:
        # Fallback: 从ui_elements生成
        ui_elements = ai_result.get("ui_elements", [])
        design_highlights = []
        if ui_elements:
            visual_elements = [e for e in ui_elements if any(k in e.lower() for k in ['image', 'icon', 'logo', 'color', 'background', 'chart', 'graph'])]
            if visual_elements:
                design_highlights.append({
                    "category": "visual",
                    "cn": f"包含{len(visual_elements)}个视觉元素: {', '.join(visual_elements[:3])}",
                    "en": f"Contains {len(visual_elements)} visual elements: {', '.join(visual_elements[:3])}"
                })
            interactive_elements = [e for e in ui_elements if any(k in e.lower() for k in ['button', 'input', 'toggle', 'slider', 'picker', 'selector'])]
            if interactive_elements:
                design_highlights.append({
                    "category": "interaction",
                    "cn": f"交互组件: {', '.join(interactive_elements[:3])}",
                    "en": f"Interactive components: {', '.join(interactive_elements[:3])}"
                })
        if not design_highlights:
            design_highlights.append({"category": "general", "cn": "标准页面布局", "en": "Standard page layout"})
    
    # 4. product_insight - 优先使用AI返回的
    ai_insight = ai_result.get("product_insight", {})
    if isinstance(ai_insight, dict) and ai_insight.get("cn"):
        product_insight = ai_insight
    else:
        # Fallback: 自动生成
        desc_cn = ai_result.get("description_cn", "")
        desc_en = ai_result.get("description_en", "")
        product_insight = {
            "cn": f"{screen_type}类型页面，{desc_cn[:30]}..." if len(desc_cn) > 30 else desc_cn,
            "en": f"{screen_type} page type. {desc_en[:50]}..." if len(desc_en) > 50 else desc_en
        }
    
    # 5. tags - 优先使用AI返回的
    ai_tags = ai_result.get("tags", [])
    if isinstance(ai_tags, list) and len(ai_tags) > 0:
        tags = ai_tags
    else:
        # Fallback: 从keywords生成
        keywords = ai_result.get("keywords_found", [])
        tags = [{"cn": type_names["cn"], "en": type_names["en"]}]
        for kw in keywords[:5]:
            if len(kw) < 20:
                tags.append({"cn": kw, "en": kw})
    
    return {
        "screen_type": screen_type,
        "naming": naming,
        "core_function": core_function,
        "design_highlights": design_highlights,
        "product_insight": product_insight,
        "tags": tags,
        "confidence": confidence
    }


def process_project(project_path):
    """处理单个项目"""
    ai_analysis_file = os.path.join(project_path, "ai_analysis.json")
    structured_file = os.path.join(project_path, "structured_descriptions.json")
    
    if not os.path.exists(ai_analysis_file):
        print(f"  [SKIP] No ai_analysis.json found")
        return False
    
    # 读取AI分析结果
    with open(ai_analysis_file, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    if not results:
        print(f"  [SKIP] No results in ai_analysis.json")
        return False
    
    # 转换每个截图的分析结果
    structured = {}
    for filename, ai_result in results.items():
        structured[filename] = convert_analysis_to_structured(ai_result)
    
    # 写入结构化描述文件
    with open(structured_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Generated {len(structured)} structured descriptions")
    return True


def main():
    # 获取项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(os.path.dirname(script_dir), "projects")
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    print("=" * 60)
    print("Generating structured_descriptions.json for all projects")
    print("=" * 60)
    
    # 如果指定了项目名，只处理该项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
        else:
            print(f"Project not found: {project_name}")
        return
    
    # 处理所有项目
    for project_name in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_name)
        if os.path.isdir(project_path) and project_name != "null":
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()


"""
将 ai_analysis.json 转换为 structured_descriptions.json
供前端使用的结构化描述文件
"""

import os
import json
import sys

# 页面类型映射 - 用于生成更好的命名
SCREEN_TYPE_NAMES = {
    "Launch": {"cn": "启动页", "en": "Launch Screen"},
    "Welcome": {"cn": "欢迎页", "en": "Welcome"},
    "Onboarding": {"cn": "引导流程", "en": "Onboarding"},
    "Registration": {"cn": "注册页", "en": "Registration"},
    "Login": {"cn": "登录页", "en": "Login"},
    "Goal": {"cn": "目标设置", "en": "Goal Setting"},
    "Profile": {"cn": "个人资料", "en": "Profile"},
    "Paywall": {"cn": "付费墙", "en": "Paywall"},
    "Home": {"cn": "首页", "en": "Home"},
    "Dashboard": {"cn": "仪表盘", "en": "Dashboard"},
    "Settings": {"cn": "设置", "en": "Settings"},
    "Notification": {"cn": "通知", "en": "Notification"},
    "Search": {"cn": "搜索", "en": "Search"},
    "Detail": {"cn": "详情页", "en": "Detail"},
    "List": {"cn": "列表页", "en": "List"},
    "Modal": {"cn": "弹窗", "en": "Modal"},
    "Loading": {"cn": "加载页", "en": "Loading"},
    "Error": {"cn": "错误页", "en": "Error"},
    "Success": {"cn": "成功页", "en": "Success"},
    "Empty": {"cn": "空状态", "en": "Empty State"},
    "Logging": {"cn": "记录页", "en": "Logging"},
    "Progress": {"cn": "进度页", "en": "Progress"},
    "Activity": {"cn": "活动页", "en": "Activity"},
    "Social": {"cn": "社交", "en": "Social"},
    "Content": {"cn": "内容页", "en": "Content"},
}


def convert_analysis_to_structured(ai_result):
    """将单个AI分析结果转换为结构化描述 - 优先使用AI返回的结构化数据"""
    
    screen_type = ai_result.get("screen_type", "Unknown")
    sub_type = ai_result.get("sub_type", "")
    confidence = ai_result.get("confidence", 0.8)
    
    # 获取类型名称（用于fallback）
    type_names = SCREEN_TYPE_NAMES.get(screen_type, {"cn": screen_type, "en": screen_type})
    
    # === 优先使用AI返回的结构化数据 ===
    
    # 1. naming - 优先使用AI返回的
    ai_naming = ai_result.get("naming", {})
    if isinstance(ai_naming, dict) and ai_naming.get("cn"):
        naming = ai_naming
    else:
        # Fallback: 从screen_type生成
        naming = {"cn": type_names['cn'], "en": type_names['en']}
        if sub_type:
            sub_display = sub_type.replace("_", " ").title()
            naming["cn"] = f"{type_names['cn']} - {sub_display}"
            naming["en"] = f"{type_names['en']} - {sub_display}"
    
    # 2. core_function - 优先使用AI返回的
    ai_core = ai_result.get("core_function", {})
    if isinstance(ai_core, dict) and ai_core.get("cn"):
        core_function = ai_core
    else:
        # Fallback: 使用description
        core_function = {
            "cn": ai_result.get("description_cn", ""),
            "en": ai_result.get("description_en", "")
        }
    
    # 3. design_highlights - 优先使用AI返回的
    ai_highlights = ai_result.get("design_highlights", [])
    if isinstance(ai_highlights, list) and len(ai_highlights) > 0:
        design_highlights = ai_highlights
    else:
        # Fallback: 从ui_elements生成
        ui_elements = ai_result.get("ui_elements", [])
        design_highlights = []
        if ui_elements:
            visual_elements = [e for e in ui_elements if any(k in e.lower() for k in ['image', 'icon', 'logo', 'color', 'background', 'chart', 'graph'])]
            if visual_elements:
                design_highlights.append({
                    "category": "visual",
                    "cn": f"包含{len(visual_elements)}个视觉元素: {', '.join(visual_elements[:3])}",
                    "en": f"Contains {len(visual_elements)} visual elements: {', '.join(visual_elements[:3])}"
                })
            interactive_elements = [e for e in ui_elements if any(k in e.lower() for k in ['button', 'input', 'toggle', 'slider', 'picker', 'selector'])]
            if interactive_elements:
                design_highlights.append({
                    "category": "interaction",
                    "cn": f"交互组件: {', '.join(interactive_elements[:3])}",
                    "en": f"Interactive components: {', '.join(interactive_elements[:3])}"
                })
        if not design_highlights:
            design_highlights.append({"category": "general", "cn": "标准页面布局", "en": "Standard page layout"})
    
    # 4. product_insight - 优先使用AI返回的
    ai_insight = ai_result.get("product_insight", {})
    if isinstance(ai_insight, dict) and ai_insight.get("cn"):
        product_insight = ai_insight
    else:
        # Fallback: 自动生成
        desc_cn = ai_result.get("description_cn", "")
        desc_en = ai_result.get("description_en", "")
        product_insight = {
            "cn": f"{screen_type}类型页面，{desc_cn[:30]}..." if len(desc_cn) > 30 else desc_cn,
            "en": f"{screen_type} page type. {desc_en[:50]}..." if len(desc_en) > 50 else desc_en
        }
    
    # 5. tags - 优先使用AI返回的
    ai_tags = ai_result.get("tags", [])
    if isinstance(ai_tags, list) and len(ai_tags) > 0:
        tags = ai_tags
    else:
        # Fallback: 从keywords生成
        keywords = ai_result.get("keywords_found", [])
        tags = [{"cn": type_names["cn"], "en": type_names["en"]}]
        for kw in keywords[:5]:
            if len(kw) < 20:
                tags.append({"cn": kw, "en": kw})
    
    return {
        "screen_type": screen_type,
        "naming": naming,
        "core_function": core_function,
        "design_highlights": design_highlights,
        "product_insight": product_insight,
        "tags": tags,
        "confidence": confidence
    }


def process_project(project_path):
    """处理单个项目"""
    ai_analysis_file = os.path.join(project_path, "ai_analysis.json")
    structured_file = os.path.join(project_path, "structured_descriptions.json")
    
    if not os.path.exists(ai_analysis_file):
        print(f"  [SKIP] No ai_analysis.json found")
        return False
    
    # 读取AI分析结果
    with open(ai_analysis_file, "r", encoding="utf-8") as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    if not results:
        print(f"  [SKIP] No results in ai_analysis.json")
        return False
    
    # 转换每个截图的分析结果
    structured = {}
    for filename, ai_result in results.items():
        structured[filename] = convert_analysis_to_structured(ai_result)
    
    # 写入结构化描述文件
    with open(structured_file, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"  [OK] Generated {len(structured)} structured descriptions")
    return True


def main():
    # 获取项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    projects_dir = os.path.join(os.path.dirname(script_dir), "projects")
    
    if not os.path.exists(projects_dir):
        print(f"Projects directory not found: {projects_dir}")
        return
    
    print("=" * 60)
    print("Generating structured_descriptions.json for all projects")
    print("=" * 60)
    
    # 如果指定了项目名，只处理该项目
    if len(sys.argv) > 1:
        project_name = sys.argv[1]
        project_path = os.path.join(projects_dir, project_name)
        if os.path.exists(project_path):
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
        else:
            print(f"Project not found: {project_name}")
        return
    
    # 处理所有项目
    for project_name in os.listdir(projects_dir):
        project_path = os.path.join(projects_dir, project_name)
        if os.path.isdir(project_path) and project_name != "null":
            print(f"\nProcessing: {project_name}")
            process_project(project_path)
    
    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()

