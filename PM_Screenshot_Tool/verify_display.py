# -*- coding: utf-8 -*-
"""
自动验证Web显示
================
检查排序、分组是否正确
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def verify_project(project_name: str):
    """验证单个项目的显示"""
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # 1. 读取本地ai_analysis.json
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    analysis_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(analysis_file):
        print("  [ERROR] ai_analysis.json not found")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 2. 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 999))
    
    # 3. 检查Onboarding是否在前面
    first_onboarding_idx = None
    last_onboarding_idx = None
    onboarding_files = []
    
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        
        if stype == 'Onboarding':
            if first_onboarding_idx is None:
                first_onboarding_idx = idx
            last_onboarding_idx = idx
            onboarding_files.append((idx, filename))
    
    print(f"\n  Onboarding分析:")
    print(f"    - 总数: {len(onboarding_files)}")
    if first_onboarding_idx:
        print(f"    - 范围: #{first_onboarding_idx} - #{last_onboarding_idx}")
    
    # 4. 检查Onboarding是否连续
    if onboarding_files:
        expected_indices = list(range(first_onboarding_idx, last_onboarding_idx + 1))
        actual_indices = [idx for idx, _ in onboarding_files]
        
        # 找出缺失的（应该是Paywall等）
        missing = set(expected_indices) - set(actual_indices)
        if missing:
            print(f"    - 中间有其他类型: {sorted(missing)}")
            # 检查这些是什么类型
            for idx in sorted(missing)[:5]:
                for fn, r in results.items():
                    if r.get('index') == idx:
                        print(f"      #{idx}: {r.get('screen_type')}")
                        break
    
    # 5. 检查是否有Onboarding出现在Core功能之后
    core_start = None
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        if stype in ('Feature', 'Content', 'Tracking', 'Progress', 'Settings', 'Profile'):
            if core_start is None:
                core_start = idx
            break
    
    late_onboarding = []
    if core_start:
        for idx, fn in onboarding_files:
            if idx > core_start:
                late_onboarding.append(idx)
    
    if late_onboarding:
        issues.append(f"Onboarding出现在Core功能之后: {late_onboarding[:5]}")
    
    # 6. 检查前5张是否都是Onboarding
    first_5_types = []
    for filename, r in sorted_items[:5]:
        first_5_types.append(r.get('screen_type', '?'))
    
    print(f"\n  前5张截图类型: {first_5_types}")
    
    non_onboarding_early = [t for t in first_5_types if t not in ('Onboarding', 'Launch', 'Paywall')]
    if non_onboarding_early:
        issues.append(f"前5张有非Onboarding类型: {non_onboarding_early}")
    
    # 7. 检查Web API
    try:
        resp = requests.get(f"http://localhost:5000/api/screenshots/{project_name}", timeout=5)
        if resp.status_code == 200:
            api_data = resp.json()
            api_types = api_data.get('screen_types', {})
            
            # 比较本地和API的screen_types
            local_types = {fn: r.get('screen_type') for fn, r in results.items()}
            
            mismatches = []
            for fn in local_types:
                if fn in api_types and api_types[fn] != local_types[fn]:
                    mismatches.append(f"{fn}: local={local_types[fn]}, api={api_types[fn]}")
            
            if mismatches:
                issues.append(f"本地与API数据不一致: {len(mismatches)}个")
                for m in mismatches[:3]:
                    print(f"    - {m}")
            else:
                print(f"\n  API数据: 一致 ✓")
    except Exception as e:
        print(f"\n  API检查失败: {e}")
    
    # 8. 总结
    print(f"\n  问题总结:")
    if issues:
        for issue in issues:
            print(f"    ⚠️ {issue}")
    else:
        print(f"    ✓ 未发现问题")
    
    return issues


def verify_all():
    """验证所有项目"""
    
    projects = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    print("\n" + "=" * 60)
    print("  AUTO VERIFY WEB DISPLAY")
    print("=" * 60)
    
    all_issues = {}
    
    for project in projects:
        issues = verify_project(project)
        if issues:
            all_issues[project] = issues
    
    # 总结
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个项目有问题:")
        for proj, issues in all_issues.items():
            print(f"\n  {proj}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n✓ 所有项目验证通过")


if __name__ == "__main__":
    verify_all()


"""
自动验证Web显示
================
检查排序、分组是否正确
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def verify_project(project_name: str):
    """验证单个项目的显示"""
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # 1. 读取本地ai_analysis.json
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    analysis_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(analysis_file):
        print("  [ERROR] ai_analysis.json not found")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 2. 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 999))
    
    # 3. 检查Onboarding是否在前面
    first_onboarding_idx = None
    last_onboarding_idx = None
    onboarding_files = []
    
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        
        if stype == 'Onboarding':
            if first_onboarding_idx is None:
                first_onboarding_idx = idx
            last_onboarding_idx = idx
            onboarding_files.append((idx, filename))
    
    print(f"\n  Onboarding分析:")
    print(f"    - 总数: {len(onboarding_files)}")
    if first_onboarding_idx:
        print(f"    - 范围: #{first_onboarding_idx} - #{last_onboarding_idx}")
    
    # 4. 检查Onboarding是否连续
    if onboarding_files:
        expected_indices = list(range(first_onboarding_idx, last_onboarding_idx + 1))
        actual_indices = [idx for idx, _ in onboarding_files]
        
        # 找出缺失的（应该是Paywall等）
        missing = set(expected_indices) - set(actual_indices)
        if missing:
            print(f"    - 中间有其他类型: {sorted(missing)}")
            # 检查这些是什么类型
            for idx in sorted(missing)[:5]:
                for fn, r in results.items():
                    if r.get('index') == idx:
                        print(f"      #{idx}: {r.get('screen_type')}")
                        break
    
    # 5. 检查是否有Onboarding出现在Core功能之后
    core_start = None
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        if stype in ('Feature', 'Content', 'Tracking', 'Progress', 'Settings', 'Profile'):
            if core_start is None:
                core_start = idx
            break
    
    late_onboarding = []
    if core_start:
        for idx, fn in onboarding_files:
            if idx > core_start:
                late_onboarding.append(idx)
    
    if late_onboarding:
        issues.append(f"Onboarding出现在Core功能之后: {late_onboarding[:5]}")
    
    # 6. 检查前5张是否都是Onboarding
    first_5_types = []
    for filename, r in sorted_items[:5]:
        first_5_types.append(r.get('screen_type', '?'))
    
    print(f"\n  前5张截图类型: {first_5_types}")
    
    non_onboarding_early = [t for t in first_5_types if t not in ('Onboarding', 'Launch', 'Paywall')]
    if non_onboarding_early:
        issues.append(f"前5张有非Onboarding类型: {non_onboarding_early}")
    
    # 7. 检查Web API
    try:
        resp = requests.get(f"http://localhost:5000/api/screenshots/{project_name}", timeout=5)
        if resp.status_code == 200:
            api_data = resp.json()
            api_types = api_data.get('screen_types', {})
            
            # 比较本地和API的screen_types
            local_types = {fn: r.get('screen_type') for fn, r in results.items()}
            
            mismatches = []
            for fn in local_types:
                if fn in api_types and api_types[fn] != local_types[fn]:
                    mismatches.append(f"{fn}: local={local_types[fn]}, api={api_types[fn]}")
            
            if mismatches:
                issues.append(f"本地与API数据不一致: {len(mismatches)}个")
                for m in mismatches[:3]:
                    print(f"    - {m}")
            else:
                print(f"\n  API数据: 一致 ✓")
    except Exception as e:
        print(f"\n  API检查失败: {e}")
    
    # 8. 总结
    print(f"\n  问题总结:")
    if issues:
        for issue in issues:
            print(f"    ⚠️ {issue}")
    else:
        print(f"    ✓ 未发现问题")
    
    return issues


