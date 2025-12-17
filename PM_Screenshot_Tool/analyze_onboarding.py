# -*- coding: utf-8 -*-
"""让AI专家评估Onboarding分类"""

import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 加载API
config_path = 'config/api_keys.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic

# 读取Calm分析结果
with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前25张的分类情况
first_25 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 25:
        first_25.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'function': info.get('core_function', {}).get('cn', '')
        })

first_25.sort(key=lambda x: x['idx'])

# 构建分析内容
screens_text = '\n'.join([
    f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']} - {s['function']}"
    for s in first_25
])

prompt = '''你是一位资深产品经理、用户体验专家和增长黑客。请给出移动App领域"Onboarding"的权威定义。

请从以下角度全面阐述：

1. **学术/业界标准定义**
   - Onboarding的本质是什么？
   - 与Welcome、Tutorial、FTUE(First Time User Experience)的区别？

2. **Onboarding的核心目标**（按重要性排序）

3. **Onboarding包含的典型页面类型**
   - 哪些页面属于Onboarding？
   - 哪些页面容易被误认为Onboarding？

4. **Onboarding的边界**
   - Paywall算Onboarding吗？
   - 权限请求算Onboarding吗？
   - 邀请好友/分享算Onboarding吗？
   - 首次功能使用引导算Onboarding吗？

5. **行业最佳实践**
   - 顶级App（如Calm、Headspace、Duolingo）的Onboarding特点

请给出清晰、可操作的定义，便于我们在产品分析中准确分类。'''

client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)

print('=== AI专家分析 ===')
print()
print(response.content[0].text)



import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 加载API
config_path = 'config/api_keys.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic

# 读取Calm分析结果
with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前25张的分类情况
first_25 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 25:
        first_25.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'function': info.get('core_function', {}).get('cn', '')
        })

first_25.sort(key=lambda x: x['idx'])

# 构建分析内容
screens_text = '\n'.join([
    f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']} - {s['function']}"
    for s in first_25
])

prompt = '''你是一位资深产品经理、用户体验专家和增长黑客。请给出移动App领域"Onboarding"的权威定义。

请从以下角度全面阐述：

1. **学术/业界标准定义**
   - Onboarding的本质是什么？
   - 与Welcome、Tutorial、FTUE(First Time User Experience)的区别？

2. **Onboarding的核心目标**（按重要性排序）

3. **Onboarding包含的典型页面类型**
   - 哪些页面属于Onboarding？
   - 哪些页面容易被误认为Onboarding？

4. **Onboarding的边界**
   - Paywall算Onboarding吗？
   - 权限请求算Onboarding吗？
   - 邀请好友/分享算Onboarding吗？
   - 首次功能使用引导算Onboarding吗？

5. **行业最佳实践**
   - 顶级App（如Calm、Headspace、Duolingo）的Onboarding特点

请给出清晰、可操作的定义，便于我们在产品分析中准确分类。'''

client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)

print('=== AI专家分析 ===')
print()
print(response.content[0].text)



import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 加载API
config_path = 'config/api_keys.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic

# 读取Calm分析结果
with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前25张的分类情况
first_25 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 25:
        first_25.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'function': info.get('core_function', {}).get('cn', '')
        })

first_25.sort(key=lambda x: x['idx'])

# 构建分析内容
screens_text = '\n'.join([
    f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']} - {s['function']}"
    for s in first_25
])

prompt = '''你是一位资深产品经理、用户体验专家和增长黑客。请给出移动App领域"Onboarding"的权威定义。

请从以下角度全面阐述：

1. **学术/业界标准定义**
   - Onboarding的本质是什么？
   - 与Welcome、Tutorial、FTUE(First Time User Experience)的区别？

2. **Onboarding的核心目标**（按重要性排序）

3. **Onboarding包含的典型页面类型**
   - 哪些页面属于Onboarding？
   - 哪些页面容易被误认为Onboarding？

4. **Onboarding的边界**
   - Paywall算Onboarding吗？
   - 权限请求算Onboarding吗？
   - 邀请好友/分享算Onboarding吗？
   - 首次功能使用引导算Onboarding吗？

5. **行业最佳实践**
   - 顶级App（如Calm、Headspace、Duolingo）的Onboarding特点

请给出清晰、可操作的定义，便于我们在产品分析中准确分类。'''

client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)

print('=== AI专家分析 ===')
print()
print(response.content[0].text)



import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 加载API
config_path = 'config/api_keys.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic

