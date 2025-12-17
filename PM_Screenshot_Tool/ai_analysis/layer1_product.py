# -*- coding: utf-8 -*-
"""
Layer 1: 产品认知模块
通过分析缩略图网格，快速理解产品类型、目标用户和整体结构
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProductProfile:
    """产品画像"""
    app_name: str
    app_category: str                    # 健康/冥想/健身/饮食等
    sub_category: str                    # 更细分的类别
    target_users: str                    # 目标用户描述
    core_value: str                      # 核心价值主张
    business_model: str                  # 商业模式
    estimated_stages: List[str]          # 预估的流程阶段
    visual_style: str                    # 视觉风格（极简/丰富/游戏化等）
    primary_color: str                   # 主色调
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 提示词
# ============================================================

PRODUCT_RECOGNITION_PROMPT = """你是一位资深产品经理，正在快速分析一款移动App的整体情况。

我会给你一张由多张App截图组成的网格图（按顺序排列），请通过这些截图快速判断：

## 需要输出的信息

1. **app_category**: App大类（选择一个）
   - 健康健身 (Health & Fitness)
   - 冥想正念 (Meditation)
   - 饮食营养 (Nutrition & Diet)
   - 运动追踪 (Sports Tracking)
   - 睡眠改善 (Sleep)
   - 心理健康 (Mental Health)
   - 女性健康 (Women's Health)
   - 效率工具 (Productivity)
   - 教育学习 (Education)
   - 社交通讯 (Social)
   - 娱乐 (Entertainment)
   - 金融 (Finance)
   - 其他 (Other)

2. **sub_category**: 更细分的类别（自由填写，如"卡路里追踪"、"跑步训练"等）

3. **target_users**: 目标用户画像（20-40字描述）

4. **core_value**: 核心价值主张（15-30字，这个App解决什么问题）

5. **business_model**: 商业模式
   - 订阅制 (Subscription)
   - 一次性付费 (One-time Purchase)
   - 免费+广告 (Free with Ads)
   - 免费增值 (Freemium)
   - 混合模式 (Hybrid)

6. **estimated_stages**: 预估的用户流程阶段（数组，按顺序）
   例如: ["Welcome", "Onboarding", "Paywall", "Core Features", "Settings"]
   
   常见阶段：
   - Launch: 启动/闪屏
   - Welcome: 欢迎/价值介绍
   - Onboarding: 引导/信息收集
   - SignUp: 注册登录
   - Paywall: 付费墙
   - Home: 首页
   - Core Features: 核心功能
   - Content: 内容浏览
   - Tracking: 追踪记录
   - Progress: 进度统计
   - Social: 社交功能
   - Profile: 个人中心
   - Settings: 设置

7. **visual_style**: 视觉风格
   - 极简清新 (Minimalist)
   - 丰富多彩 (Colorful)
   - 专业商务 (Professional)
   - 游戏化 (Gamified)
   - 自然舒适 (Natural)
   - 科技感 (Tech)
   - 温暖治愈 (Warm)

8. **primary_color**: 主色调（如 "蓝色"、"绿色"、"紫色渐变" 等）

## 输出格式

请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "app_category": "类别",
  "sub_category": "细分类别",
  "target_users": "目标用户描述",
  "core_value": "核心价值主张",
  "business_model": "商业模式",
  "estimated_stages": ["阶段1", "阶段2", "阶段3"],
  "visual_style": "视觉风格",
  "primary_color": "主色调",
  "confidence": 0.9
}
```

## 分析要点

1. 通过第一张图判断是否有品牌Logo/启动页
2. 观察是否有引导问卷、目标选择等Onboarding元素
3. 寻找价格、订阅按钮等Paywall标志
4. 识别核心功能界面的特征（图表、列表、播放器等）
5. 注意整体色调和设计风格

只输出JSON，不要有任何解释文字。"""


class ProductRecognizer:
    """产品识别器 - Layer 1"""
    
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
    
    def create_thumbnail_grid(
        self, 
        image_folder: str, 
        grid_size: Tuple[int, int] = (5, 5),
        thumb_size: Tuple[int, int] = (200, 400)
    ) -> Optional[bytes]:
        """
        创建缩略图网格
        
        Args:
            image_folder: 截图文件夹路径
            grid_size: 网格大小 (列, 行)
            thumb_size: 每个缩略图大小
        
        Returns:
            网格图的PNG字节数据
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None
        
        cols, rows = grid_size
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if len(images) > max_images:
            step = len(images) / max_images
            sampled = [images[int(i * step)] for i in range(max_images)]
            images = sampled
        
        # 创建网格画布
        grid_width = cols * thumb_size[0]
        grid_height = rows * thumb_size[1]
        grid_image = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # 填充缩略图
        for idx, filename in enumerate(images):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 居中放置
                x = col * thumb_size[0] + (thumb_size[0] - img.width) // 2
                y = row * thumb_size[1] + (thumb_size[1] - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        return buffer.getvalue()
    
    def analyze(self, project_path: str, app_name: str = "") -> ProductProfile:
        """
        分析产品，生成产品画像
        
        Args:
            project_path: 项目路径
            app_name: App名称（可选）
        
        Returns:
            ProductProfile 产品画像
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 创建缩略图网格
        print("  [Layer 1] Creating thumbnail grid...")
        grid_data = self.create_thumbnail_grid(screens_folder)
        
        if not grid_data:
            return self._default_profile(app_name or os.path.basename(project_path))
        
        if not self.client:
            print("  [WARN] API not configured, using default profile")
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 调用API分析
        print("  [Layer 1] Analyzing product profile...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
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
                                "media_type": "image/png",
                                "data": grid_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": PRODUCT_RECOGNITION_PROMPT
                        }
                    ]
                }]
            )
            
            raw_response = response.content[0].text
            parsed = self._parse_json(raw_response)
            
            if parsed:
                return ProductProfile(
                    app_name=app_name or os.path.basename(project_path).replace("_Analysis", ""),
                    app_category=parsed.get("app_category", "Other"),
                    sub_category=parsed.get("sub_category", ""),
                    target_users=parsed.get("target_users", ""),
                    core_value=parsed.get("core_value", ""),
                    business_model=parsed.get("business_model", "Subscription"),
                    estimated_stages=parsed.get("estimated_stages", []),
                    visual_style=parsed.get("visual_style", ""),
                    primary_color=parsed.get("primary_color", ""),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_profile(app_name or os.path.basename(project_path))
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        # 直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 提取 { ... }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_profile(self, app_name: str) -> ProductProfile:
        """返回默认的产品画像"""
        return ProductProfile(
            app_name=app_name,
            app_category="Other",
            sub_category="",
            target_users="一般用户",
            core_value="",
            business_model="Subscription",
            estimated_stages=["Welcome", "Onboarding", "Core Features"],
            visual_style="",
            primary_color="",
            confidence=0.3
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1: Product Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # 分析
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    
    print("\n" + "=" * 60)
    print("Product Profile")
    print("=" * 60)
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))


"""
Layer 1: 产品认知模块
通过分析缩略图网格，快速理解产品类型、目标用户和整体结构
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProductProfile:
    """产品画像"""
    app_name: str
    app_category: str                    # 健康/冥想/健身/饮食等
    sub_category: str                    # 更细分的类别
    target_users: str                    # 目标用户描述
    core_value: str                      # 核心价值主张
    business_model: str                  # 商业模式
    estimated_stages: List[str]          # 预估的流程阶段
    visual_style: str                    # 视觉风格（极简/丰富/游戏化等）
    primary_color: str                   # 主色调
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 提示词
# ============================================================

PRODUCT_RECOGNITION_PROMPT = """你是一位资深产品经理，正在快速分析一款移动App的整体情况。

我会给你一张由多张App截图组成的网格图（按顺序排列），请通过这些截图快速判断：

## 需要输出的信息

1. **app_category**: App大类（选择一个）
   - 健康健身 (Health & Fitness)
   - 冥想正念 (Meditation)
   - 饮食营养 (Nutrition & Diet)
   - 运动追踪 (Sports Tracking)
   - 睡眠改善 (Sleep)
   - 心理健康 (Mental Health)
   - 女性健康 (Women's Health)
   - 效率工具 (Productivity)
   - 教育学习 (Education)
   - 社交通讯 (Social)
   - 娱乐 (Entertainment)
   - 金融 (Finance)
   - 其他 (Other)

2. **sub_category**: 更细分的类别（自由填写，如"卡路里追踪"、"跑步训练"等）

3. **target_users**: 目标用户画像（20-40字描述）

4. **core_value**: 核心价值主张（15-30字，这个App解决什么问题）

5. **business_model**: 商业模式
   - 订阅制 (Subscription)
   - 一次性付费 (One-time Purchase)
   - 免费+广告 (Free with Ads)
   - 免费增值 (Freemium)
   - 混合模式 (Hybrid)

6. **estimated_stages**: 预估的用户流程阶段（数组，按顺序）
   例如: ["Welcome", "Onboarding", "Paywall", "Core Features", "Settings"]
   
   常见阶段：
   - Launch: 启动/闪屏
   - Welcome: 欢迎/价值介绍
   - Onboarding: 引导/信息收集
   - SignUp: 注册登录
   - Paywall: 付费墙
   - Home: 首页
   - Core Features: 核心功能
   - Content: 内容浏览
   - Tracking: 追踪记录
   - Progress: 进度统计
   - Social: 社交功能
   - Profile: 个人中心
   - Settings: 设置

7. **visual_style**: 视觉风格
   - 极简清新 (Minimalist)
   - 丰富多彩 (Colorful)
   - 专业商务 (Professional)
   - 游戏化 (Gamified)
   - 自然舒适 (Natural)
   - 科技感 (Tech)
   - 温暖治愈 (Warm)

8. **primary_color**: 主色调（如 "蓝色"、"绿色"、"紫色渐变" 等）

## 输出格式

请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "app_category": "类别",
  "sub_category": "细分类别",
  "target_users": "目标用户描述",
  "core_value": "核心价值主张",
  "business_model": "商业模式",
  "estimated_stages": ["阶段1", "阶段2", "阶段3"],
  "visual_style": "视觉风格",
  "primary_color": "主色调",
  "confidence": 0.9
}
```

