# -*- coding: utf-8 -*-
"""
Layer 2: 结构识别模块
基于产品画像，识别截图序列的流程阶段边界
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1
from layer1_product import ProductProfile


@dataclass
class FlowStage:
    """流程阶段"""
    name: str                    # 阶段名称
    start_index: int             # 起始索引（1-based）
    end_index: int               # 结束索引（1-based）
    description: str             # 阶段描述
    expected_types: List[str]    # 该阶段预期的screen_type列表
    screenshot_count: int = 0    # 该阶段的截图数量


@dataclass
class FlowStructure:
    """流程结构"""
    total_screenshots: int
    stages: List[FlowStage]
    paywall_position: str        # "early" / "middle" / "late" / "none"
    onboarding_length: str       # "short" (1-5) / "medium" (6-10) / "long" (11+)
    has_signup: bool
    has_social: bool
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 阶段类型与screen_type映射
# ============================================================

STAGE_TYPE_MAPPING = {
    "Launch": ["Launch"],
    "Welcome": ["Welcome", "Launch"],
    "Onboarding": ["Onboarding", "Permission"],
    "SignUp": ["SignUp"],
    "Paywall": ["Paywall"],
    "Home": ["Home"],
    "Core Features": ["Feature", "Content", "Tracking", "Progress"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social"],
    "Profile": ["Profile"],
    "Settings": ["Settings", "Profile"],
}


# ============================================================
# 提示词
# ============================================================

STRUCTURE_RECOGNITION_PROMPT = """你是一位资深产品经理，正在分析一款App的用户流程结构。

