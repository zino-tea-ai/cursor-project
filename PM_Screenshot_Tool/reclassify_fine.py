# -*- coding: utf-8 -*-
"""
细颗粒度分类 - 支持逐页对比
每个阶段控制在5-10张左右，便于精确对比
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 细颗粒度阶段定义（健身/健康类App通用）
# 格式: (阶段代码, 阶段名, 预估占比起点, 预估占比终点)
FINE_PHASES = [
    # Onboarding 拆分为多个子阶段
    ("01", "Launch",      0.00, 0.02),   # 启动页 1-2张
    ("02", "Welcome",     0.02, 0.05),   # 欢迎/价值主张 2-3张
    ("03", "Auth",        0.05, 0.10),   # 登录/注册 3-5张
    ("04", "Goals",       0.10, 0.15),   # 目标设置 3-5张
    ("05", "Profile",     0.15, 0.22),   # 个人信息 5-7张
    ("06", "Activity",    0.22, 0.27),   # 活动水平 3-5张
    ("07", "Preference",  0.27, 0.32),   # 偏好设置 3-5张
    ("08", "Motivation",  0.32, 0.38),   # 激励/预期 4-6张
    ("09", "Permissions", 0.38, 0.42),   # 权限请求 2-4张
    ("10", "Paywall",     0.42, 0.50),   # 付费墙 5-8张
    # 主App功能
    ("11", "Home",        0.50, 0.58),   # 首页/仪表盘
    ("12", "Logging",     0.58, 0.68),   # 记录功能
    ("13", "Stats",       0.68, 0.75),   # 统计/报表
    ("14", "Features",    0.75, 0.85),   # 其他功能
    ("15", "Social",      0.85, 0.92),   # 社交功能
    ("16", "Settings",    0.92, 1.00),   # 设置/账户
]

def classify_fine(project_name):
    """细颗粒度分类"""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        print(f"  [跳过] {project_name}: Downloads不存在")
        return 0
    
    # 获取截图列表
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        print(f"  [跳过] {project_name}: 无截图")
        return 0
    
    # 清空并重建Screens
    if os.path.exists(screens_path):
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 按细颗粒度分类
    count = 0
    for phase_code, phase_name, start_pct, end_pct in FINE_PHASES:
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)
        
        # 确保每个阶段至少有内容时才处理
        if start_idx >= total:
            continue
            
        end_idx = min(end_idx, total)
        
        phase_screens = screenshots[start_idx:end_idx]
        
        for step, orig_file in enumerate(phase_screens, 1):
            src = os.path.join(downloads_path, orig_file)
            new_name = f"{phase_code}_{phase_name}_{step:02d}.png"
            dst = os.path.join(screens_path, new_name)
            shutil.copy2(src, dst)
            count += 1
    
    return count

def generate_summary():
    """生成分类汇总"""
    print("\n" + "=" * 70)
    print("分类汇总")
    print("=" * 70)
    
    # 收集所有产品的阶段数据
    all_stats = {}
    
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        screens_path = os.path.join(proj_path, "Screens")
        
        if not os.path.isdir(screens_path):
            continue
        
        all_stats[proj_name] = {}
        
        for f in os.listdir(screens_path):
            if f.endswith('.png'):
                parts = f.split('_')
                if len(parts) >= 2:
                    phase_key = f"{parts[0]}_{parts[1]}"
                    all_stats[proj_name][phase_key] = all_stats[proj_name].get(phase_key, 0) + 1
    
    # 打印对比表
    if not all_stats:
        print("无数据")
        return
    
    # 收集所有阶段
    all_phases = set()
    for stats in all_stats.values():
        all_phases.update(stats.keys())
    all_phases = sorted(all_phases)
    
    # 打印表头
    products = list(all_stats.keys())
    header = f"{'阶段':<15}" + "".join(f"{p.replace('_Analysis',''):<12}" for p in products)
    print(header)
    print("-" * len(header))
    
    # 打印每行
    for phase in all_phases:
        row = f"{phase:<15}"
        for prod in products:
            cnt = all_stats[prod].get(phase, 0)
            row += f"{cnt:<12}"
        print(row)
    
    print("-" * len(header))
    
    # 总计
    row = f"{'总计':<15}"
    for prod in products:
        total = sum(all_stats[prod].values())
        row += f"{total:<12}"
    print(row)

def main():
    print("=" * 70)
    print("细颗粒度分类 - 支持逐页对比")
    print("=" * 70)
    print("\n阶段定义:")
    for code, name, s, e in FINE_PHASES:
        pct = f"{int(s*100)}-{int(e*100)}%"
        print(f"  {code}_{name:<12} {pct}")
    
    print("\n" + "-" * 70)
    print("开始分类...")
    print("-" * 70)
    
    # 获取所有项目
    projects = [d for d in os.listdir(PROJECTS_DIR) 
                if os.path.isdir(os.path.join(PROJECTS_DIR, d, "Downloads"))]
    
    for proj in projects:
        count = classify_fine(proj)
        print(f"  {proj.replace('_Analysis',''):<20} → {count} 张")
    
    # 生成汇总
    generate_summary()
    
    print("\n✅ 分类完成！刷新网页查看效果")

if __name__ == "__main__":
    main()






"""
细颗粒度分类 - 支持逐页对比
每个阶段控制在5-10张左右，便于精确对比
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 细颗粒度阶段定义（健身/健康类App通用）
# 格式: (阶段代码, 阶段名, 预估占比起点, 预估占比终点)
FINE_PHASES = [
    # Onboarding 拆分为多个子阶段
    ("01", "Launch",      0.00, 0.02),   # 启动页 1-2张
    ("02", "Welcome",     0.02, 0.05),   # 欢迎/价值主张 2-3张
    ("03", "Auth",        0.05, 0.10),   # 登录/注册 3-5张
    ("04", "Goals",       0.10, 0.15),   # 目标设置 3-5张
    ("05", "Profile",     0.15, 0.22),   # 个人信息 5-7张
    ("06", "Activity",    0.22, 0.27),   # 活动水平 3-5张
    ("07", "Preference",  0.27, 0.32),   # 偏好设置 3-5张
    ("08", "Motivation",  0.32, 0.38),   # 激励/预期 4-6张
    ("09", "Permissions", 0.38, 0.42),   # 权限请求 2-4张
    ("10", "Paywall",     0.42, 0.50),   # 付费墙 5-8张
    # 主App功能
    ("11", "Home",        0.50, 0.58),   # 首页/仪表盘
    ("12", "Logging",     0.58, 0.68),   # 记录功能
    ("13", "Stats",       0.68, 0.75),   # 统计/报表
    ("14", "Features",    0.75, 0.85),   # 其他功能
    ("15", "Social",      0.85, 0.92),   # 社交功能
    ("16", "Settings",    0.92, 1.00),   # 设置/账户
]