## 分析要点

1. 通过第一张图判断是否有品牌Logo/启动页
2. 观察是否有引导问卷、目标选择等Onboarding元素
3. 寻找价格、订阅按钮等Paywall标志
4. 识别核心功能界面的特征（图表、列表、播放器等）
5. 注意整体色调和设计风格

只输出JSON，不要有任何解释文字。"""


class ProductRecognizer:
    """产品识别器 - Layer 1"""
    
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
    
    def create_thumbnail_grid(
        self, 
        image_folder: str, 
        grid_size: Tuple[int, int] = (5, 5),
        thumb_size: Tuple[int, int] = (200, 400)
    ) -> Optional[bytes]:
        """
        创建缩略图网格
        
        Args:
            image_folder: 截图文件夹路径
            grid_size: 网格大小 (列, 行)
            thumb_size: 每个缩略图大小
        
        Returns:
            网格图的PNG字节数据
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None
        
        cols, rows = grid_size
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if len(images) > max_images:
            step = len(images) / max_images
            sampled = [images[int(i * step)] for i in range(max_images)]
            images = sampled
        
        # 创建网格画布
        grid_width = cols * thumb_size[0]
        grid_height = rows * thumb_size[1]
        grid_image = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # 填充缩略图
        for idx, filename in enumerate(images):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 居中放置
                x = col * thumb_size[0] + (thumb_size[0] - img.width) // 2
                y = row * thumb_size[1] + (thumb_size[1] - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        return buffer.getvalue()
    
    def analyze(self, project_path: str, app_name: str = "") -> ProductProfile:
        """
        分析产品，生成产品画像
        
        Args:
            project_path: 项目路径
            app_name: App名称（可选）
        
        Returns:
            ProductProfile 产品画像
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 创建缩略图网格
        print("  [Layer 1] Creating thumbnail grid...")
        grid_data = self.create_thumbnail_grid(screens_folder)
        
        if not grid_data:
            return self._default_profile(app_name or os.path.basename(project_path))
        
        if not self.client:
            print("  [WARN] API not configured, using default profile")
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 调用API分析
        print("  [Layer 1] Analyzing product profile...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
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
                                "media_type": "image/png",
                                "data": grid_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": PRODUCT_RECOGNITION_PROMPT
                        }
                    ]
                }]
            )
            
            raw_response = response.content[0].text
            parsed = self._parse_json(raw_response)
            
            if parsed:
                return ProductProfile(
                    app_name=app_name or os.path.basename(project_path).replace("_Analysis", ""),
                    app_category=parsed.get("app_category", "Other"),
                    sub_category=parsed.get("sub_category", ""),
                    target_users=parsed.get("target_users", ""),
                    core_value=parsed.get("core_value", ""),
                    business_model=parsed.get("business_model", "Subscription"),
                    estimated_stages=parsed.get("estimated_stages", []),
                    visual_style=parsed.get("visual_style", ""),
                    primary_color=parsed.get("primary_color", ""),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_profile(app_name or os.path.basename(project_path))
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        # 直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 提取 { ... }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_profile(self, app_name: str) -> ProductProfile:
        """返回默认的产品画像"""
        return ProductProfile(
            app_name=app_name,
            app_category="Other",
            sub_category="",
            target_users="一般用户",
            core_value="",
            business_model="Subscription",
            estimated_stages=["Welcome", "Onboarding", "Core Features"],
            visual_style="",
            primary_color="",
            confidence=0.3
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1: Product Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # 分析
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    
    print("\n" + "=" * 60)
    print("Product Profile")
    print("=" * 60)
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))


"""
Layer 1: 产品认知模块
通过分析缩略图网格，快速理解产品类型、目标用户和整体结构
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProductProfile:
    """产品画像"""
    app_name: str
    app_category: str                    # 健康/冥想/健身/饮食等
    sub_category: str                    # 更细分的类别
    target_users: str                    # 目标用户描述
    core_value: str                      # 核心价值主张
    business_model: str                  # 商业模式
    estimated_stages: List[str]          # 预估的流程阶段
    visual_style: str                    # 视觉风格（极简/丰富/游戏化等）
    primary_color: str                   # 主色调
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 提示词
# ============================================================

PRODUCT_RECOGNITION_PROMPT = """你是一位资深产品经理，正在快速分析一款移动App的整体情况。

我会给你一张由多张App截图组成的网格图（按顺序排列），请通过这些截图快速判断：

## 需要输出的信息

1. **app_category**: App大类（选择一个）
   - 健康健身 (Health & Fitness)
   - 冥想正念 (Meditation)
   - 饮食营养 (Nutrition & Diet)
   - 运动追踪 (Sports Tracking)
   - 睡眠改善 (Sleep)
   - 心理健康 (Mental Health)
   - 女性健康 (Women's Health)
   - 效率工具 (Productivity)
   - 教育学习 (Education)
   - 社交通讯 (Social)
   - 娱乐 (Entertainment)
   - 金融 (Finance)
   - 其他 (Other)

2. **sub_category**: 更细分的类别（自由填写，如"卡路里追踪"、"跑步训练"等）

3. **target_users**: 目标用户画像（20-40字描述）

4. **core_value**: 核心价值主张（15-30字，这个App解决什么问题）

5. **business_model**: 商业模式
   - 订阅制 (Subscription)
   - 一次性付费 (One-time Purchase)
   - 免费+广告 (Free with Ads)
   - 免费增值 (Freemium)
   - 混合模式 (Hybrid)

6. **estimated_stages**: 预估的用户流程阶段（数组，按顺序）
   例如: ["Welcome", "Onboarding", "Paywall", "Core Features", "Settings"]
   
   常见阶段：
   - Launch: 启动/闪屏
   - Welcome: 欢迎/价值介绍
   - Onboarding: 引导/信息收集
   - SignUp: 注册登录
   - Paywall: 付费墙
   - Home: 首页
   - Core Features: 核心功能
   - Content: 内容浏览
   - Tracking: 追踪记录
   - Progress: 进度统计
   - Social: 社交功能
   - Profile: 个人中心
   - Settings: 设置

7. **visual_style**: 视觉风格
   - 极简清新 (Minimalist)
   - 丰富多彩 (Colorful)
   - 专业商务 (Professional)
   - 游戏化 (Gamified)
   - 自然舒适 (Natural)
   - 科技感 (Tech)
   - 温暖治愈 (Warm)

8. **primary_color**: 主色调（如 "蓝色"、"绿色"、"紫色渐变" 等）

## 输出格式

请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "app_category": "类别",
  "sub_category": "细分类别",
  "target_users": "目标用户描述",
  "core_value": "核心价值主张",
  "business_model": "商业模式",
  "estimated_stages": ["阶段1", "阶段2", "阶段3"],
  "visual_style": "视觉风格",
  "primary_color": "主色调",
  "confidence": 0.9
}
```

## 分析要点

1. 通过第一张图判断是否有品牌Logo/启动页
2. 观察是否有引导问卷、目标选择等Onboarding元素
3. 寻找价格、订阅按钮等Paywall标志
4. 识别核心功能界面的特征（图表、列表、播放器等）
5. 注意整体色调和设计风格

只输出JSON，不要有任何解释文字。"""


class ProductRecognizer:
    """产品识别器 - Layer 1"""
    
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
    
    def create_thumbnail_grid(
        self, 
        image_folder: str, 
        grid_size: Tuple[int, int] = (5, 5),
        thumb_size: Tuple[int, int] = (200, 400)
    ) -> Optional[bytes]:
        """
        创建缩略图网格
        
        Args:
            image_folder: 截图文件夹路径
            grid_size: 网格大小 (列, 行)
            thumb_size: 每个缩略图大小
        
        Returns:
            网格图的PNG字节数据
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None
        
        cols, rows = grid_size
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if len(images) > max_images:
            step = len(images) / max_images
            sampled = [images[int(i * step)] for i in range(max_images)]
            images = sampled
        
        # 创建网格画布
        grid_width = cols * thumb_size[0]
        grid_height = rows * thumb_size[1]
        grid_image = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # 填充缩略图
        for idx, filename in enumerate(images):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 居中放置
                x = col * thumb_size[0] + (thumb_size[0] - img.width) // 2
                y = row * thumb_size[1] + (thumb_size[1] - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        return buffer.getvalue()
    
    def analyze(self, project_path: str, app_name: str = "") -> ProductProfile:
        """
        分析产品，生成产品画像
        
        Args:
            project_path: 项目路径
            app_name: App名称（可选）
        
        Returns:
            ProductProfile 产品画像
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 创建缩略图网格
        print("  [Layer 1] Creating thumbnail grid...")
        grid_data = self.create_thumbnail_grid(screens_folder)
        
        if not grid_data:
            return self._default_profile(app_name or os.path.basename(project_path))
        
        if not self.client:
            print("  [WARN] API not configured, using default profile")
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 调用API分析
        print("  [Layer 1] Analyzing product profile...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
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
                                "media_type": "image/png",
                                "data": grid_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": PRODUCT_RECOGNITION_PROMPT
                        }
                    ]
                }]
            )
            
            raw_response = response.content[0].text
            parsed = self._parse_json(raw_response)
            
            if parsed:
                return ProductProfile(
                    app_name=app_name or os.path.basename(project_path).replace("_Analysis", ""),
                    app_category=parsed.get("app_category", "Other"),
                    sub_category=parsed.get("sub_category", ""),
                    target_users=parsed.get("target_users", ""),
                    core_value=parsed.get("core_value", ""),
                    business_model=parsed.get("business_model", "Subscription"),
                    estimated_stages=parsed.get("estimated_stages", []),
                    visual_style=parsed.get("visual_style", ""),
                    primary_color=parsed.get("primary_color", ""),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_profile(app_name or os.path.basename(project_path))
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        # 直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 提取 { ... }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_profile(self, app_name: str) -> ProductProfile:
        """返回默认的产品画像"""
        return ProductProfile(
            app_name=app_name,
            app_category="Other",
            sub_category="",
            target_users="一般用户",
            core_value="",
            business_model="Subscription",
            estimated_stages=["Welcome", "Onboarding", "Core Features"],
            visual_style="",
            primary_color="",
            confidence=0.3
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1: Product Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # 分析
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    
    print("\n" + "=" * 60)
    print("Product Profile")
    print("=" * 60)
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))