## 产品背景
- App类型: {app_category}
- 细分类别: {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 商业模式: {business_model}

## 任务
我会给你这款App的全部截图网格（按顺序排列，从左到右、从上到下），请识别用户流程的阶段划分。

截图总数: {total_screenshots}
网格排列: {grid_info}

## 阶段类型说明
- Launch: 启动页/闪屏（通常只有1张，显示logo）
- Welcome: 欢迎页/价值介绍（1-3张，展示产品亮点）
- Onboarding: 引导流程（收集用户信息、目标、偏好的问卷页面）
- SignUp: 注册/登录页面
- Paywall: 付费墙（显示价格、订阅选项）
- Home: 首页/主界面（底部导航栏、仪表盘）
- Core Features: 核心功能区（具体功能页面）
- Content: 内容浏览区（文章、视频、音频播放）
- Tracking: 追踪记录区（数据输入、日志）
- Progress: 进度统计区（图表、成就）
- Social: 社交功能区（社区、分享、排行榜）
- Profile: 个人中心
- Settings: 设置页面

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{{
  "stages": [
    {{
      "name": "阶段名称",
      "start_index": 1,
      "end_index": 3,
      "description": "该阶段的简短描述"
    }},
    {{
      "name": "下一阶段",
      "start_index": 4,
      "end_index": 10,
      "description": "描述"
    }}
  ],
  "paywall_position": "early/middle/late/none",
  "onboarding_length": "short/medium/long",
  "has_signup": true/false,
  "has_social": true/false,
  "confidence": 0.9
}}
```

## 注意事项
1. start_index 和 end_index 是1-based的索引（第1张、第2张...）
2. 阶段必须连续，不能有重叠或空隙
3. 最后一个阶段的end_index必须等于总截图数
4. paywall_position: early=前1/3, middle=中间1/3, late=后1/3, none=没有
5. onboarding_length: short=1-5张, medium=6-10张, long=11+张

只输出JSON，不要有任何解释文字。"""


class StructureRecognizer:
    """结构识别器 - Layer 2"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
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
    
    def create_sequence_grid(
        self, 
        image_folder: str,
        max_rows: int = 10,
        thumb_width: int = 150
    ) -> Tuple[Optional[bytes], int, str]:
        """
        创建带序号的截图序列网格
        
        Returns:
            (网格图字节, 总截图数, 网格信息描述)
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None, 0, ""
        
        total = len(images)
        
        # 计算网格大小
        cols = min(10, total)  # 最多10列
        rows = min(max_rows, (total + cols - 1) // cols)
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if total > max_images:
            step = total / max_images
            sampled_indices = [int(i * step) for i in range(max_images)]
            sampled = [(i+1, images[i]) for i in sampled_indices]
        else:
            sampled = [(i+1, f) for i, f in enumerate(images)]
        
        # 估算缩略图高度（假设手机截图比例约为 9:19）
        thumb_height = int(thumb_width * 2.1)
        
        # 创建网格画布
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (240, 240, 240))
        
        # 填充缩略图
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(grid_image)
        
        for idx, (original_idx, filename) in enumerate(sampled):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail((thumb_width - 4, thumb_height - 20), Image.Resampling.LANCZOS)
                
                # 计算位置
                x = col * thumb_width + (thumb_width - img.width) // 2
                y = row * thumb_height + 15 + (thumb_height - 15 - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
                # 绘制序号
                num_x = col * thumb_width + 5
                num_y = row * thumb_height + 2
                draw.text((num_x, num_y), f"#{original_idx}", fill=(100, 100, 100))
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        grid_info = f"{cols}列 x {rows}行"
        if total > max_images:
            grid_info += f"（采样自{total}张）"
        
        return buffer.getvalue(), total, grid_info
    
    def analyze(
        self, 
        project_path: str, 
        product_profile: ProductProfile
    ) -> FlowStructure:
        """
        分析流程结构
        
        Args:
            project_path: 项目路径
            product_profile: Layer 1的产品画像
        
        Returns:
            FlowStructure 流程结构
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_structure(0)
        
        # 创建序列网格
        print("  [Layer 2] Creating sequence grid...")
        grid_data, total_screenshots, grid_info = self.create_sequence_grid(screens_folder)
        
        if not grid_data or total_screenshots == 0:
            return self._default_structure(0)
        
        if not self.client:
            print("  [WARN] API not configured, using default structure")
            return self._default_structure(total_screenshots)
        
        # 构建提示词
        prompt = STRUCTURE_RECOGNITION_PROMPT.format(
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            business_model=product_profile.business_model,
            total_screenshots=total_screenshots,
            grid_info=grid_info
        )
        
        # 调用API分析
        print("  [Layer 2] Analyzing flow structure...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": grid_base64
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
            parsed = self._parse_json(raw_response)
            
            if parsed:
                stages = []
                for stage_data in parsed.get("stages", []):
                    name = stage_data.get("name", "Unknown")
                    expected_types = STAGE_TYPE_MAPPING.get(name, ["Feature"])
                    
                    stage = FlowStage(
                        name=name,
                        start_index=stage_data.get("start_index", 1),
                        end_index=stage_data.get("end_index", 1),
                        description=stage_data.get("description", ""),
                        expected_types=expected_types,
                        screenshot_count=stage_data.get("end_index", 1) - stage_data.get("start_index", 1) + 1
                    )
                    stages.append(stage)
                
                return FlowStructure(
                    total_screenshots=total_screenshots,
                    stages=stages,
                    paywall_position=parsed.get("paywall_position", "none"),
                    onboarding_length=parsed.get("onboarding_length", "medium"),
                    has_signup=parsed.get("has_signup", False),
                    has_social=parsed.get("has_social", False),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_structure(total_screenshots)
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_structure(self, total: int) -> FlowStructure:
        """返回默认的流程结构"""
        if total == 0:
            return FlowStructure(
                total_screenshots=0,
                stages=[],
                paywall_position="none",
                onboarding_length="medium",
                has_signup=False,
                has_social=False,
                confidence=0.0
            )
        
        # 默认划分：10% Welcome, 20% Onboarding, 5% Paywall, 55% Core, 10% Settings
        stages = []
        
        welcome_end = max(1, int(total * 0.1))
        stages.append(FlowStage(
            name="Welcome",
            start_index=1,
            end_index=welcome_end,
            description="欢迎和价值介绍",
            expected_types=["Welcome", "Launch"],
            screenshot_count=welcome_end
        ))
        
        onboarding_end = max(welcome_end + 1, int(total * 0.3))
        stages.append(FlowStage(
            name="Onboarding",
            start_index=welcome_end + 1,
            end_index=onboarding_end,
            description="引导流程",
            expected_types=["Onboarding", "Permission"],
            screenshot_count=onboarding_end - welcome_end
        ))
        
        paywall_end = max(onboarding_end + 1, int(total * 0.35))
        stages.append(FlowStage(
            name="Paywall",
            start_index=onboarding_end + 1,
            end_index=paywall_end,
            description="付费墙",
            expected_types=["Paywall"],
            screenshot_count=paywall_end - onboarding_end
        ))
        
        core_end = max(paywall_end + 1, int(total * 0.9))
        stages.append(FlowStage(
            name="Core Features",
            start_index=paywall_end + 1,
            end_index=core_end,
            description="核心功能",
            expected_types=["Feature", "Content", "Tracking", "Progress", "Home"],
            screenshot_count=core_end - paywall_end
        ))
        
        stages.append(FlowStage(
            name="Settings",
            start_index=core_end + 1,
            end_index=total,
            description="设置和账户",
            expected_types=["Settings", "Profile"],
            screenshot_count=total - core_end
        ))
        
        return FlowStructure(
            total_screenshots=total,
            stages=stages,
            paywall_position="early",
            onboarding_length="medium",
            has_signup=False,
            has_social=False,
            confidence=0.3
        )
    
    def get_stage_for_index(self, flow_structure: FlowStructure, index: int) -> Optional[FlowStage]:
        """根据索引获取所属阶段"""
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                return stage
        return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 2: Structure Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    print(f"  Target: {profile.target_users}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    
    print("\n" + "=" * 60)
    print("Flow Structure")
    print("=" * 60)
    for stage in structure.stages:
        print(f"  [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
    print(f"\n  Paywall Position: {structure.paywall_position}")
    print(f"  Onboarding Length: {structure.onboarding_length}")
    print(f"  Confidence: {structure.confidence:.0%}")


"""
Layer 2: 结构识别模块
基于产品画像，识别截图序列的流程阶段边界
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1
from layer1_product import ProductProfile


@dataclass
class FlowStage:
    """流程阶段"""
    name: str                    # 阶段名称
    start_index: int             # 起始索引（1-based）
    end_index: int               # 结束索引（1-based）
    description: str             # 阶段描述
    expected_types: List[str]    # 该阶段预期的screen_type列表
    screenshot_count: int = 0    # 该阶段的截图数量


@dataclass
class FlowStructure:
    """流程结构"""
    total_screenshots: int
    stages: List[FlowStage]
    paywall_position: str        # "early" / "middle" / "late" / "none"
    onboarding_length: str       # "short" (1-5) / "medium" (6-10) / "long" (11+)
    has_signup: bool
    has_social: bool
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 阶段类型与screen_type映射
# ============================================================

STAGE_TYPE_MAPPING = {
    "Launch": ["Launch"],
    "Welcome": ["Welcome", "Launch"],
    "Onboarding": ["Onboarding", "Permission"],
    "SignUp": ["SignUp"],
    "Paywall": ["Paywall"],
    "Home": ["Home"],
    "Core Features": ["Feature", "Content", "Tracking", "Progress"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social"],
    "Profile": ["Profile"],
    "Settings": ["Settings", "Profile"],
}


# ============================================================
# 提示词
# ============================================================

STRUCTURE_RECOGNITION_PROMPT = """你是一位资深产品经理，正在分析一款App的用户流程结构。

## 产品背景
- App类型: {app_category}
- 细分类别: {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 商业模式: {business_model}

## 任务
我会给你这款App的全部截图网格（按顺序排列，从左到右、从上到下），请识别用户流程的阶段划分。

截图总数: {total_screenshots}
网格排列: {grid_info}

## 阶段类型说明
- Launch: 启动页/闪屏（通常只有1张，显示logo）
- Welcome: 欢迎页/价值介绍（1-3张，展示产品亮点）
- Onboarding: 引导流程（收集用户信息、目标、偏好的问卷页面）
- SignUp: 注册/登录页面
- Paywall: 付费墙（显示价格、订阅选项）
- Home: 首页/主界面（底部导航栏、仪表盘）
- Core Features: 核心功能区（具体功能页面）
- Content: 内容浏览区（文章、视频、音频播放）
- Tracking: 追踪记录区（数据输入、日志）
- Progress: 进度统计区（图表、成就）
- Social: 社交功能区（社区、分享、排行榜）
- Profile: 个人中心
- Settings: 设置页面

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{{
  "stages": [
    {{
      "name": "阶段名称",
      "start_index": 1,
      "end_index": 3,
      "description": "该阶段的简短描述"
    }},
    {{
      "name": "下一阶段",
      "start_index": 4,
      "end_index": 10,
      "description": "描述"
    }}
  ],
  "paywall_position": "early/middle/late/none",
  "onboarding_length": "short/medium/long",
  "has_signup": true/false,
  "has_social": true/false,
  "confidence": 0.9
}}
```

## 注意事项
1. start_index 和 end_index 是1-based的索引（第1张、第2张...）
2. 阶段必须连续，不能有重叠或空隙
3. 最后一个阶段的end_index必须等于总截图数
4. paywall_position: early=前1/3, middle=中间1/3, late=后1/3, none=没有
5. onboarding_length: short=1-5张, medium=6-10张, long=11+张

只输出JSON，不要有任何解释文字。"""


class StructureRecognizer:
    """结构识别器 - Layer 2"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
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
    
    def create_sequence_grid(
        self, 
        image_folder: str,
        max_rows: int = 10,
        thumb_width: int = 150
    ) -> Tuple[Optional[bytes], int, str]:
        """
        创建带序号的截图序列网格
        
        Returns:
            (网格图字节, 总截图数, 网格信息描述)
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None, 0, ""
        
        total = len(images)
        
        # 计算网格大小
        cols = min(10, total)  # 最多10列
        rows = min(max_rows, (total + cols - 1) // cols)
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if total > max_images:
            step = total / max_images
            sampled_indices = [int(i * step) for i in range(max_images)]
            sampled = [(i+1, images[i]) for i in sampled_indices]
        else:
            sampled = [(i+1, f) for i, f in enumerate(images)]
        
        # 估算缩略图高度（假设手机截图比例约为 9:19）
        thumb_height = int(thumb_width * 2.1)
        
        # 创建网格画布
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (240, 240, 240))
        
        # 填充缩略图
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(grid_image)
        
        for idx, (original_idx, filename) in enumerate(sampled):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail((thumb_width - 4, thumb_height - 20), Image.Resampling.LANCZOS)
                
                # 计算位置
                x = col * thumb_width + (thumb_width - img.width) // 2
                y = row * thumb_height + 15 + (thumb_height - 15 - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
                # 绘制序号
                num_x = col * thumb_width + 5
                num_y = row * thumb_height + 2
                draw.text((num_x, num_y), f"#{original_idx}", fill=(100, 100, 100))
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        grid_info = f"{cols}列 x {rows}行"
        if total > max_images:
            grid_info += f"（采样自{total}张）"
        
        return buffer.getvalue(), total, grid_info
    
    def analyze(
        self, 
        project_path: str, 
        product_profile: ProductProfile
    ) -> FlowStructure:
        """
        分析流程结构
        
        Args:
            project_path: 项目路径
            product_profile: Layer 1的产品画像
        
        Returns:
            FlowStructure 流程结构
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_structure(0)
        
        # 创建序列网格
        print("  [Layer 2] Creating sequence grid...")
        grid_data, total_screenshots, grid_info = self.create_sequence_grid(screens_folder)
        
        if not grid_data or total_screenshots == 0:
            return self._default_structure(0)
        
        if not self.client:
            print("  [WARN] API not configured, using default structure")
            return self._default_structure(total_screenshots)
        
        # 构建提示词
        prompt = STRUCTURE_RECOGNITION_PROMPT.format(
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            business_model=product_profile.business_model,
            total_screenshots=total_screenshots,
            grid_info=grid_info
        )
        
        # 调用API分析
        print("  [Layer 2] Analyzing flow structure...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": grid_base64
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
            parsed = self._parse_json(raw_response)
            
            if parsed:
                stages = []
                for stage_data in parsed.get("stages", []):
                    name = stage_data.get("name", "Unknown")
                    expected_types = STAGE_TYPE_MAPPING.get(name, ["Feature"])
                    
                    stage = FlowStage(
                        name=name,
                        start_index=stage_data.get("start_index", 1),
                        end_index=stage_data.get("end_index", 1),
                        description=stage_data.get("description", ""),
                        expected_types=expected_types,
                        screenshot_count=stage_data.get("end_index", 1) - stage_data.get("start_index", 1) + 1
                    )
                    stages.append(stage)
                
                return FlowStructure(
                    total_screenshots=total_screenshots,
                    stages=stages,
                    paywall_position=parsed.get("paywall_position", "none"),
                    onboarding_length=parsed.get("onboarding_length", "medium"),
                    has_signup=parsed.get("has_signup", False),
                    has_social=parsed.get("has_social", False),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_structure(total_screenshots)
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_structure(self, total: int) -> FlowStructure:
        """返回默认的流程结构"""
        if total == 0:
            return FlowStructure(
                total_screenshots=0,
                stages=[],
                paywall_position="none",
                onboarding_length="medium",
                has_signup=False,
                has_social=False,
                confidence=0.0
            )
        
        # 默认划分：10% Welcome, 20% Onboarding, 5% Paywall, 55% Core, 10% Settings
        stages = []
        
        welcome_end = max(1, int(total * 0.1))
        stages.append(FlowStage(
            name="Welcome",
            start_index=1,
            end_index=welcome_end,
            description="欢迎和价值介绍",
            expected_types=["Welcome", "Launch"],
            screenshot_count=welcome_end
        ))
        
        onboarding_end = max(welcome_end + 1, int(total * 0.3))
        stages.append(FlowStage(
            name="Onboarding",
            start_index=welcome_end + 1,
            end_index=onboarding_end,
            description="引导流程",
            expected_types=["Onboarding", "Permission"],
            screenshot_count=onboarding_end - welcome_end
        ))
        
        paywall_end = max(onboarding_end + 1, int(total * 0.35))
        stages.append(FlowStage(
            name="Paywall",
            start_index=onboarding_end + 1,
            end_index=paywall_end,
            description="付费墙",
            expected_types=["Paywall"],
            screenshot_count=paywall_end - onboarding_end
        ))
        
        core_end = max(paywall_end + 1, int(total * 0.9))
        stages.append(FlowStage(
            name="Core Features",
            start_index=paywall_end + 1,
            end_index=core_end,
            description="核心功能",
            expected_types=["Feature", "Content", "Tracking", "Progress", "Home"],
            screenshot_count=core_end - paywall_end
        ))
        
        stages.append(FlowStage(
            name="Settings",
            start_index=core_end + 1,
            end_index=total,
            description="设置和账户",
            expected_types=["Settings", "Profile"],
            screenshot_count=total - core_end
        ))
        
        return FlowStructure(
            total_screenshots=total,
            stages=stages,
            paywall_position="early",
            onboarding_length="medium",
            has_signup=False,
            has_social=False,
            confidence=0.3
        )
    
    def get_stage_for_index(self, flow_structure: FlowStructure, index: int) -> Optional[FlowStage]:
        """根据索引获取所属阶段"""
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                return stage
        return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 2: Structure Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    print(f"  Target: {profile.target_users}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    
    print("\n" + "=" * 60)
    print("Flow Structure")
    print("=" * 60)
    for stage in structure.stages:
        print(f"  [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
    print(f"\n  Paywall Position: {structure.paywall_position}")
    print(f"  Onboarding Length: {structure.onboarding_length}")
    print(f"  Confidence: {structure.confidence:.0%}")


"""
Layer 2: 结构识别模块
基于产品画像，识别截图序列的流程阶段边界
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1
from layer1_product import ProductProfile


@dataclass
class FlowStage:
    """流程阶段"""
    name: str                    # 阶段名称
    start_index: int             # 起始索引（1-based）
    end_index: int               # 结束索引（1-based）
    description: str             # 阶段描述
    expected_types: List[str]    # 该阶段预期的screen_type列表
    screenshot_count: int = 0    # 该阶段的截图数量


@dataclass
class FlowStructure:
    """流程结构"""
    total_screenshots: int
    stages: List[FlowStage]
    paywall_position: str        # "early" / "middle" / "late" / "none"
    onboarding_length: str       # "short" (1-5) / "medium" (6-10) / "long" (11+)
    has_signup: bool
    has_social: bool
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 阶段类型与screen_type映射
# ============================================================

STAGE_TYPE_MAPPING = {
    "Launch": ["Launch"],
    "Welcome": ["Welcome", "Launch"],
    "Onboarding": ["Onboarding", "Permission"],
    "SignUp": ["SignUp"],
    "Paywall": ["Paywall"],
    "Home": ["Home"],
    "Core Features": ["Feature", "Content", "Tracking", "Progress"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social"],
    "Profile": ["Profile"],
    "Settings": ["Settings", "Profile"],
}


# ============================================================
# 提示词
# ============================================================

STRUCTURE_RECOGNITION_PROMPT = """你是一位资深产品经理，正在分析一款App的用户流程结构。

## 产品背景
- App类型: {app_category}
- 细分类别: {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 商业模式: {business_model}

## 任务
我会给你这款App的全部截图网格（按顺序排列，从左到右、从上到下），请识别用户流程的阶段划分。

截图总数: {total_screenshots}
网格排列: {grid_info}

## 阶段类型说明
- Launch: 启动页/闪屏（通常只有1张，显示logo）
- Welcome: 欢迎页/价值介绍（1-3张，展示产品亮点）
- Onboarding: 引导流程（收集用户信息、目标、偏好的问卷页面）
- SignUp: 注册/登录页面
- Paywall: 付费墙（显示价格、订阅选项）
- Home: 首页/主界面（底部导航栏、仪表盘）
- Core Features: 核心功能区（具体功能页面）
- Content: 内容浏览区（文章、视频、音频播放）
- Tracking: 追踪记录区（数据输入、日志）
- Progress: 进度统计区（图表、成就）
- Social: 社交功能区（社区、分享、排行榜）
- Profile: 个人中心
- Settings: 设置页面

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{{
  "stages": [
    {{
      "name": "阶段名称",
      "start_index": 1,
      "end_index": 3,
      "description": "该阶段的简短描述"
    }},
    {{
      "name": "下一阶段",
      "start_index": 4,
      "end_index": 10,
      "description": "描述"
    }}
  ],
  "paywall_position": "early/middle/late/none",
  "onboarding_length": "short/medium/long",
  "has_signup": true/false,
  "has_social": true/false,
  "confidence": 0.9
}}
```

## 注意事项
1. start_index 和 end_index 是1-based的索引（第1张、第2张...）
2. 阶段必须连续，不能有重叠或空隙
3. 最后一个阶段的end_index必须等于总截图数
4. paywall_position: early=前1/3, middle=中间1/3, late=后1/3, none=没有
5. onboarding_length: short=1-5张, medium=6-10张, long=11+张

只输出JSON，不要有任何解释文字。"""


class StructureRecognizer:
    """结构识别器 - Layer 2"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
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
    
    def create_sequence_grid(
        self, 
        image_folder: str,
        max_rows: int = 10,
        thumb_width: int = 150
    ) -> Tuple[Optional[bytes], int, str]:
        """
        创建带序号的截图序列网格
        
        Returns:
            (网格图字节, 总截图数, 网格信息描述)
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None, 0, ""
        
        total = len(images)
        
        # 计算网格大小
        cols = min(10, total)  # 最多10列
        rows = min(max_rows, (total + cols - 1) // cols)
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if total > max_images:
            step = total / max_images
            sampled_indices = [int(i * step) for i in range(max_images)]
            sampled = [(i+1, images[i]) for i in sampled_indices]
        else:
            sampled = [(i+1, f) for i, f in enumerate(images)]
        
        # 估算缩略图高度（假设手机截图比例约为 9:19）
        thumb_height = int(thumb_width * 2.1)
        
        # 创建网格画布
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (240, 240, 240))
        
        # 填充缩略图
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(grid_image)
        
        for idx, (original_idx, filename) in enumerate(sampled):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail((thumb_width - 4, thumb_height - 20), Image.Resampling.LANCZOS)
                
                # 计算位置
                x = col * thumb_width + (thumb_width - img.width) // 2
                y = row * thumb_height + 15 + (thumb_height - 15 - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
                # 绘制序号
                num_x = col * thumb_width + 5
                num_y = row * thumb_height + 2
                draw.text((num_x, num_y), f"#{original_idx}", fill=(100, 100, 100))
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        grid_info = f"{cols}列 x {rows}行"
        if total > max_images:
            grid_info += f"（采样自{total}张）"
        
        return buffer.getvalue(), total, grid_info
    
    def analyze(
        self, 
        project_path: str, 
        product_profile: ProductProfile
    ) -> FlowStructure:
        """
        分析流程结构
        
        Args:
            project_path: 项目路径
            product_profile: Layer 1的产品画像
        
        Returns:
            FlowStructure 流程结构
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_structure(0)
        
        # 创建序列网格
        print("  [Layer 2] Creating sequence grid...")
        grid_data, total_screenshots, grid_info = self.create_sequence_grid(screens_folder)
        
        if not grid_data or total_screenshots == 0:
            return self._default_structure(0)
        
        if not self.client:
            print("  [WARN] API not configured, using default structure")
            return self._default_structure(total_screenshots)
        
        # 构建提示词
        prompt = STRUCTURE_RECOGNITION_PROMPT.format(
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            business_model=product_profile.business_model,
            total_screenshots=total_screenshots,
            grid_info=grid_info
        )
        
        # 调用API分析
        print("  [Layer 2] Analyzing flow structure...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": grid_base64
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
            parsed = self._parse_json(raw_response)
            
            if parsed:
                stages = []
                for stage_data in parsed.get("stages", []):
                    name = stage_data.get("name", "Unknown")
                    expected_types = STAGE_TYPE_MAPPING.get(name, ["Feature"])
                    
                    stage = FlowStage(
                        name=name,
                        start_index=stage_data.get("start_index", 1),
                        end_index=stage_data.get("end_index", 1),
                        description=stage_data.get("description", ""),
                        expected_types=expected_types,
                        screenshot_count=stage_data.get("end_index", 1) - stage_data.get("start_index", 1) + 1
                    )
                    stages.append(stage)
                
                return FlowStructure(
                    total_screenshots=total_screenshots,
                    stages=stages,
                    paywall_position=parsed.get("paywall_position", "none"),
                    onboarding_length=parsed.get("onboarding_length", "medium"),
                    has_signup=parsed.get("has_signup", False),
                    has_social=parsed.get("has_social", False),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_structure(total_screenshots)
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_structure(self, total: int) -> FlowStructure:
        """返回默认的流程结构"""
        if total == 0:
            return FlowStructure(
                total_screenshots=0,
                stages=[],
                paywall_position="none",
                onboarding_length="medium",
                has_signup=False,
                has_social=False,
                confidence=0.0
            )
        
        # 默认划分：10% Welcome, 20% Onboarding, 5% Paywall, 55% Core, 10% Settings
        stages = []
        
        welcome_end = max(1, int(total * 0.1))
        stages.append(FlowStage(
            name="Welcome",
            start_index=1,
            end_index=welcome_end,
            description="欢迎和价值介绍",
            expected_types=["Welcome", "Launch"],
            screenshot_count=welcome_end
        ))
        
        onboarding_end = max(welcome_end + 1, int(total * 0.3))
        stages.append(FlowStage(
            name="Onboarding",
            start_index=welcome_end + 1,
            end_index=onboarding_end,
            description="引导流程",
            expected_types=["Onboarding", "Permission"],
            screenshot_count=onboarding_end - welcome_end
        ))
        
        paywall_end = max(onboarding_end + 1, int(total * 0.35))
        stages.append(FlowStage(
            name="Paywall",
            start_index=onboarding_end + 1,
            end_index=paywall_end,
            description="付费墙",
            expected_types=["Paywall"],
            screenshot_count=paywall_end - onboarding_end
        ))
        
        core_end = max(paywall_end + 1, int(total * 0.9))
        stages.append(FlowStage(
            name="Core Features",
            start_index=paywall_end + 1,
            end_index=core_end,
            description="核心功能",
            expected_types=["Feature", "Content", "Tracking", "Progress", "Home"],
            screenshot_count=core_end - paywall_end
        ))
        
        stages.append(FlowStage(
            name="Settings",
            start_index=core_end + 1,
            end_index=total,
            description="设置和账户",
            expected_types=["Settings", "Profile"],
            screenshot_count=total - core_end
        ))
        
        return FlowStructure(
            total_screenshots=total,
            stages=stages,
            paywall_position="early",
            onboarding_length="medium",
            has_signup=False,
            has_social=False,
            confidence=0.3
        )
    
    def get_stage_for_index(self, flow_structure: FlowStructure, index: int) -> Optional[FlowStage]:
        """根据索引获取所属阶段"""
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                return stage
        return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 2: Structure Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    print(f"  Target: {profile.target_users}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    
    print("\n" + "=" * 60)
    print("Flow Structure")
    print("=" * 60)
    for stage in structure.stages:
        print(f"  [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
    print(f"\n  Paywall Position: {structure.paywall_position}")
    print(f"  Onboarding Length: {structure.onboarding_length}")
    print(f"  Confidence: {structure.confidence:.0%}")


"""
Layer 2: 结构识别模块
基于产品画像，识别截图序列的流程阶段边界
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1
from layer1_product import ProductProfile


@dataclass
class FlowStage:
    """流程阶段"""
    name: str                    # 阶段名称
    start_index: int             # 起始索引（1-based）
    end_index: int               # 结束索引（1-based）
    description: str             # 阶段描述
    expected_types: List[str]    # 该阶段预期的screen_type列表
    screenshot_count: int = 0    # 该阶段的截图数量


@dataclass
class FlowStructure:
    """流程结构"""
    total_screenshots: int
    stages: List[FlowStage]
    paywall_position: str        # "early" / "middle" / "late" / "none"
    onboarding_length: str       # "short" (1-5) / "medium" (6-10) / "long" (11+)
    has_signup: bool
    has_social: bool
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 阶段类型与screen_type映射
# ============================================================

STAGE_TYPE_MAPPING = {
    "Launch": ["Launch"],
    "Welcome": ["Welcome", "Launch"],
    "Onboarding": ["Onboarding", "Permission"],
    "SignUp": ["SignUp"],
    "Paywall": ["Paywall"],
    "Home": ["Home"],
    "Core Features": ["Feature", "Content", "Tracking", "Progress"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social"],
    "Profile": ["Profile"],
    "Settings": ["Settings", "Profile"],
}


# ============================================================
# 提示词
# ============================================================

STRUCTURE_RECOGNITION_PROMPT = """你是一位资深产品经理，正在分析一款App的用户流程结构。

## 产品背景
- App类型: {app_category}
- 细分类别: {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 商业模式: {business_model}

## 任务
我会给你这款App的全部截图网格（按顺序排列，从左到右、从上到下），请识别用户流程的阶段划分。

截图总数: {total_screenshots}
网格排列: {grid_info}

## 阶段类型说明
- Launch: 启动页/闪屏（通常只有1张，显示logo）
- Welcome: 欢迎页/价值介绍（1-3张，展示产品亮点）
- Onboarding: 引导流程（收集用户信息、目标、偏好的问卷页面）
- SignUp: 注册/登录页面
- Paywall: 付费墙（显示价格、订阅选项）
- Home: 首页/主界面（底部导航栏、仪表盘）
- Core Features: 核心功能区（具体功能页面）
- Content: 内容浏览区（文章、视频、音频播放）
- Tracking: 追踪记录区（数据输入、日志）
- Progress: 进度统计区（图表、成就）
- Social: 社交功能区（社区、分享、排行榜）
- Profile: 个人中心
- Settings: 设置页面

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{{
  "stages": [
    {{
      "name": "阶段名称",
      "start_index": 1,
      "end_index": 3,
      "description": "该阶段的简短描述"
    }},
    {{
      "name": "下一阶段",
      "start_index": 4,
      "end_index": 10,
      "description": "描述"
    }}
  ],
  "paywall_position": "early/middle/late/none",
  "onboarding_length": "short/medium/long",
  "has_signup": true/false,
  "has_social": true/false,
  "confidence": 0.9
}}
```

## 注意事项
1. start_index 和 end_index 是1-based的索引（第1张、第2张...）
2. 阶段必须连续，不能有重叠或空隙
3. 最后一个阶段的end_index必须等于总截图数
4. paywall_position: early=前1/3, middle=中间1/3, late=后1/3, none=没有
5. onboarding_length: short=1-5张, medium=6-10张, long=11+张

只输出JSON，不要有任何解释文字。"""


class StructureRecognizer:
    """结构识别器 - Layer 2"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
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
    
    def create_sequence_grid(
        self, 
        image_folder: str,
        max_rows: int = 10,
        thumb_width: int = 150
    ) -> Tuple[Optional[bytes], int, str]:
        """
        创建带序号的截图序列网格
        
        Returns:
            (网格图字节, 总截图数, 网格信息描述)
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None, 0, ""
        
        total = len(images)
        
        # 计算网格大小
        cols = min(10, total)  # 最多10列
        rows = min(max_rows, (total + cols - 1) // cols)
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if total > max_images:
            step = total / max_images
            sampled_indices = [int(i * step) for i in range(max_images)]
            sampled = [(i+1, images[i]) for i in sampled_indices]
        else:
            sampled = [(i+1, f) for i, f in enumerate(images)]
        
        # 估算缩略图高度（假设手机截图比例约为 9:19）
        thumb_height = int(thumb_width * 2.1)
        
        # 创建网格画布
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (240, 240, 240))
        
        # 填充缩略图
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(grid_image)
        
        for idx, (original_idx, filename) in enumerate(sampled):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail((thumb_width - 4, thumb_height - 20), Image.Resampling.LANCZOS)
                
                # 计算位置
                x = col * thumb_width + (thumb_width - img.width) // 2
                y = row * thumb_height + 15 + (thumb_height - 15 - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
                # 绘制序号
                num_x = col * thumb_width + 5
                num_y = row * thumb_height + 2
                draw.text((num_x, num_y), f"#{original_idx}", fill=(100, 100, 100))
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        grid_info = f"{cols}列 x {rows}行"
        if total > max_images:
            grid_info += f"（采样自{total}张）"
        
        return buffer.getvalue(), total, grid_info
    
    def analyze(
        self, 
        project_path: str, 
        product_profile: ProductProfile
    ) -> FlowStructure:
        """
        分析流程结构
        
        Args:
            project_path: 项目路径
            product_profile: Layer 1的产品画像
        
        Returns:
            FlowStructure 流程结构
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_structure(0)
        
        # 创建序列网格
        print("  [Layer 2] Creating sequence grid...")
        grid_data, total_screenshots, grid_info = self.create_sequence_grid(screens_folder)
        
        if not grid_data or total_screenshots == 0:
            return self._default_structure(0)
        
        if not self.client:
            print("  [WARN] API not configured, using default structure")
            return self._default_structure(total_screenshots)
        
        # 构建提示词
        prompt = STRUCTURE_RECOGNITION_PROMPT.format(
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            business_model=product_profile.business_model,
            total_screenshots=total_screenshots,
            grid_info=grid_info
        )
        
        # 调用API分析
        print("  [Layer 2] Analyzing flow structure...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": grid_base64
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
            parsed = self._parse_json(raw_response)
            
            if parsed:
                stages = []
                for stage_data in parsed.get("stages", []):
                    name = stage_data.get("name", "Unknown")
                    expected_types = STAGE_TYPE_MAPPING.get(name, ["Feature"])
                    
                    stage = FlowStage(
                        name=name,
                        start_index=stage_data.get("start_index", 1),
                        end_index=stage_data.get("end_index", 1),
                        description=stage_data.get("description", ""),
                        expected_types=expected_types,
                        screenshot_count=stage_data.get("end_index", 1) - stage_data.get("start_index", 1) + 1
                    )
                    stages.append(stage)
                
                return FlowStructure(
                    total_screenshots=total_screenshots,
                    stages=stages,
                    paywall_position=parsed.get("paywall_position", "none"),
                    onboarding_length=parsed.get("onboarding_length", "medium"),
                    has_signup=parsed.get("has_signup", False),
                    has_social=parsed.get("has_social", False),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_structure(total_screenshots)
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_structure(self, total: int) -> FlowStructure:
        """返回默认的流程结构"""
        if total == 0:
            return FlowStructure(
                total_screenshots=0,
                stages=[],
                paywall_position="none",
                onboarding_length="medium",
                has_signup=False,
                has_social=False,
                confidence=0.0
            )
        
        # 默认划分：10% Welcome, 20% Onboarding, 5% Paywall, 55% Core, 10% Settings
        stages = []
        
        welcome_end = max(1, int(total * 0.1))
        stages.append(FlowStage(
            name="Welcome",
            start_index=1,
            end_index=welcome_end,
            description="欢迎和价值介绍",
            expected_types=["Welcome", "Launch"],
            screenshot_count=welcome_end
        ))
        
        onboarding_end = max(welcome_end + 1, int(total * 0.3))
        stages.append(FlowStage(
            name="Onboarding",
            start_index=welcome_end + 1,
            end_index=onboarding_end,
            description="引导流程",
            expected_types=["Onboarding", "Permission"],
            screenshot_count=onboarding_end - welcome_end
        ))
        
        paywall_end = max(onboarding_end + 1, int(total * 0.35))
        stages.append(FlowStage(
            name="Paywall",
            start_index=onboarding_end + 1,
            end_index=paywall_end,
            description="付费墙",
            expected_types=["Paywall"],
            screenshot_count=paywall_end - onboarding_end
        ))
        
        core_end = max(paywall_end + 1, int(total * 0.9))
        stages.append(FlowStage(
            name="Core Features",
            start_index=paywall_end + 1,
            end_index=core_end,
            description="核心功能",
            expected_types=["Feature", "Content", "Tracking", "Progress", "Home"],
            screenshot_count=core_end - paywall_end
        ))
        
        stages.append(FlowStage(
            name="Settings",
            start_index=core_end + 1,
            end_index=total,
            description="设置和账户",
            expected_types=["Settings", "Profile"],
            screenshot_count=total - core_end
        ))
        
        return FlowStructure(
            total_screenshots=total,
            stages=stages,
            paywall_position="early",
            onboarding_length="medium",
            has_signup=False,
            has_social=False,
            confidence=0.3
        )
    
    def get_stage_for_index(self, flow_structure: FlowStructure, index: int) -> Optional[FlowStage]:
        """根据索引获取所属阶段"""
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                return stage
        return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 2: Structure Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    print(f"  Target: {profile.target_users}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    
    print("\n" + "=" * 60)
    print("Flow Structure")
    print("=" * 60)
    for stage in structure.stages:
        print(f"  [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
    print(f"\n  Paywall Position: {structure.paywall_position}")
    print(f"  Onboarding Length: {structure.onboarding_length}")
    print(f"  Confidence: {structure.confidence:.0%}")



"""
Layer 2: 结构识别模块
基于产品画像，识别截图序列的流程阶段边界
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1
from layer1_product import ProductProfile


@dataclass
class FlowStage:
    """流程阶段"""
    name: str                    # 阶段名称
    start_index: int             # 起始索引（1-based）
    end_index: int               # 结束索引（1-based）
    description: str             # 阶段描述
    expected_types: List[str]    # 该阶段预期的screen_type列表
    screenshot_count: int = 0    # 该阶段的截图数量


@dataclass
class FlowStructure:
    """流程结构"""
    total_screenshots: int
    stages: List[FlowStage]
    paywall_position: str        # "early" / "middle" / "late" / "none"
    onboarding_length: str       # "short" (1-5) / "medium" (6-10) / "long" (11+)
    has_signup: bool
    has_social: bool
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 阶段类型与screen_type映射
# ============================================================

STAGE_TYPE_MAPPING = {
    "Launch": ["Launch"],
    "Welcome": ["Welcome", "Launch"],
    "Onboarding": ["Onboarding", "Permission"],
    "SignUp": ["SignUp"],
    "Paywall": ["Paywall"],
    "Home": ["Home"],
    "Core Features": ["Feature", "Content", "Tracking", "Progress"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social"],
    "Profile": ["Profile"],
    "Settings": ["Settings", "Profile"],
}


# ============================================================
# 提示词
# ============================================================

STRUCTURE_RECOGNITION_PROMPT = """你是一位资深产品经理，正在分析一款App的用户流程结构。

## 产品背景
- App类型: {app_category}
- 细分类别: {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 商业模式: {business_model}

## 任务
我会给你这款App的全部截图网格（按顺序排列，从左到右、从上到下），请识别用户流程的阶段划分。

截图总数: {total_screenshots}
网格排列: {grid_info}

## 阶段类型说明
- Launch: 启动页/闪屏（通常只有1张，显示logo）
- Welcome: 欢迎页/价值介绍（1-3张，展示产品亮点）
- Onboarding: 引导流程（收集用户信息、目标、偏好的问卷页面）
- SignUp: 注册/登录页面
- Paywall: 付费墙（显示价格、订阅选项）
- Home: 首页/主界面（底部导航栏、仪表盘）
- Core Features: 核心功能区（具体功能页面）
- Content: 内容浏览区（文章、视频、音频播放）
- Tracking: 追踪记录区（数据输入、日志）
- Progress: 进度统计区（图表、成就）
- Social: 社交功能区（社区、分享、排行榜）
- Profile: 个人中心
- Settings: 设置页面

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{{
  "stages": [
    {{
      "name": "阶段名称",
      "start_index": 1,
      "end_index": 3,
      "description": "该阶段的简短描述"
    }},
    {{
      "name": "下一阶段",
      "start_index": 4,
      "end_index": 10,
      "description": "描述"
    }}
  ],
  "paywall_position": "early/middle/late/none",
  "onboarding_length": "short/medium/long",
  "has_signup": true/false,
  "has_social": true/false,
  "confidence": 0.9
}}
```

## 注意事项
1. start_index 和 end_index 是1-based的索引（第1张、第2张...）
2. 阶段必须连续，不能有重叠或空隙
3. 最后一个阶段的end_index必须等于总截图数
4. paywall_position: early=前1/3, middle=中间1/3, late=后1/3, none=没有
5. onboarding_length: short=1-5张, medium=6-10张, long=11+张

只输出JSON，不要有任何解释文字。"""


class StructureRecognizer:
    """结构识别器 - Layer 2"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
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
    
    def create_sequence_grid(
        self, 
        image_folder: str,
        max_rows: int = 10,
        thumb_width: int = 150
    ) -> Tuple[Optional[bytes], int, str]:
        """
        创建带序号的截图序列网格
        
        Returns:
            (网格图字节, 总截图数, 网格信息描述)
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None, 0, ""
        
        total = len(images)
        
        # 计算网格大小
        cols = min(10, total)  # 最多10列
        rows = min(max_rows, (total + cols - 1) // cols)
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if total > max_images:
            step = total / max_images
            sampled_indices = [int(i * step) for i in range(max_images)]
            sampled = [(i+1, images[i]) for i in sampled_indices]
        else:
            sampled = [(i+1, f) for i, f in enumerate(images)]
        
        # 估算缩略图高度（假设手机截图比例约为 9:19）
        thumb_height = int(thumb_width * 2.1)
        
        # 创建网格画布
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (240, 240, 240))
        
        # 填充缩略图
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(grid_image)
        
        for idx, (original_idx, filename) in enumerate(sampled):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail((thumb_width - 4, thumb_height - 20), Image.Resampling.LANCZOS)
                
                # 计算位置
                x = col * thumb_width + (thumb_width - img.width) // 2
                y = row * thumb_height + 15 + (thumb_height - 15 - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
                # 绘制序号
                num_x = col * thumb_width + 5
                num_y = row * thumb_height + 2
                draw.text((num_x, num_y), f"#{original_idx}", fill=(100, 100, 100))
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        grid_info = f"{cols}列 x {rows}行"
        if total > max_images:
            grid_info += f"（采样自{total}张）"
        
        return buffer.getvalue(), total, grid_info
    
    def analyze(
        self, 
        project_path: str, 
        product_profile: ProductProfile
    ) -> FlowStructure:
        """
        分析流程结构
        
        Args:
            project_path: 项目路径
            product_profile: Layer 1的产品画像
        
        Returns:
            FlowStructure 流程结构
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_structure(0)
        
        # 创建序列网格
        print("  [Layer 2] Creating sequence grid...")
        grid_data, total_screenshots, grid_info = self.create_sequence_grid(screens_folder)
        
        if not grid_data or total_screenshots == 0:
            return self._default_structure(0)
        
        if not self.client:
            print("  [WARN] API not configured, using default structure")
            return self._default_structure(total_screenshots)
        
        # 构建提示词
        prompt = STRUCTURE_RECOGNITION_PROMPT.format(
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            business_model=product_profile.business_model,
            total_screenshots=total_screenshots,
            grid_info=grid_info
        )
        
        # 调用API分析
        print("  [Layer 2] Analyzing flow structure...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": grid_base64
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
            parsed = self._parse_json(raw_response)
            
            if parsed:
                stages = []
                for stage_data in parsed.get("stages", []):
                    name = stage_data.get("name", "Unknown")
                    expected_types = STAGE_TYPE_MAPPING.get(name, ["Feature"])
                    
                    stage = FlowStage(
                        name=name,
                        start_index=stage_data.get("start_index", 1),
                        end_index=stage_data.get("end_index", 1),
                        description=stage_data.get("description", ""),
                        expected_types=expected_types,
                        screenshot_count=stage_data.get("end_index", 1) - stage_data.get("start_index", 1) + 1
                    )
                    stages.append(stage)
                
                return FlowStructure(
                    total_screenshots=total_screenshots,
                    stages=stages,
                    paywall_position=parsed.get("paywall_position", "none"),
                    onboarding_length=parsed.get("onboarding_length", "medium"),
                    has_signup=parsed.get("has_signup", False),
                    has_social=parsed.get("has_social", False),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_structure(total_screenshots)
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_structure(self, total: int) -> FlowStructure:
        """返回默认的流程结构"""
        if total == 0:
            return FlowStructure(
                total_screenshots=0,
                stages=[],
                paywall_position="none",
                onboarding_length="medium",
                has_signup=False,
                has_social=False,
                confidence=0.0
            )
        
        # 默认划分：10% Welcome, 20% Onboarding, 5% Paywall, 55% Core, 10% Settings
        stages = []
        
        welcome_end = max(1, int(total * 0.1))
        stages.append(FlowStage(
            name="Welcome",
            start_index=1,
            end_index=welcome_end,
            description="欢迎和价值介绍",
            expected_types=["Welcome", "Launch"],
            screenshot_count=welcome_end
        ))
        
        onboarding_end = max(welcome_end + 1, int(total * 0.3))
        stages.append(FlowStage(
            name="Onboarding",
            start_index=welcome_end + 1,
            end_index=onboarding_end,
            description="引导流程",
            expected_types=["Onboarding", "Permission"],
            screenshot_count=onboarding_end - welcome_end
        ))
        
        paywall_end = max(onboarding_end + 1, int(total * 0.35))
        stages.append(FlowStage(
            name="Paywall",
            start_index=onboarding_end + 1,
            end_index=paywall_end,
            description="付费墙",
            expected_types=["Paywall"],
            screenshot_count=paywall_end - onboarding_end
        ))
        
        core_end = max(paywall_end + 1, int(total * 0.9))
        stages.append(FlowStage(
            name="Core Features",
            start_index=paywall_end + 1,
            end_index=core_end,
            description="核心功能",
            expected_types=["Feature", "Content", "Tracking", "Progress", "Home"],
            screenshot_count=core_end - paywall_end
        ))
        
        stages.append(FlowStage(
            name="Settings",
            start_index=core_end + 1,
            end_index=total,
            description="设置和账户",
            expected_types=["Settings", "Profile"],
            screenshot_count=total - core_end
        ))
        
        return FlowStructure(
            total_screenshots=total,
            stages=stages,
            paywall_position="early",
            onboarding_length="medium",
            has_signup=False,
            has_social=False,
            confidence=0.3
        )
    
    def get_stage_for_index(self, flow_structure: FlowStructure, index: int) -> Optional[FlowStage]:
        """根据索引获取所属阶段"""
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                return stage
        return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 2: Structure Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    print(f"  Target: {profile.target_users}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    
    print("\n" + "=" * 60)
    print("Flow Structure")
    print("=" * 60)
    for stage in structure.stages:
        print(f"  [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
    print(f"\n  Paywall Position: {structure.paywall_position}")
    print(f"  Onboarding Length: {structure.onboarding_length}")
    print(f"  Confidence: {structure.confidence:.0%}")


"""
Layer 2: 结构识别模块
基于产品画像，识别截图序列的流程阶段边界
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1
from layer1_product import ProductProfile


@dataclass
class FlowStage:
    """流程阶段"""
    name: str                    # 阶段名称
    start_index: int             # 起始索引（1-based）
    end_index: int               # 结束索引（1-based）
    description: str             # 阶段描述
    expected_types: List[str]    # 该阶段预期的screen_type列表
    screenshot_count: int = 0    # 该阶段的截图数量


@dataclass
class FlowStructure:
    """流程结构"""
    total_screenshots: int
    stages: List[FlowStage]
    paywall_position: str        # "early" / "middle" / "late" / "none"
    onboarding_length: str       # "short" (1-5) / "medium" (6-10) / "long" (11+)
    has_signup: bool
    has_social: bool
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 阶段类型与screen_type映射
# ============================================================

STAGE_TYPE_MAPPING = {
    "Launch": ["Launch"],
    "Welcome": ["Welcome", "Launch"],
    "Onboarding": ["Onboarding", "Permission"],
    "SignUp": ["SignUp"],
    "Paywall": ["Paywall"],
    "Home": ["Home"],
    "Core Features": ["Feature", "Content", "Tracking", "Progress"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social"],
    "Profile": ["Profile"],
    "Settings": ["Settings", "Profile"],
}


# ============================================================
# 提示词
# ============================================================

STRUCTURE_RECOGNITION_PROMPT = """你是一位资深产品经理，正在分析一款App的用户流程结构。

## 产品背景
- App类型: {app_category}
- 细分类别: {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 商业模式: {business_model}

## 任务
我会给你这款App的全部截图网格（按顺序排列，从左到右、从上到下），请识别用户流程的阶段划分。

截图总数: {total_screenshots}
网格排列: {grid_info}

## 阶段类型说明
- Launch: 启动页/闪屏（通常只有1张，显示logo）
- Welcome: 欢迎页/价值介绍（1-3张，展示产品亮点）
- Onboarding: 引导流程（收集用户信息、目标、偏好的问卷页面）
- SignUp: 注册/登录页面
- Paywall: 付费墙（显示价格、订阅选项）
- Home: 首页/主界面（底部导航栏、仪表盘）
- Core Features: 核心功能区（具体功能页面）
- Content: 内容浏览区（文章、视频、音频播放）
- Tracking: 追踪记录区（数据输入、日志）
- Progress: 进度统计区（图表、成就）
- Social: 社交功能区（社区、分享、排行榜）
- Profile: 个人中心
- Settings: 设置页面

## 输出要求
请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{{
  "stages": [
    {{
      "name": "阶段名称",
      "start_index": 1,
      "end_index": 3,
      "description": "该阶段的简短描述"
    }},
    {{
      "name": "下一阶段",
      "start_index": 4,
      "end_index": 10,
      "description": "描述"
    }}
  ],
  "paywall_position": "early/middle/late/none",
  "onboarding_length": "short/medium/long",
  "has_signup": true/false,
  "has_social": true/false,
  "confidence": 0.9
}}
```

## 注意事项
1. start_index 和 end_index 是1-based的索引（第1张、第2张...）
2. 阶段必须连续，不能有重叠或空隙
3. 最后一个阶段的end_index必须等于总截图数
4. paywall_position: early=前1/3, middle=中间1/3, late=后1/3, none=没有
5. onboarding_length: short=1-5张, medium=6-10张, long=11+张

只输出JSON，不要有任何解释文字。"""


class StructureRecognizer:
    """结构识别器 - Layer 2"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.client = None
        
        if self.api_key and ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def _load_api_key(self) -> Optional[str]:
        """从配置文件或环境变量加载API Key"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            return api_key
        
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
    
    def create_sequence_grid(
        self, 
        image_folder: str,
        max_rows: int = 10,
        thumb_width: int = 150
    ) -> Tuple[Optional[bytes], int, str]:
        """
        创建带序号的截图序列网格
        
        Returns:
            (网格图字节, 总截图数, 网格信息描述)
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None, 0, ""
        
        total = len(images)
        
        # 计算网格大小
        cols = min(10, total)  # 最多10列
        rows = min(max_rows, (total + cols - 1) // cols)
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if total > max_images:
            step = total / max_images
            sampled_indices = [int(i * step) for i in range(max_images)]
            sampled = [(i+1, images[i]) for i in sampled_indices]
        else:
            sampled = [(i+1, f) for i, f in enumerate(images)]
        
        # 估算缩略图高度（假设手机截图比例约为 9:19）
        thumb_height = int(thumb_width * 2.1)
        
        # 创建网格画布
        grid_width = cols * thumb_width
        grid_height = rows * thumb_height
        grid_image = Image.new('RGB', (grid_width, grid_height), (240, 240, 240))
        
        # 填充缩略图
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(grid_image)
        
        for idx, (original_idx, filename) in enumerate(sampled):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail((thumb_width - 4, thumb_height - 20), Image.Resampling.LANCZOS)
                
                # 计算位置
                x = col * thumb_width + (thumb_width - img.width) // 2
                y = row * thumb_height + 15 + (thumb_height - 15 - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
                # 绘制序号
                num_x = col * thumb_width + 5
                num_y = row * thumb_height + 2
                draw.text((num_x, num_y), f"#{original_idx}", fill=(100, 100, 100))
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        grid_info = f"{cols}列 x {rows}行"
        if total > max_images:
            grid_info += f"（采样自{total}张）"
        
        return buffer.getvalue(), total, grid_info
    
    def analyze(
        self, 
        project_path: str, 
        product_profile: ProductProfile
    ) -> FlowStructure:
        """
        分析流程结构
        
        Args:
            project_path: 项目路径
            product_profile: Layer 1的产品画像
        
        Returns:
            FlowStructure 流程结构
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_structure(0)
        
        # 创建序列网格
        print("  [Layer 2] Creating sequence grid...")
        grid_data, total_screenshots, grid_info = self.create_sequence_grid(screens_folder)
        
        if not grid_data or total_screenshots == 0:
            return self._default_structure(0)
        
        if not self.client:
            print("  [WARN] API not configured, using default structure")
            return self._default_structure(total_screenshots)
        
        # 构建提示词
        prompt = STRUCTURE_RECOGNITION_PROMPT.format(
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            business_model=product_profile.business_model,
            total_screenshots=total_screenshots,
            grid_info=grid_info
        )
        
        # 调用API分析
        print("  [Layer 2] Analyzing flow structure...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": grid_base64
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
            parsed = self._parse_json(raw_response)
            
            if parsed:
                stages = []
                for stage_data in parsed.get("stages", []):
                    name = stage_data.get("name", "Unknown")
                    expected_types = STAGE_TYPE_MAPPING.get(name, ["Feature"])
                    
                    stage = FlowStage(
                        name=name,
                        start_index=stage_data.get("start_index", 1),
                        end_index=stage_data.get("end_index", 1),
                        description=stage_data.get("description", ""),
                        expected_types=expected_types,
                        screenshot_count=stage_data.get("end_index", 1) - stage_data.get("start_index", 1) + 1
                    )
                    stages.append(stage)
                
                return FlowStructure(
                    total_screenshots=total_screenshots,
                    stages=stages,
                    paywall_position=parsed.get("paywall_position", "none"),
                    onboarding_length=parsed.get("onboarding_length", "medium"),
                    has_signup=parsed.get("has_signup", False),
                    has_social=parsed.get("has_social", False),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_structure(total_screenshots)
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        try:
            return json.loads(text)
        except:
            pass
        
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_structure(self, total: int) -> FlowStructure:
        """返回默认的流程结构"""
        if total == 0:
            return FlowStructure(
                total_screenshots=0,
                stages=[],
                paywall_position="none",
                onboarding_length="medium",
                has_signup=False,
                has_social=False,
                confidence=0.0
            )
        
        # 默认划分：10% Welcome, 20% Onboarding, 5% Paywall, 55% Core, 10% Settings
        stages = []
        
        welcome_end = max(1, int(total * 0.1))
        stages.append(FlowStage(
            name="Welcome",
            start_index=1,
            end_index=welcome_end,
            description="欢迎和价值介绍",
            expected_types=["Welcome", "Launch"],
            screenshot_count=welcome_end
        ))
        
        onboarding_end = max(welcome_end + 1, int(total * 0.3))
        stages.append(FlowStage(
            name="Onboarding",
            start_index=welcome_end + 1,
            end_index=onboarding_end,
            description="引导流程",
            expected_types=["Onboarding", "Permission"],
            screenshot_count=onboarding_end - welcome_end
        ))
        
        paywall_end = max(onboarding_end + 1, int(total * 0.35))
        stages.append(FlowStage(
            name="Paywall",
            start_index=onboarding_end + 1,
            end_index=paywall_end,
            description="付费墙",
            expected_types=["Paywall"],
            screenshot_count=paywall_end - onboarding_end
        ))
        
        core_end = max(paywall_end + 1, int(total * 0.9))
        stages.append(FlowStage(
            name="Core Features",
            start_index=paywall_end + 1,
            end_index=core_end,
            description="核心功能",
            expected_types=["Feature", "Content", "Tracking", "Progress", "Home"],
            screenshot_count=core_end - paywall_end
        ))
        
        stages.append(FlowStage(
            name="Settings",
            start_index=core_end + 1,
            end_index=total,
            description="设置和账户",
            expected_types=["Settings", "Profile"],
            screenshot_count=total - core_end
        ))
        
        return FlowStructure(
            total_screenshots=total,
            stages=stages,
            paywall_position="early",
            onboarding_length="medium",
            has_signup=False,
            has_social=False,
            confidence=0.3
        )
    
    def get_stage_for_index(self, flow_structure: FlowStructure, index: int) -> Optional[FlowStage]:
        """根据索引获取所属阶段"""
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                return stage
        return None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 2: Structure Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    print(f"  Target: {profile.target_users}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    
    print("\n" + "=" * 60)
    print("Flow Structure")
    print("=" * 60)
    for stage in structure.stages:
        print(f"  [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
    print(f"\n  Paywall Position: {structure.paywall_position}")
    print(f"  Onboarding Length: {structure.onboarding_length}")
    print(f"  Confidence: {structure.confidence:.0%}")










































