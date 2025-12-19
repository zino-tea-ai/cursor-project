# -*- coding: utf-8 -*-
"""Onboarding边界定义"""

import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

config_path = 'config/api_keys.json'
with open(config_path, 'r') as f:
    config = json.load(f)
os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic
client = anthropic.Anthropic()

prompt = """请简洁回答：在移动App产品设计中，以下页面是否属于Onboarding？

1. Paywall（付费墙）
2. Permission Request（权限请求）  
3. Referral/Invite Friends（邀请好友）
4. 首次功能使用教学（如首次打开某功能的引导）
5. 深呼吸/情感铺垫类引导
6. 场景选择/偏好设置

对每个给出：属于/不属于/争议，以及一句话理由。

最后给出一个简洁的Onboarding分类标准（可用于自动化识别）。"""

response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)
print(response.content[0].text)


"""Onboarding边界定义"""

import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

config_path = 'config/api_keys.json'
with open(config_path, 'r') as f:
    config = json.load(f)
os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic
client = anthropic.Anthropic()

prompt = """请简洁回答：在移动App产品设计中，以下页面是否属于Onboarding？

1. Paywall（付费墙）
2. Permission Request（权限请求）  
3. Referral/Invite Friends（邀请好友）
4. 首次功能使用教学（如首次打开某功能的引导）
5. 深呼吸/情感铺垫类引导
6. 场景选择/偏好设置

对每个给出：属于/不属于/争议，以及一句话理由。

最后给出一个简洁的Onboarding分类标准（可用于自动化识别）。"""

response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)
print(response.content[0].text)


"""Onboarding边界定义"""

import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

config_path = 'config/api_keys.json'
with open(config_path, 'r') as f:
    config = json.load(f)
os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic
client = anthropic.Anthropic()

prompt = """请简洁回答：在移动App产品设计中，以下页面是否属于Onboarding？

1. Paywall（付费墙）
2. Permission Request（权限请求）  
3. Referral/Invite Friends（邀请好友）
4. 首次功能使用教学（如首次打开某功能的引导）
5. 深呼吸/情感铺垫类引导
6. 场景选择/偏好设置

对每个给出：属于/不属于/争议，以及一句话理由。

最后给出一个简洁的Onboarding分类标准（可用于自动化识别）。"""

response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)
print(response.content[0].text)


"""Onboarding边界定义"""

import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

config_path = 'config/api_keys.json'
with open(config_path, 'r') as f:
    config = json.load(f)
os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic
client = anthropic.Anthropic()

prompt = """请简洁回答：在移动App产品设计中，以下页面是否属于Onboarding？

1. Paywall（付费墙）
2. Permission Request（权限请求）  
3. Referral/Invite Friends（邀请好友）
4. 首次功能使用教学（如首次打开某功能的引导）
5. 深呼吸/情感铺垫类引导
6. 场景选择/偏好设置

对每个给出：属于/不属于/争议，以及一句话理由。

最后给出一个简洁的Onboarding分类标准（可用于自动化识别）。"""

response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)
print(response.content[0].text)



"""Onboarding边界定义"""

import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

config_path = 'config/api_keys.json'
with open(config_path, 'r') as f:
    config = json.load(f)
os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic
client = anthropic.Anthropic()

prompt = """请简洁回答：在移动App产品设计中，以下页面是否属于Onboarding？

1. Paywall（付费墙）
2. Permission Request（权限请求）  
3. Referral/Invite Friends（邀请好友）
4. 首次功能使用教学（如首次打开某功能的引导）
5. 深呼吸/情感铺垫类引导
6. 场景选择/偏好设置

对每个给出：属于/不属于/争议，以及一句话理由。

最后给出一个简洁的Onboarding分类标准（可用于自动化识别）。"""

response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)
print(response.content[0].text)


"""Onboarding边界定义"""

import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

config_path = 'config/api_keys.json'
with open(config_path, 'r') as f:
    config = json.load(f)
os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')

import anthropic
client = anthropic.Anthropic()

prompt = """请简洁回答：在移动App产品设计中，以下页面是否属于Onboarding？

1. Paywall（付费墙）
2. Permission Request（权限请求）  
3. Referral/Invite Friends（邀请好友）
4. 首次功能使用教学（如首次打开某功能的引导）
5. 深呼吸/情感铺垫类引导
6. 场景选择/偏好设置

对每个给出：属于/不属于/争议，以及一句话理由。

最后给出一个简洁的Onboarding分类标准（可用于自动化识别）。"""

response = client.messages.create(
    model='claude-opus-4-5-20251101',
    max_tokens=1500,
    messages=[{'role': 'user', 'content': prompt}]
)
print(response.content[0].text)










