"""
Layer 1: 产品认知模块
通过分析缩略图网格，快速理解产品类型、目标用户和整体结构
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProductProfile:
    """产品画像"""
    app_name: str
    app_category: str                    # 健康/冥想/健身/饮食等
    sub_category: str                    # 更细分的类别
    target_users: str                    # 目标用户描述
    core_value: str                      # 核心价值主张
    business_model: str                  # 商业模式
    estimated_stages: List[str]          # 预估的流程阶段
    visual_style: str                    # 视觉风格（极简/丰富/游戏化等）
    primary_color: str                   # 主色调
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 提示词
# ============================================================

PRODUCT_RECOGNITION_PROMPT = """你是一位资深产品经理，正在快速分析一款移动App的整体情况。

我会给你一张由多张App截图组成的网格图（按顺序排列），请通过这些截图快速判断：

## 需要输出的信息

1. **app_category**: App大类（选择一个）
   - 健康健身 (Health & Fitness)
   - 冥想正念 (Meditation)
   - 饮食营养 (Nutrition & Diet)
   - 运动追踪 (Sports Tracking)
   - 睡眠改善 (Sleep)
   - 心理健康 (Mental Health)
   - 女性健康 (Women's Health)
   - 效率工具 (Productivity)
   - 教育学习 (Education)
   - 社交通讯 (Social)
   - 娱乐 (Entertainment)
   - 金融 (Finance)
   - 其他 (Other)

2. **sub_category**: 更细分的类别（自由填写，如"卡路里追踪"、"跑步训练"等）

3. **target_users**: 目标用户画像（20-40字描述）

4. **core_value**: 核心价值主张（15-30字，这个App解决什么问题）

5. **business_model**: 商业模式
   - 订阅制 (Subscription)
   - 一次性付费 (One-time Purchase)
   - 免费+广告 (Free with Ads)
   - 免费增值 (Freemium)
   - 混合模式 (Hybrid)

6. **estimated_stages**: 预估的用户流程阶段（数组，按顺序）
   例如: ["Welcome", "Onboarding", "Paywall", "Core Features", "Settings"]
   
   常见阶段：
   - Launch: 启动/闪屏
   - Welcome: 欢迎/价值介绍
   - Onboarding: 引导/信息收集
   - SignUp: 注册登录
   - Paywall: 付费墙
   - Home: 首页
   - Core Features: 核心功能
   - Content: 内容浏览
   - Tracking: 追踪记录
   - Progress: 进度统计
   - Social: 社交功能
   - Profile: 个人中心
   - Settings: 设置

7. **visual_style**: 视觉风格
   - 极简清新 (Minimalist)
   - 丰富多彩 (Colorful)
   - 专业商务 (Professional)
   - 游戏化 (Gamified)
   - 自然舒适 (Natural)
   - 科技感 (Tech)
   - 温暖治愈 (Warm)

8. **primary_color**: 主色调（如 "蓝色"、"绿色"、"紫色渐变" 等）

## 输出格式

请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "app_category": "类别",
  "sub_category": "细分类别",
  "target_users": "目标用户描述",
  "core_value": "核心价值主张",
  "business_model": "商业模式",
  "estimated_stages": ["阶段1", "阶段2", "阶段3"],
  "visual_style": "视觉风格",
  "primary_color": "主色调",
  "confidence": 0.9
}
```

## 分析要点

1. 通过第一张图判断是否有品牌Logo/启动页
2. 观察是否有引导问卷、目标选择等Onboarding元素
3. 寻找价格、订阅按钮等Paywall标志
4. 识别核心功能界面的特征（图表、列表、播放器等）
5. 注意整体色调和设计风格

只输出JSON，不要有任何解释文字。"""


class ProductRecognizer:
    """产品识别器 - Layer 1"""
    
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
    
    def create_thumbnail_grid(
        self, 
        image_folder: str, 
        grid_size: Tuple[int, int] = (5, 5),
        thumb_size: Tuple[int, int] = (200, 400)
    ) -> Optional[bytes]:
        """
        创建缩略图网格
        
        Args:
            image_folder: 截图文件夹路径
            grid_size: 网格大小 (列, 行)
            thumb_size: 每个缩略图大小
        
        Returns:
            网格图的PNG字节数据
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None
        
        cols, rows = grid_size
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if len(images) > max_images:
            step = len(images) / max_images
            sampled = [images[int(i * step)] for i in range(max_images)]
            images = sampled
        
        # 创建网格画布
        grid_width = cols * thumb_size[0]
        grid_height = rows * thumb_size[1]
        grid_image = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # 填充缩略图
        for idx, filename in enumerate(images):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 居中放置
                x = col * thumb_size[0] + (thumb_size[0] - img.width) // 2
                y = row * thumb_size[1] + (thumb_size[1] - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        return buffer.getvalue()
    
    def analyze(self, project_path: str, app_name: str = "") -> ProductProfile:
        """
        分析产品，生成产品画像
        
        Args:
            project_path: 项目路径
            app_name: App名称（可选）
        
        Returns:
            ProductProfile 产品画像
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 创建缩略图网格
        print("  [Layer 1] Creating thumbnail grid...")
        grid_data = self.create_thumbnail_grid(screens_folder)
        
        if not grid_data:
            return self._default_profile(app_name or os.path.basename(project_path))
        
        if not self.client:
            print("  [WARN] API not configured, using default profile")
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 调用API分析
        print("  [Layer 1] Analyzing product profile...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
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
                                "media_type": "image/png",
                                "data": grid_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": PRODUCT_RECOGNITION_PROMPT
                        }
                    ]
                }]
            )
            
            raw_response = response.content[0].text
            parsed = self._parse_json(raw_response)
            
            if parsed:
                return ProductProfile(
                    app_name=app_name or os.path.basename(project_path).replace("_Analysis", ""),
                    app_category=parsed.get("app_category", "Other"),
                    sub_category=parsed.get("sub_category", ""),
                    target_users=parsed.get("target_users", ""),
                    core_value=parsed.get("core_value", ""),
                    business_model=parsed.get("business_model", "Subscription"),
                    estimated_stages=parsed.get("estimated_stages", []),
                    visual_style=parsed.get("visual_style", ""),
                    primary_color=parsed.get("primary_color", ""),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_profile(app_name or os.path.basename(project_path))
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        # 直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 提取 { ... }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_profile(self, app_name: str) -> ProductProfile:
        """返回默认的产品画像"""
        return ProductProfile(
            app_name=app_name,
            app_category="Other",
            sub_category="",
            target_users="一般用户",
            core_value="",
            business_model="Subscription",
            estimated_stages=["Welcome", "Onboarding", "Core Features"],
            visual_style="",
            primary_color="",
            confidence=0.3
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1: Product Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # 分析
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    
    print("\n" + "=" * 60)
    print("Product Profile")
    print("=" * 60)
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))



"""
Layer 1: 产品认知模块
通过分析缩略图网格，快速理解产品类型、目标用户和整体结构
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProductProfile:
    """产品画像"""
    app_name: str
    app_category: str                    # 健康/冥想/健身/饮食等
    sub_category: str                    # 更细分的类别
    target_users: str                    # 目标用户描述
    core_value: str                      # 核心价值主张
    business_model: str                  # 商业模式
    estimated_stages: List[str]          # 预估的流程阶段
    visual_style: str                    # 视觉风格（极简/丰富/游戏化等）
    primary_color: str                   # 主色调
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 提示词
# ============================================================

PRODUCT_RECOGNITION_PROMPT = """你是一位资深产品经理，正在快速分析一款移动App的整体情况。

我会给你一张由多张App截图组成的网格图（按顺序排列），请通过这些截图快速判断：

## 需要输出的信息

1. **app_category**: App大类（选择一个）
   - 健康健身 (Health & Fitness)
   - 冥想正念 (Meditation)
   - 饮食营养 (Nutrition & Diet)
   - 运动追踪 (Sports Tracking)
   - 睡眠改善 (Sleep)
   - 心理健康 (Mental Health)
   - 女性健康 (Women's Health)
   - 效率工具 (Productivity)
   - 教育学习 (Education)
   - 社交通讯 (Social)
   - 娱乐 (Entertainment)
   - 金融 (Finance)
   - 其他 (Other)

2. **sub_category**: 更细分的类别（自由填写，如"卡路里追踪"、"跑步训练"等）

3. **target_users**: 目标用户画像（20-40字描述）

4. **core_value**: 核心价值主张（15-30字，这个App解决什么问题）

5. **business_model**: 商业模式
   - 订阅制 (Subscription)
   - 一次性付费 (One-time Purchase)
   - 免费+广告 (Free with Ads)
   - 免费增值 (Freemium)
   - 混合模式 (Hybrid)

6. **estimated_stages**: 预估的用户流程阶段（数组，按顺序）
   例如: ["Welcome", "Onboarding", "Paywall", "Core Features", "Settings"]
   
   常见阶段：
   - Launch: 启动/闪屏
   - Welcome: 欢迎/价值介绍
   - Onboarding: 引导/信息收集
   - SignUp: 注册登录
   - Paywall: 付费墙
   - Home: 首页
   - Core Features: 核心功能
   - Content: 内容浏览
   - Tracking: 追踪记录
   - Progress: 进度统计
   - Social: 社交功能
   - Profile: 个人中心
   - Settings: 设置

7. **visual_style**: 视觉风格
   - 极简清新 (Minimalist)
   - 丰富多彩 (Colorful)
   - 专业商务 (Professional)
   - 游戏化 (Gamified)
   - 自然舒适 (Natural)
   - 科技感 (Tech)
   - 温暖治愈 (Warm)

8. **primary_color**: 主色调（如 "蓝色"、"绿色"、"紫色渐变" 等）

## 输出格式

请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "app_category": "类别",
  "sub_category": "细分类别",
  "target_users": "目标用户描述",
  "core_value": "核心价值主张",
  "business_model": "商业模式",
  "estimated_stages": ["阶段1", "阶段2", "阶段3"],
  "visual_style": "视觉风格",
  "primary_color": "主色调",
  "confidence": 0.9
}
```

