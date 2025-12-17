# -*- coding: utf-8 -*-
"""检查已下载产品和竞品列表"""

import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# 检查已下载的产品
projects_dir = 'projects'
downloaded = []
for name in os.listdir(projects_dir):
    path = os.path.join(projects_dir, name)
    if os.path.isdir(path) and name.endswith('_Analysis'):
        screens_dir = os.path.join(path, 'Screens')
        count = 0
        if os.path.exists(screens_dir):
            count = len([f for f in os.listdir(screens_dir) if f.endswith('.png')])
        downloaded.append({'name': name.replace('_Analysis', ''), 'screens': count})

print('=== 已下载产品 ===')
for p in sorted(downloaded, key=lambda x: -x['screens']):
    status = '✓' if p['screens'] > 0 else '✗'
    print(f"  {status} {p['name']:30s} {p['screens']:3d} 张")
print(f"\n总计: {len(downloaded)} 个产品")

# 检查竞品列表
competitor_file = 'data/competitors_priority.json'
if os.path.exists(competitor_file):
    with open(competitor_file, 'r', encoding='utf-8') as f:
        competitors = json.load(f)
    
    downloaded_names = [p['name'].lower().replace('_', ' ').replace('-', ' ') for p in downloaded]
    
    print('\n=== 待下载竞品 ===')
    pending = []
    for c in competitors.get('P0', []) + competitors.get('P1', []):
        name = c.get('name', c.get('App Name', ''))
        name_lower = name.lower().replace('_', ' ').replace('-', ' ')
        if name_lower not in downloaded_names:
            pending.append(name)
    
    for name in pending[:20]:  # 只显示前20个
        print(f"  → {name}")
    
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 个")
    
    print(f"\n待下载: {len(pending)} 个")
else:
    print('\n[!] 未找到竞品列表文件')


"""检查已下载产品和竞品列表"""

import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# 检查已下载的产品
projects_dir = 'projects'
downloaded = []
for name in os.listdir(projects_dir):
    path = os.path.join(projects_dir, name)
    if os.path.isdir(path) and name.endswith('_Analysis'):
        screens_dir = os.path.join(path, 'Screens')
        count = 0
        if os.path.exists(screens_dir):
            count = len([f for f in os.listdir(screens_dir) if f.endswith('.png')])
        downloaded.append({'name': name.replace('_Analysis', ''), 'screens': count})

print('=== 已下载产品 ===')
for p in sorted(downloaded, key=lambda x: -x['screens']):
    status = '✓' if p['screens'] > 0 else '✗'
    print(f"  {status} {p['name']:30s} {p['screens']:3d} 张")
print(f"\n总计: {len(downloaded)} 个产品")

# 检查竞品列表
competitor_file = 'data/competitors_priority.json'
if os.path.exists(competitor_file):
    with open(competitor_file, 'r', encoding='utf-8') as f:
        competitors = json.load(f)
    
    downloaded_names = [p['name'].lower().replace('_', ' ').replace('-', ' ') for p in downloaded]
    
    print('\n=== 待下载竞品 ===')
    pending = []
    for c in competitors.get('P0', []) + competitors.get('P1', []):
        name = c.get('name', c.get('App Name', ''))
        name_lower = name.lower().replace('_', ' ').replace('-', ' ')
        if name_lower not in downloaded_names:
            pending.append(name)
    
    for name in pending[:20]:  # 只显示前20个
        print(f"  → {name}")
    
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 个")
    
    print(f"\n待下载: {len(pending)} 个")
else:
    print('\n[!] 未找到竞品列表文件')


"""检查已下载产品和竞品列表"""

import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# 检查已下载的产品
projects_dir = 'projects'
downloaded = []
for name in os.listdir(projects_dir):
    path = os.path.join(projects_dir, name)
    if os.path.isdir(path) and name.endswith('_Analysis'):
        screens_dir = os.path.join(path, 'Screens')
        count = 0
        if os.path.exists(screens_dir):
            count = len([f for f in os.listdir(screens_dir) if f.endswith('.png')])
        downloaded.append({'name': name.replace('_Analysis', ''), 'screens': count})

print('=== 已下载产品 ===')
for p in sorted(downloaded, key=lambda x: -x['screens']):
    status = '✓' if p['screens'] > 0 else '✗'
    print(f"  {status} {p['name']:30s} {p['screens']:3d} 张")
print(f"\n总计: {len(downloaded)} 个产品")

# 检查竞品列表
competitor_file = 'data/competitors_priority.json'
if os.path.exists(competitor_file):
    with open(competitor_file, 'r', encoding='utf-8') as f:
        competitors = json.load(f)
    
    downloaded_names = [p['name'].lower().replace('_', ' ').replace('-', ' ') for p in downloaded]
    
    print('\n=== 待下载竞品 ===')
    pending = []
    for c in competitors.get('P0', []) + competitors.get('P1', []):
        name = c.get('name', c.get('App Name', ''))
        name_lower = name.lower().replace('_', ' ').replace('-', ' ')
        if name_lower not in downloaded_names:
            pending.append(name)
    
    for name in pending[:20]:  # 只显示前20个
        print(f"  → {name}")
    
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 个")
    
    print(f"\n待下载: {len(pending)} 个")
else:
    print('\n[!] 未找到竞品列表文件')


