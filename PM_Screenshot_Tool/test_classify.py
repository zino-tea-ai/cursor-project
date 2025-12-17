# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import base64
from PIL import Image
import io
import anthropic

# 加载API key
with open('config/api_keys.json', 'r') as f:
    data = json.load(f)
    key = data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    
client = anthropic.Anthropic(api_key=key)

# 测试一张图片
img_path = 'projects/Calm_Analysis/Screens/Screen_001.png'
print(f"Testing: {img_path}")

with Image.open(img_path) as img:
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img = img.resize((400, int(img.height * 400 / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 简化prompt测试
prompt = """按照screensdesign.com的标准分析这张App截图。

判断标准（按顺序）：
1. 有明确的价格展示（$X.XX）？ → Paywall
2. 有底部Tab导航栏（3-5个图标）？ → Core  
3. 其他情况（无Tab栏）→ Onboarding

重点：
- 深呼吸引导页、目标选择页、信息收集页，只要没有Tab栏就是Onboarding
- Core必须有底部Tab导航栏

请用JSON格式回答：
{"category": "Onboarding或Paywall或Core", "reasoning": "判断理由", "has_tab_bar": true/false}"""

response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=300,
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img_data}},
            {'type': 'text', 'text': prompt}
        ]
    }]
)

print('\nAPI Response:')
print(response.content[0].text)

# 尝试解析
text = response.content[0].text
json_start = text.find('{')
json_end = text.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    result = json.loads(text[json_start:json_end])
    print(f"\nParsed: {result}")


sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import base64
from PIL import Image
import io
import anthropic

# 加载API key
with open('config/api_keys.json', 'r') as f:
    data = json.load(f)
    key = data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    
client = anthropic.Anthropic(api_key=key)

# 测试一张图片
img_path = 'projects/Calm_Analysis/Screens/Screen_001.png'
print(f"Testing: {img_path}")

with Image.open(img_path) as img:
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img = img.resize((400, int(img.height * 400 / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 简化prompt测试
prompt = """按照screensdesign.com的标准分析这张App截图。

判断标准（按顺序）：
1. 有明确的价格展示（$X.XX）？ → Paywall
2. 有底部Tab导航栏（3-5个图标）？ → Core  
3. 其他情况（无Tab栏）→ Onboarding

重点：
- 深呼吸引导页、目标选择页、信息收集页，只要没有Tab栏就是Onboarding
- Core必须有底部Tab导航栏

请用JSON格式回答：
{"category": "Onboarding或Paywall或Core", "reasoning": "判断理由", "has_tab_bar": true/false}"""

response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=300,
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img_data}},
            {'type': 'text', 'text': prompt}
        ]
    }]
)

print('\nAPI Response:')
print(response.content[0].text)

# 尝试解析
text = response.content[0].text
json_start = text.find('{')
json_end = text.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    result = json.loads(text[json_start:json_end])
    print(f"\nParsed: {result}")


sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import base64
from PIL import Image
import io
import anthropic

# 加载API key
with open('config/api_keys.json', 'r') as f:
    data = json.load(f)
    key = data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    
client = anthropic.Anthropic(api_key=key)

# 测试一张图片
img_path = 'projects/Calm_Analysis/Screens/Screen_001.png'
print(f"Testing: {img_path}")

with Image.open(img_path) as img:
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img = img.resize((400, int(img.height * 400 / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 简化prompt测试
prompt = """按照screensdesign.com的标准分析这张App截图。

判断标准（按顺序）：
1. 有明确的价格展示（$X.XX）？ → Paywall
2. 有底部Tab导航栏（3-5个图标）？ → Core  
3. 其他情况（无Tab栏）→ Onboarding

重点：
- 深呼吸引导页、目标选择页、信息收集页，只要没有Tab栏就是Onboarding
- Core必须有底部Tab导航栏

请用JSON格式回答：
{"category": "Onboarding或Paywall或Core", "reasoning": "判断理由", "has_tab_bar": true/false}"""

response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=300,
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img_data}},
            {'type': 'text', 'text': prompt}
        ]
    }]
)

print('\nAPI Response:')
print(response.content[0].text)

# 尝试解析
text = response.content[0].text
json_start = text.find('{')
json_end = text.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    result = json.loads(text[json_start:json_end])
    print(f"\nParsed: {result}")


sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import base64
from PIL import Image
import io
import anthropic

