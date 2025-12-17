# -*- coding: utf-8 -*-
"""
AI截图分析器 - 核心模块
使用 Claude Vision API 分析App截图
输出结构化分析数据（含设计亮点、产品洞察）
"""

import os
import json
import base64
import time
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("警告: anthropic 库未安装，请运行: pip install anthropic")

# 导入验证规则
from validation_rules import SCREEN_TYPES, KEYWORD_RULES


# ============================================================
# 数据结构
# ============================================================

@dataclass
class DesignHighlight:
    """设计亮点"""
    category: str           # visual, interaction, conversion, emotional
    cn: str                 # 中文描述
    en: str                 # 英文描述


@dataclass
class BilingualText:
    """双语文本"""
    cn: str
    en: str


@dataclass
class BilingualTag:
    """双语标签"""
    cn: str
    en: str


@dataclass
class StructuredAnalysisResult:
    """结构化分析结果"""
    filename: str
    screen_type: str                        # 主类型
    sub_type: str                           # 子类型
    
    # 双语命名
    naming: Dict[str, str]                  # {"cn": "目标选择", "en": "Goal Selection"}
    
    # 核心功能（一句话）
    core_function: Dict[str, str]           # {"cn": "收集用户健康目标", "en": "Collect health goals"}
    
    # 设计亮点（3-5条）
    design_highlights: List[Dict]           # [{"category": "visual", "cn": "...", "en": "..."}]
    
    # 产品洞察
    product_insight: Dict[str, str]         # {"cn": "...", "en": "..."}
    
    # 双语标签
    tags: List[Dict[str, str]]              # [{"cn": "信息收集", "en": "Data Collection"}]
    
    # 兼容旧字段
    description_cn: str
    description_en: str
    ui_elements: List[str]
    keywords_found: List[str]
    confidence: float
    raw_response: str
    analysis_time: float
    error: Optional[str] = None


@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    project_name: str
    total_screenshots: int
    analyzed_count: int
    failed_count: int
    results: Dict[str, dict]
    start_time: str
    end_time: str
    total_time: float


# ============================================================
# 分析Prompt模板 - 结构化输出
# ============================================================

STRUCTURED_ANALYSIS_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。
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


# 兼容旧版本的简单Prompt
ANALYSIS_PROMPT = """分析这张移动App截图，判断它属于哪种类型的页面。

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

## 输出要求：
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "screen_type": "类型名（从上面列表选择）",
  "sub_type": "子类型（如: goal_selection, price_display, navigation等）",
  "description_cn": "中文描述（15-30字，描述页面内容和功能）",
  "description_en": "English description (10-20 words)",
  "ui_elements": ["element1", "element2", "element3"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95
}
```

只输出JSON，不要有任何解释文字"""


VERIFICATION_PROMPT = """验证这张截图是否属于 "{screen_type}" 类型。

该类型的典型特征：
- 关键词: {keywords}
- UI元素: {ui_elements}

请仔细检查截图，回答：
1. 这张截图是否确实属于 "{screen_type}" 类型？
2. 如果不是，它更可能是什么类型？

请严格按以下JSON格式输出：

```json
{{
  "is_correct": true或false,
  "confidence": 0.0-1.0的置信度,
  "suggested_type": "如果is_correct为false，给出建议的类型",
  "reason": "简短说明判断理由"
}}
```

只输出JSON，不要其他内容。"""


# ============================================================
# AI分析器类
# ============================================================

