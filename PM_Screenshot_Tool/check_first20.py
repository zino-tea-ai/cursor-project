# -*- coding: utf-8 -*-
"""检查Calm前20张截图分类"""

import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前20张
first_20 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 20:
        first_20.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'auto_fixed': info.get('auto_fixed', False),
            'original': info.get('original_type', '')
        })

first_20.sort(key=lambda x: x['idx'])

print('=== Calm前20张分类 ===')
print()
for s in first_20:
    fix_mark = f"(原:{s['original']})" if s['auto_fixed'] else ''
    print(f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']:20s} {fix_mark}")


"""检查Calm前20张截图分类"""

import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前20张
first_20 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 20:
        first_20.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'auto_fixed': info.get('auto_fixed', False),
            'original': info.get('original_type', '')
        })

first_20.sort(key=lambda x: x['idx'])

print('=== Calm前20张分类 ===')
print()
for s in first_20:
    fix_mark = f"(原:{s['original']})" if s['auto_fixed'] else ''
    print(f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']:20s} {fix_mark}")


"""检查Calm前20张截图分类"""

import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前20张
first_20 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 20:
        first_20.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'auto_fixed': info.get('auto_fixed', False),
            'original': info.get('original_type', '')
        })

first_20.sort(key=lambda x: x['idx'])

print('=== Calm前20张分类 ===')
print()
for s in first_20:
    fix_mark = f"(原:{s['original']})" if s['auto_fixed'] else ''
    print(f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']:20s} {fix_mark}")


"""检查Calm前20张截图分类"""

import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前20张
first_20 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 20:
        first_20.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'auto_fixed': info.get('auto_fixed', False),
            'original': info.get('original_type', '')
        })

first_20.sort(key=lambda x: x['idx'])

print('=== Calm前20张分类 ===')
print()
for s in first_20:
    fix_mark = f"(原:{s['original']})" if s['auto_fixed'] else ''
    print(f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']:20s} {fix_mark}")



"""检查Calm前20张截图分类"""

import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前20张
first_20 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 20:
        first_20.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'auto_fixed': info.get('auto_fixed', False),
            'original': info.get('original_type', '')
        })

first_20.sort(key=lambda x: x['idx'])

print('=== Calm前20张分类 ===')
print()
for s in first_20:
    fix_mark = f"(原:{s['original']})" if s['auto_fixed'] else ''
    print(f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']:20s} {fix_mark}")


"""检查Calm前20张截图分类"""

import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前20张
first_20 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 20:
        first_20.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'auto_fixed': info.get('auto_fixed', False),
            'original': info.get('original_type', '')
        })

first_20.sort(key=lambda x: x['idx'])

print('=== Calm前20张分类 ===')
print()
for s in first_20:
    fix_mark = f"(原:{s['original']})" if s['auto_fixed'] else ''
    print(f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']:20s} {fix_mark}")


















