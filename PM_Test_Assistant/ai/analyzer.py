# -*- coding: utf-8 -*-
"""
AI 分析器 - 使用 GPT-4V / Claude Vision 分析截图
"""

import os
import json
import base64
from typing import Optional, Dict


class AIAnalyzer:
    """AI 问题分析器"""
    
    ANALYSIS_PROMPT = """你是一位产品经理，正在帮助记录 APP 体验过程中发现的问题。

用户提供了一个截图，以及用户的简短描述（可能为空）。

请分析这个截图，判断可能存在的问题，输出JSON格式：

```json
{
  "title": "问题标题（简洁，10字以内）",
  "category": "问题分类（设计/开发/待讨论）",
  "page": "所在页面（根据截图判断）",
  "type": "问题类型（UI视觉/交互反馈/流程逻辑/性能问题）",
  "description": "问题描述（用开发/设计能理解的专业语言，50字以内）",
  "suggestion": "修改建议（具体可执行的改进建议，50字以内）"
}
```

分类标准：
- 设计问题：颜色、间距、字体、布局、视觉风格等
- 开发问题：功能异常、点击无效、加载问题、状态缺失等
- 待讨论：不确定归属，或产品逻辑本身可能有问题

只输出JSON，不要输出其他内容。"""

    def __init__(self):
        self.config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config', 'settings.json'
        )
        self.load_config()
        
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_keys = config.get('api_keys', {})
                    self.provider = config.get('ai_provider', 'openai')
                    self.model = config.get('ai_model', 'gpt-4o')
            else:
                self.api_keys = {}
                self.provider = 'openai'
                self.model = 'gpt-4o'
        except Exception as e:
            print(f"Load config error: {e}")
            self.api_keys = {}
            self.provider = 'openai'
            self.model = 'gpt-4o'
    
    def _encode_image(self, image_path: str) -> str:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode("utf-8")
    
    def _get_media_type(self, image_path: str) -> str:
        """获取图片MIME类型"""
        ext = os.path.splitext(image_path)[1].lower()
        types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return types.get(ext, 'image/png')
    
    def analyze(self, image_path: str, user_note: str = "") -> Dict:
        """
        分析截图
        
        Args:
            image_path: 截图路径
            user_note: 用户备注
            
        Returns:
            分析结果字典
        """
        # 检查API Key
        openai_key = self.api_keys.get('openai') or os.environ.get('OPENAI_API_KEY')
        anthropic_key = self.api_keys.get('anthropic') or os.environ.get('ANTHROPIC_API_KEY')
        
        if self.provider == 'openai' and openai_key:
            return self._analyze_with_openai(image_path, user_note, openai_key)
        elif self.provider == 'anthropic' and anthropic_key:
            return self._analyze_with_claude(image_path, user_note, anthropic_key)
        elif openai_key:
            return self._analyze_with_openai(image_path, user_note, openai_key)
        elif anthropic_key:
            return self._analyze_with_claude(image_path, user_note, anthropic_key)
        else:
            # 没有API Key，返回基于用户备注的默认结果
            return self._fallback_result(user_note)
    
    def _analyze_with_openai(self, image_path: str, user_note: str, api_key: str) -> Dict:
        """使用OpenAI GPT-4V分析"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=api_key)
            
            # 构建消息
            user_message = self.ANALYSIS_PROMPT
            if user_note:
                user_message += f"\n\n用户描述：{user_note}"
            
            # 编码图片
            image_data = self._encode_image(image_path)
            media_type = self._get_media_type(image_path)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_message},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            # 解析响应
            content = response.choices[0].message.content
            return self._parse_response(content, user_note)
            
        except Exception as e:
            print(f"OpenAI analysis error: {e}")
            return self._fallback_result(user_note, str(e))
    
    def _analyze_with_claude(self, image_path: str, user_note: str, api_key: str) -> Dict:
        """使用Claude Vision分析"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=api_key)
            
            # 构建消息
            user_message = self.ANALYSIS_PROMPT
            if user_note:
                user_message += f"\n\n用户描述：{user_note}"
            
            # 编码图片
            image_data = self._encode_image(image_path)
            media_type = self._get_media_type(image_path)
            
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {"type": "text", "text": user_message}
                        ]
                    }
                ]
            )
            
            # 解析响应
            content = response.content[0].text
            return self._parse_response(content, user_note)
            
        except Exception as e:
            print(f"Claude analysis error: {e}")
            return self._fallback_result(user_note, str(e))
    
    def _parse_response(self, content: str, user_note: str) -> Dict:
        """解析AI响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'title': result.get('title', '问题记录'),
                    'category': result.get('category', '待讨论'),
                    'page': result.get('page', ''),
                    'type': result.get('type', ''),
                    'description': result.get('description', ''),
                    'suggestion': result.get('suggestion', '')
                }
        except json.JSONDecodeError:
            pass
        
        # 解析失败，使用默认结果
        return self._fallback_result(user_note)
    
    def _fallback_result(self, user_note: str, error: str = "") -> Dict:
        """默认结果（无API或解析失败时）"""
        return {
            'title': user_note[:20] if user_note else '截图记录',
            'category': '待分析',
            'page': '',
            'type': '',
            'description': user_note or '等待分析',
            'suggestion': error if error else '请配置API Key以启用AI分析'
        }
