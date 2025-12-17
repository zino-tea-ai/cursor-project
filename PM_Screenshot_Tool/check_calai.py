# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json

with open('projects/Cal_AI_-_Calorie_Tracker_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 按index排序
items = sorted(results.items(), key=lambda x: x[1].get('index', 0))

print('Cal AI - All 93 screenshots:')
print('='*50)
for f, r in items:
    idx = r.get('index', 0)
    stype = r.get('screen_type', '?')
    print(f'{idx:2}. {stype:12} | {f}')

sys.stdout.reconfigure(encoding='utf-8')
import json

with open('projects/Cal_AI_-_Calorie_Tracker_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 按index排序
items = sorted(results.items(), key=lambda x: x[1].get('index', 0))

print('Cal AI - All 93 screenshots:')
print('='*50)
for f, r in items:
    idx = r.get('index', 0)
    stype = r.get('screen_type', '?')
    print(f'{idx:2}. {stype:12} | {f}')

sys.stdout.reconfigure(encoding='utf-8')
import json

with open('projects/Cal_AI_-_Calorie_Tracker_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 按index排序
items = sorted(results.items(), key=lambda x: x[1].get('index', 0))

print('Cal AI - All 93 screenshots:')
print('='*50)
for f, r in items:
    idx = r.get('index', 0)
    stype = r.get('screen_type', '?')
    print(f'{idx:2}. {stype:12} | {f}')

sys.stdout.reconfigure(encoding='utf-8')
import json

with open('projects/Cal_AI_-_Calorie_Tracker_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 按index排序
items = sorted(results.items(), key=lambda x: x[1].get('index', 0))

print('Cal AI - All 93 screenshots:')
print('='*50)
for f, r in items:
    idx = r.get('index', 0)
    stype = r.get('screen_type', '?')
    print(f'{idx:2}. {stype:12} | {f}')

sys.stdout.reconfigure(encoding='utf-8')
import json

with open('projects/Cal_AI_-_Calorie_Tracker_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 按index排序
items = sorted(results.items(), key=lambda x: x[1].get('index', 0))

print('Cal AI - All 93 screenshots:')
print('='*50)
for f, r in items:
    idx = r.get('index', 0)
    stype = r.get('screen_type', '?')
    print(f'{idx:2}. {stype:12} | {f}')

sys.stdout.reconfigure(encoding='utf-8')
import json

with open('projects/Cal_AI_-_Calorie_Tracker_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 按index排序
items = sorted(results.items(), key=lambda x: x[1].get('index', 0))

print('Cal AI - All 93 screenshots:')
print('='*50)
for f, r in items:
    idx = r.get('index', 0)
    stype = r.get('screen_type', '?')
    print(f'{idx:2}. {stype:12} | {f}')
