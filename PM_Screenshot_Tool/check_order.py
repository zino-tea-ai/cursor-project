# -*- coding: utf-8 -*-
"""检查页面顺序"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

products = [
    'Calm_Analysis',
    'MyFitnessPal_Analysis', 
    'Flo_Analysis'
]

for product in products:
    path = f'projects/{product}/ai_analysis.json'
    if not os.path.exists(path):
        print(f'[!] {product}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 0))
    
    print(f'\n{"="*60}')
    print(f'  {product} 前15张顺序')
    print(f'{"="*60}')
    
    for filename, info in sorted_items[:15]:
        idx = info.get('index', 0)
        st = info.get('screen_type', '?')
        name = info.get('naming', {}).get('cn', '')
        print(f'{idx:3d}. {filename:25s} | {st:12s} | {name}')


"""检查页面顺序"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

products = [
    'Calm_Analysis',
    'MyFitnessPal_Analysis', 
    'Flo_Analysis'
]

for product in products:
    path = f'projects/{product}/ai_analysis.json'
    if not os.path.exists(path):
        print(f'[!] {product}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 0))
    
    print(f'\n{"="*60}')
    print(f'  {product} 前15张顺序')
    print(f'{"="*60}')
    
    for filename, info in sorted_items[:15]:
        idx = info.get('index', 0)
        st = info.get('screen_type', '?')
        name = info.get('naming', {}).get('cn', '')
        print(f'{idx:3d}. {filename:25s} | {st:12s} | {name}')


"""检查页面顺序"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

products = [
    'Calm_Analysis',
    'MyFitnessPal_Analysis', 
    'Flo_Analysis'
]

for product in products:
    path = f'projects/{product}/ai_analysis.json'
    if not os.path.exists(path):
        print(f'[!] {product}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 0))
    
    print(f'\n{"="*60}')
    print(f'  {product} 前15张顺序')
    print(f'{"="*60}')
    
    for filename, info in sorted_items[:15]:
        idx = info.get('index', 0)
        st = info.get('screen_type', '?')
        name = info.get('naming', {}).get('cn', '')
        print(f'{idx:3d}. {filename:25s} | {st:12s} | {name}')


"""检查页面顺序"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

products = [
    'Calm_Analysis',
    'MyFitnessPal_Analysis', 
    'Flo_Analysis'
]

for product in products:
    path = f'projects/{product}/ai_analysis.json'
    if not os.path.exists(path):
        print(f'[!] {product}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 0))
    
    print(f'\n{"="*60}')
    print(f'  {product} 前15张顺序')
    print(f'{"="*60}')
    
    for filename, info in sorted_items[:15]:
        idx = info.get('index', 0)
        st = info.get('screen_type', '?')
        name = info.get('naming', {}).get('cn', '')
        print(f'{idx:3d}. {filename:25s} | {st:12s} | {name}')



"""检查页面顺序"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

products = [
    'Calm_Analysis',
    'MyFitnessPal_Analysis', 
    'Flo_Analysis'
]

for product in products:
    path = f'projects/{product}/ai_analysis.json'
    if not os.path.exists(path):
        print(f'[!] {product}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 0))
    
    print(f'\n{"="*60}')
    print(f'  {product} 前15张顺序')
    print(f'{"="*60}')
    
    for filename, info in sorted_items[:15]:
        idx = info.get('index', 0)
        st = info.get('screen_type', '?')
        name = info.get('naming', {}).get('cn', '')
        print(f'{idx:3d}. {filename:25s} | {st:12s} | {name}')


"""检查页面顺序"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

products = [
    'Calm_Analysis',
    'MyFitnessPal_Analysis', 
    'Flo_Analysis'
]

for product in products:
    path = f'projects/{product}/ai_analysis.json'
    if not os.path.exists(path):
        print(f'[!] {product}: 文件不存在')
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = data.get('results', {})
    
    # 按index排序
    sorted_items = sorted(results.items(), key=lambda x: x[1].get('index', 0))
    
    print(f'\n{"="*60}')
    print(f'  {product} 前15张顺序')
    print(f'{"="*60}')
    
    for filename, info in sorted_items[:15]:
        idx = info.get('index', 0)
        st = info.get('screen_type', '?')
        name = info.get('naming', {}).get('cn', '')
        print(f'{idx:3d}. {filename:25s} | {st:12s} | {name}')


