def verify_all():
    """验证所有项目"""
    
    projects = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    print("\n" + "=" * 60)
    print("  AUTO VERIFY WEB DISPLAY")
    print("=" * 60)
    
    all_issues = {}
    
    for project in projects:
        issues = verify_project(project)
        if issues:
            all_issues[project] = issues
    
    # 总结
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个项目有问题:")
        for proj, issues in all_issues.items():
            print(f"\n  {proj}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n✓ 所有项目验证通过")


if __name__ == "__main__":
    verify_all()


"""
自动验证Web显示
================
检查排序、分组是否正确
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def verify_project(project_name: str):
    """验证单个项目的显示"""
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # 1. 读取本地ai_analysis.json
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    analysis_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(analysis_file):
        print("  [ERROR] ai_analysis.json not found")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 2. 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 999))
    
    # 3. 检查Onboarding是否在前面
    first_onboarding_idx = None
    last_onboarding_idx = None
    onboarding_files = []
    
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        
        if stype == 'Onboarding':
            if first_onboarding_idx is None:
                first_onboarding_idx = idx
            last_onboarding_idx = idx
            onboarding_files.append((idx, filename))
    
    print(f"\n  Onboarding分析:")
    print(f"    - 总数: {len(onboarding_files)}")
    if first_onboarding_idx:
        print(f"    - 范围: #{first_onboarding_idx} - #{last_onboarding_idx}")
    
    # 4. 检查Onboarding是否连续
    if onboarding_files:
        expected_indices = list(range(first_onboarding_idx, last_onboarding_idx + 1))
        actual_indices = [idx for idx, _ in onboarding_files]
        
        # 找出缺失的（应该是Paywall等）
        missing = set(expected_indices) - set(actual_indices)
        if missing:
            print(f"    - 中间有其他类型: {sorted(missing)}")
            # 检查这些是什么类型
            for idx in sorted(missing)[:5]:
                for fn, r in results.items():
                    if r.get('index') == idx:
                        print(f"      #{idx}: {r.get('screen_type')}")
                        break
    
    # 5. 检查是否有Onboarding出现在Core功能之后
    core_start = None
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        if stype in ('Feature', 'Content', 'Tracking', 'Progress', 'Settings', 'Profile'):
            if core_start is None:
                core_start = idx
            break
    
    late_onboarding = []
    if core_start:
        for idx, fn in onboarding_files:
            if idx > core_start:
                late_onboarding.append(idx)
    
    if late_onboarding:
        issues.append(f"Onboarding出现在Core功能之后: {late_onboarding[:5]}")
    
    # 6. 检查前5张是否都是Onboarding
    first_5_types = []
    for filename, r in sorted_items[:5]:
        first_5_types.append(r.get('screen_type', '?'))
    
    print(f"\n  前5张截图类型: {first_5_types}")
    
    non_onboarding_early = [t for t in first_5_types if t not in ('Onboarding', 'Launch', 'Paywall')]
    if non_onboarding_early:
        issues.append(f"前5张有非Onboarding类型: {non_onboarding_early}")
    
    # 7. 检查Web API
    try:
        resp = requests.get(f"http://localhost:5000/api/screenshots/{project_name}", timeout=5)
        if resp.status_code == 200:
            api_data = resp.json()
            api_types = api_data.get('screen_types', {})
            
            # 比较本地和API的screen_types
            local_types = {fn: r.get('screen_type') for fn, r in results.items()}
            
            mismatches = []
            for fn in local_types:
                if fn in api_types and api_types[fn] != local_types[fn]:
                    mismatches.append(f"{fn}: local={local_types[fn]}, api={api_types[fn]}")
            
            if mismatches:
                issues.append(f"本地与API数据不一致: {len(mismatches)}个")
                for m in mismatches[:3]:
                    print(f"    - {m}")
            else:
                print(f"\n  API数据: 一致 ✓")
    except Exception as e:
        print(f"\n  API检查失败: {e}")
    
    # 8. 总结
    print(f"\n  问题总结:")
    if issues:
        for issue in issues:
            print(f"    ⚠️ {issue}")
    else:
        print(f"    ✓ 未发现问题")
    
    return issues


def verify_all():
    """验证所有项目"""
    
    projects = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    print("\n" + "=" * 60)
    print("  AUTO VERIFY WEB DISPLAY")
    print("=" * 60)
    
    all_issues = {}
    
    for project in projects:
        issues = verify_project(project)
        if issues:
            all_issues[project] = issues
    
    # 总结
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个项目有问题:")
        for proj, issues in all_issues.items():
            print(f"\n  {proj}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n✓ 所有项目验证通过")


if __name__ == "__main__":
    verify_all()


"""
自动验证Web显示
================
检查排序、分组是否正确
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def verify_project(project_name: str):
    """验证单个项目的显示"""
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # 1. 读取本地ai_analysis.json
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    analysis_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(analysis_file):
        print("  [ERROR] ai_analysis.json not found")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 2. 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 999))
    
    # 3. 检查Onboarding是否在前面
    first_onboarding_idx = None
    last_onboarding_idx = None
    onboarding_files = []
    
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        
        if stype == 'Onboarding':
            if first_onboarding_idx is None:
                first_onboarding_idx = idx
            last_onboarding_idx = idx
            onboarding_files.append((idx, filename))
    
    print(f"\n  Onboarding分析:")
    print(f"    - 总数: {len(onboarding_files)}")
    if first_onboarding_idx:
        print(f"    - 范围: #{first_onboarding_idx} - #{last_onboarding_idx}")
    
    # 4. 检查Onboarding是否连续
    if onboarding_files:
        expected_indices = list(range(first_onboarding_idx, last_onboarding_idx + 1))
        actual_indices = [idx for idx, _ in onboarding_files]
        
        # 找出缺失的（应该是Paywall等）
        missing = set(expected_indices) - set(actual_indices)
        if missing:
            print(f"    - 中间有其他类型: {sorted(missing)}")
            # 检查这些是什么类型
            for idx in sorted(missing)[:5]:
                for fn, r in results.items():
                    if r.get('index') == idx:
                        print(f"      #{idx}: {r.get('screen_type')}")
                        break
    
    # 5. 检查是否有Onboarding出现在Core功能之后
    core_start = None
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        if stype in ('Feature', 'Content', 'Tracking', 'Progress', 'Settings', 'Profile'):
            if core_start is None:
                core_start = idx
            break
    
    late_onboarding = []
    if core_start:
        for idx, fn in onboarding_files:
            if idx > core_start:
                late_onboarding.append(idx)
    
    if late_onboarding:
        issues.append(f"Onboarding出现在Core功能之后: {late_onboarding[:5]}")
    
    # 6. 检查前5张是否都是Onboarding
    first_5_types = []
    for filename, r in sorted_items[:5]:
        first_5_types.append(r.get('screen_type', '?'))
    
    print(f"\n  前5张截图类型: {first_5_types}")
    
    non_onboarding_early = [t for t in first_5_types if t not in ('Onboarding', 'Launch', 'Paywall')]
    if non_onboarding_early:
        issues.append(f"前5张有非Onboarding类型: {non_onboarding_early}")
    
    # 7. 检查Web API
    try:
        resp = requests.get(f"http://localhost:5000/api/screenshots/{project_name}", timeout=5)
        if resp.status_code == 200:
            api_data = resp.json()
            api_types = api_data.get('screen_types', {})
            
            # 比较本地和API的screen_types
            local_types = {fn: r.get('screen_type') for fn, r in results.items()}
            
            mismatches = []
            for fn in local_types:
                if fn in api_types and api_types[fn] != local_types[fn]:
                    mismatches.append(f"{fn}: local={local_types[fn]}, api={api_types[fn]}")
            
            if mismatches:
                issues.append(f"本地与API数据不一致: {len(mismatches)}个")
                for m in mismatches[:3]:
                    print(f"    - {m}")
            else:
                print(f"\n  API数据: 一致 ✓")
    except Exception as e:
        print(f"\n  API检查失败: {e}")
    
    # 8. 总结
    print(f"\n  问题总结:")
    if issues:
        for issue in issues:
            print(f"    ⚠️ {issue}")
    else:
        print(f"    ✓ 未发现问题")
    
    return issues