# 读取Calm分析结果
with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前25张的分类情况
first_25 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 25:
        first_25.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'function': info.get('core_function', {}).get('cn', '')
        })

first_25.sort(key=lambda x: x['idx'])

# 构建分析内容
screens_text = '\n'.join([
    f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']} - {s['function']}"
    for s in first_25
])

prompt = '''你是一位资深产品经理、用户体验专家和增长黑客。请给出移动App领域"Onboarding"的权威定义。

请从以下角度全面阐述：

1. **学术/业界标准定义**
   - Onboarding的本质是什么？
   - 与Welcome、Tutorial、FTUE(First Time User Experience)的区别？

2. **Onboarding的核心目标**（按重要性排序）

3. **Onboarding包含的典型页面类型**
   - 哪些页面属于Onboarding？
   - 哪些页面容易被误认为Onboarding？

4. **Onboarding的边界**
   - Paywall算Onboarding吗？
   - 权限请求算Onboarding吗？
   - 邀请好友/分享算Onboarding吗？
   - 首次功能使用引导算Onboarding吗？

5. **行业最佳实践**
   - 顶级App（如Calm、Headspace、Duolingo）的Onboarding特点

请给出清晰、可操作的定义，便于我们在产品分析中准确分类。'''

client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)

print('=== AI专家分析 ===')
print()
print(response.content[0].text)



import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 加载API
config_path = 'config/api_keys.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic

# 读取Calm分析结果
with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前25张的分类情况
first_25 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 25:
        first_25.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'function': info.get('core_function', {}).get('cn', '')
        })

first_25.sort(key=lambda x: x['idx'])

# 构建分析内容
screens_text = '\n'.join([
    f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']} - {s['function']}"
    for s in first_25
])

prompt = '''你是一位资深产品经理、用户体验专家和增长黑客。请给出移动App领域"Onboarding"的权威定义。

请从以下角度全面阐述：

1. **学术/业界标准定义**
   - Onboarding的本质是什么？
   - 与Welcome、Tutorial、FTUE(First Time User Experience)的区别？

2. **Onboarding的核心目标**（按重要性排序）

3. **Onboarding包含的典型页面类型**
   - 哪些页面属于Onboarding？
   - 哪些页面容易被误认为Onboarding？

4. **Onboarding的边界**
   - Paywall算Onboarding吗？
   - 权限请求算Onboarding吗？
   - 邀请好友/分享算Onboarding吗？
   - 首次功能使用引导算Onboarding吗？

5. **行业最佳实践**
   - 顶级App（如Calm、Headspace、Duolingo）的Onboarding特点

请给出清晰、可操作的定义，便于我们在产品分析中准确分类。'''

client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)

print('=== AI专家分析 ===')
print()
print(response.content[0].text)



import json
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# 加载API
config_path = 'config/api_keys.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic

# 读取Calm分析结果
with open('projects/Calm_Analysis/ai_analysis.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

results = data.get('results', {})

# 获取前25张的分类情况
first_25 = []
for filename, info in results.items():
    idx = info.get('index', 0)
    if idx <= 25:
        first_25.append({
            'idx': idx,
            'file': filename,
            'type': info.get('screen_type'),
            'name_cn': info.get('naming', {}).get('cn', ''),
            'function': info.get('core_function', {}).get('cn', '')
        })

first_25.sort(key=lambda x: x['idx'])

# 构建分析内容
screens_text = '\n'.join([
    f"{s['idx']:2d}. {s['type']:12s} | {s['name_cn']} - {s['function']}"
    for s in first_25
])

prompt = '''你是一位资深产品经理、用户体验专家和增长黑客。请给出移动App领域"Onboarding"的权威定义。

请从以下角度全面阐述：

1. **学术/业界标准定义**
   - Onboarding的本质是什么？
   - 与Welcome、Tutorial、FTUE(First Time User Experience)的区别？

2. **Onboarding的核心目标**（按重要性排序）

3. **Onboarding包含的典型页面类型**
   - 哪些页面属于Onboarding？
   - 哪些页面容易被误认为Onboarding？

4. **Onboarding的边界**
   - Paywall算Onboarding吗？
   - 权限请求算Onboarding吗？
   - 邀请好友/分享算Onboarding吗？
   - 首次功能使用引导算Onboarding吗？

5. **行业最佳实践**
   - 顶级App（如Calm、Headspace、Duolingo）的Onboarding特点

请给出清晰、可操作的定义，便于我们在产品分析中准确分类。'''

client = anthropic.Anthropic()
response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)

print('=== AI专家分析 ===')
print()
print(response.content[0].text)

