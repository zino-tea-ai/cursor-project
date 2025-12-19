# -*- coding: utf-8 -*-
"""
OpenAI GPT Vision 截图分析器
支持 GPT-4o, GPT-4o-mini, GPT-5.2 系列模型
"""

import os
import json
import base64
import time
from typing import Optional, Dict, List, Tuple
from datetime import datetime

# API相关
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("警告: openai 库未安装，请运行: pip install openai")


# ============================================================
# 模型配置
# ============================================================

OPENAI_MODELS = {
    # 快速模型 - 批量初筛
    'fast': 'gpt-4o-mini',
    # 标准模型 - 常规分析
    'standard': 'gpt-4o',
    # 深度模型 - 复杂推理（GPT-5.2 Thinking）
    'deep': 'gpt-4o',  # 当 GPT-5.2 可用时改为 'gpt-5.2'
    # 最强模型 - 关键验证
    'pro': 'gpt-4o',   # 当 GPT-5.2 Pro 可用时改为 'gpt-5.2-pro'
}


# ============================================================
# 分析Prompt模板
# ============================================================

ANALYSIS_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。
请从专业PM视角进行深度分析，输出结构化数据。

## 可选的页面类型：
- Launch: 启动页/闪屏页（显示logo、品牌名）
- Welcome: 欢迎页/价值主张页（介绍产品功能）
- Permission: 权限请求页（系统弹窗请求通知/位置/健康权限）
- SignUp: 注册/登录页（邮箱、密码、社交登录按钮）
- Onboarding: 引导问卷页（收集用户信息、目标、偏好）
- Paywall: 付费墙/订阅页（显示价格、试用、订阅按钮）
- Home: 首页/仪表盘（主界面、底部导航栏）
- Feature: 具体功能页
- Content: 内容/媒体播放页
- Profile: 个人中心/账户页
- Settings: 设置页
- Social: 社交/社区页
- Tracking: 追踪/记录页（输入数据）
- Progress: 进度/统计页（图表、数据展示）
- Other: 其他

## 设计亮点分类：
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 常用设计模式标签（选择3-5个最相关的）：
信息收集/Data Collection, 价值展示/Value Proposition, 进度指示/Progress Indicator,
个性化/Personalization, 社交证明/Social Proof, 稀缺性/Scarcity,
游戏化/Gamification, 多选/Multi-select, 卡片布局/Card Layout,
数据可视化/Data Viz, 空状态/Empty State, 引导提示/Tooltip,
底部弹窗/Bottom Sheet, 步骤引导/Stepper, 表单/Form,
列表/List, 搜索/Search, 筛选/Filter, 分类/Tabs,
图表/Chart, 日历/Calendar, 时间选择/Time Picker