def verify_all():
    """验证所有项目"""
    
    projects = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    print("\n" + "=" * 60)
    print("  AUTO VERIFY WEB DISPLAY")
    print("=" * 60)
    
    all_issues = {}
    
    for project in projects:
        issues = verify_project(project)
        if issues:
            all_issues[project] = issues
    
    # 总结
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个项目有问题:")
        for proj, issues in all_issues.items():
            print(f"\n  {proj}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n✓ 所有项目验证通过")


if __name__ == "__main__":
    verify_all()



"""
自动验证Web显示
================
检查排序、分组是否正确
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def verify_project(project_name: str):
    """验证单个项目的显示"""
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # 1. 读取本地ai_analysis.json
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    analysis_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(analysis_file):
        print("  [ERROR] ai_analysis.json not found")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 2. 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 999))
    
    # 3. 检查Onboarding是否在前面
    first_onboarding_idx = None
    last_onboarding_idx = None
    onboarding_files = []
    
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        
        if stype == 'Onboarding':
            if first_onboarding_idx is None:
                first_onboarding_idx = idx
            last_onboarding_idx = idx
            onboarding_files.append((idx, filename))
    
    print(f"\n  Onboarding分析:")
    print(f"    - 总数: {len(onboarding_files)}")
    if first_onboarding_idx:
        print(f"    - 范围: #{first_onboarding_idx} - #{last_onboarding_idx}")
    
    # 4. 检查Onboarding是否连续
    if onboarding_files:
        expected_indices = list(range(first_onboarding_idx, last_onboarding_idx + 1))
        actual_indices = [idx for idx, _ in onboarding_files]
        
        # 找出缺失的（应该是Paywall等）
        missing = set(expected_indices) - set(actual_indices)
        if missing:
            print(f"    - 中间有其他类型: {sorted(missing)}")
            # 检查这些是什么类型
            for idx in sorted(missing)[:5]:
                for fn, r in results.items():
                    if r.get('index') == idx:
                        print(f"      #{idx}: {r.get('screen_type')}")
                        break
    
    # 5. 检查是否有Onboarding出现在Core功能之后
    core_start = None
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        if stype in ('Feature', 'Content', 'Tracking', 'Progress', 'Settings', 'Profile'):
            if core_start is None:
                core_start = idx
            break
    
    late_onboarding = []
    if core_start:
        for idx, fn in onboarding_files:
            if idx > core_start:
                late_onboarding.append(idx)
    
    if late_onboarding:
        issues.append(f"Onboarding出现在Core功能之后: {late_onboarding[:5]}")
    
    # 6. 检查前5张是否都是Onboarding
    first_5_types = []
    for filename, r in sorted_items[:5]:
        first_5_types.append(r.get('screen_type', '?'))
    
    print(f"\n  前5张截图类型: {first_5_types}")
    
    non_onboarding_early = [t for t in first_5_types if t not in ('Onboarding', 'Launch', 'Paywall')]
    if non_onboarding_early:
        issues.append(f"前5张有非Onboarding类型: {non_onboarding_early}")
    
    # 7. 检查Web API
    try:
        resp = requests.get(f"http://localhost:5000/api/screenshots/{project_name}", timeout=5)
        if resp.status_code == 200:
            api_data = resp.json()
            api_types = api_data.get('screen_types', {})
            
            # 比较本地和API的screen_types
            local_types = {fn: r.get('screen_type') for fn, r in results.items()}
            
            mismatches = []
            for fn in local_types:
                if fn in api_types and api_types[fn] != local_types[fn]:
                    mismatches.append(f"{fn}: local={local_types[fn]}, api={api_types[fn]}")
            
            if mismatches:
                issues.append(f"本地与API数据不一致: {len(mismatches)}个")
                for m in mismatches[:3]:
                    print(f"    - {m}")
            else:
                print(f"\n  API数据: 一致 ✓")
    except Exception as e:
        print(f"\n  API检查失败: {e}")
    
    # 8. 总结
    print(f"\n  问题总结:")
    if issues:
        for issue in issues:
            print(f"    ⚠️ {issue}")
    else:
        print(f"    ✓ 未发现问题")
    
    return issues


def verify_all():
    """验证所有项目"""
    
    projects = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    print("\n" + "=" * 60)
    print("  AUTO VERIFY WEB DISPLAY")
    print("=" * 60)
    
    all_issues = {}
    
    for project in projects:
        issues = verify_project(project)
        if issues:
            all_issues[project] = issues
    
    # 总结
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个项目有问题:")
        for proj, issues in all_issues.items():
            print(f"\n  {proj}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n✓ 所有项目验证通过")


if __name__ == "__main__":
    verify_all()


"""
自动验证Web显示
================
检查排序、分组是否正确
"""

import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

def verify_project(project_name: str):
    """验证单个项目的显示"""
    
    print(f"\n{'='*60}")
    print(f"  {project_name}")
    print(f"{'='*60}")
    
    issues = []
    
    # 1. 读取本地ai_analysis.json
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    analysis_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(analysis_file):
        print("  [ERROR] ai_analysis.json not found")
        return
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 2. 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 999))
    
    # 3. 检查Onboarding是否在前面
    first_onboarding_idx = None
    last_onboarding_idx = None
    onboarding_files = []
    
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        
        if stype == 'Onboarding':
            if first_onboarding_idx is None:
                first_onboarding_idx = idx
            last_onboarding_idx = idx
            onboarding_files.append((idx, filename))
    
    print(f"\n  Onboarding分析:")
    print(f"    - 总数: {len(onboarding_files)}")
    if first_onboarding_idx:
        print(f"    - 范围: #{first_onboarding_idx} - #{last_onboarding_idx}")
    
    # 4. 检查Onboarding是否连续
    if onboarding_files:
        expected_indices = list(range(first_onboarding_idx, last_onboarding_idx + 1))
        actual_indices = [idx for idx, _ in onboarding_files]
        
        # 找出缺失的（应该是Paywall等）
        missing = set(expected_indices) - set(actual_indices)
        if missing:
            print(f"    - 中间有其他类型: {sorted(missing)}")
            # 检查这些是什么类型
            for idx in sorted(missing)[:5]:
                for fn, r in results.items():
                    if r.get('index') == idx:
                        print(f"      #{idx}: {r.get('screen_type')}")
                        break
    
    # 5. 检查是否有Onboarding出现在Core功能之后
    core_start = None
    for filename, r in sorted_items:
        idx = r.get('index', 0)
        stype = r.get('screen_type', '')
        if stype in ('Feature', 'Content', 'Tracking', 'Progress', 'Settings', 'Profile'):
            if core_start is None:
                core_start = idx
            break
    
    late_onboarding = []
    if core_start:
        for idx, fn in onboarding_files:
            if idx > core_start:
                late_onboarding.append(idx)
    
    if late_onboarding:
        issues.append(f"Onboarding出现在Core功能之后: {late_onboarding[:5]}")
    
    # 6. 检查前5张是否都是Onboarding
    first_5_types = []
    for filename, r in sorted_items[:5]:
        first_5_types.append(r.get('screen_type', '?'))
    
    print(f"\n  前5张截图类型: {first_5_types}")
    
    non_onboarding_early = [t for t in first_5_types if t not in ('Onboarding', 'Launch', 'Paywall')]
    if non_onboarding_early:
        issues.append(f"前5张有非Onboarding类型: {non_onboarding_early}")
    
    # 7. 检查Web API
    try:
        resp = requests.get(f"http://localhost:5000/api/screenshots/{project_name}", timeout=5)
        if resp.status_code == 200:
            api_data = resp.json()
            api_types = api_data.get('screen_types', {})
            
            # 比较本地和API的screen_types
            local_types = {fn: r.get('screen_type') for fn, r in results.items()}
            
            mismatches = []
            for fn in local_types:
                if fn in api_types and api_types[fn] != local_types[fn]:
                    mismatches.append(f"{fn}: local={local_types[fn]}, api={api_types[fn]}")
            
            if mismatches:
                issues.append(f"本地与API数据不一致: {len(mismatches)}个")
                for m in mismatches[:3]:
                    print(f"    - {m}")
            else:
                print(f"\n  API数据: 一致 ✓")
    except Exception as e:
        print(f"\n  API检查失败: {e}")
    
    # 8. 总结
    print(f"\n  问题总结:")
    if issues:
        for issue in issues:
            print(f"    ⚠️ {issue}")
    else:
        print(f"    ✓ 未发现问题")
    
    return issues


def verify_all():
    """验证所有项目"""
    
    projects = [
        "Calm_Analysis",
        "Cal_AI_-_Calorie_Tracker_Analysis",
        "Flo_Period_Pregnancy_Tracker_Analysis",
        "MyFitnessPal_Calorie_Counter_Analysis",
        "Runna_Running_Training_Plans_Analysis",
        "Strava_Run_Bike_Hike_Analysis"
    ]
    
    print("\n" + "=" * 60)
    print("  AUTO VERIFY WEB DISPLAY")
    print("=" * 60)
    
    all_issues = {}
    
    for project in projects:
        issues = verify_project(project)
        if issues:
            all_issues[project] = issues
    
    # 总结
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    
    if all_issues:
        print(f"\n发现 {len(all_issues)} 个项目有问题:")
        for proj, issues in all_issues.items():
            print(f"\n  {proj}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print("\n✓ 所有项目验证通过")


if __name__ == "__main__":
    verify_all()










































