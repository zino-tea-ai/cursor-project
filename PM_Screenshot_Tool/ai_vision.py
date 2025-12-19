# -*- coding: utf-8 -*-
"""
AI Vision Module - 使用Claude Vision进行截图验证
Sonnet: 搜索结果页识别目标App
Haiku: 批量验证截图归属
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 模型配置
SONNET_MODEL = "claude-3-5-sonnet-20241022"  # 检索用 - 更准确
HAIKU_MODEL = "claude-3-haiku-20240307"      # 验证用 - 更快更便宜

API_URL = "https://api.anthropic.com/v1/messages"


class AIVision:
    """AI视觉验证类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> tuple:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            data = f.read()
        
        # 判断图片类型
        if image_path.lower().endswith(".png"):
            media_type = "image/png"
        elif image_path.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_path.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/png"
        
        return base64.standard_b64encode(data).decode("utf-8"), media_type
    
    async def _call_api(self, model: str, messages: list, max_tokens: int = 1024) -> dict:
        """调用Claude API"""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["content"][0]["text"]
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API Error {response.status}: {error_text}"
                    }
    
    async def identify_app_in_search(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Sonnet分析搜索结果页，识别目标App的位置
        
        Args:
            screenshot_path: 搜索结果页截图路径
            target_app: 目标App信息 {"name": "Cal AI", "publisher": "Viral Development", "features": [...]}
        
        Returns:
            {
                "found": True/False,
                "position": "第1个卡片" / "row1_col2" / 坐标,
                "app_name": "匹配到的App名称",
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"found": False, "error": "Screenshot file not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        # 构建Prompt
        app_name = target_app.get("name", "")
        publisher = target_app.get("publisher", "")
        features = target_app.get("features", [])
        
        prompt = f"""分析这张screensdesign.com的搜索结果页面截图。

我要找的目标App是：
- 名称：{app_name}
- 发行商：{publisher}
- 特征：{', '.join(features) if features else '无特定特征'}

请仔细查看页面中的所有App卡片，找出与目标App匹配的那个。

返回JSON格式：
{{
    "found": true/false,
    "position": "描述App在页面中的位置（如：第1个卡片、左上角、第2行第1列等）",
    "matched_name": "页面上显示的App名称",
    "confidence": 0.0-1.0的置信度,
    "reason": "为什么认为这是/不是目标App"
}}

只返回JSON，不要其他文字。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(SONNET_MODEL, messages)
        
        if not result["success"]:
            return {"found": False, "error": result["error"]}
        
        try:
            # 解析JSON响应
            content = result["content"].strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "found": False,
                "error": f"Failed to parse response: {e}",
                "raw_response": result["content"]
            }
    
    async def verify_screenshot(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Haiku验证单张截图是否属于目标App
        
        Args:
            screenshot_path: 截图路径
            target_app: 目标App信息
        
        Returns:
            {
                "belongs": True/False,
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"belongs": False, "confidence": 0, "error": "File not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        app_name = target_app.get("name", "")
        features = target_app.get("features", [])
        
        # 简洁的Prompt以提高Haiku效率
        prompt = f"""判断这张App截图是否属于"{app_name}"。

App特征：{', '.join(features) if features else '卡路里追踪、食物识别、营养管理'}

返回JSON：
{{"belongs": true/false, "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(HAIKU_MODEL, messages, max_tokens=256)
        
        if not result["success"]:
            return {"belongs": False, "confidence": 0, "error": result["error"]}
        
        try:
            content = result["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # 尝试简单解析
            content_lower = result["content"].lower()
            if '"belongs": true' in content_lower or '"belongs":true' in content_lower:
                return {"belongs": True, "confidence": 0.7, "reason": "Parsed from response"}
            elif '"belongs": false' in content_lower or '"belongs":false' in content_lower:
                return {"belongs": False, "confidence": 0.7, "reason": "Parsed from response"}
            else:
                return {"belongs": False, "confidence": 0, "error": "Parse failed", "raw": result["content"]}
    
    async def batch_verify(self, screenshots: List[str], target_app: dict, 
                          concurrency: int = 5, progress_callback=None) -> Dict[str, dict]:
        """
        批量验证截图
        
        Args:
            screenshots: 截图路径列表
            target_app: 目标App信息
            concurrency: 并发数
            progress_callback: 进度回调函数 callback(current, total)
        
        Returns:
            {
                "Screen_001.png": {"belongs": True, "confidence": 0.95, "reason": "..."},
                "Screen_002.png": {"belongs": False, "confidence": 0.8, "reason": "..."},
                ...
            }
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        total = len(screenshots)
        completed = 0
        
        async def verify_one(path: str):
            nonlocal completed
            async with semaphore:
                filename = os.path.basename(path)
                result = await self.verify_screenshot(path, target_app)
                results[filename] = result
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                
                return filename, result
        
        # 创建所有任务
        tasks = [verify_one(path) for path in screenshots]
        
        # 执行并等待所有任务完成
        await asyncio.gather(*tasks)
        
        return results
    
    def filter_screenshots(self, verification_results: Dict[str, dict], 
                          confidence_threshold: float = 0.6) -> tuple:
        """
        根据验证结果过滤截图
        
        Args:
            verification_results: batch_verify的返回结果
            confidence_threshold: 置信度阈值
        
        Returns:
            (passed_list, rejected_list, uncertain_list)
        """
        passed = []
        rejected = []
        uncertain = []
        
        for filename, result in verification_results.items():
            if result.get("error"):
                uncertain.append(filename)
            elif result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                passed.append(filename)
            elif not result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                rejected.append(filename)
            else:
                uncertain.append(filename)
        
        return passed, rejected, uncertain


# ==================== 辅助函数 ====================

def load_api_key() -> str:
    """从配置文件加载API Key"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "api_keys.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ANTHROPIC_API_KEY", "")
    return os.environ.get("ANTHROPIC_API_KEY", "")


async def test_vision():
    """测试AI视觉模块"""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found")
        return
    
    vision = AIVision(api_key)
    
    # 测试识别搜索结果
    test_search_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/debug_after_click.png"
    if os.path.exists(test_search_screenshot):
        print("Testing search identification...")
        result = await vision.identify_app_in_search(
            test_search_screenshot,
            {
                "name": "Cal AI - Calorie Tracker",
                "publisher": "Viral Development",
                "features": ["卡路里追踪", "AI食物识别", "营养管理"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试单张截图验证
    test_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/Screens/Screen_001.png"
    if os.path.exists(test_screenshot):
        print("\nTesting screenshot verification...")
        result = await vision.verify_screenshot(
            test_screenshot,
            {
                "name": "Cal AI",
                "features": ["卡路里追踪", "AI食物识别", "苹果logo"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_vision())


"""
AI Vision Module - 使用Claude Vision进行截图验证
Sonnet: 搜索结果页识别目标App
Haiku: 批量验证截图归属
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 模型配置
SONNET_MODEL = "claude-3-5-sonnet-20241022"  # 检索用 - 更准确
HAIKU_MODEL = "claude-3-haiku-20240307"      # 验证用 - 更快更便宜

API_URL = "https://api.anthropic.com/v1/messages"


class AIVision:
    """AI视觉验证类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> tuple:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            data = f.read()
        
        # 判断图片类型
        if image_path.lower().endswith(".png"):
            media_type = "image/png"
        elif image_path.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_path.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/png"
        
        return base64.standard_b64encode(data).decode("utf-8"), media_type
    
    async def _call_api(self, model: str, messages: list, max_tokens: int = 1024) -> dict:
        """调用Claude API"""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["content"][0]["text"]
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API Error {response.status}: {error_text}"
                    }
    
    async def identify_app_in_search(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Sonnet分析搜索结果页，识别目标App的位置
        
        Args:
            screenshot_path: 搜索结果页截图路径
            target_app: 目标App信息 {"name": "Cal AI", "publisher": "Viral Development", "features": [...]}
        
        Returns:
            {
                "found": True/False,
                "position": "第1个卡片" / "row1_col2" / 坐标,
                "app_name": "匹配到的App名称",
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"found": False, "error": "Screenshot file not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        # 构建Prompt
        app_name = target_app.get("name", "")
        publisher = target_app.get("publisher", "")
        features = target_app.get("features", [])
        
        prompt = f"""分析这张screensdesign.com的搜索结果页面截图。

我要找的目标App是：
- 名称：{app_name}
- 发行商：{publisher}
- 特征：{', '.join(features) if features else '无特定特征'}

请仔细查看页面中的所有App卡片，找出与目标App匹配的那个。

返回JSON格式：
{{
    "found": true/false,
    "position": "描述App在页面中的位置（如：第1个卡片、左上角、第2行第1列等）",
    "matched_name": "页面上显示的App名称",
    "confidence": 0.0-1.0的置信度,
    "reason": "为什么认为这是/不是目标App"
}}

只返回JSON，不要其他文字。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(SONNET_MODEL, messages)
        
        if not result["success"]:
            return {"found": False, "error": result["error"]}
        
        try:
            # 解析JSON响应
            content = result["content"].strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "found": False,
                "error": f"Failed to parse response: {e}",
                "raw_response": result["content"]
            }
    
    async def verify_screenshot(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Haiku验证单张截图是否属于目标App
        
        Args:
            screenshot_path: 截图路径
            target_app: 目标App信息
        
        Returns:
            {
                "belongs": True/False,
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"belongs": False, "confidence": 0, "error": "File not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        app_name = target_app.get("name", "")
        features = target_app.get("features", [])
        
        # 简洁的Prompt以提高Haiku效率
        prompt = f"""判断这张App截图是否属于"{app_name}"。

App特征：{', '.join(features) if features else '卡路里追踪、食物识别、营养管理'}

返回JSON：
{{"belongs": true/false, "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(HAIKU_MODEL, messages, max_tokens=256)
        
        if not result["success"]:
            return {"belongs": False, "confidence": 0, "error": result["error"]}
        
        try:
            content = result["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # 尝试简单解析
            content_lower = result["content"].lower()
            if '"belongs": true' in content_lower or '"belongs":true' in content_lower:
                return {"belongs": True, "confidence": 0.7, "reason": "Parsed from response"}
            elif '"belongs": false' in content_lower or '"belongs":false' in content_lower:
                return {"belongs": False, "confidence": 0.7, "reason": "Parsed from response"}
            else:
                return {"belongs": False, "confidence": 0, "error": "Parse failed", "raw": result["content"]}
    
    async def batch_verify(self, screenshots: List[str], target_app: dict, 
                          concurrency: int = 5, progress_callback=None) -> Dict[str, dict]:
        """
        批量验证截图
        
        Args:
            screenshots: 截图路径列表
            target_app: 目标App信息
            concurrency: 并发数
            progress_callback: 进度回调函数 callback(current, total)
        
        Returns:
            {
                "Screen_001.png": {"belongs": True, "confidence": 0.95, "reason": "..."},
                "Screen_002.png": {"belongs": False, "confidence": 0.8, "reason": "..."},
                ...
            }
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        total = len(screenshots)
        completed = 0
        
        async def verify_one(path: str):
            nonlocal completed
            async with semaphore:
                filename = os.path.basename(path)
                result = await self.verify_screenshot(path, target_app)
                results[filename] = result
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                
                return filename, result
        
        # 创建所有任务
        tasks = [verify_one(path) for path in screenshots]
        
        # 执行并等待所有任务完成
        await asyncio.gather(*tasks)
        
        return results
    
    def filter_screenshots(self, verification_results: Dict[str, dict], 
                          confidence_threshold: float = 0.6) -> tuple:
        """
        根据验证结果过滤截图
        
        Args:
            verification_results: batch_verify的返回结果
            confidence_threshold: 置信度阈值
        
        Returns:
            (passed_list, rejected_list, uncertain_list)
        """
        passed = []
        rejected = []
        uncertain = []
        
        for filename, result in verification_results.items():
            if result.get("error"):
                uncertain.append(filename)
            elif result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                passed.append(filename)
            elif not result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                rejected.append(filename)
            else:
                uncertain.append(filename)
        
        return passed, rejected, uncertain


# ==================== 辅助函数 ====================

def load_api_key() -> str:
    """从配置文件加载API Key"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "api_keys.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ANTHROPIC_API_KEY", "")
    return os.environ.get("ANTHROPIC_API_KEY", "")


async def test_vision():
    """测试AI视觉模块"""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found")
        return
    
    vision = AIVision(api_key)
    
    # 测试识别搜索结果
    test_search_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/debug_after_click.png"
    if os.path.exists(test_search_screenshot):
        print("Testing search identification...")
        result = await vision.identify_app_in_search(
            test_search_screenshot,
            {
                "name": "Cal AI - Calorie Tracker",
                "publisher": "Viral Development",
                "features": ["卡路里追踪", "AI食物识别", "营养管理"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试单张截图验证
    test_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/Screens/Screen_001.png"
    if os.path.exists(test_screenshot):
        print("\nTesting screenshot verification...")
        result = await vision.verify_screenshot(
            test_screenshot,
            {
                "name": "Cal AI",
                "features": ["卡路里追踪", "AI食物识别", "苹果logo"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_vision())


"""
AI Vision Module - 使用Claude Vision进行截图验证
Sonnet: 搜索结果页识别目标App
Haiku: 批量验证截图归属
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 模型配置
SONNET_MODEL = "claude-3-5-sonnet-20241022"  # 检索用 - 更准确
HAIKU_MODEL = "claude-3-haiku-20240307"      # 验证用 - 更快更便宜

API_URL = "https://api.anthropic.com/v1/messages"


class AIVision:
    """AI视觉验证类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> tuple:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            data = f.read()
        
        # 判断图片类型
        if image_path.lower().endswith(".png"):
            media_type = "image/png"
        elif image_path.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_path.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/png"
        
        return base64.standard_b64encode(data).decode("utf-8"), media_type
    
    async def _call_api(self, model: str, messages: list, max_tokens: int = 1024) -> dict:
        """调用Claude API"""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["content"][0]["text"]
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API Error {response.status}: {error_text}"
                    }
    
    async def identify_app_in_search(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Sonnet分析搜索结果页，识别目标App的位置
        
        Args:
            screenshot_path: 搜索结果页截图路径
            target_app: 目标App信息 {"name": "Cal AI", "publisher": "Viral Development", "features": [...]}
        
        Returns:
            {
                "found": True/False,
                "position": "第1个卡片" / "row1_col2" / 坐标,
                "app_name": "匹配到的App名称",
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"found": False, "error": "Screenshot file not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        # 构建Prompt
        app_name = target_app.get("name", "")
        publisher = target_app.get("publisher", "")
        features = target_app.get("features", [])
        
        prompt = f"""分析这张screensdesign.com的搜索结果页面截图。

我要找的目标App是：
- 名称：{app_name}
- 发行商：{publisher}
- 特征：{', '.join(features) if features else '无特定特征'}

请仔细查看页面中的所有App卡片，找出与目标App匹配的那个。

返回JSON格式：
{{
    "found": true/false,
    "position": "描述App在页面中的位置（如：第1个卡片、左上角、第2行第1列等）",
    "matched_name": "页面上显示的App名称",
    "confidence": 0.0-1.0的置信度,
    "reason": "为什么认为这是/不是目标App"
}}

只返回JSON，不要其他文字。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(SONNET_MODEL, messages)
        
        if not result["success"]:
            return {"found": False, "error": result["error"]}
        
        try:
            # 解析JSON响应
            content = result["content"].strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "found": False,
                "error": f"Failed to parse response: {e}",
                "raw_response": result["content"]
            }
    
    async def verify_screenshot(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Haiku验证单张截图是否属于目标App
        
        Args:
            screenshot_path: 截图路径
            target_app: 目标App信息
        
        Returns:
            {
                "belongs": True/False,
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"belongs": False, "confidence": 0, "error": "File not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        app_name = target_app.get("name", "")
        features = target_app.get("features", [])
        
        # 简洁的Prompt以提高Haiku效率
        prompt = f"""判断这张App截图是否属于"{app_name}"。

App特征：{', '.join(features) if features else '卡路里追踪、食物识别、营养管理'}

返回JSON：
{{"belongs": true/false, "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(HAIKU_MODEL, messages, max_tokens=256)
        
        if not result["success"]:
            return {"belongs": False, "confidence": 0, "error": result["error"]}
        
        try:
            content = result["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # 尝试简单解析
            content_lower = result["content"].lower()
            if '"belongs": true' in content_lower or '"belongs":true' in content_lower:
                return {"belongs": True, "confidence": 0.7, "reason": "Parsed from response"}
            elif '"belongs": false' in content_lower or '"belongs":false' in content_lower:
                return {"belongs": False, "confidence": 0.7, "reason": "Parsed from response"}
            else:
                return {"belongs": False, "confidence": 0, "error": "Parse failed", "raw": result["content"]}
    
    async def batch_verify(self, screenshots: List[str], target_app: dict, 
                          concurrency: int = 5, progress_callback=None) -> Dict[str, dict]:
        """
        批量验证截图
        
        Args:
            screenshots: 截图路径列表
            target_app: 目标App信息
            concurrency: 并发数
            progress_callback: 进度回调函数 callback(current, total)
        
        Returns:
            {
                "Screen_001.png": {"belongs": True, "confidence": 0.95, "reason": "..."},
                "Screen_002.png": {"belongs": False, "confidence": 0.8, "reason": "..."},
                ...
            }
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        total = len(screenshots)
        completed = 0
        
        async def verify_one(path: str):
            nonlocal completed
            async with semaphore:
                filename = os.path.basename(path)
                result = await self.verify_screenshot(path, target_app)
                results[filename] = result
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                
                return filename, result
        
        # 创建所有任务
        tasks = [verify_one(path) for path in screenshots]
        
        # 执行并等待所有任务完成
        await asyncio.gather(*tasks)
        
        return results
    
    def filter_screenshots(self, verification_results: Dict[str, dict], 
                          confidence_threshold: float = 0.6) -> tuple:
        """
        根据验证结果过滤截图
        
        Args:
            verification_results: batch_verify的返回结果
            confidence_threshold: 置信度阈值
        
        Returns:
            (passed_list, rejected_list, uncertain_list)
        """
        passed = []
        rejected = []
        uncertain = []
        
        for filename, result in verification_results.items():
            if result.get("error"):
                uncertain.append(filename)
            elif result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                passed.append(filename)
            elif not result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                rejected.append(filename)
            else:
                uncertain.append(filename)
        
        return passed, rejected, uncertain


# ==================== 辅助函数 ====================

def load_api_key() -> str:
    """从配置文件加载API Key"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "api_keys.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ANTHROPIC_API_KEY", "")
    return os.environ.get("ANTHROPIC_API_KEY", "")


async def test_vision():
    """测试AI视觉模块"""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found")
        return
    
    vision = AIVision(api_key)
    
    # 测试识别搜索结果
    test_search_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/debug_after_click.png"
    if os.path.exists(test_search_screenshot):
        print("Testing search identification...")
        result = await vision.identify_app_in_search(
            test_search_screenshot,
            {
                "name": "Cal AI - Calorie Tracker",
                "publisher": "Viral Development",
                "features": ["卡路里追踪", "AI食物识别", "营养管理"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试单张截图验证
    test_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/Screens/Screen_001.png"
    if os.path.exists(test_screenshot):
        print("\nTesting screenshot verification...")
        result = await vision.verify_screenshot(
            test_screenshot,
            {
                "name": "Cal AI",
                "features": ["卡路里追踪", "AI食物识别", "苹果logo"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_vision())


"""
AI Vision Module - 使用Claude Vision进行截图验证
Sonnet: 搜索结果页识别目标App
Haiku: 批量验证截图归属
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 模型配置
SONNET_MODEL = "claude-3-5-sonnet-20241022"  # 检索用 - 更准确
HAIKU_MODEL = "claude-3-haiku-20240307"      # 验证用 - 更快更便宜

API_URL = "https://api.anthropic.com/v1/messages"


class AIVision:
    """AI视觉验证类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> tuple:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            data = f.read()
        
        # 判断图片类型
        if image_path.lower().endswith(".png"):
            media_type = "image/png"
        elif image_path.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_path.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/png"
        
        return base64.standard_b64encode(data).decode("utf-8"), media_type
    
    async def _call_api(self, model: str, messages: list, max_tokens: int = 1024) -> dict:
        """调用Claude API"""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["content"][0]["text"]
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API Error {response.status}: {error_text}"
                    }
    
    async def identify_app_in_search(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Sonnet分析搜索结果页，识别目标App的位置
        
        Args:
            screenshot_path: 搜索结果页截图路径
            target_app: 目标App信息 {"name": "Cal AI", "publisher": "Viral Development", "features": [...]}
        
        Returns:
            {
                "found": True/False,
                "position": "第1个卡片" / "row1_col2" / 坐标,
                "app_name": "匹配到的App名称",
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"found": False, "error": "Screenshot file not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        # 构建Prompt
        app_name = target_app.get("name", "")
        publisher = target_app.get("publisher", "")
        features = target_app.get("features", [])
        
        prompt = f"""分析这张screensdesign.com的搜索结果页面截图。

我要找的目标App是：
- 名称：{app_name}
- 发行商：{publisher}
- 特征：{', '.join(features) if features else '无特定特征'}

请仔细查看页面中的所有App卡片，找出与目标App匹配的那个。

返回JSON格式：
{{
    "found": true/false,
    "position": "描述App在页面中的位置（如：第1个卡片、左上角、第2行第1列等）",
    "matched_name": "页面上显示的App名称",
    "confidence": 0.0-1.0的置信度,
    "reason": "为什么认为这是/不是目标App"
}}

只返回JSON，不要其他文字。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(SONNET_MODEL, messages)
        
        if not result["success"]:
            return {"found": False, "error": result["error"]}
        
        try:
            # 解析JSON响应
            content = result["content"].strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "found": False,
                "error": f"Failed to parse response: {e}",
                "raw_response": result["content"]
            }
    
    async def verify_screenshot(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Haiku验证单张截图是否属于目标App
        
        Args:
            screenshot_path: 截图路径
            target_app: 目标App信息
        
        Returns:
            {
                "belongs": True/False,
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"belongs": False, "confidence": 0, "error": "File not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        app_name = target_app.get("name", "")
        features = target_app.get("features", [])
        
        # 简洁的Prompt以提高Haiku效率
        prompt = f"""判断这张App截图是否属于"{app_name}"。

App特征：{', '.join(features) if features else '卡路里追踪、食物识别、营养管理'}

返回JSON：
{{"belongs": true/false, "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(HAIKU_MODEL, messages, max_tokens=256)
        
        if not result["success"]:
            return {"belongs": False, "confidence": 0, "error": result["error"]}
        
        try:
            content = result["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # 尝试简单解析
            content_lower = result["content"].lower()
            if '"belongs": true' in content_lower or '"belongs":true' in content_lower:
                return {"belongs": True, "confidence": 0.7, "reason": "Parsed from response"}
            elif '"belongs": false' in content_lower or '"belongs":false' in content_lower:
                return {"belongs": False, "confidence": 0.7, "reason": "Parsed from response"}
            else:
                return {"belongs": False, "confidence": 0, "error": "Parse failed", "raw": result["content"]}
    
    async def batch_verify(self, screenshots: List[str], target_app: dict, 
                          concurrency: int = 5, progress_callback=None) -> Dict[str, dict]:
        """
        批量验证截图
        
        Args:
            screenshots: 截图路径列表
            target_app: 目标App信息
            concurrency: 并发数
            progress_callback: 进度回调函数 callback(current, total)
        
        Returns:
            {
                "Screen_001.png": {"belongs": True, "confidence": 0.95, "reason": "..."},
                "Screen_002.png": {"belongs": False, "confidence": 0.8, "reason": "..."},
                ...
            }
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        total = len(screenshots)
        completed = 0
        
        async def verify_one(path: str):
            nonlocal completed
            async with semaphore:
                filename = os.path.basename(path)
                result = await self.verify_screenshot(path, target_app)
                results[filename] = result
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                
                return filename, result
        
        # 创建所有任务
        tasks = [verify_one(path) for path in screenshots]
        
        # 执行并等待所有任务完成
        await asyncio.gather(*tasks)
        
        return results
    
    def filter_screenshots(self, verification_results: Dict[str, dict], 
                          confidence_threshold: float = 0.6) -> tuple:
        """
        根据验证结果过滤截图
        
        Args:
            verification_results: batch_verify的返回结果
            confidence_threshold: 置信度阈值
        
        Returns:
            (passed_list, rejected_list, uncertain_list)
        """
        passed = []
        rejected = []
        uncertain = []
        
        for filename, result in verification_results.items():
            if result.get("error"):
                uncertain.append(filename)
            elif result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                passed.append(filename)
            elif not result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                rejected.append(filename)
            else:
                uncertain.append(filename)
        
        return passed, rejected, uncertain


# ==================== 辅助函数 ====================

def load_api_key() -> str:
    """从配置文件加载API Key"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "api_keys.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ANTHROPIC_API_KEY", "")
    return os.environ.get("ANTHROPIC_API_KEY", "")


async def test_vision():
    """测试AI视觉模块"""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found")
        return
    
    vision = AIVision(api_key)
    
    # 测试识别搜索结果
    test_search_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/debug_after_click.png"
    if os.path.exists(test_search_screenshot):
        print("Testing search identification...")
        result = await vision.identify_app_in_search(
            test_search_screenshot,
            {
                "name": "Cal AI - Calorie Tracker",
                "publisher": "Viral Development",
                "features": ["卡路里追踪", "AI食物识别", "营养管理"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试单张截图验证
    test_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/Screens/Screen_001.png"
    if os.path.exists(test_screenshot):
        print("\nTesting screenshot verification...")
        result = await vision.verify_screenshot(
            test_screenshot,
            {
                "name": "Cal AI",
                "features": ["卡路里追踪", "AI食物识别", "苹果logo"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_vision())



"""
AI Vision Module - 使用Claude Vision进行截图验证
Sonnet: 搜索结果页识别目标App
Haiku: 批量验证截图归属
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 模型配置
SONNET_MODEL = "claude-3-5-sonnet-20241022"  # 检索用 - 更准确
HAIKU_MODEL = "claude-3-haiku-20240307"      # 验证用 - 更快更便宜

API_URL = "https://api.anthropic.com/v1/messages"


class AIVision:
    """AI视觉验证类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> tuple:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            data = f.read()
        
        # 判断图片类型
        if image_path.lower().endswith(".png"):
            media_type = "image/png"
        elif image_path.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_path.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/png"
        
        return base64.standard_b64encode(data).decode("utf-8"), media_type
    
    async def _call_api(self, model: str, messages: list, max_tokens: int = 1024) -> dict:
        """调用Claude API"""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["content"][0]["text"]
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API Error {response.status}: {error_text}"
                    }
    
    async def identify_app_in_search(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Sonnet分析搜索结果页，识别目标App的位置
        
        Args:
            screenshot_path: 搜索结果页截图路径
            target_app: 目标App信息 {"name": "Cal AI", "publisher": "Viral Development", "features": [...]}
        
        Returns:
            {
                "found": True/False,
                "position": "第1个卡片" / "row1_col2" / 坐标,
                "app_name": "匹配到的App名称",
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"found": False, "error": "Screenshot file not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        # 构建Prompt
        app_name = target_app.get("name", "")
        publisher = target_app.get("publisher", "")
        features = target_app.get("features", [])
        
        prompt = f"""分析这张screensdesign.com的搜索结果页面截图。

我要找的目标App是：
- 名称：{app_name}
- 发行商：{publisher}
- 特征：{', '.join(features) if features else '无特定特征'}

请仔细查看页面中的所有App卡片，找出与目标App匹配的那个。

返回JSON格式：
{{
    "found": true/false,
    "position": "描述App在页面中的位置（如：第1个卡片、左上角、第2行第1列等）",
    "matched_name": "页面上显示的App名称",
    "confidence": 0.0-1.0的置信度,
    "reason": "为什么认为这是/不是目标App"
}}

只返回JSON，不要其他文字。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(SONNET_MODEL, messages)
        
        if not result["success"]:
            return {"found": False, "error": result["error"]}
        
        try:
            # 解析JSON响应
            content = result["content"].strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "found": False,
                "error": f"Failed to parse response: {e}",
                "raw_response": result["content"]
            }
    
    async def verify_screenshot(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Haiku验证单张截图是否属于目标App
        
        Args:
            screenshot_path: 截图路径
            target_app: 目标App信息
        
        Returns:
            {
                "belongs": True/False,
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"belongs": False, "confidence": 0, "error": "File not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        app_name = target_app.get("name", "")
        features = target_app.get("features", [])
        
        # 简洁的Prompt以提高Haiku效率
        prompt = f"""判断这张App截图是否属于"{app_name}"。

App特征：{', '.join(features) if features else '卡路里追踪、食物识别、营养管理'}

返回JSON：
{{"belongs": true/false, "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(HAIKU_MODEL, messages, max_tokens=256)
        
        if not result["success"]:
            return {"belongs": False, "confidence": 0, "error": result["error"]}
        
        try:
            content = result["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # 尝试简单解析
            content_lower = result["content"].lower()
            if '"belongs": true' in content_lower or '"belongs":true' in content_lower:
                return {"belongs": True, "confidence": 0.7, "reason": "Parsed from response"}
            elif '"belongs": false' in content_lower or '"belongs":false' in content_lower:
                return {"belongs": False, "confidence": 0.7, "reason": "Parsed from response"}
            else:
                return {"belongs": False, "confidence": 0, "error": "Parse failed", "raw": result["content"]}
    
    async def batch_verify(self, screenshots: List[str], target_app: dict, 
                          concurrency: int = 5, progress_callback=None) -> Dict[str, dict]:
        """
        批量验证截图
        
        Args:
            screenshots: 截图路径列表
            target_app: 目标App信息
            concurrency: 并发数
            progress_callback: 进度回调函数 callback(current, total)
        
        Returns:
            {
                "Screen_001.png": {"belongs": True, "confidence": 0.95, "reason": "..."},
                "Screen_002.png": {"belongs": False, "confidence": 0.8, "reason": "..."},
                ...
            }
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        total = len(screenshots)
        completed = 0
        
        async def verify_one(path: str):
            nonlocal completed
            async with semaphore:
                filename = os.path.basename(path)
                result = await self.verify_screenshot(path, target_app)
                results[filename] = result
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                
                return filename, result
        
        # 创建所有任务
        tasks = [verify_one(path) for path in screenshots]
        
        # 执行并等待所有任务完成
        await asyncio.gather(*tasks)
        
        return results
    
    def filter_screenshots(self, verification_results: Dict[str, dict], 
                          confidence_threshold: float = 0.6) -> tuple:
        """
        根据验证结果过滤截图
        
        Args:
            verification_results: batch_verify的返回结果
            confidence_threshold: 置信度阈值
        
        Returns:
            (passed_list, rejected_list, uncertain_list)
        """
        passed = []
        rejected = []
        uncertain = []
        
        for filename, result in verification_results.items():
            if result.get("error"):
                uncertain.append(filename)
            elif result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                passed.append(filename)
            elif not result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                rejected.append(filename)
            else:
                uncertain.append(filename)
        
        return passed, rejected, uncertain


# ==================== 辅助函数 ====================

def load_api_key() -> str:
    """从配置文件加载API Key"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "api_keys.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ANTHROPIC_API_KEY", "")
    return os.environ.get("ANTHROPIC_API_KEY", "")


async def test_vision():
    """测试AI视觉模块"""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found")
        return
    
    vision = AIVision(api_key)
    
    # 测试识别搜索结果
    test_search_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/debug_after_click.png"
    if os.path.exists(test_search_screenshot):
        print("Testing search identification...")
        result = await vision.identify_app_in_search(
            test_search_screenshot,
            {
                "name": "Cal AI - Calorie Tracker",
                "publisher": "Viral Development",
                "features": ["卡路里追踪", "AI食物识别", "营养管理"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试单张截图验证
    test_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/Screens/Screen_001.png"
    if os.path.exists(test_screenshot):
        print("\nTesting screenshot verification...")
        result = await vision.verify_screenshot(
            test_screenshot,
            {
                "name": "Cal AI",
                "features": ["卡路里追踪", "AI食物识别", "苹果logo"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_vision())


"""
AI Vision Module - 使用Claude Vision进行截图验证
Sonnet: 搜索结果页识别目标App
Haiku: 批量验证截图归属
"""

import os
import sys
import json
import base64
import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

# 模型配置
SONNET_MODEL = "claude-3-5-sonnet-20241022"  # 检索用 - 更准确
HAIKU_MODEL = "claude-3-haiku-20240307"      # 验证用 - 更快更便宜

API_URL = "https://api.anthropic.com/v1/messages"


class AIVision:
    """AI视觉验证类"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def _encode_image(self, image_path: str) -> tuple:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            data = f.read()
        
        # 判断图片类型
        if image_path.lower().endswith(".png"):
            media_type = "image/png"
        elif image_path.lower().endswith((".jpg", ".jpeg")):
            media_type = "image/jpeg"
        elif image_path.lower().endswith(".webp"):
            media_type = "image/webp"
        elif image_path.lower().endswith(".gif"):
            media_type = "image/gif"
        else:
            media_type = "image/png"
        
        return base64.standard_b64encode(data).decode("utf-8"), media_type
    
    async def _call_api(self, model: str, messages: list, max_tokens: int = 1024) -> dict:
        """调用Claude API"""
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=self.headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "content": result["content"][0]["text"]
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"API Error {response.status}: {error_text}"
                    }
    
    async def identify_app_in_search(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Sonnet分析搜索结果页，识别目标App的位置
        
        Args:
            screenshot_path: 搜索结果页截图路径
            target_app: 目标App信息 {"name": "Cal AI", "publisher": "Viral Development", "features": [...]}
        
        Returns:
            {
                "found": True/False,
                "position": "第1个卡片" / "row1_col2" / 坐标,
                "app_name": "匹配到的App名称",
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"found": False, "error": "Screenshot file not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        # 构建Prompt
        app_name = target_app.get("name", "")
        publisher = target_app.get("publisher", "")
        features = target_app.get("features", [])
        
        prompt = f"""分析这张screensdesign.com的搜索结果页面截图。

我要找的目标App是：
- 名称：{app_name}
- 发行商：{publisher}
- 特征：{', '.join(features) if features else '无特定特征'}

请仔细查看页面中的所有App卡片，找出与目标App匹配的那个。

返回JSON格式：
{{
    "found": true/false,
    "position": "描述App在页面中的位置（如：第1个卡片、左上角、第2行第1列等）",
    "matched_name": "页面上显示的App名称",
    "confidence": 0.0-1.0的置信度,
    "reason": "为什么认为这是/不是目标App"
}}

只返回JSON，不要其他文字。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(SONNET_MODEL, messages)
        
        if not result["success"]:
            return {"found": False, "error": result["error"]}
        
        try:
            # 解析JSON响应
            content = result["content"].strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "found": False,
                "error": f"Failed to parse response: {e}",
                "raw_response": result["content"]
            }
    
    async def verify_screenshot(self, screenshot_path: str, target_app: dict) -> dict:
        """
        使用Haiku验证单张截图是否属于目标App
        
        Args:
            screenshot_path: 截图路径
            target_app: 目标App信息
        
        Returns:
            {
                "belongs": True/False,
                "confidence": 0.95,
                "reason": "识别理由"
            }
        """
        if not os.path.exists(screenshot_path):
            return {"belongs": False, "confidence": 0, "error": "File not found"}
        
        image_data, media_type = self._encode_image(screenshot_path)
        
        app_name = target_app.get("name", "")
        features = target_app.get("features", [])
        
        # 简洁的Prompt以提高Haiku效率
        prompt = f"""判断这张App截图是否属于"{app_name}"。

App特征：{', '.join(features) if features else '卡路里追踪、食物识别、营养管理'}

返回JSON：
{{"belongs": true/false, "confidence": 0.0-1.0, "reason": "简短理由"}}

只返回JSON。"""

        messages = [{
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
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }]
        
        result = await self._call_api(HAIKU_MODEL, messages, max_tokens=256)
        
        if not result["success"]:
            return {"belongs": False, "confidence": 0, "error": result["error"]}
        
        try:
            content = result["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            parsed = json.loads(content)
            return parsed
        except json.JSONDecodeError:
            # 尝试简单解析
            content_lower = result["content"].lower()
            if '"belongs": true' in content_lower or '"belongs":true' in content_lower:
                return {"belongs": True, "confidence": 0.7, "reason": "Parsed from response"}
            elif '"belongs": false' in content_lower or '"belongs":false' in content_lower:
                return {"belongs": False, "confidence": 0.7, "reason": "Parsed from response"}
            else:
                return {"belongs": False, "confidence": 0, "error": "Parse failed", "raw": result["content"]}
    
    async def batch_verify(self, screenshots: List[str], target_app: dict, 
                          concurrency: int = 5, progress_callback=None) -> Dict[str, dict]:
        """
        批量验证截图
        
        Args:
            screenshots: 截图路径列表
            target_app: 目标App信息
            concurrency: 并发数
            progress_callback: 进度回调函数 callback(current, total)
        
        Returns:
            {
                "Screen_001.png": {"belongs": True, "confidence": 0.95, "reason": "..."},
                "Screen_002.png": {"belongs": False, "confidence": 0.8, "reason": "..."},
                ...
            }
        """
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        total = len(screenshots)
        completed = 0
        
        async def verify_one(path: str):
            nonlocal completed
            async with semaphore:
                filename = os.path.basename(path)
                result = await self.verify_screenshot(path, target_app)
                results[filename] = result
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, total)
                
                return filename, result
        
        # 创建所有任务
        tasks = [verify_one(path) for path in screenshots]
        
        # 执行并等待所有任务完成
        await asyncio.gather(*tasks)
        
        return results
    
    def filter_screenshots(self, verification_results: Dict[str, dict], 
                          confidence_threshold: float = 0.6) -> tuple:
        """
        根据验证结果过滤截图
        
        Args:
            verification_results: batch_verify的返回结果
            confidence_threshold: 置信度阈值
        
        Returns:
            (passed_list, rejected_list, uncertain_list)
        """
        passed = []
        rejected = []
        uncertain = []
        
        for filename, result in verification_results.items():
            if result.get("error"):
                uncertain.append(filename)
            elif result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                passed.append(filename)
            elif not result.get("belongs") and result.get("confidence", 0) >= confidence_threshold:
                rejected.append(filename)
            else:
                uncertain.append(filename)
        
        return passed, rejected, uncertain


# ==================== 辅助函数 ====================

def load_api_key() -> str:
    """从配置文件加载API Key"""
    config_path = os.path.join(os.path.dirname(__file__), "config", "api_keys.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("ANTHROPIC_API_KEY", "")
    return os.environ.get("ANTHROPIC_API_KEY", "")


async def test_vision():
    """测试AI视觉模块"""
    api_key = load_api_key()
    if not api_key:
        print("Error: No API key found")
        return
    
    vision = AIVision(api_key)
    
    # 测试识别搜索结果
    test_search_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/debug_after_click.png"
    if os.path.exists(test_search_screenshot):
        print("Testing search identification...")
        result = await vision.identify_app_in_search(
            test_search_screenshot,
            {
                "name": "Cal AI - Calorie Tracker",
                "publisher": "Viral Development",
                "features": ["卡路里追踪", "AI食物识别", "营养管理"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 测试单张截图验证
    test_screenshot = "projects/Cal_AI_-_Calorie_Tracker_Analysis/Screens/Screen_001.png"
    if os.path.exists(test_screenshot):
        print("\nTesting screenshot verification...")
        result = await vision.verify_screenshot(
            test_screenshot,
            {
                "name": "Cal AI",
                "features": ["卡路里追踪", "AI食物识别", "苹果logo"]
            }
        )
        print(f"Result: {json.dumps(result, ensure_ascii=False, indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_vision())










