def classify_fine(project_name):
    """细颗粒度分类"""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        print(f"  [跳过] {project_name}: Downloads不存在")
        return 0
    
    # 获取截图列表
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        print(f"  [跳过] {project_name}: 无截图")
        return 0
    
    # 清空并重建Screens
    if os.path.exists(screens_path):
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 按细颗粒度分类
    count = 0
    for phase_code, phase_name, start_pct, end_pct in FINE_PHASES:
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)
        
        # 确保每个阶段至少有内容时才处理
        if start_idx >= total:
            continue
            
        end_idx = min(end_idx, total)
        
        phase_screens = screenshots[start_idx:end_idx]
        
        for step, orig_file in enumerate(phase_screens, 1):
            src = os.path.join(downloads_path, orig_file)
            new_name = f"{phase_code}_{phase_name}_{step:02d}.png"
            dst = os.path.join(screens_path, new_name)
            shutil.copy2(src, dst)
            count += 1
    
    return count

def generate_summary():
    """生成分类汇总"""
    print("\n" + "=" * 70)
    print("分类汇总")
    print("=" * 70)
    
    # 收集所有产品的阶段数据
    all_stats = {}
    
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        screens_path = os.path.join(proj_path, "Screens")
        
        if not os.path.isdir(screens_path):
            continue
        
        all_stats[proj_name] = {}
        
        for f in os.listdir(screens_path):
            if f.endswith('.png'):
                parts = f.split('_')
                if len(parts) >= 2:
                    phase_key = f"{parts[0]}_{parts[1]}"
                    all_stats[proj_name][phase_key] = all_stats[proj_name].get(phase_key, 0) + 1
    
    # 打印对比表
    if not all_stats:
        print("无数据")
        return
    
    # 收集所有阶段
    all_phases = set()
    for stats in all_stats.values():
        all_phases.update(stats.keys())
    all_phases = sorted(all_phases)
    
    # 打印表头
    products = list(all_stats.keys())
    header = f"{'阶段':<15}" + "".join(f"{p.replace('_Analysis',''):<12}" for p in products)
    print(header)
    print("-" * len(header))
    
    # 打印每行
    for phase in all_phases:
        row = f"{phase:<15}"
        for prod in products:
            cnt = all_stats[prod].get(phase, 0)
            row += f"{cnt:<12}"
        print(row)
    
    print("-" * len(header))
    
    # 总计
    row = f"{'总计':<15}"
    for prod in products:
        total = sum(all_stats[prod].values())
        row += f"{total:<12}"
    print(row)