# 加载API key
with open('config/api_keys.json', 'r') as f:
    data = json.load(f)
    key = data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    
client = anthropic.Anthropic(api_key=key)

# 测试一张图片
img_path = 'projects/Calm_Analysis/Screens/Screen_001.png'
print(f"Testing: {img_path}")

with Image.open(img_path) as img:
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img = img.resize((400, int(img.height * 400 / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 简化prompt测试
prompt = """按照screensdesign.com的标准分析这张App截图。

判断标准（按顺序）：
1. 有明确的价格展示（$X.XX）？ → Paywall
2. 有底部Tab导航栏（3-5个图标）？ → Core  
3. 其他情况（无Tab栏）→ Onboarding

重点：
- 深呼吸引导页、目标选择页、信息收集页，只要没有Tab栏就是Onboarding
- Core必须有底部Tab导航栏

请用JSON格式回答：
{"category": "Onboarding或Paywall或Core", "reasoning": "判断理由", "has_tab_bar": true/false}"""

response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=300,
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img_data}},
            {'type': 'text', 'text': prompt}
        ]
    }]
)

print('\nAPI Response:')
print(response.content[0].text)

# 尝试解析
text = response.content[0].text
json_start = text.find('{')
json_end = text.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    result = json.loads(text[json_start:json_end])
    print(f"\nParsed: {result}")


sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import base64
from PIL import Image
import io
import anthropic

# 加载API key
with open('config/api_keys.json', 'r') as f:
    data = json.load(f)
    key = data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    
client = anthropic.Anthropic(api_key=key)

# 测试一张图片
img_path = 'projects/Calm_Analysis/Screens/Screen_001.png'
print(f"Testing: {img_path}")

with Image.open(img_path) as img:
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img = img.resize((400, int(img.height * 400 / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 简化prompt测试
prompt = """按照screensdesign.com的标准分析这张App截图。

判断标准（按顺序）：
1. 有明确的价格展示（$X.XX）？ → Paywall
2. 有底部Tab导航栏（3-5个图标）？ → Core  
3. 其他情况（无Tab栏）→ Onboarding

重点：
- 深呼吸引导页、目标选择页、信息收集页，只要没有Tab栏就是Onboarding
- Core必须有底部Tab导航栏

请用JSON格式回答：
{"category": "Onboarding或Paywall或Core", "reasoning": "判断理由", "has_tab_bar": true/false}"""

response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=300,
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img_data}},
            {'type': 'text', 'text': prompt}
        ]
    }]
)

print('\nAPI Response:')
print(response.content[0].text)

# 尝试解析
text = response.content[0].text
json_start = text.find('{')
json_end = text.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    result = json.loads(text[json_start:json_end])
    print(f"\nParsed: {result}")


sys.stdout.reconfigure(encoding='utf-8')
import os
import json
import base64
from PIL import Image
import io
import anthropic

# 加载API key
with open('config/api_keys.json', 'r') as f:
    data = json.load(f)
    key = data.get('anthropic_api_key') or data.get('ANTHROPIC_API_KEY')
    
client = anthropic.Anthropic(api_key=key)

# 测试一张图片
img_path = 'projects/Calm_Analysis/Screens/Screen_001.png'
print(f"Testing: {img_path}")

with Image.open(img_path) as img:
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    img = img.resize((400, int(img.height * 400 / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=75)
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

# 简化prompt测试
prompt = """按照screensdesign.com的标准分析这张App截图。

判断标准（按顺序）：
1. 有明确的价格展示（$X.XX）？ → Paywall
2. 有底部Tab导航栏（3-5个图标）？ → Core  
3. 其他情况（无Tab栏）→ Onboarding

重点：
- 深呼吸引导页、目标选择页、信息收集页，只要没有Tab栏就是Onboarding
- Core必须有底部Tab导航栏

请用JSON格式回答：
{"category": "Onboarding或Paywall或Core", "reasoning": "判断理由", "has_tab_bar": true/false}"""

response = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=300,
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img_data}},
            {'type': 'text', 'text': prompt}
        ]
    }]
)

print('\nAPI Response:')
print(response.content[0].text)

# 尝试解析
text = response.content[0].text
json_start = text.find('{')
json_end = text.rfind('}') + 1
if json_start >= 0 and json_end > json_start:
    result = json.loads(text[json_start:json_end])
    print(f"\nParsed: {result}")