class AIScreenshotAnalyzer:
    """AI截图分析器"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-sonnet-4-20250514",
        use_structured: bool = True
    ):
        """
        初始化分析器
        
        Args:
            api_key: Anthropic API Key，如果不提供则从环境变量读取
            model: 使用的模型，默认 claude-sonnet-4-20250514
            use_structured: 是否使用结构化Prompt（默认True）
        """
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.use_structured = use_structured
        self.client = None
        
        if not self.api_key:
            print("=" * 60)
            print("[WARNING] ANTHROPIC_API_KEY not found")
            print("=" * 60)
            print("请通过以下方式之一设置API Key:")
            print("")
            print("方式1: 环境变量")
            print("  Windows: set ANTHROPIC_API_KEY=your_key_here")
            print("  Linux/Mac: export ANTHROPIC_API_KEY=your_key_here")
            print("")
            print("方式2: 代码中传入")
            print("  analyzer = AIScreenshotAnalyzer(api_key='your_key_here')")
            print("")
            print("获取API Key: https://console.anthropic.com/")
            print("=" * 60)
        else:
            if ANTHROPIC_AVAILABLE:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                print(f"[OK] AI Analyzer initialized (model: {self.model}, structured: {self.use_structured})")
            else:
                print("[ERROR] anthropic library not installed")
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        # 先尝试环境变量
        api_key = os.getenv("ANTHROPIC_API_KEY")
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
                    return config.get("ANTHROPIC_API_KEY")
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
        # 尝试直接解析
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取 ```json ... ``` 中的内容
        import re
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
        # 确保所有必需字段存在
        result = {
            "filename": filename,
            "screen_type": parsed.get("screen_type", "Unknown"),
            "sub_type": parsed.get("sub_type", ""),
            
            # 双语命名
            "naming": parsed.get("naming", {
                "cn": parsed.get("description_cn", "")[:20] if parsed.get("description_cn") else "",
                "en": parsed.get("description_en", "")[:30] if parsed.get("description_en") else ""
            }),
            
            # 核心功能
            "core_function": parsed.get("core_function", {
                "cn": parsed.get("description_cn", ""),
                "en": parsed.get("description_en", "")
            }),
            
            # 设计亮点
            "design_highlights": parsed.get("design_highlights", []),
            
            # 产品洞察
            "product_insight": parsed.get("product_insight", {
                "cn": "",
                "en": ""
            }),
            
            # 标签
            "tags": parsed.get("tags", []),
            
            # 兼容旧字段
            "description_cn": parsed.get("description_cn", 
                parsed.get("core_function", {}).get("cn", "")),
            "description_en": parsed.get("description_en",
                parsed.get("core_function", {}).get("en", "")),
            "ui_elements": parsed.get("ui_elements", []),
            "keywords_found": parsed.get("keywords_found", []),
            "confidence": float(parsed.get("confidence", 0.5)),
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
        
        # 错误结果模板
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
                "error": error_msg
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
        
        # 选择Prompt
        prompt = STRUCTURED_ANALYSIS_PROMPT if self.use_structured else ANALYSIS_PROMPT
        
        # 调用API
        last_error = None
        for attempt in range(retry_count + 1):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1500,
                    messages=[{
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
                )
                
                raw_response = response.content[0].text
                parsed = self._parse_json_response(raw_response)
                
                if parsed:
                    result = self._normalize_result(parsed, filename)
                    result["raw_response"] = raw_response
                    result["analysis_time"] = time.time() - start_time
                    result["error"] = None
                    return result
                else:
                    last_error = "Failed to parse JSON response"
                    
            except anthropic.RateLimitError as e:
                last_error = f"Rate limit: {e}"
                time.sleep(5)  # 等待5秒后重试
            except anthropic.APIError as e:
                last_error = f"API error: {e}"
            except Exception as e:
                last_error = str(e)
            
            if attempt < retry_count:
                time.sleep(1)  # 重试前等待
        
        # 所有重试都失败
        return error_result(last_error or "Unknown error")
    
    def verify_result(self, image_path: str, claimed_type: str) -> Dict:
        """
        验证分析结果是否正确
        
        Args:
            image_path: 图片路径
            claimed_type: 声称的类型
        
        Returns:
            验证结果字典
        """
        if not self.client:
            return {"is_correct": None, "error": "API not configured"}
        
        # 获取该类型的关键词
        rule = KEYWORD_RULES.get(claimed_type, {})
        keywords = ", ".join(rule.get("visual_keywords", [])[:10])
        ui_elements = ", ".join(rule.get("ui_elements", []))
        
        # 构建验证prompt
        prompt = VERIFICATION_PROMPT.format(
            screen_type=claimed_type,
            keywords=keywords,
            ui_elements=ui_elements
        )
        
        try:
            image_data, media_type = self._encode_image(image_path)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{
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
            )
            
            parsed = self._parse_json_response(response.content[0].text)
            return parsed if parsed else {"is_correct": None, "error": "Failed to parse response"}
            
        except Exception as e:
            return {"is_correct": None, "error": str(e)}
    
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
            progress_callback: 进度回调函数 callback(current, total, filename, result)
        
        Returns:
            BatchAnalysisResult 字典
        """
        start_time = datetime.now()
        
        # 获取所有图片文件
        image_files = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(image_files)
        results = {}
        failed_count = 0
        
        print(f"\n[BATCH] Starting analysis: {image_folder}")
        print(f"   Total: {total} screenshots")
        print(f"   Model: {self.model}")
        print(f"   Structured: {self.use_structured}")
        print("-" * 50)
        
        for i, filename in enumerate(image_files, 1):
            image_path = os.path.join(image_folder, filename)
            
            # 分析
            result = self.analyze_single(image_path)
            results[filename] = result
            
            if result.get("error"):
                failed_count += 1
                status = "FAIL"
            else:
                status = "OK"
            
            # 打印进度
            screen_type = result.get("screen_type", "Unknown")
            confidence = result.get("confidence", 0)
            print(f"[{i:3d}/{total}] {status:4s} {filename[:30]:30s} -> {screen_type:15s} ({confidence:.0%})")
            
            # 回调
            if progress_callback:
                progress_callback(i, total, filename, result)
            
            # 延迟
            if i < total:
                time.sleep(delay)
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # 构建结果
        batch_result = {
            "project_name": os.path.basename(image_folder),
            "total_screenshots": total,
            "analyzed_count": total - failed_count,
            "failed_count": failed_count,
            "results": results,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_time": total_time,
            "structured_mode": self.use_structured
        }
        
        # 保存结果
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, ensure_ascii=False, indent=2)
            print(f"\n[SAVED] Results saved: {output_file}")
        
        print("-" * 50)
        print(f"[DONE] Analysis complete: {total - failed_count}/{total} success")
        print(f"[TIME] Total: {total_time:.1f}s ({total_time/total:.2f}s per image)")
        
        return batch_result