def main():
    print("=" * 70)
    print("细颗粒度分类 - 支持逐页对比")
    print("=" * 70)
    print("\n阶段定义:")
    for code, name, s, e in FINE_PHASES:
        pct = f"{int(s*100)}-{int(e*100)}%"
        print(f"  {code}_{name:<12} {pct}")
    
    print("\n" + "-" * 70)
    print("开始分类...")
    print("-" * 70)
    
    # 获取所有项目
    projects = [d for d in os.listdir(PROJECTS_DIR) 
                if os.path.isdir(os.path.join(PROJECTS_DIR, d, "Downloads"))]
    
    for proj in projects:
        count = classify_fine(proj)
        print(f"  {proj.replace('_Analysis',''):<20} → {count} 张")
    
    # 生成汇总
    generate_summary()
    
    print("\n✅ 分类完成！刷新网页查看效果")

if __name__ == "__main__":
    main()






"""
细颗粒度分类 - 支持逐页对比
每个阶段控制在5-10张左右，便于精确对比
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 细颗粒度阶段定义（健身/健康类App通用）
# 格式: (阶段代码, 阶段名, 预估占比起点, 预估占比终点)
FINE_PHASES = [
    # Onboarding 拆分为多个子阶段
    ("01", "Launch",      0.00, 0.02),   # 启动页 1-2张
    ("02", "Welcome",     0.02, 0.05),   # 欢迎/价值主张 2-3张
    ("03", "Auth",        0.05, 0.10),   # 登录/注册 3-5张
    ("04", "Goals",       0.10, 0.15),   # 目标设置 3-5张
    ("05", "Profile",     0.15, 0.22),   # 个人信息 5-7张
    ("06", "Activity",    0.22, 0.27),   # 活动水平 3-5张
    ("07", "Preference",  0.27, 0.32),   # 偏好设置 3-5张
    ("08", "Motivation",  0.32, 0.38),   # 激励/预期 4-6张
    ("09", "Permissions", 0.38, 0.42),   # 权限请求 2-4张
    ("10", "Paywall",     0.42, 0.50),   # 付费墙 5-8张
    # 主App功能
    ("11", "Home",        0.50, 0.58),   # 首页/仪表盘
    ("12", "Logging",     0.58, 0.68),   # 记录功能
    ("13", "Stats",       0.68, 0.75),   # 统计/报表
    ("14", "Features",    0.75, 0.85),   # 其他功能
    ("15", "Social",      0.85, 0.92),   # 社交功能
    ("16", "Settings",    0.92, 1.00),   # 设置/账户
]

def classify_fine(project_name):
    """细颗粒度分类"""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        print(f"  [跳过] {project_name}: Downloads不存在")
        return 0
    
    # 获取截图列表
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        print(f"  [跳过] {project_name}: 无截图")
        return 0
    
    # 清空并重建Screens
    if os.path.exists(screens_path):
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 按细颗粒度分类
    count = 0
    for phase_code, phase_name, start_pct, end_pct in FINE_PHASES:
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)
        
        # 确保每个阶段至少有内容时才处理
        if start_idx >= total:
            continue
            
        end_idx = min(end_idx, total)
        
        phase_screens = screenshots[start_idx:end_idx]
        
        for step, orig_file in enumerate(phase_screens, 1):
            src = os.path.join(downloads_path, orig_file)
            new_name = f"{phase_code}_{phase_name}_{step:02d}.png"
            dst = os.path.join(screens_path, new_name)
            shutil.copy2(src, dst)
            count += 1
    
    return count

def generate_summary():
    """生成分类汇总"""
    print("\n" + "=" * 70)
    print("分类汇总")
    print("=" * 70)
    
    # 收集所有产品的阶段数据
    all_stats = {}
    
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        screens_path = os.path.join(proj_path, "Screens")
        
        if not os.path.isdir(screens_path):
            continue
        
        all_stats[proj_name] = {}
        
        for f in os.listdir(screens_path):
            if f.endswith('.png'):
                parts = f.split('_')
                if len(parts) >= 2:
                    phase_key = f"{parts[0]}_{parts[1]}"
                    all_stats[proj_name][phase_key] = all_stats[proj_name].get(phase_key, 0) + 1
    
    # 打印对比表
    if not all_stats:
        print("无数据")
        return
    
    # 收集所有阶段
    all_phases = set()
    for stats in all_stats.values():
        all_phases.update(stats.keys())
    all_phases = sorted(all_phases)
    
    # 打印表头
    products = list(all_stats.keys())
    header = f"{'阶段':<15}" + "".join(f"{p.replace('_Analysis',''):<12}" for p in products)
    print(header)
    print("-" * len(header))
    
    # 打印每行
    for phase in all_phases:
        row = f"{phase:<15}"
        for prod in products:
            cnt = all_stats[prod].get(phase, 0)
            row += f"{cnt:<12}"
        print(row)
    
    print("-" * len(header))
    
    # 总计
    row = f"{'总计':<15}"
    for prod in products:
        total = sum(all_stats[prod].values())
        row += f"{total:<12}"
    print(row)

def main():
    print("=" * 70)
    print("细颗粒度分类 - 支持逐页对比")
    print("=" * 70)
    print("\n阶段定义:")
    for code, name, s, e in FINE_PHASES:
        pct = f"{int(s*100)}-{int(e*100)}%"
        print(f"  {code}_{name:<12} {pct}")
    
    print("\n" + "-" * 70)
    print("开始分类...")
    print("-" * 70)
    
    # 获取所有项目
    projects = [d for d in os.listdir(PROJECTS_DIR) 
                if os.path.isdir(os.path.join(PROJECTS_DIR, d, "Downloads"))]
    
    for proj in projects:
        count = classify_fine(proj)
        print(f"  {proj.replace('_Analysis',''):<20} → {count} 张")
    
    # 生成汇总
    generate_summary()
    
    print("\n✅ 分类完成！刷新网页查看效果")

if __name__ == "__main__":
    main()






"""
细颗粒度分类 - 支持逐页对比
每个阶段控制在5-10张左右，便于精确对比
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 细颗粒度阶段定义（健身/健康类App通用）
# 格式: (阶段代码, 阶段名, 预估占比起点, 预估占比终点)
FINE_PHASES = [
    # Onboarding 拆分为多个子阶段
    ("01", "Launch",      0.00, 0.02),   # 启动页 1-2张
    ("02", "Welcome",     0.02, 0.05),   # 欢迎/价值主张 2-3张
    ("03", "Auth",        0.05, 0.10),   # 登录/注册 3-5张
    ("04", "Goals",       0.10, 0.15),   # 目标设置 3-5张
    ("05", "Profile",     0.15, 0.22),   # 个人信息 5-7张
    ("06", "Activity",    0.22, 0.27),   # 活动水平 3-5张
    ("07", "Preference",  0.27, 0.32),   # 偏好设置 3-5张
    ("08", "Motivation",  0.32, 0.38),   # 激励/预期 4-6张
    ("09", "Permissions", 0.38, 0.42),   # 权限请求 2-4张
    ("10", "Paywall",     0.42, 0.50),   # 付费墙 5-8张
    # 主App功能
    ("11", "Home",        0.50, 0.58),   # 首页/仪表盘
    ("12", "Logging",     0.58, 0.68),   # 记录功能
    ("13", "Stats",       0.68, 0.75),   # 统计/报表
    ("14", "Features",    0.75, 0.85),   # 其他功能
    ("15", "Social",      0.85, 0.92),   # 社交功能
    ("16", "Settings",    0.92, 1.00),   # 设置/账户
]