## 输出要求：
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "screen_type": "类型名",
  "sub_type": "子类型",
  "naming": {
    "cn": "页面中文名（2-6字，简洁专业）",
    "en": "Page English Name (2-4 words)"
  },
  "core_function": {
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  },
  "design_highlights": [
    {
      "category": "visual",
      "cn": "设计亮点1中文描述",
      "en": "Design highlight 1 in English"
    },
    {
      "category": "interaction",
      "cn": "设计亮点2中文描述",
      "en": "Design highlight 2 in English"
    },
    {
      "category": "conversion",
      "cn": "设计亮点3中文描述",
      "en": "Design highlight 3 in English"
    }
  ],
  "product_insight": {
    "cn": "产品洞察（从PM视角分析设计意图和值得借鉴之处，30-60字）",
    "en": "Product insight from PM perspective (15-40 words)"
  },
  "tags": [
    {"cn": "标签1中文", "en": "Tag1 English"},
    {"cn": "标签2中文", "en": "Tag2 English"},
    {"cn": "标签3中文", "en": "Tag3 English"}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95
}
```

## 分析要点：
1. naming要简洁专业，如"目标选择"而非"目标选择页面"
2. design_highlights至少3条，覆盖不同category
3. product_insight要有深度，指出设计意图和可借鉴之处
4. tags选择最相关的3-5个，使用上面列出的标准标签
5. confidence是你对判断的置信度，0.0-1.0

只输出JSON，不要有任何解释文字。"""


# ============================================================
# OpenAI分析器类
# ============================================================

class OpenAIScreenshotAnalyzer:
    """OpenAI GPT Vision 截图分析器"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = None,
        tier: str = 'standard'
    ):
        """
        初始化分析器
        
        Args:
            api_key: OpenAI API Key，如果不提供则从环境变量或配置文件读取
            model: 使用的模型，如果不提供则根据tier自动选择
            tier: 模型层级 - fast/standard/deep/pro
        """
        self.api_key = api_key or self._load_api_key()
        self.tier = tier
        self.model = model or OPENAI_MODELS.get(tier, 'gpt-4o')
        self.client = None
        
        if not self.api_key:
            print("=" * 60)
            print("[WARNING] OPENAI_API_KEY not found")
            print("=" * 60)
            print("请通过以下方式之一设置API Key:")
            print("")
            print("方式1: 配置文件")
            print("  在 config/api_keys.json 中添加 OPENAI_API_KEY")
            print("")
            print("方式2: 环境变量")
            print("  Windows: set OPENAI_API_KEY=your_key_here")
            print("  Linux/Mac: export OPENAI_API_KEY=your_key_here")
            print("")
            print("获取API Key: https://platform.openai.com/api-keys")
            print("=" * 60)
        else:
            if OPENAI_AVAILABLE:
                try:
                    self.client = OpenAI(api_key=self.api_key)
                except TypeError:
                    # 某些环境下可能有代理问题，尝试不带额外参数初始化
                    import httpx
                    self.client = OpenAI(api_key=self.api_key, http_client=httpx.Client())
                print(f"[OK] OpenAI Analyzer initialized (model: {self.model}, tier: {self.tier})")
            else:
                print("[ERROR] openai library not installed")
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        # 先尝试环境变量
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # 再尝试配置文件
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get("OPENAI_API_KEY")
            except Exception:
                pass
        
        return None
    
    def _encode_image(self, image_path: str) -> Tuple[str, str]:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # 判断媒体类型
        ext = os.path.splitext(image_path)[1].lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(ext, "image/png")
        
        return image_data, media_type
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """解析AI响应中的JSON"""
        import re
        
        # 尝试直接解析
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 ```json ... ``` 中的内容
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试提取 { ... } 中的内容
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _normalize_result(self, parsed: Dict, filename: str) -> Dict:
        """将解析结果规范化为完整的结构化格式"""
        result = {
            "filename": filename,
            "screen_type": parsed.get("screen_type", "Unknown"),
            "sub_type": parsed.get("sub_type", ""),
            "naming": parsed.get("naming", {
                "cn": parsed.get("description_cn", "")[:20] if parsed.get("description_cn") else "",
                "en": parsed.get("description_en", "")[:30] if parsed.get("description_en") else ""
            }),
            "core_function": parsed.get("core_function", {
                "cn": parsed.get("description_cn", ""),
                "en": parsed.get("description_en", "")
            }),
            "design_highlights": parsed.get("design_highlights", []),
            "product_insight": parsed.get("product_insight", {"cn": "", "en": ""}),
            "tags": parsed.get("tags", []),
            "description_cn": parsed.get("description_cn", 
                parsed.get("core_function", {}).get("cn", "")),
            "description_en": parsed.get("description_en",
                parsed.get("core_function", {}).get("en", "")),
            "ui_elements": parsed.get("ui_elements", []),
            "keywords_found": parsed.get("keywords_found", []),
            "confidence": float(parsed.get("confidence", 0.5)),
            "provider": "openai",
            "model": self.model
        }
        
        # 如果没有description但有core_function，使用core_function
        if not result["description_cn"] and result["core_function"].get("cn"):
            result["description_cn"] = result["core_function"]["cn"]
        if not result["description_en"] and result["core_function"].get("en"):
            result["description_en"] = result["core_function"]["en"]
        
        return result
    
    def analyze_single(self, image_path: str, retry_count: int = 2) -> Dict:
        """
        分析单张截图
        
        Args:
            image_path: 图片路径
            retry_count: 失败重试次数
        
        Returns:
            结构化分析结果字典
        """
        filename = os.path.basename(image_path)
        start_time = time.time()
        
        def error_result(error_msg: str) -> Dict:
            return {
                "filename": filename,
                "screen_type": "Unknown",
                "sub_type": "",
                "naming": {"cn": "分析失败", "en": "Analysis Failed"},
                "core_function": {"cn": error_msg, "en": "Analysis failed"},
                "design_highlights": [],
                "product_insight": {"cn": "", "en": ""},
                "tags": [],
                "description_cn": error_msg,
                "description_en": "Analysis failed",
                "ui_elements": [],
                "keywords_found": [],
                "confidence": 0.0,
                "raw_response": "",
                "analysis_time": time.time() - start_time,
                "error": error_msg,
                "provider": "openai",
                "model": self.model
            }
        
        if not self.client:
            return error_result("未配置API")
        
        if not os.path.exists(image_path):
            return error_result(f"文件不存在: {image_path}")
        
        # 编码图片
        try:
            image_data, media_type = self._encode_image(image_path)
        except Exception as e:
            return error_result(f"图片读取错误: {e}")
        
        # 调用API
        last_error = None
        for attempt in range(retry_count + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}",
                                    "detail": "high"
                                }
                            },
                            {
                                "type": "text",
                                "text": ANALYSIS_PROMPT
                            }
                        ]
                    }]
                )
                
                raw_response = response.choices[0].message.content
                parsed = self._parse_json_response(raw_response)
                
                if parsed:
                    result = self._normalize_result(parsed, filename)
                    result["raw_response"] = raw_response
                    result["analysis_time"] = time.time() - start_time
                    result["error"] = None
                    return result
                else:
                    last_error = "Failed to parse JSON response"
                    
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower():
                    last_error = f"Rate limit: {e}"
                    time.sleep(5)
                else:
                    last_error = f"API error: {e}"
            
            if attempt < retry_count:
                time.sleep(1)
        
        return error_result(last_error or "Unknown error")
    
    def analyze_batch(
        self,
        image_folder: str,
        output_file: Optional[str] = None,
        delay: float = 0.3,
        progress_callback=None
    ) -> Dict:
        """
        批量分析文件夹中的所有截图
        
        Args:
            image_folder: 图片文件夹路径
            output_file: 输出JSON文件路径
            delay: 每次API调用间隔（秒）
            progress_callback: 进度回调函数
        
        Returns:
            批量分析结果字典
        """
        start_time = datetime.now()
        
        image_files = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(image_files)
        results = {}
        failed_count = 0
        
        print(f"\n[BATCH] Starting OpenAI analysis: {image_folder}")
        print(f"   Total: {total} screenshots")
        print(f"   Model: {self.model}")
        print(f"   Tier: {self.tier}")
        print("-" * 50)
        
        for i, filename in enumerate(image_files, 1):
            image_path = os.path.join(image_folder, filename)
            result = self.analyze_single(image_path)
            results[filename] = result
            
            if result.get("error"):
                failed_count += 1
                status = "FAIL"
            else:
                status = "OK"
            
            screen_type = result.get("screen_type", "Unknown")
            confidence = result.get("confidence", 0)
            print(f"[{i:3d}/{total}] {status:4s} {filename[:30]:30s} -> {screen_type:15s} ({confidence:.0%})")
            
            if progress_callback:
                progress_callback(i, total, filename, result)
            
            if i < total:
                time.sleep(delay)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        batch_result = {
            "project_name": os.path.basename(image_folder),
            "total_screenshots": total,
            "analyzed_count": total - failed_count,
            "failed_count": failed_count,
            "results": results,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_time": total_time,
            "provider": "openai",
            "model": self.model,
            "tier": self.tier
        }
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, ensure_ascii=False, indent=2)
            print(f"\n[SAVED] Results saved: {output_file}")
        
        print("-" * 50)
        print(f"[DONE] Analysis complete: {total - failed_count}/{total} success")
        print(f"[TIME] Total: {total_time:.1f}s ({total_time/total:.2f}s per image)")
        
        return batch_result


# ============================================================
# 便捷函数
# ============================================================

def analyze_screenshot_openai(image_path: str, tier: str = 'standard') -> Dict:
    """
    使用OpenAI分析单张截图的便捷函数
    
    Args:
        image_path: 图片路径
        tier: 模型层级 - fast/standard/deep/pro
    
    Returns:
        分析结果字典
    """
    analyzer = OpenAIScreenshotAnalyzer(tier=tier)
    return analyzer.analyze_single(image_path)


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenAI GPT Vision 截图分析器")
    parser.add_argument("--image", type=str, help="单张图片路径")
    parser.add_argument("--folder", type=str, help="图片文件夹路径")
    parser.add_argument("--tier", type=str, default="standard", 
                        choices=['fast', 'standard', 'deep', 'pro'],
                        help="模型层级: fast(gpt-4o-mini), standard(gpt-4o), deep, pro")
    parser.add_argument("--model", type=str, help="指定模型名称（覆盖tier设置）")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    
    args = parser.parse_args()
    
    if args.image:
        analyzer = OpenAIScreenshotAnalyzer(model=args.model, tier=args.tier)
        result = analyzer.analyze_single(args.image)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.folder:
        analyzer = OpenAIScreenshotAnalyzer(model=args.model, tier=args.tier)
        output_file = args.output or os.path.join(args.folder, "openai_analysis.json")
        analyzer.analyze_batch(args.folder, output_file)
    
    else:
        parser.print_help()









