## 分析要点

1. 通过第一张图判断是否有品牌Logo/启动页
2. 观察是否有引导问卷、目标选择等Onboarding元素
3. 寻找价格、订阅按钮等Paywall标志
4. 识别核心功能界面的特征（图表、列表、播放器等）
5. 注意整体色调和设计风格

只输出JSON，不要有任何解释文字。"""


class ProductRecognizer:
    """产品识别器 - Layer 1"""
    
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
    
    def create_thumbnail_grid(
        self, 
        image_folder: str, 
        grid_size: Tuple[int, int] = (5, 5),
        thumb_size: Tuple[int, int] = (200, 400)
    ) -> Optional[bytes]:
        """
        创建缩略图网格
        
        Args:
            image_folder: 截图文件夹路径
            grid_size: 网格大小 (列, 行)
            thumb_size: 每个缩略图大小
        
        Returns:
            网格图的PNG字节数据
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None
        
        cols, rows = grid_size
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if len(images) > max_images:
            step = len(images) / max_images
            sampled = [images[int(i * step)] for i in range(max_images)]
            images = sampled
        
        # 创建网格画布
        grid_width = cols * thumb_size[0]
        grid_height = rows * thumb_size[1]
        grid_image = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # 填充缩略图
        for idx, filename in enumerate(images):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 居中放置
                x = col * thumb_size[0] + (thumb_size[0] - img.width) // 2
                y = row * thumb_size[1] + (thumb_size[1] - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        return buffer.getvalue()
    
    def analyze(self, project_path: str, app_name: str = "") -> ProductProfile:
        """
        分析产品，生成产品画像
        
        Args:
            project_path: 项目路径
            app_name: App名称（可选）
        
        Returns:
            ProductProfile 产品画像
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 创建缩略图网格
        print("  [Layer 1] Creating thumbnail grid...")
        grid_data = self.create_thumbnail_grid(screens_folder)
        
        if not grid_data:
            return self._default_profile(app_name or os.path.basename(project_path))
        
        if not self.client:
            print("  [WARN] API not configured, using default profile")
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 调用API分析
        print("  [Layer 1] Analyzing product profile...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
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
                                "media_type": "image/png",
                                "data": grid_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": PRODUCT_RECOGNITION_PROMPT
                        }
                    ]
                }]
            )
            
            raw_response = response.content[0].text
            parsed = self._parse_json(raw_response)
            
            if parsed:
                return ProductProfile(
                    app_name=app_name or os.path.basename(project_path).replace("_Analysis", ""),
                    app_category=parsed.get("app_category", "Other"),
                    sub_category=parsed.get("sub_category", ""),
                    target_users=parsed.get("target_users", ""),
                    core_value=parsed.get("core_value", ""),
                    business_model=parsed.get("business_model", "Subscription"),
                    estimated_stages=parsed.get("estimated_stages", []),
                    visual_style=parsed.get("visual_style", ""),
                    primary_color=parsed.get("primary_color", ""),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_profile(app_name or os.path.basename(project_path))
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        # 直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 提取 { ... }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_profile(self, app_name: str) -> ProductProfile:
        """返回默认的产品画像"""
        return ProductProfile(
            app_name=app_name,
            app_category="Other",
            sub_category="",
            target_users="一般用户",
            core_value="",
            business_model="Subscription",
            estimated_stages=["Welcome", "Onboarding", "Core Features"],
            visual_style="",
            primary_color="",
            confidence=0.3
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1: Product Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # 分析
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    
    print("\n" + "=" * 60)
    print("Product Profile")
    print("=" * 60)
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))


"""
Layer 1: 产品认知模块
通过分析缩略图网格，快速理解产品类型、目标用户和整体结构
"""

import os
import sys
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from PIL import Image

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ProductProfile:
    """产品画像"""
    app_name: str
    app_category: str                    # 健康/冥想/健身/饮食等
    sub_category: str                    # 更细分的类别
    target_users: str                    # 目标用户描述
    core_value: str                      # 核心价值主张
    business_model: str                  # 商业模式
    estimated_stages: List[str]          # 预估的流程阶段
    visual_style: str                    # 视觉风格（极简/丰富/游戏化等）
    primary_color: str                   # 主色调
    confidence: float
    raw_analysis: str = ""


# ============================================================
# 提示词
# ============================================================

PRODUCT_RECOGNITION_PROMPT = """你是一位资深产品经理，正在快速分析一款移动App的整体情况。

我会给你一张由多张App截图组成的网格图（按顺序排列），请通过这些截图快速判断：

## 需要输出的信息

1. **app_category**: App大类（选择一个）
   - 健康健身 (Health & Fitness)
   - 冥想正念 (Meditation)
   - 饮食营养 (Nutrition & Diet)
   - 运动追踪 (Sports Tracking)
   - 睡眠改善 (Sleep)
   - 心理健康 (Mental Health)
   - 女性健康 (Women's Health)
   - 效率工具 (Productivity)
   - 教育学习 (Education)
   - 社交通讯 (Social)
   - 娱乐 (Entertainment)
   - 金融 (Finance)
   - 其他 (Other)

2. **sub_category**: 更细分的类别（自由填写，如"卡路里追踪"、"跑步训练"等）

3. **target_users**: 目标用户画像（20-40字描述）

4. **core_value**: 核心价值主张（15-30字，这个App解决什么问题）

5. **business_model**: 商业模式
   - 订阅制 (Subscription)
   - 一次性付费 (One-time Purchase)
   - 免费+广告 (Free with Ads)
   - 免费增值 (Freemium)
   - 混合模式 (Hybrid)

6. **estimated_stages**: 预估的用户流程阶段（数组，按顺序）
   例如: ["Welcome", "Onboarding", "Paywall", "Core Features", "Settings"]
   
   常见阶段：
   - Launch: 启动/闪屏
   - Welcome: 欢迎/价值介绍
   - Onboarding: 引导/信息收集
   - SignUp: 注册登录
   - Paywall: 付费墙
   - Home: 首页
   - Core Features: 核心功能
   - Content: 内容浏览
   - Tracking: 追踪记录
   - Progress: 进度统计
   - Social: 社交功能
   - Profile: 个人中心
   - Settings: 设置

7. **visual_style**: 视觉风格
   - 极简清新 (Minimalist)
   - 丰富多彩 (Colorful)
   - 专业商务 (Professional)
   - 游戏化 (Gamified)
   - 自然舒适 (Natural)
   - 科技感 (Tech)
   - 温暖治愈 (Warm)

8. **primary_color**: 主色调（如 "蓝色"、"绿色"、"紫色渐变" 等）

## 输出格式

请严格按以下JSON格式输出，不要输出任何其他内容：

```json
{
  "app_category": "类别",
  "sub_category": "细分类别",
  "target_users": "目标用户描述",
  "core_value": "核心价值主张",
  "business_model": "商业模式",
  "estimated_stages": ["阶段1", "阶段2", "阶段3"],
  "visual_style": "视觉风格",
  "primary_color": "主色调",
  "confidence": 0.9
}
```

## 分析要点

1. 通过第一张图判断是否有品牌Logo/启动页
2. 观察是否有引导问卷、目标选择等Onboarding元素
3. 寻找价格、订阅按钮等Paywall标志
4. 识别核心功能界面的特征（图表、列表、播放器等）
5. 注意整体色调和设计风格

只输出JSON，不要有任何解释文字。"""


class ProductRecognizer:
    """产品识别器 - Layer 1"""
    
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
    
    def create_thumbnail_grid(
        self, 
        image_folder: str, 
        grid_size: Tuple[int, int] = (5, 5),
        thumb_size: Tuple[int, int] = (200, 400)
    ) -> Optional[bytes]:
        """
        创建缩略图网格
        
        Args:
            image_folder: 截图文件夹路径
            grid_size: 网格大小 (列, 行)
            thumb_size: 每个缩略图大小
        
        Returns:
            网格图的PNG字节数据
        """
        # 获取所有图片
        images = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        if not images:
            return None
        
        cols, rows = grid_size
        max_images = cols * rows
        
        # 如果图片太多，均匀采样
        if len(images) > max_images:
            step = len(images) / max_images
            sampled = [images[int(i * step)] for i in range(max_images)]
            images = sampled
        
        # 创建网格画布
        grid_width = cols * thumb_size[0]
        grid_height = rows * thumb_size[1]
        grid_image = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
        
        # 填充缩略图
        for idx, filename in enumerate(images):
            if idx >= max_images:
                break
            
            col = idx % cols
            row = idx // cols
            
            try:
                img_path = os.path.join(image_folder, filename)
                img = Image.open(img_path)
                
                # 等比缩放
                img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                # 居中放置
                x = col * thumb_size[0] + (thumb_size[0] - img.width) // 2
                y = row * thumb_size[1] + (thumb_size[1] - img.height) // 2
                
                # 转换模式
                if img.mode == 'RGBA':
                    # 创建白色背景
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                grid_image.paste(img, (x, y))
                img.close()
                
            except Exception as e:
                print(f"  [WARN] Failed to process {filename}: {e}")
        
        # 转换为字节
        buffer = io.BytesIO()
        grid_image.save(buffer, format='PNG', optimize=True)
        grid_image.close()
        
        return buffer.getvalue()
    
    def analyze(self, project_path: str, app_name: str = "") -> ProductProfile:
        """
        分析产品，生成产品画像
        
        Args:
            project_path: 项目路径
            app_name: App名称（可选）
        
        Returns:
            ProductProfile 产品画像
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 创建缩略图网格
        print("  [Layer 1] Creating thumbnail grid...")
        grid_data = self.create_thumbnail_grid(screens_folder)
        
        if not grid_data:
            return self._default_profile(app_name or os.path.basename(project_path))
        
        if not self.client:
            print("  [WARN] API not configured, using default profile")
            return self._default_profile(app_name or os.path.basename(project_path))
        
        # 调用API分析
        print("  [Layer 1] Analyzing product profile...")
        try:
            grid_base64 = base64.standard_b64encode(grid_data).decode('utf-8')
            
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
                                "media_type": "image/png",
                                "data": grid_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": PRODUCT_RECOGNITION_PROMPT
                        }
                    ]
                }]
            )
            
            raw_response = response.content[0].text
            parsed = self._parse_json(raw_response)
            
            if parsed:
                return ProductProfile(
                    app_name=app_name or os.path.basename(project_path).replace("_Analysis", ""),
                    app_category=parsed.get("app_category", "Other"),
                    sub_category=parsed.get("sub_category", ""),
                    target_users=parsed.get("target_users", ""),
                    core_value=parsed.get("core_value", ""),
                    business_model=parsed.get("business_model", "Subscription"),
                    estimated_stages=parsed.get("estimated_stages", []),
                    visual_style=parsed.get("visual_style", ""),
                    primary_color=parsed.get("primary_color", ""),
                    confidence=float(parsed.get("confidence", 0.5)),
                    raw_analysis=raw_response
                )
            
        except Exception as e:
            print(f"  [ERROR] API call failed: {e}")
        
        return self._default_profile(app_name or os.path.basename(project_path))
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析JSON响应"""
        import re
        
        # 直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # 提取 { ... }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        
        return None
    
    def _default_profile(self, app_name: str) -> ProductProfile:
        """返回默认的产品画像"""
        return ProductProfile(
            app_name=app_name,
            app_category="Other",
            sub_category="",
            target_users="一般用户",
            core_value="",
            business_model="Subscription",
            estimated_stages=["Welcome", "Onboarding", "Core Features"],
            visual_style="",
            primary_color="",
            confidence=0.3
        )


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Layer 1: Product Recognition")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # 分析
    recognizer = ProductRecognizer()
    profile = recognizer.analyze(project_path)
    
    print("\n" + "=" * 60)
    print("Product Profile")
    print("=" * 60)
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))


