def classify_fine(project_name):
    """细颗粒度分类"""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        print(f"  [跳过] {project_name}: Downloads不存在")
        return 0
    
    # 获取截图列表
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        print(f"  [跳过] {project_name}: 无截图")
        return 0
    
    # 清空并重建Screens
    if os.path.exists(screens_path):
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 按细颗粒度分类
    count = 0
    for phase_code, phase_name, start_pct, end_pct in FINE_PHASES:
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)
        
        # 确保每个阶段至少有内容时才处理
        if start_idx >= total:
            continue
            
        end_idx = min(end_idx, total)
        
        phase_screens = screenshots[start_idx:end_idx]
        
        for step, orig_file in enumerate(phase_screens, 1):
            src = os.path.join(downloads_path, orig_file)
            new_name = f"{phase_code}_{phase_name}_{step:02d}.png"
            dst = os.path.join(screens_path, new_name)
            shutil.copy2(src, dst)
            count += 1
    
    return count

def generate_summary():
    """生成分类汇总"""
    print("\n" + "=" * 70)
    print("分类汇总")
    print("=" * 70)
    
    # 收集所有产品的阶段数据
    all_stats = {}
    
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        screens_path = os.path.join(proj_path, "Screens")
        
        if not os.path.isdir(screens_path):
            continue
        
        all_stats[proj_name] = {}
        
        for f in os.listdir(screens_path):
            if f.endswith('.png'):
                parts = f.split('_')
                if len(parts) >= 2:
                    phase_key = f"{parts[0]}_{parts[1]}"
                    all_stats[proj_name][phase_key] = all_stats[proj_name].get(phase_key, 0) + 1
    
    # 打印对比表
    if not all_stats:
        print("无数据")
        return
    
    # 收集所有阶段
    all_phases = set()
    for stats in all_stats.values():
        all_phases.update(stats.keys())
    all_phases = sorted(all_phases)
    
    # 打印表头
    products = list(all_stats.keys())
    header = f"{'阶段':<15}" + "".join(f"{p.replace('_Analysis',''):<12}" for p in products)
    print(header)
    print("-" * len(header))
    
    # 打印每行
    for phase in all_phases:
        row = f"{phase:<15}"
        for prod in products:
            cnt = all_stats[prod].get(phase, 0)
            row += f"{cnt:<12}"
        print(row)
    
    print("-" * len(header))
    
    # 总计
    row = f"{'总计':<15}"
    for prod in products:
        total = sum(all_stats[prod].values())
        row += f"{total:<12}"
    print(row)