"""检查已下载产品和竞品列表"""

import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# 检查已下载的产品
projects_dir = 'projects'
downloaded = []
for name in os.listdir(projects_dir):
    path = os.path.join(projects_dir, name)
    if os.path.isdir(path) and name.endswith('_Analysis'):
        screens_dir = os.path.join(path, 'Screens')
        count = 0
        if os.path.exists(screens_dir):
            count = len([f for f in os.listdir(screens_dir) if f.endswith('.png')])
        downloaded.append({'name': name.replace('_Analysis', ''), 'screens': count})

print('=== 已下载产品 ===')
for p in sorted(downloaded, key=lambda x: -x['screens']):
    status = '✓' if p['screens'] > 0 else '✗'
    print(f"  {status} {p['name']:30s} {p['screens']:3d} 张")
print(f"\n总计: {len(downloaded)} 个产品")

# 检查竞品列表
competitor_file = 'data/competitors_priority.json'
if os.path.exists(competitor_file):
    with open(competitor_file, 'r', encoding='utf-8') as f:
        competitors = json.load(f)
    
    downloaded_names = [p['name'].lower().replace('_', ' ').replace('-', ' ') for p in downloaded]
    
    print('\n=== 待下载竞品 ===')
    pending = []
    for c in competitors.get('P0', []) + competitors.get('P1', []):
        name = c.get('name', c.get('App Name', ''))
        name_lower = name.lower().replace('_', ' ').replace('-', ' ')
        if name_lower not in downloaded_names:
            pending.append(name)
    
    for name in pending[:20]:  # 只显示前20个
        print(f"  → {name}")
    
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 个")
    
    print(f"\n待下载: {len(pending)} 个")
else:
    print('\n[!] 未找到竞品列表文件')



"""检查已下载产品和竞品列表"""

import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# 检查已下载的产品
projects_dir = 'projects'
downloaded = []
for name in os.listdir(projects_dir):
    path = os.path.join(projects_dir, name)
    if os.path.isdir(path) and name.endswith('_Analysis'):
        screens_dir = os.path.join(path, 'Screens')
        count = 0
        if os.path.exists(screens_dir):
            count = len([f for f in os.listdir(screens_dir) if f.endswith('.png')])
        downloaded.append({'name': name.replace('_Analysis', ''), 'screens': count})

print('=== 已下载产品 ===')
for p in sorted(downloaded, key=lambda x: -x['screens']):
    status = '✓' if p['screens'] > 0 else '✗'
    print(f"  {status} {p['name']:30s} {p['screens']:3d} 张")
print(f"\n总计: {len(downloaded)} 个产品")

# 检查竞品列表
competitor_file = 'data/competitors_priority.json'
if os.path.exists(competitor_file):
    with open(competitor_file, 'r', encoding='utf-8') as f:
        competitors = json.load(f)
    
    downloaded_names = [p['name'].lower().replace('_', ' ').replace('-', ' ') for p in downloaded]
    
    print('\n=== 待下载竞品 ===')
    pending = []
    for c in competitors.get('P0', []) + competitors.get('P1', []):
        name = c.get('name', c.get('App Name', ''))
        name_lower = name.lower().replace('_', ' ').replace('-', ' ')
        if name_lower not in downloaded_names:
            pending.append(name)
    
    for name in pending[:20]:  # 只显示前20个
        print(f"  → {name}")
    
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 个")
    
    print(f"\n待下载: {len(pending)} 个")
else:
    print('\n[!] 未找到竞品列表文件')


"""检查已下载产品和竞品列表"""

import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# 检查已下载的产品
projects_dir = 'projects'
downloaded = []
for name in os.listdir(projects_dir):
    path = os.path.join(projects_dir, name)
    if os.path.isdir(path) and name.endswith('_Analysis'):
        screens_dir = os.path.join(path, 'Screens')
        count = 0
        if os.path.exists(screens_dir):
            count = len([f for f in os.listdir(screens_dir) if f.endswith('.png')])
        downloaded.append({'name': name.replace('_Analysis', ''), 'screens': count})

print('=== 已下载产品 ===')
for p in sorted(downloaded, key=lambda x: -x['screens']):
    status = '✓' if p['screens'] > 0 else '✗'
    print(f"  {status} {p['name']:30s} {p['screens']:3d} 张")
print(f"\n总计: {len(downloaded)} 个产品")

# 检查竞品列表
competitor_file = 'data/competitors_priority.json'
if os.path.exists(competitor_file):
    with open(competitor_file, 'r', encoding='utf-8') as f:
        competitors = json.load(f)
    
    downloaded_names = [p['name'].lower().replace('_', ' ').replace('-', ' ') for p in downloaded]
    
    print('\n=== 待下载竞品 ===')
    pending = []
    for c in competitors.get('P0', []) + competitors.get('P1', []):
        name = c.get('name', c.get('App Name', ''))
        name_lower = name.lower().replace('_', ' ').replace('-', ' ')
        if name_lower not in downloaded_names:
            pending.append(name)
    
    for name in pending[:20]:  # 只显示前20个
        print(f"  → {name}")
    
    if len(pending) > 20:
        print(f"  ... 还有 {len(pending) - 20} 个")
    
    print(f"\n待下载: {len(pending)} 个")
else:
    print('\n[!] 未找到竞品列表文件')


