# ============================================================
# 结果转换工具
# ============================================================

def convert_to_descriptions_json(analysis_result: Dict, output_path: str):
    """
    将分析结果转换为网页使用的 descriptions.json 格式
    
    Args:
        analysis_result: analyze_batch的返回结果
        output_path: 输出文件路径
    """
    descriptions = {}
    
    for filename, result in analysis_result.get("results", {}).items():
        # 优先使用core_function，其次是description_cn
        core_func = result.get("core_function", {})
        naming = result.get("naming", {})
        
        # 构建描述文本：页面名称 + 核心功能
        cn_name = naming.get("cn", "")
        cn_func = core_func.get("cn", result.get("description_cn", ""))
        
        if cn_name and cn_func:
            desc = f"{cn_name}：{cn_func}"
        else:
            desc = cn_func or cn_name or result.get("description_cn", "")
        
        descriptions[filename] = desc
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(descriptions, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Descriptions saved: {output_path}")


def convert_to_structured_descriptions(analysis_result: Dict, output_path: str):
    """
    将分析结果转换为结构化的 descriptions_structured.json
    包含完整的设计亮点、产品洞察等
    
    Args:
        analysis_result: analyze_batch的返回结果
        output_path: 输出文件路径
    """
    structured = {}
    
    for filename, result in analysis_result.get("results", {}).items():
        structured[filename] = {
            "screen_type": result.get("screen_type", "Unknown"),
            "naming": result.get("naming", {}),
            "core_function": result.get("core_function", {}),
            "design_highlights": result.get("design_highlights", []),
            "product_insight": result.get("product_insight", {}),
            "tags": result.get("tags", []),
            "confidence": result.get("confidence", 0)
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Structured descriptions saved: {output_path}")


# ============================================================
# 便捷函数
# ============================================================

def analyze_screenshot(image_path: str, api_key: Optional[str] = None) -> Dict:
    """
    分析单张截图的便捷函数
    
    Args:
        image_path: 图片路径
        api_key: Anthropic API Key
    
    Returns:
        分析结果字典
    """
    analyzer = AIScreenshotAnalyzer(api_key=api_key)
    return analyzer.analyze_single(image_path)


def analyze_project(
    project_path: str,
    api_key: Optional[str] = None,
    use_screens: bool = True,
    structured: bool = True
) -> Dict:
    """
    分析整个项目的便捷函数
    
    Args:
        project_path: 项目路径
        api_key: Anthropic API Key
        use_screens: 是否使用Screens文件夹（否则用Downloads）
        structured: 是否使用结构化分析
    
    Returns:
        批量分析结果字典
    """
    folder = "Screens" if use_screens else "Downloads"
    image_folder = os.path.join(project_path, folder)
    output_file = os.path.join(project_path, "ai_analysis.json")
    
    analyzer = AIScreenshotAnalyzer(api_key=api_key, use_structured=structured)
    result = analyzer.analyze_batch(image_folder, output_file)
    
    # 同时生成descriptions.json
    desc_file = os.path.join(project_path, "descriptions.json")
    convert_to_descriptions_json(result, desc_file)
    
    # 生成结构化描述
    if structured:
        struct_file = os.path.join(project_path, "descriptions_structured.json")
        convert_to_structured_descriptions(result, struct_file)
    
    return result


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI截图分析器 - 结构化输出")
    parser.add_argument("--project", type=str, help="项目路径或名称")
    parser.add_argument("--image", type=str, help="单张图片路径")
    parser.add_argument("--api-key", type=str, help="Anthropic API Key")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-20250514", help="模型名称")
    parser.add_argument("--delay", type=float, default=0.3, help="API调用间隔（秒）")
    parser.add_argument("--simple", action="store_true", help="使用简单模式（不输出结构化数据）")
    
    args = parser.parse_args()
    
    if args.image:
        # 分析单张图片
        analyzer = AIScreenshotAnalyzer(
            api_key=args.api_key, 
            model=args.model,
            use_structured=not args.simple
        )
        result = analyzer.analyze_single(args.image)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.project:
        # 分析整个项目
        if not os.path.isabs(args.project):
            # 相对路径，假设在projects文件夹下
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            args.project = os.path.join(base_dir, "projects", args.project)
        
        result = analyze_project(
            args.project,
            api_key=args.api_key,
            structured=not args.simple
        )
    
    else:
        parser.print_help()