def main():
    print("=" * 70)
    print("细颗粒度分类 - 支持逐页对比")
    print("=" * 70)
    print("\n阶段定义:")
    for code, name, s, e in FINE_PHASES:
        pct = f"{int(s*100)}-{int(e*100)}%"
        print(f"  {code}_{name:<12} {pct}")
    
    print("\n" + "-" * 70)
    print("开始分类...")
    print("-" * 70)
    
    # 获取所有项目
    projects = [d for d in os.listdir(PROJECTS_DIR) 
                if os.path.isdir(os.path.join(PROJECTS_DIR, d, "Downloads"))]
    
    for proj in projects:
        count = classify_fine(proj)
        print(f"  {proj.replace('_Analysis',''):<20} → {count} 张")
    
    # 生成汇总
    generate_summary()
    
    print("\n✅ 分类完成！刷新网页查看效果")

if __name__ == "__main__":
    main()







"""
细颗粒度分类 - 支持逐页对比
每个阶段控制在5-10张左右，便于精确对比
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 细颗粒度阶段定义（健身/健康类App通用）
# 格式: (阶段代码, 阶段名, 预估占比起点, 预估占比终点)
FINE_PHASES = [
    # Onboarding 拆分为多个子阶段
    ("01", "Launch",      0.00, 0.02),   # 启动页 1-2张
    ("02", "Welcome",     0.02, 0.05),   # 欢迎/价值主张 2-3张
    ("03", "Auth",        0.05, 0.10),   # 登录/注册 3-5张
    ("04", "Goals",       0.10, 0.15),   # 目标设置 3-5张
    ("05", "Profile",     0.15, 0.22),   # 个人信息 5-7张
    ("06", "Activity",    0.22, 0.27),   # 活动水平 3-5张
    ("07", "Preference",  0.27, 0.32),   # 偏好设置 3-5张
    ("08", "Motivation",  0.32, 0.38),   # 激励/预期 4-6张
    ("09", "Permissions", 0.38, 0.42),   # 权限请求 2-4张
    ("10", "Paywall",     0.42, 0.50),   # 付费墙 5-8张
    # 主App功能
    ("11", "Home",        0.50, 0.58),   # 首页/仪表盘
    ("12", "Logging",     0.58, 0.68),   # 记录功能
    ("13", "Stats",       0.68, 0.75),   # 统计/报表
    ("14", "Features",    0.75, 0.85),   # 其他功能
    ("15", "Social",      0.85, 0.92),   # 社交功能
    ("16", "Settings",    0.92, 1.00),   # 设置/账户
]

def classify_fine(project_name):
    """细颗粒度分类"""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        print(f"  [跳过] {project_name}: Downloads不存在")
        return 0
    
    # 获取截图列表
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        print(f"  [跳过] {project_name}: 无截图")
        return 0
    
    # 清空并重建Screens
    if os.path.exists(screens_path):
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 按细颗粒度分类
    count = 0
    for phase_code, phase_name, start_pct, end_pct in FINE_PHASES:
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)
        
        # 确保每个阶段至少有内容时才处理
        if start_idx >= total:
            continue
            
        end_idx = min(end_idx, total)
        
        phase_screens = screenshots[start_idx:end_idx]
        
        for step, orig_file in enumerate(phase_screens, 1):
            src = os.path.join(downloads_path, orig_file)
            new_name = f"{phase_code}_{phase_name}_{step:02d}.png"
            dst = os.path.join(screens_path, new_name)
            shutil.copy2(src, dst)
            count += 1
    
    return count

def generate_summary():
    """生成分类汇总"""
    print("\n" + "=" * 70)
    print("分类汇总")
    print("=" * 70)
    
    # 收集所有产品的阶段数据
    all_stats = {}
    
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        screens_path = os.path.join(proj_path, "Screens")
        
        if not os.path.isdir(screens_path):
            continue
        
        all_stats[proj_name] = {}
        
        for f in os.listdir(screens_path):
            if f.endswith('.png'):
                parts = f.split('_')
                if len(parts) >= 2:
                    phase_key = f"{parts[0]}_{parts[1]}"
                    all_stats[proj_name][phase_key] = all_stats[proj_name].get(phase_key, 0) + 1
    
    # 打印对比表
    if not all_stats:
        print("无数据")
        return
    
    # 收集所有阶段
    all_phases = set()
    for stats in all_stats.values():
        all_phases.update(stats.keys())
    all_phases = sorted(all_phases)
    
    # 打印表头
    products = list(all_stats.keys())
    header = f"{'阶段':<15}" + "".join(f"{p.replace('_Analysis',''):<12}" for p in products)
    print(header)
    print("-" * len(header))
    
    # 打印每行
    for phase in all_phases:
        row = f"{phase:<15}"
        for prod in products:
            cnt = all_stats[prod].get(phase, 0)
            row += f"{cnt:<12}"
        print(row)
    
    print("-" * len(header))
    
    # 总计
    row = f"{'总计':<15}"
    for prod in products:
        total = sum(all_stats[prod].values())
        row += f"{total:<12}"
    print(row)

def main():
    print("=" * 70)
    print("细颗粒度分类 - 支持逐页对比")
    print("=" * 70)
    print("\n阶段定义:")
    for code, name, s, e in FINE_PHASES:
        pct = f"{int(s*100)}-{int(e*100)}%"
        print(f"  {code}_{name:<12} {pct}")
    
    print("\n" + "-" * 70)
    print("开始分类...")
    print("-" * 70)
    
    # 获取所有项目
    projects = [d for d in os.listdir(PROJECTS_DIR) 
                if os.path.isdir(os.path.join(PROJECTS_DIR, d, "Downloads"))]
    
    for proj in projects:
        count = classify_fine(proj)
        print(f"  {proj.replace('_Analysis',''):<20} → {count} 张")
    
    # 生成汇总
    generate_summary()
    
    print("\n✅ 分类完成！刷新网页查看效果")

if __name__ == "__main__":
    main()






"""
细颗粒度分类 - 支持逐页对比
每个阶段控制在5-10张左右，便于精确对比
"""

import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 细颗粒度阶段定义（健身/健康类App通用）
# 格式: (阶段代码, 阶段名, 预估占比起点, 预估占比终点)
FINE_PHASES = [
    # Onboarding 拆分为多个子阶段
    ("01", "Launch",      0.00, 0.02),   # 启动页 1-2张
    ("02", "Welcome",     0.02, 0.05),   # 欢迎/价值主张 2-3张
    ("03", "Auth",        0.05, 0.10),   # 登录/注册 3-5张
    ("04", "Goals",       0.10, 0.15),   # 目标设置 3-5张
    ("05", "Profile",     0.15, 0.22),   # 个人信息 5-7张
    ("06", "Activity",    0.22, 0.27),   # 活动水平 3-5张
    ("07", "Preference",  0.27, 0.32),   # 偏好设置 3-5张
    ("08", "Motivation",  0.32, 0.38),   # 激励/预期 4-6张
    ("09", "Permissions", 0.38, 0.42),   # 权限请求 2-4张
    ("10", "Paywall",     0.42, 0.50),   # 付费墙 5-8张
    # 主App功能
    ("11", "Home",        0.50, 0.58),   # 首页/仪表盘
    ("12", "Logging",     0.58, 0.68),   # 记录功能
    ("13", "Stats",       0.68, 0.75),   # 统计/报表
    ("14", "Features",    0.75, 0.85),   # 其他功能
    ("15", "Social",      0.85, 0.92),   # 社交功能
    ("16", "Settings",    0.92, 1.00),   # 设置/账户
]

def classify_fine(project_name):
    """细颗粒度分类"""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path):
        print(f"  [跳过] {project_name}: Downloads不存在")
        return 0
    
    # 获取截图列表
    screenshots = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    total = len(screenshots)
    
    if total == 0:
        print(f"  [跳过] {project_name}: 无截图")
        return 0
    
    # 清空并重建Screens
    if os.path.exists(screens_path):
        shutil.rmtree(screens_path)
    os.makedirs(screens_path)
    
    # 按细颗粒度分类
    count = 0
    for phase_code, phase_name, start_pct, end_pct in FINE_PHASES:
        start_idx = int(total * start_pct)
        end_idx = int(total * end_pct)
        
        # 确保每个阶段至少有内容时才处理
        if start_idx >= total:
            continue
            
        end_idx = min(end_idx, total)
        
        phase_screens = screenshots[start_idx:end_idx]
        
        for step, orig_file in enumerate(phase_screens, 1):
            src = os.path.join(downloads_path, orig_file)
            new_name = f"{phase_code}_{phase_name}_{step:02d}.png"
            dst = os.path.join(screens_path, new_name)
            shutil.copy2(src, dst)
            count += 1
    
    return count

def generate_summary():
    """生成分类汇总"""
    print("\n" + "=" * 70)
    print("分类汇总")
    print("=" * 70)
    
    # 收集所有产品的阶段数据
    all_stats = {}
    
    for proj_name in os.listdir(PROJECTS_DIR):
        proj_path = os.path.join(PROJECTS_DIR, proj_name)
        screens_path = os.path.join(proj_path, "Screens")
        
        if not os.path.isdir(screens_path):
            continue
        
        all_stats[proj_name] = {}
        
        for f in os.listdir(screens_path):
            if f.endswith('.png'):
                parts = f.split('_')
                if len(parts) >= 2:
                    phase_key = f"{parts[0]}_{parts[1]}"
                    all_stats[proj_name][phase_key] = all_stats[proj_name].get(phase_key, 0) + 1
    
    # 打印对比表
    if not all_stats:
        print("无数据")
        return
    
    # 收集所有阶段
    all_phases = set()
    for stats in all_stats.values():
        all_phases.update(stats.keys())
    all_phases = sorted(all_phases)
    
    # 打印表头
    products = list(all_stats.keys())
    header = f"{'阶段':<15}" + "".join(f"{p.replace('_Analysis',''):<12}" for p in products)
    print(header)
    print("-" * len(header))
    
    # 打印每行
    for phase in all_phases:
        row = f"{phase:<15}"
        for prod in products:
            cnt = all_stats[prod].get(phase, 0)
            row += f"{cnt:<12}"
        print(row)
    
    print("-" * len(header))
    
    # 总计
    row = f"{'总计':<15}"
    for prod in products:
        total = sum(all_stats[prod].values())
        row += f"{total:<12}"
    print(row)

def main():
    print("=" * 70)
    print("细颗粒度分类 - 支持逐页对比")
    print("=" * 70)
    print("\n阶段定义:")
    for code, name, s, e in FINE_PHASES:
        pct = f"{int(s*100)}-{int(e*100)}%"
        print(f"  {code}_{name:<12} {pct}")
    
    print("\n" + "-" * 70)
    print("开始分类...")
    print("-" * 70)
    
    # 获取所有项目
    projects = [d for d in os.listdir(PROJECTS_DIR) 
                if os.path.isdir(os.path.join(PROJECTS_DIR, d, "Downloads"))]
    
    for proj in projects:
        count = classify_fine(proj)
        print(f"  {proj.replace('_Analysis',''):<20} → {count} 张")
    
    # 生成汇总
    generate_summary()
    
    print("\n✅ 分类完成！刷新网页查看效果")

if __name__ == "__main__":
    main()






















