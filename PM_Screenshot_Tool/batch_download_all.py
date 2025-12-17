# -*- coding: utf-8 -*-
"""批量下载所有竞品"""

import os
import sys
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# 已下载的产品
DOWNLOADED = [
    'myfitnesspal', 'runna', 'strava', 'calm', 'cal ai', 'flo'
]

# 从competitors.json获取待下载列表
def get_pending_apps():
    with open('data/competitors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pending = []
    for app in data.get('top30', []):
        name = app.get('app_name', '')
        name_lower = name.lower()
        
        # 检查是否已下载
        is_downloaded = False
        for d in DOWNLOADED:
            if d in name_lower or name_lower in d:
                is_downloaded = True
                break
        
        if not is_downloaded and app.get('priority') in ['P0', 'P1']:
            pending.append({
                'name': name,
                'priority': app.get('priority'),
                'revenue': app.get('revenue', 0)
            })
    
    return pending

def main():
    pending = get_pending_apps()
    
    print("=" * 60)
    print("  待下载竞品列表")
    print("=" * 60)
    print()
    
    for i, app in enumerate(pending, 1):
        rev = app['revenue'] / 1000000
        print(f"  {i:2d}. [{app['priority']}] {app['name']:40s} ${rev:.1f}M")
    
    print()
    print(f"  总计: {len(pending)} 个产品")
    print("=" * 60)
    
    # 询问是否开始
    print("\n准备下载？")
    print("  - 每个产品约需1-2分钟")
    print("  - 需要Chrome保持打开状态")
    print("  - 确保已登录screensdesign.com")
    print()
    
    return pending

if __name__ == "__main__":
    pending = main()


"""批量下载所有竞品"""

import os
import sys
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# 已下载的产品
DOWNLOADED = [
    'myfitnesspal', 'runna', 'strava', 'calm', 'cal ai', 'flo'
]

# 从competitors.json获取待下载列表
def get_pending_apps():
    with open('data/competitors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pending = []
    for app in data.get('top30', []):
        name = app.get('app_name', '')
        name_lower = name.lower()
        
        # 检查是否已下载
        is_downloaded = False
        for d in DOWNLOADED:
            if d in name_lower or name_lower in d:
                is_downloaded = True
                break
        
        if not is_downloaded and app.get('priority') in ['P0', 'P1']:
            pending.append({
                'name': name,
                'priority': app.get('priority'),
                'revenue': app.get('revenue', 0)
            })
    
    return pending

def main():
    pending = get_pending_apps()
    
    print("=" * 60)
    print("  待下载竞品列表")
    print("=" * 60)
    print()
    
    for i, app in enumerate(pending, 1):
        rev = app['revenue'] / 1000000
        print(f"  {i:2d}. [{app['priority']}] {app['name']:40s} ${rev:.1f}M")
    
    print()
    print(f"  总计: {len(pending)} 个产品")
    print("=" * 60)
    
    # 询问是否开始
    print("\n准备下载？")
    print("  - 每个产品约需1-2分钟")
    print("  - 需要Chrome保持打开状态")
    print("  - 确保已登录screensdesign.com")
    print()
    
    return pending

if __name__ == "__main__":
    pending = main()


"""批量下载所有竞品"""

import os
import sys
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# 已下载的产品
DOWNLOADED = [
    'myfitnesspal', 'runna', 'strava', 'calm', 'cal ai', 'flo'
]

# 从competitors.json获取待下载列表
def get_pending_apps():
    with open('data/competitors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pending = []
    for app in data.get('top30', []):
        name = app.get('app_name', '')
        name_lower = name.lower()
        
        # 检查是否已下载
        is_downloaded = False
        for d in DOWNLOADED:
            if d in name_lower or name_lower in d:
                is_downloaded = True
                break
        
        if not is_downloaded and app.get('priority') in ['P0', 'P1']:
            pending.append({
                'name': name,
                'priority': app.get('priority'),
                'revenue': app.get('revenue', 0)
            })
    
    return pending

def main():
    pending = get_pending_apps()
    
    print("=" * 60)
    print("  待下载竞品列表")
    print("=" * 60)
    print()
    
    for i, app in enumerate(pending, 1):
        rev = app['revenue'] / 1000000
        print(f"  {i:2d}. [{app['priority']}] {app['name']:40s} ${rev:.1f}M")
    
    print()
    print(f"  总计: {len(pending)} 个产品")
    print("=" * 60)
    
    # 询问是否开始
    print("\n准备下载？")
    print("  - 每个产品约需1-2分钟")
    print("  - 需要Chrome保持打开状态")
    print("  - 确保已登录screensdesign.com")
    print()
    
    return pending

if __name__ == "__main__":
    pending = main()


"""批量下载所有竞品"""

import os
import sys
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# 已下载的产品
DOWNLOADED = [
    'myfitnesspal', 'runna', 'strava', 'calm', 'cal ai', 'flo'
]

# 从competitors.json获取待下载列表
def get_pending_apps():
    with open('data/competitors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pending = []
    for app in data.get('top30', []):
        name = app.get('app_name', '')
        name_lower = name.lower()
        
        # 检查是否已下载
        is_downloaded = False
        for d in DOWNLOADED:
            if d in name_lower or name_lower in d:
                is_downloaded = True
                break
        
        if not is_downloaded and app.get('priority') in ['P0', 'P1']:
            pending.append({
                'name': name,
                'priority': app.get('priority'),
                'revenue': app.get('revenue', 0)
            })
    
    return pending

def main():
    pending = get_pending_apps()
    
    print("=" * 60)
    print("  待下载竞品列表")
    print("=" * 60)
    print()
    
    for i, app in enumerate(pending, 1):
        rev = app['revenue'] / 1000000
        print(f"  {i:2d}. [{app['priority']}] {app['name']:40s} ${rev:.1f}M")
    
    print()
    print(f"  总计: {len(pending)} 个产品")
    print("=" * 60)
    
    # 询问是否开始
    print("\n准备下载？")
    print("  - 每个产品约需1-2分钟")
    print("  - 需要Chrome保持打开状态")
    print("  - 确保已登录screensdesign.com")
    print()
    
    return pending

if __name__ == "__main__":
    pending = main()



"""批量下载所有竞品"""

import os
import sys
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# 已下载的产品
DOWNLOADED = [
    'myfitnesspal', 'runna', 'strava', 'calm', 'cal ai', 'flo'
]

# 从competitors.json获取待下载列表
def get_pending_apps():
    with open('data/competitors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pending = []
    for app in data.get('top30', []):
        name = app.get('app_name', '')
        name_lower = name.lower()
        
        # 检查是否已下载
        is_downloaded = False
        for d in DOWNLOADED:
            if d in name_lower or name_lower in d:
                is_downloaded = True
                break
        
        if not is_downloaded and app.get('priority') in ['P0', 'P1']:
            pending.append({
                'name': name,
                'priority': app.get('priority'),
                'revenue': app.get('revenue', 0)
            })
    
    return pending

def main():
    pending = get_pending_apps()
    
    print("=" * 60)
    print("  待下载竞品列表")
    print("=" * 60)
    print()
    
    for i, app in enumerate(pending, 1):
        rev = app['revenue'] / 1000000
        print(f"  {i:2d}. [{app['priority']}] {app['name']:40s} ${rev:.1f}M")
    
    print()
    print(f"  总计: {len(pending)} 个产品")
    print("=" * 60)
    
    # 询问是否开始
    print("\n准备下载？")
    print("  - 每个产品约需1-2分钟")
    print("  - 需要Chrome保持打开状态")
    print("  - 确保已登录screensdesign.com")
    print()
    
    return pending

if __name__ == "__main__":
    pending = main()


"""批量下载所有竞品"""

import os
import sys
import json
import time
sys.stdout.reconfigure(encoding='utf-8')

# 已下载的产品
DOWNLOADED = [
    'myfitnesspal', 'runna', 'strava', 'calm', 'cal ai', 'flo'
]

# 从competitors.json获取待下载列表
def get_pending_apps():
    with open('data/competitors.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pending = []
    for app in data.get('top30', []):
        name = app.get('app_name', '')
        name_lower = name.lower()
        
        # 检查是否已下载
        is_downloaded = False
        for d in DOWNLOADED:
            if d in name_lower or name_lower in d:
                is_downloaded = True
                break
        
        if not is_downloaded and app.get('priority') in ['P0', 'P1']:
            pending.append({
                'name': name,
                'priority': app.get('priority'),
                'revenue': app.get('revenue', 0)
            })
    
    return pending

def main():
    pending = get_pending_apps()
    
    print("=" * 60)
    print("  待下载竞品列表")
    print("=" * 60)
    print()
    
    for i, app in enumerate(pending, 1):
        rev = app['revenue'] / 1000000
        print(f"  {i:2d}. [{app['priority']}] {app['name']:40s} ${rev:.1f}M")
    
    print()
    print(f"  总计: {len(pending)} 个产品")
    print("=" * 60)
    
    # 询问是否开始
    print("\n准备下载？")
    print("  - 每个产品约需1-2分钟")
    print("  - 需要Chrome保持打开状态")
    print("  - 确保已登录screensdesign.com")
    print()
    
    return pending

if __name__ == "__main__":
    pending = main()


















