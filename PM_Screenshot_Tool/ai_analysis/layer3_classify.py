# -*- coding: utf-8 -*-
"""
Layer 3: 精确分类模块
结合产品画像和流程结构，带上下文地分析每张截图
"""

import os
import sys
import json
import base64
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image
import io

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1和2
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage

# Few-shot学习
try:
    from few_shot_examples import get_onboarding_examples, get_examples_prompt
    FEWSHOT_AVAILABLE = True
except ImportError:
    FEWSHOT_AVAILABLE = False


# ============================================================
# 配置
# ============================================================

DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10

# 递进压缩配置（失败时逐级压缩）
COMPRESSION_LEVELS = [
    {"max_size": 4 * 1024 * 1024, "width": 800, "quality": 85},   # Level 0: 轻度压缩
    {"max_size": 2 * 1024 * 1024, "width": 600, "quality": 75},   # Level 1: 中度压缩
    {"max_size": 1 * 1024 * 1024, "width": 400, "quality": 65},   # Level 2: 强压缩
]

MAX_RETRIES = 3  # 最大重试次数


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ScreenClassification:
    """单张截图的分类结果"""
    filename: str
    index: int                          # 1-based索引
    screen_type: str
    sub_type: str
    
    # 双语命名
    naming: Dict[str, str]
    
    # 核心功能
    core_function: Dict[str, str]
    
    # 设计亮点
    design_highlights: List[Dict]
    
    # 产品洞察
    product_insight: Dict[str, str]
    
    # 标签
    tags: List[Dict[str, str]]
    
    # 上下文信息
    stage_name: str
    position_in_stage: str              # "early" / "middle" / "late"
    
    # 元数据
    confidence: float
    reasoning: str                       # AI的判断理由
    ui_elements: List[str]
    keywords_found: List[str]
    
    # 兼容字段
    description_cn: str = ""
    description_en: str = ""
    error: Optional[str] = None


# ============================================================
# 上下文增强提示词
# ============================================================

CONTEXT_CLASSIFICATION_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。

## 产品背景
- App名称: {app_name}
- App类型: {app_category} / {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 视觉风格: {visual_style}

## 当前截图位置
- 这是第 {position} 张截图（共 {total} 张）
- 所属阶段: {stage_name}（第 {stage_start}-{stage_end} 张）
- 阶段描述: {stage_description}
- 在阶段中的位置: {position_in_stage}

## 上下文信息
- 前一张: {prev_info}
- 后一张: {next_info}

## 阶段约束
当前处于 "{stage_name}" 阶段，该阶段通常包含以下类型：
{expected_types}

# ⭐ 核心判断原则（最重要！）

**问自己：这个页面的主要目的是「帮助用户成功使用产品」还是「向用户索取价值」？**

| 受益方 | 页面目的 | 分类方向 |
|--------|----------|----------|
| 用户 | 教会用户怎么用、收集信息以更好服务用户、获取使用所需权限 | Onboarding |
| 产品 | 付费、分享、评分、邀请好友 | Paywall/Referral |

---

## 页面类型定义

### Onboarding（用户引导）⭐ 核心类型
**定义**：帮助用户从下载到首次体验核心价值的引导流程

属于Onboarding：
- 价值展示（产品能为你做什么）
- 目标设定（你想达成什么）
- 偏好收集（你喜欢什么）
- 场景选择（你想在什么场景使用）
- 功能教学（教你怎么用）
- 情感铺垫（如深呼吸引导，为体验做心理准备）
- 权限请求（使用产品所需的系统权限）

**不属于**Onboarding：
- 付费相关 → Paywall
- 邀请好友/分享 → Referral
- 评分请求 → Other

典型特征：
- 进度指示器、Continue/Next/Skip按钮
- 无底部导航栏（还在引导流程中）
- 通常在前20张截图

### Launch（启动页）
- 显示App logo和品牌名
- 通常是第1张截图
- 页面简洁，无交互元素

### Welcome（欢迎页）
- 属于Onboarding的一部分
- 介绍产品价值主张
- 大图/插图 + 简短文字
- "Get Started"按钮

### Permission（权限请求）
- 属于Onboarding的一部分
- iOS/Android系统弹窗样式
- 请求通知/位置/健康/相机权限

### SignUp（注册登录）
- 邮箱/手机号/密码输入框
- 社交登录按钮
- 可以归入Onboarding也可独立

### Paywall（付费墙）⚠️ 不属于Onboarding
- 明确显示价格（$X.XX/月）
- 订阅套餐选项、试用期说明
- 目的是转化付费，受益方是产品

### Referral（邀请增长）⚠️ 不属于Onboarding  
- 邀请好友、分享奖励
- "Invite Friends"、"Share to get rewards"
- 目的是获客增长，受益方是产品
- 用户尚未体验价值就被要求分享

### Home（首页）
- 有底部导航栏（Tab Bar）
- App的主界面/仪表盘

### Feature（功能页）
- 有底部导航栏
- App的常规功能页面
⚠️ 没有底部导航栏且在前20张 → 很可能不是Feature

### Content（内容页）
- 音频/视频播放界面
- 文章/故事阅读界面

### Profile（个人中心）
- 用户头像、昵称、账户信息

### Settings（设置页）
- 设置选项列表、开关项

### Social（社交页）
- 好友列表、社区动态
⚠️ 注意与Referral区分：Social是功能，Referral是增长手段

### Tracking（记录页）
- 数据输入、添加记录

### Progress（进度页）
- 图表、统计、成就

### Other（其他）
- 不属于以上任何类型

---

## 分类决策流程

```
1. 先问：受益方是谁？
   - 向用户索取（付费/分享/评分）→ Paywall/Referral/Other
   - 帮助用户 → 继续判断

2. 再问：有底部导航栏吗？
   - 有 → Home/Feature/Content/Profile/Settings/Tracking/Progress
   - 无 → 继续判断

3. 最后问：在前20张吗？
   - 是 → Launch/Welcome/Onboarding/Permission/SignUp
   - 否 → Feature/Content/Other
```

## 设计亮点分类
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 输出要求
请严格按以下JSON格式输出：

```json
{{
  "screen_type": "类型名",
  "sub_type": "子类型（如goal_selection, breathing_guide等）",
  "naming": {{
    "cn": "页面中文名（2-6字）",
    "en": "Page Name (2-4 words)"
  }},
  "core_function": {{
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  }},
  "design_highlights": [
    {{"category": "visual", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "interaction", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "emotional", "cn": "亮点描述", "en": "Highlight"}}
  ],
  "product_insight": {{
    "cn": "产品洞察（30-60字）",
    "en": "Product insight (15-40 words)"
  }},
  "tags": [
    {{"cn": "标签1", "en": "Tag1"}},
    {{"cn": "标签2", "en": "Tag2"}}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95,
  "reasoning": "简短说明为什么判断为这个类型（考虑位置和上下文）"
}}
```

只输出JSON，不要有任何解释文字。"""


class ContextClassifier:
    """上下文感知分类器 - Layer 3"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5
    ):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        self.client = None
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
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
    
    def _compress_image(self, image_path: str, compression_level: int = 0) -> Tuple[str, str]:
        """
        压缩图片并返回base64和媒体类型
        
        Args:
            image_path: 图片路径
            compression_level: 压缩等级 (0=轻度, 1=中度, 2=强压缩)
        """
        try:
            # 获取压缩配置
            level = min(compression_level, len(COMPRESSION_LEVELS) - 1)
            config = COMPRESSION_LEVELS[level]
            max_size = config["max_size"]
            target_width = config["width"]
            quality = config["quality"]
            
            file_size = os.path.getsize(image_path)
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 如果文件太大或指定了压缩等级，进行压缩
            if file_size > max_size or compression_level > 0:
                img = Image.open(io.BytesIO(image_data))
                
                # 缩小
                if img.width > target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # 转RGB
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality, optimize=True)
                img.close()
                
                compressed_size = buffer.tell()
                if compression_level > 0:
                    print(f"    [COMPRESS L{level}] {file_size//1024}KB -> {compressed_size//1024}KB")
                
                return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
            
            # 不需要压缩，直接返回
            ext = os.path.splitext(image_path)[1].lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/png")
            
            return base64.standard_b64encode(image_data).decode('utf-8'), media_type
            
        except Exception as e:
            raise Exception(f"Image processing error: {e}")
    
    def _get_position_in_stage(self, index: int, stage: FlowStage) -> str:
        """计算在阶段中的位置"""
        stage_length = stage.end_index - stage.start_index + 1
        position_in_stage = index - stage.start_index + 1
        
        if stage_length <= 2:
            return "single"
        
        ratio = position_in_stage / stage_length
        if ratio <= 0.33:
            return "early (阶段开始)"
        elif ratio <= 0.66:
            return "middle (阶段中部)"
        else:
            return "late (阶段结束)"
    
    def classify_single(
        self,
        image_path: str,
        index: int,
        total: int,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        prev_result: Optional[Dict] = None,
        next_filename: Optional[str] = None,
        retry_count: int = 0
    ) -> ScreenClassification:
        """
        分类单张截图（带上下文，自动重试）
        
        Args:
            retry_count: 当前重试次数，用于递进压缩
        """
        filename = os.path.basename(image_path)
        
        # 找到当前所属阶段
        current_stage = None
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                current_stage = stage
                break
        
        if not current_stage:
            current_stage = FlowStage(
                name="Unknown",
                start_index=1,
                end_index=total,
                description="未识别阶段",
                expected_types=["Feature"],
                screenshot_count=total
            )
        
        # 构建上下文信息
        prev_info = "无（这是第一张）"
        if prev_result:
            prev_info = f"{prev_result.get('screen_type', 'Unknown')} - {prev_result.get('naming', {}).get('cn', '')}"
        
        next_info = "无（这是最后一张）"
        if next_filename:
            next_info = f"待分析: {next_filename}"
        
        position_in_stage = self._get_position_in_stage(index, current_stage)
        expected_types_str = "\n".join([f"  - {t}" for t in current_stage.expected_types])
        
        # 构建提示词
        prompt = CONTEXT_CLASSIFICATION_PROMPT.format(
            app_name=product_profile.app_name,
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            visual_style=product_profile.visual_style,
            position=index,
            total=total,
            stage_name=current_stage.name,
            stage_start=current_stage.start_index,
            stage_end=current_stage.end_index,
            stage_description=current_stage.description,
            position_in_stage=position_in_stage,
            prev_info=prev_info,
            next_info=next_info,
            expected_types=expected_types_str
        )
        
        # 添加Few-shot示例（从其他产品学习）
        if FEWSHOT_AVAILABLE and index <= 30:  # 前30张最容易混淆，添加示例
            project_name = os.path.basename(os.path.dirname(image_path))
            few_shot = get_onboarding_examples(exclude_product=project_name)
            if few_shot:
                prompt = few_shot + "\n" + prompt
        
        # 调用API（带自动重试和递进压缩）
        try:
            # 根据重试次数决定压缩等级
            compression_level = retry_count
            image_base64, media_type = self._compress_image(image_path, compression_level)
            
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
                                "data": image_base64
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
                with self.lock:
                    self.success_count += 1
                
                return ScreenClassification(
                    filename=filename,
                    index=index,
                    screen_type=parsed.get("screen_type", "Unknown"),
                    sub_type=parsed.get("sub_type", ""),
                    naming=parsed.get("naming", {"cn": "", "en": ""}),
                    core_function=parsed.get("core_function", {"cn": "", "en": ""}),
                    design_highlights=parsed.get("design_highlights", []),
                    product_insight=parsed.get("product_insight", {"cn": "", "en": ""}),
                    tags=parsed.get("tags", []),
                    stage_name=current_stage.name,
                    position_in_stage=position_in_stage.split(" ")[0],
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", ""),
                    ui_elements=parsed.get("ui_elements", []),
                    keywords_found=parsed.get("keywords_found", []),
                    description_cn=parsed.get("core_function", {}).get("cn", ""),
                    description_en=parsed.get("core_function", {}).get("en", "")
                )
            else:
                # JSON解析失败，重试
                if retry_count < MAX_RETRIES:
                    time.sleep(1)
                    return self.classify_single(
                        image_path, index, total, product_profile, flow_structure,
                        prev_result, next_filename, retry_count + 1
                    )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检查是否是图片大小/格式相关的错误，自动重试
            is_image_error = any(x in error_str for x in [
                'image', 'size', 'too large', 'invalid_request', '400', 'base64'
            ])
            
            if is_image_error and retry_count < MAX_RETRIES:
                # 使用更强的压缩重试
                time.sleep(1)
                return self.classify_single(
                    image_path, index, total, product_profile, flow_structure,
                    prev_result, next_filename, retry_count + 1
                )
            
            with self.lock:
                self.fail_count += 1
            
            return ScreenClassification(
                filename=filename,
                index=index,
                screen_type="Unknown",
                sub_type="",
                naming={"cn": "分析失败", "en": "Analysis Failed"},
                core_function={"cn": str(e), "en": "Error"},
                design_highlights=[],
                product_insight={"cn": "", "en": ""},
                tags=[],
                stage_name=current_stage.name,
                position_in_stage="unknown",
                confidence=0.0,
                reasoning="",
                ui_elements=[],
                keywords_found=[],
                error=str(e)
            )
        
        # 解析失败且重试耗尽
        with self.lock:
            self.fail_count += 1
        
        return ScreenClassification(
            filename=filename,
            index=index,
            screen_type="Unknown",
            sub_type="",
            naming={"cn": "解析失败", "en": "Parse Failed"},
            core_function={"cn": "JSON解析失败", "en": "JSON parse error"},
            design_highlights=[],
            product_insight={"cn": "", "en": ""},
            tags=[],
            stage_name=current_stage.name,
            position_in_stage="unknown",
            confidence=0.0,
            reasoning="",
            ui_elements=[],
            keywords_found=[],
            error="JSON parse error"
        )
    
    def classify_all(
        self,
        project_path: str,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        分类所有截图（并行处理）
        
        Returns:
            {filename: classification_dict}
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return {}
        
        # 获取所有截图
        screenshots = sorted([
            f for f in os.listdir(screens_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(screenshots)
        if total == 0:
            return {}
        
        print(f"  [Layer 3] Classifying {total} screenshots (concurrent: {self.concurrent})...")
        
        results = {}
        start_time = datetime.now()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交任务
            futures = {}
            for idx, filename in enumerate(screenshots, 1):
                image_path = os.path.join(screens_folder, filename)
                
                # 获取前一个结果（如果有）
                prev_result = None
                if idx > 1:
                    prev_filename = screenshots[idx - 2]
                    prev_result = results.get(prev_filename)
                
                # 获取下一个文件名
                next_filename = None
                if idx < total:
                    next_filename = screenshots[idx]
                
                future = executor.submit(
                    self.classify_single,
                    image_path,
                    idx,
                    total,
                    product_profile,
                    flow_structure,
                    prev_result,
                    next_filename
                )
                futures[future] = (filename, idx)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures):
                filename, idx = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = asdict(result)
                    
                    # 进度显示
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total - completed)
                    
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r  [{bar}] {completed}/{total} ({pct:.0%}) | {int(remaining)}s left')
                    sys.stdout.flush()
                    
                    if progress_callback:
                        progress_callback(completed, total, filename, result)
                    
                except Exception as e:
                    print(f"\n  [ERROR] {filename}: {e}")
                    results[filename] = {
                        "filename": filename,
                        "index": idx,
                        "screen_type": "Unknown",
                        "error": str(e)
                    }
        
        print()  # 换行
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  [Layer 3] Complete: {self.success_count} success, {self.fail_count} failed")
        print(f"  [Layer 3] Time: {elapsed:.1f}s ({elapsed/total:.2f}s per image)")
        
        return results
    
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


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    from layer2_structure import StructureRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 3: Context Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of screenshots to test")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    product_recognizer = ProductRecognizer()
    profile = product_recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    print(f"  Stages: {len(structure.stages)}")
    
    # Layer 3 (limited test)
    print(f"\n[Layer 3] Classification (testing {args.limit} screenshots)...")
    classifier = ContextClassifier(concurrent=2)
    
    # 只测试前几张
    screens_folder = os.path.join(project_path, "Screens")
    screenshots = sorted([
        f for f in os.listdir(screens_folder)
        if f.lower().endswith('.png')
    ])[:args.limit]
    
    for idx, filename in enumerate(screenshots, 1):
        image_path = os.path.join(screens_folder, filename)
        result = classifier.classify_single(
            image_path, idx, len(screenshots), profile, structure
        )
        print(f"\n  [{idx}] {filename}")
        print(f"      Type: {result.screen_type} ({result.sub_type})")
        print(f"      Stage: {result.stage_name}")
        print(f"      Reason: {result.reasoning}")


Layer 3: 精确分类模块
结合产品画像和流程结构，带上下文地分析每张截图
"""

import os
import sys
import json
import base64
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image
import io

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1和2
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage

# Few-shot学习
try:
    from few_shot_examples import get_onboarding_examples, get_examples_prompt
    FEWSHOT_AVAILABLE = True
except ImportError:
    FEWSHOT_AVAILABLE = False


# ============================================================
# 配置
# ============================================================

DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10

# 递进压缩配置（失败时逐级压缩）
COMPRESSION_LEVELS = [
    {"max_size": 4 * 1024 * 1024, "width": 800, "quality": 85},   # Level 0: 轻度压缩
    {"max_size": 2 * 1024 * 1024, "width": 600, "quality": 75},   # Level 1: 中度压缩
    {"max_size": 1 * 1024 * 1024, "width": 400, "quality": 65},   # Level 2: 强压缩
]

MAX_RETRIES = 3  # 最大重试次数


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ScreenClassification:
    """单张截图的分类结果"""
    filename: str
    index: int                          # 1-based索引
    screen_type: str
    sub_type: str
    
    # 双语命名
    naming: Dict[str, str]
    
    # 核心功能
    core_function: Dict[str, str]
    
    # 设计亮点
    design_highlights: List[Dict]
    
    # 产品洞察
    product_insight: Dict[str, str]
    
    # 标签
    tags: List[Dict[str, str]]
    
    # 上下文信息
    stage_name: str
    position_in_stage: str              # "early" / "middle" / "late"
    
    # 元数据
    confidence: float
    reasoning: str                       # AI的判断理由
    ui_elements: List[str]
    keywords_found: List[str]
    
    # 兼容字段
    description_cn: str = ""
    description_en: str = ""
    error: Optional[str] = None


# ============================================================
# 上下文增强提示词
# ============================================================

CONTEXT_CLASSIFICATION_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。

## 产品背景
- App名称: {app_name}
- App类型: {app_category} / {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 视觉风格: {visual_style}

## 当前截图位置
- 这是第 {position} 张截图（共 {total} 张）
- 所属阶段: {stage_name}（第 {stage_start}-{stage_end} 张）
- 阶段描述: {stage_description}
- 在阶段中的位置: {position_in_stage}

## 上下文信息
- 前一张: {prev_info}
- 后一张: {next_info}

## 阶段约束
当前处于 "{stage_name}" 阶段，该阶段通常包含以下类型：
{expected_types}

# ⭐ 核心判断原则（最重要！）

**问自己：这个页面的主要目的是「帮助用户成功使用产品」还是「向用户索取价值」？**

| 受益方 | 页面目的 | 分类方向 |
|--------|----------|----------|
| 用户 | 教会用户怎么用、收集信息以更好服务用户、获取使用所需权限 | Onboarding |
| 产品 | 付费、分享、评分、邀请好友 | Paywall/Referral |

---

## 页面类型定义

### Onboarding（用户引导）⭐ 核心类型
**定义**：帮助用户从下载到首次体验核心价值的引导流程

属于Onboarding：
- 价值展示（产品能为你做什么）
- 目标设定（你想达成什么）
- 偏好收集（你喜欢什么）
- 场景选择（你想在什么场景使用）
- 功能教学（教你怎么用）
- 情感铺垫（如深呼吸引导，为体验做心理准备）
- 权限请求（使用产品所需的系统权限）

**不属于**Onboarding：
- 付费相关 → Paywall
- 邀请好友/分享 → Referral
- 评分请求 → Other

典型特征：
- 进度指示器、Continue/Next/Skip按钮
- 无底部导航栏（还在引导流程中）
- 通常在前20张截图

### Launch（启动页）
- 显示App logo和品牌名
- 通常是第1张截图
- 页面简洁，无交互元素

### Welcome（欢迎页）
- 属于Onboarding的一部分
- 介绍产品价值主张
- 大图/插图 + 简短文字
- "Get Started"按钮

### Permission（权限请求）
- 属于Onboarding的一部分
- iOS/Android系统弹窗样式
- 请求通知/位置/健康/相机权限

### SignUp（注册登录）
- 邮箱/手机号/密码输入框
- 社交登录按钮
- 可以归入Onboarding也可独立

### Paywall（付费墙）⚠️ 不属于Onboarding
- 明确显示价格（$X.XX/月）
- 订阅套餐选项、试用期说明
- 目的是转化付费，受益方是产品

### Referral（邀请增长）⚠️ 不属于Onboarding  
- 邀请好友、分享奖励
- "Invite Friends"、"Share to get rewards"
- 目的是获客增长，受益方是产品
- 用户尚未体验价值就被要求分享

### Home（首页）
- 有底部导航栏（Tab Bar）
- App的主界面/仪表盘

### Feature（功能页）
- 有底部导航栏
- App的常规功能页面
⚠️ 没有底部导航栏且在前20张 → 很可能不是Feature

### Content（内容页）
- 音频/视频播放界面
- 文章/故事阅读界面

### Profile（个人中心）
- 用户头像、昵称、账户信息

### Settings（设置页）
- 设置选项列表、开关项

### Social（社交页）
- 好友列表、社区动态
⚠️ 注意与Referral区分：Social是功能，Referral是增长手段

### Tracking（记录页）
- 数据输入、添加记录

### Progress（进度页）
- 图表、统计、成就

### Other（其他）
- 不属于以上任何类型

---

## 分类决策流程

```
1. 先问：受益方是谁？
   - 向用户索取（付费/分享/评分）→ Paywall/Referral/Other
   - 帮助用户 → 继续判断

2. 再问：有底部导航栏吗？
   - 有 → Home/Feature/Content/Profile/Settings/Tracking/Progress
   - 无 → 继续判断

3. 最后问：在前20张吗？
   - 是 → Launch/Welcome/Onboarding/Permission/SignUp
   - 否 → Feature/Content/Other
```

## 设计亮点分类
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 输出要求
请严格按以下JSON格式输出：

```json
{{
  "screen_type": "类型名",
  "sub_type": "子类型（如goal_selection, breathing_guide等）",
  "naming": {{
    "cn": "页面中文名（2-6字）",
    "en": "Page Name (2-4 words)"
  }},
  "core_function": {{
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  }},
  "design_highlights": [
    {{"category": "visual", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "interaction", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "emotional", "cn": "亮点描述", "en": "Highlight"}}
  ],
  "product_insight": {{
    "cn": "产品洞察（30-60字）",
    "en": "Product insight (15-40 words)"
  }},
  "tags": [
    {{"cn": "标签1", "en": "Tag1"}},
    {{"cn": "标签2", "en": "Tag2"}}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95,
  "reasoning": "简短说明为什么判断为这个类型（考虑位置和上下文）"
}}
```

只输出JSON，不要有任何解释文字。"""


class ContextClassifier:
    """上下文感知分类器 - Layer 3"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5
    ):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        self.client = None
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
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
    
    def _compress_image(self, image_path: str, compression_level: int = 0) -> Tuple[str, str]:
        """
        压缩图片并返回base64和媒体类型
        
        Args:
            image_path: 图片路径
            compression_level: 压缩等级 (0=轻度, 1=中度, 2=强压缩)
        """
        try:
            # 获取压缩配置
            level = min(compression_level, len(COMPRESSION_LEVELS) - 1)
            config = COMPRESSION_LEVELS[level]
            max_size = config["max_size"]
            target_width = config["width"]
            quality = config["quality"]
            
            file_size = os.path.getsize(image_path)
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 如果文件太大或指定了压缩等级，进行压缩
            if file_size > max_size or compression_level > 0:
                img = Image.open(io.BytesIO(image_data))
                
                # 缩小
                if img.width > target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # 转RGB
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality, optimize=True)
                img.close()
                
                compressed_size = buffer.tell()
                if compression_level > 0:
                    print(f"    [COMPRESS L{level}] {file_size//1024}KB -> {compressed_size//1024}KB")
                
                return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
            
            # 不需要压缩，直接返回
            ext = os.path.splitext(image_path)[1].lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/png")
            
            return base64.standard_b64encode(image_data).decode('utf-8'), media_type
            
        except Exception as e:
            raise Exception(f"Image processing error: {e}")
    
    def _get_position_in_stage(self, index: int, stage: FlowStage) -> str:
        """计算在阶段中的位置"""
        stage_length = stage.end_index - stage.start_index + 1
        position_in_stage = index - stage.start_index + 1
        
        if stage_length <= 2:
            return "single"
        
        ratio = position_in_stage / stage_length
        if ratio <= 0.33:
            return "early (阶段开始)"
        elif ratio <= 0.66:
            return "middle (阶段中部)"
        else:
            return "late (阶段结束)"
    
    def classify_single(
        self,
        image_path: str,
        index: int,
        total: int,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        prev_result: Optional[Dict] = None,
        next_filename: Optional[str] = None,
        retry_count: int = 0
    ) -> ScreenClassification:
        """
        分类单张截图（带上下文，自动重试）
        
        Args:
            retry_count: 当前重试次数，用于递进压缩
        """
        filename = os.path.basename(image_path)
        
        # 找到当前所属阶段
        current_stage = None
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                current_stage = stage
                break
        
        if not current_stage:
            current_stage = FlowStage(
                name="Unknown",
                start_index=1,
                end_index=total,
                description="未识别阶段",
                expected_types=["Feature"],
                screenshot_count=total
            )
        
        # 构建上下文信息
        prev_info = "无（这是第一张）"
        if prev_result:
            prev_info = f"{prev_result.get('screen_type', 'Unknown')} - {prev_result.get('naming', {}).get('cn', '')}"
        
        next_info = "无（这是最后一张）"
        if next_filename:
            next_info = f"待分析: {next_filename}"
        
        position_in_stage = self._get_position_in_stage(index, current_stage)
        expected_types_str = "\n".join([f"  - {t}" for t in current_stage.expected_types])
        
        # 构建提示词
        prompt = CONTEXT_CLASSIFICATION_PROMPT.format(
            app_name=product_profile.app_name,
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            visual_style=product_profile.visual_style,
            position=index,
            total=total,
            stage_name=current_stage.name,
            stage_start=current_stage.start_index,
            stage_end=current_stage.end_index,
            stage_description=current_stage.description,
            position_in_stage=position_in_stage,
            prev_info=prev_info,
            next_info=next_info,
            expected_types=expected_types_str
        )
        
        # 添加Few-shot示例（从其他产品学习）
        if FEWSHOT_AVAILABLE and index <= 30:  # 前30张最容易混淆，添加示例
            project_name = os.path.basename(os.path.dirname(image_path))
            few_shot = get_onboarding_examples(exclude_product=project_name)
            if few_shot:
                prompt = few_shot + "\n" + prompt
        
        # 调用API（带自动重试和递进压缩）
        try:
            # 根据重试次数决定压缩等级
            compression_level = retry_count
            image_base64, media_type = self._compress_image(image_path, compression_level)
            
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
                                "data": image_base64
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
                with self.lock:
                    self.success_count += 1
                
                return ScreenClassification(
                    filename=filename,
                    index=index,
                    screen_type=parsed.get("screen_type", "Unknown"),
                    sub_type=parsed.get("sub_type", ""),
                    naming=parsed.get("naming", {"cn": "", "en": ""}),
                    core_function=parsed.get("core_function", {"cn": "", "en": ""}),
                    design_highlights=parsed.get("design_highlights", []),
                    product_insight=parsed.get("product_insight", {"cn": "", "en": ""}),
                    tags=parsed.get("tags", []),
                    stage_name=current_stage.name,
                    position_in_stage=position_in_stage.split(" ")[0],
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", ""),
                    ui_elements=parsed.get("ui_elements", []),
                    keywords_found=parsed.get("keywords_found", []),
                    description_cn=parsed.get("core_function", {}).get("cn", ""),
                    description_en=parsed.get("core_function", {}).get("en", "")
                )
            else:
                # JSON解析失败，重试
                if retry_count < MAX_RETRIES:
                    time.sleep(1)
                    return self.classify_single(
                        image_path, index, total, product_profile, flow_structure,
                        prev_result, next_filename, retry_count + 1
                    )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检查是否是图片大小/格式相关的错误，自动重试
            is_image_error = any(x in error_str for x in [
                'image', 'size', 'too large', 'invalid_request', '400', 'base64'
            ])
            
            if is_image_error and retry_count < MAX_RETRIES:
                # 使用更强的压缩重试
                time.sleep(1)
                return self.classify_single(
                    image_path, index, total, product_profile, flow_structure,
                    prev_result, next_filename, retry_count + 1
                )
            
            with self.lock:
                self.fail_count += 1
            
            return ScreenClassification(
                filename=filename,
                index=index,
                screen_type="Unknown",
                sub_type="",
                naming={"cn": "分析失败", "en": "Analysis Failed"},
                core_function={"cn": str(e), "en": "Error"},
                design_highlights=[],
                product_insight={"cn": "", "en": ""},
                tags=[],
                stage_name=current_stage.name,
                position_in_stage="unknown",
                confidence=0.0,
                reasoning="",
                ui_elements=[],
                keywords_found=[],
                error=str(e)
            )
        
        # 解析失败且重试耗尽
        with self.lock:
            self.fail_count += 1
        
        return ScreenClassification(
            filename=filename,
            index=index,
            screen_type="Unknown",
            sub_type="",
            naming={"cn": "解析失败", "en": "Parse Failed"},
            core_function={"cn": "JSON解析失败", "en": "JSON parse error"},
            design_highlights=[],
            product_insight={"cn": "", "en": ""},
            tags=[],
            stage_name=current_stage.name,
            position_in_stage="unknown",
            confidence=0.0,
            reasoning="",
            ui_elements=[],
            keywords_found=[],
            error="JSON parse error"
        )
    
    def classify_all(
        self,
        project_path: str,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        分类所有截图（并行处理）
        
        Returns:
            {filename: classification_dict}
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return {}
        
        # 获取所有截图
        screenshots = sorted([
            f for f in os.listdir(screens_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(screenshots)
        if total == 0:
            return {}
        
        print(f"  [Layer 3] Classifying {total} screenshots (concurrent: {self.concurrent})...")
        
        results = {}
        start_time = datetime.now()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交任务
            futures = {}
            for idx, filename in enumerate(screenshots, 1):
                image_path = os.path.join(screens_folder, filename)
                
                # 获取前一个结果（如果有）
                prev_result = None
                if idx > 1:
                    prev_filename = screenshots[idx - 2]
                    prev_result = results.get(prev_filename)
                
                # 获取下一个文件名
                next_filename = None
                if idx < total:
                    next_filename = screenshots[idx]
                
                future = executor.submit(
                    self.classify_single,
                    image_path,
                    idx,
                    total,
                    product_profile,
                    flow_structure,
                    prev_result,
                    next_filename
                )
                futures[future] = (filename, idx)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures):
                filename, idx = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = asdict(result)
                    
                    # 进度显示
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total - completed)
                    
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r  [{bar}] {completed}/{total} ({pct:.0%}) | {int(remaining)}s left')
                    sys.stdout.flush()
                    
                    if progress_callback:
                        progress_callback(completed, total, filename, result)
                    
                except Exception as e:
                    print(f"\n  [ERROR] {filename}: {e}")
                    results[filename] = {
                        "filename": filename,
                        "index": idx,
                        "screen_type": "Unknown",
                        "error": str(e)
                    }
        
        print()  # 换行
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  [Layer 3] Complete: {self.success_count} success, {self.fail_count} failed")
        print(f"  [Layer 3] Time: {elapsed:.1f}s ({elapsed/total:.2f}s per image)")
        
        return results
    
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


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    from layer2_structure import StructureRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 3: Context Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of screenshots to test")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    product_recognizer = ProductRecognizer()
    profile = product_recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    print(f"  Stages: {len(structure.stages)}")
    
    # Layer 3 (limited test)
    print(f"\n[Layer 3] Classification (testing {args.limit} screenshots)...")
    classifier = ContextClassifier(concurrent=2)
    
    # 只测试前几张
    screens_folder = os.path.join(project_path, "Screens")
    screenshots = sorted([
        f for f in os.listdir(screens_folder)
        if f.lower().endswith('.png')
    ])[:args.limit]
    
    for idx, filename in enumerate(screenshots, 1):
        image_path = os.path.join(screens_folder, filename)
        result = classifier.classify_single(
            image_path, idx, len(screenshots), profile, structure
        )
        print(f"\n  [{idx}] {filename}")
        print(f"      Type: {result.screen_type} ({result.sub_type})")
        print(f"      Stage: {result.stage_name}")
        print(f"      Reason: {result.reasoning}")


Layer 3: 精确分类模块
结合产品画像和流程结构，带上下文地分析每张截图
"""

import os
import sys
import json
import base64
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image
import io

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1和2
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage

# Few-shot学习
try:
    from few_shot_examples import get_onboarding_examples, get_examples_prompt
    FEWSHOT_AVAILABLE = True
except ImportError:
    FEWSHOT_AVAILABLE = False


# ============================================================
# 配置
# ============================================================

DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10

# 递进压缩配置（失败时逐级压缩）
COMPRESSION_LEVELS = [
    {"max_size": 4 * 1024 * 1024, "width": 800, "quality": 85},   # Level 0: 轻度压缩
    {"max_size": 2 * 1024 * 1024, "width": 600, "quality": 75},   # Level 1: 中度压缩
    {"max_size": 1 * 1024 * 1024, "width": 400, "quality": 65},   # Level 2: 强压缩
]

MAX_RETRIES = 3  # 最大重试次数


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ScreenClassification:
    """单张截图的分类结果"""
    filename: str
    index: int                          # 1-based索引
    screen_type: str
    sub_type: str
    
    # 双语命名
    naming: Dict[str, str]
    
    # 核心功能
    core_function: Dict[str, str]
    
    # 设计亮点
    design_highlights: List[Dict]
    
    # 产品洞察
    product_insight: Dict[str, str]
    
    # 标签
    tags: List[Dict[str, str]]
    
    # 上下文信息
    stage_name: str
    position_in_stage: str              # "early" / "middle" / "late"
    
    # 元数据
    confidence: float
    reasoning: str                       # AI的判断理由
    ui_elements: List[str]
    keywords_found: List[str]
    
    # 兼容字段
    description_cn: str = ""
    description_en: str = ""
    error: Optional[str] = None


# ============================================================
# 上下文增强提示词
# ============================================================

CONTEXT_CLASSIFICATION_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。

## 产品背景
- App名称: {app_name}
- App类型: {app_category} / {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 视觉风格: {visual_style}

## 当前截图位置
- 这是第 {position} 张截图（共 {total} 张）
- 所属阶段: {stage_name}（第 {stage_start}-{stage_end} 张）
- 阶段描述: {stage_description}
- 在阶段中的位置: {position_in_stage}

## 上下文信息
- 前一张: {prev_info}
- 后一张: {next_info}

## 阶段约束
当前处于 "{stage_name}" 阶段，该阶段通常包含以下类型：
{expected_types}

# ⭐ 核心判断原则（最重要！）

**问自己：这个页面的主要目的是「帮助用户成功使用产品」还是「向用户索取价值」？**

| 受益方 | 页面目的 | 分类方向 |
|--------|----------|----------|
| 用户 | 教会用户怎么用、收集信息以更好服务用户、获取使用所需权限 | Onboarding |
| 产品 | 付费、分享、评分、邀请好友 | Paywall/Referral |

---

## 页面类型定义

### Onboarding（用户引导）⭐ 核心类型
**定义**：帮助用户从下载到首次体验核心价值的引导流程

属于Onboarding：
- 价值展示（产品能为你做什么）
- 目标设定（你想达成什么）
- 偏好收集（你喜欢什么）
- 场景选择（你想在什么场景使用）
- 功能教学（教你怎么用）
- 情感铺垫（如深呼吸引导，为体验做心理准备）
- 权限请求（使用产品所需的系统权限）

**不属于**Onboarding：
- 付费相关 → Paywall
- 邀请好友/分享 → Referral
- 评分请求 → Other

典型特征：
- 进度指示器、Continue/Next/Skip按钮
- 无底部导航栏（还在引导流程中）
- 通常在前20张截图

### Launch（启动页）
- 显示App logo和品牌名
- 通常是第1张截图
- 页面简洁，无交互元素

### Welcome（欢迎页）
- 属于Onboarding的一部分
- 介绍产品价值主张
- 大图/插图 + 简短文字
- "Get Started"按钮

### Permission（权限请求）
- 属于Onboarding的一部分
- iOS/Android系统弹窗样式
- 请求通知/位置/健康/相机权限

### SignUp（注册登录）
- 邮箱/手机号/密码输入框
- 社交登录按钮
- 可以归入Onboarding也可独立

### Paywall（付费墙）⚠️ 不属于Onboarding
- 明确显示价格（$X.XX/月）
- 订阅套餐选项、试用期说明
- 目的是转化付费，受益方是产品

### Referral（邀请增长）⚠️ 不属于Onboarding  
- 邀请好友、分享奖励
- "Invite Friends"、"Share to get rewards"
- 目的是获客增长，受益方是产品
- 用户尚未体验价值就被要求分享

### Home（首页）
- 有底部导航栏（Tab Bar）
- App的主界面/仪表盘

### Feature（功能页）
- 有底部导航栏
- App的常规功能页面
⚠️ 没有底部导航栏且在前20张 → 很可能不是Feature

### Content（内容页）
- 音频/视频播放界面
- 文章/故事阅读界面

### Profile（个人中心）
- 用户头像、昵称、账户信息

### Settings（设置页）
- 设置选项列表、开关项

### Social（社交页）
- 好友列表、社区动态
⚠️ 注意与Referral区分：Social是功能，Referral是增长手段

### Tracking（记录页）
- 数据输入、添加记录

### Progress（进度页）
- 图表、统计、成就

### Other（其他）
- 不属于以上任何类型

---

## 分类决策流程

```
1. 先问：受益方是谁？
   - 向用户索取（付费/分享/评分）→ Paywall/Referral/Other
   - 帮助用户 → 继续判断

2. 再问：有底部导航栏吗？
   - 有 → Home/Feature/Content/Profile/Settings/Tracking/Progress
   - 无 → 继续判断

3. 最后问：在前20张吗？
   - 是 → Launch/Welcome/Onboarding/Permission/SignUp
   - 否 → Feature/Content/Other
```

## 设计亮点分类
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 输出要求
请严格按以下JSON格式输出：

```json
{{
  "screen_type": "类型名",
  "sub_type": "子类型（如goal_selection, breathing_guide等）",
  "naming": {{
    "cn": "页面中文名（2-6字）",
    "en": "Page Name (2-4 words)"
  }},
  "core_function": {{
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  }},
  "design_highlights": [
    {{"category": "visual", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "interaction", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "emotional", "cn": "亮点描述", "en": "Highlight"}}
  ],
  "product_insight": {{
    "cn": "产品洞察（30-60字）",
    "en": "Product insight (15-40 words)"
  }},
  "tags": [
    {{"cn": "标签1", "en": "Tag1"}},
    {{"cn": "标签2", "en": "Tag2"}}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95,
  "reasoning": "简短说明为什么判断为这个类型（考虑位置和上下文）"
}}
```

只输出JSON，不要有任何解释文字。"""


class ContextClassifier:
    """上下文感知分类器 - Layer 3"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5
    ):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        self.client = None
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
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
    
    def _compress_image(self, image_path: str, compression_level: int = 0) -> Tuple[str, str]:
        """
        压缩图片并返回base64和媒体类型
        
        Args:
            image_path: 图片路径
            compression_level: 压缩等级 (0=轻度, 1=中度, 2=强压缩)
        """
        try:
            # 获取压缩配置
            level = min(compression_level, len(COMPRESSION_LEVELS) - 1)
            config = COMPRESSION_LEVELS[level]
            max_size = config["max_size"]
            target_width = config["width"]
            quality = config["quality"]
            
            file_size = os.path.getsize(image_path)
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 如果文件太大或指定了压缩等级，进行压缩
            if file_size > max_size or compression_level > 0:
                img = Image.open(io.BytesIO(image_data))
                
                # 缩小
                if img.width > target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # 转RGB
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality, optimize=True)
                img.close()
                
                compressed_size = buffer.tell()
                if compression_level > 0:
                    print(f"    [COMPRESS L{level}] {file_size//1024}KB -> {compressed_size//1024}KB")
                
                return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
            
            # 不需要压缩，直接返回
            ext = os.path.splitext(image_path)[1].lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/png")
            
            return base64.standard_b64encode(image_data).decode('utf-8'), media_type
            
        except Exception as e:
            raise Exception(f"Image processing error: {e}")
    
    def _get_position_in_stage(self, index: int, stage: FlowStage) -> str:
        """计算在阶段中的位置"""
        stage_length = stage.end_index - stage.start_index + 1
        position_in_stage = index - stage.start_index + 1
        
        if stage_length <= 2:
            return "single"
        
        ratio = position_in_stage / stage_length
        if ratio <= 0.33:
            return "early (阶段开始)"
        elif ratio <= 0.66:
            return "middle (阶段中部)"
        else:
            return "late (阶段结束)"
    
    def classify_single(
        self,
        image_path: str,
        index: int,
        total: int,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        prev_result: Optional[Dict] = None,
        next_filename: Optional[str] = None,
        retry_count: int = 0
    ) -> ScreenClassification:
        """
        分类单张截图（带上下文，自动重试）
        
        Args:
            retry_count: 当前重试次数，用于递进压缩
        """
        filename = os.path.basename(image_path)
        
        # 找到当前所属阶段
        current_stage = None
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                current_stage = stage
                break
        
        if not current_stage:
            current_stage = FlowStage(
                name="Unknown",
                start_index=1,
                end_index=total,
                description="未识别阶段",
                expected_types=["Feature"],
                screenshot_count=total
            )
        
        # 构建上下文信息
        prev_info = "无（这是第一张）"
        if prev_result:
            prev_info = f"{prev_result.get('screen_type', 'Unknown')} - {prev_result.get('naming', {}).get('cn', '')}"
        
        next_info = "无（这是最后一张）"
        if next_filename:
            next_info = f"待分析: {next_filename}"
        
        position_in_stage = self._get_position_in_stage(index, current_stage)
        expected_types_str = "\n".join([f"  - {t}" for t in current_stage.expected_types])
        
        # 构建提示词
        prompt = CONTEXT_CLASSIFICATION_PROMPT.format(
            app_name=product_profile.app_name,
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            visual_style=product_profile.visual_style,
            position=index,
            total=total,
            stage_name=current_stage.name,
            stage_start=current_stage.start_index,
            stage_end=current_stage.end_index,
            stage_description=current_stage.description,
            position_in_stage=position_in_stage,
            prev_info=prev_info,
            next_info=next_info,
            expected_types=expected_types_str
        )
        
        # 添加Few-shot示例（从其他产品学习）
        if FEWSHOT_AVAILABLE and index <= 30:  # 前30张最容易混淆，添加示例
            project_name = os.path.basename(os.path.dirname(image_path))
            few_shot = get_onboarding_examples(exclude_product=project_name)
            if few_shot:
                prompt = few_shot + "\n" + prompt
        
        # 调用API（带自动重试和递进压缩）
        try:
            # 根据重试次数决定压缩等级
            compression_level = retry_count
            image_base64, media_type = self._compress_image(image_path, compression_level)
            
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
                                "data": image_base64
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
                with self.lock:
                    self.success_count += 1
                
                return ScreenClassification(
                    filename=filename,
                    index=index,
                    screen_type=parsed.get("screen_type", "Unknown"),
                    sub_type=parsed.get("sub_type", ""),
                    naming=parsed.get("naming", {"cn": "", "en": ""}),
                    core_function=parsed.get("core_function", {"cn": "", "en": ""}),
                    design_highlights=parsed.get("design_highlights", []),
                    product_insight=parsed.get("product_insight", {"cn": "", "en": ""}),
                    tags=parsed.get("tags", []),
                    stage_name=current_stage.name,
                    position_in_stage=position_in_stage.split(" ")[0],
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", ""),
                    ui_elements=parsed.get("ui_elements", []),
                    keywords_found=parsed.get("keywords_found", []),
                    description_cn=parsed.get("core_function", {}).get("cn", ""),
                    description_en=parsed.get("core_function", {}).get("en", "")
                )
            else:
                # JSON解析失败，重试
                if retry_count < MAX_RETRIES:
                    time.sleep(1)
                    return self.classify_single(
                        image_path, index, total, product_profile, flow_structure,
                        prev_result, next_filename, retry_count + 1
                    )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检查是否是图片大小/格式相关的错误，自动重试
            is_image_error = any(x in error_str for x in [
                'image', 'size', 'too large', 'invalid_request', '400', 'base64'
            ])
            
            if is_image_error and retry_count < MAX_RETRIES:
                # 使用更强的压缩重试
                time.sleep(1)
                return self.classify_single(
                    image_path, index, total, product_profile, flow_structure,
                    prev_result, next_filename, retry_count + 1
                )
            
            with self.lock:
                self.fail_count += 1
            
            return ScreenClassification(
                filename=filename,
                index=index,
                screen_type="Unknown",
                sub_type="",
                naming={"cn": "分析失败", "en": "Analysis Failed"},
                core_function={"cn": str(e), "en": "Error"},
                design_highlights=[],
                product_insight={"cn": "", "en": ""},
                tags=[],
                stage_name=current_stage.name,
                position_in_stage="unknown",
                confidence=0.0,
                reasoning="",
                ui_elements=[],
                keywords_found=[],
                error=str(e)
            )
        
        # 解析失败且重试耗尽
        with self.lock:
            self.fail_count += 1
        
        return ScreenClassification(
            filename=filename,
            index=index,
            screen_type="Unknown",
            sub_type="",
            naming={"cn": "解析失败", "en": "Parse Failed"},
            core_function={"cn": "JSON解析失败", "en": "JSON parse error"},
            design_highlights=[],
            product_insight={"cn": "", "en": ""},
            tags=[],
            stage_name=current_stage.name,
            position_in_stage="unknown",
            confidence=0.0,
            reasoning="",
            ui_elements=[],
            keywords_found=[],
            error="JSON parse error"
        )
    
    def classify_all(
        self,
        project_path: str,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        分类所有截图（并行处理）
        
        Returns:
            {filename: classification_dict}
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return {}
        
        # 获取所有截图
        screenshots = sorted([
            f for f in os.listdir(screens_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(screenshots)
        if total == 0:
            return {}
        
        print(f"  [Layer 3] Classifying {total} screenshots (concurrent: {self.concurrent})...")
        
        results = {}
        start_time = datetime.now()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交任务
            futures = {}
            for idx, filename in enumerate(screenshots, 1):
                image_path = os.path.join(screens_folder, filename)
                
                # 获取前一个结果（如果有）
                prev_result = None
                if idx > 1:
                    prev_filename = screenshots[idx - 2]
                    prev_result = results.get(prev_filename)
                
                # 获取下一个文件名
                next_filename = None
                if idx < total:
                    next_filename = screenshots[idx]
                
                future = executor.submit(
                    self.classify_single,
                    image_path,
                    idx,
                    total,
                    product_profile,
                    flow_structure,
                    prev_result,
                    next_filename
                )
                futures[future] = (filename, idx)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures):
                filename, idx = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = asdict(result)
                    
                    # 进度显示
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total - completed)
                    
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r  [{bar}] {completed}/{total} ({pct:.0%}) | {int(remaining)}s left')
                    sys.stdout.flush()
                    
                    if progress_callback:
                        progress_callback(completed, total, filename, result)
                    
                except Exception as e:
                    print(f"\n  [ERROR] {filename}: {e}")
                    results[filename] = {
                        "filename": filename,
                        "index": idx,
                        "screen_type": "Unknown",
                        "error": str(e)
                    }
        
        print()  # 换行
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  [Layer 3] Complete: {self.success_count} success, {self.fail_count} failed")
        print(f"  [Layer 3] Time: {elapsed:.1f}s ({elapsed/total:.2f}s per image)")
        
        return results
    
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


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    from layer2_structure import StructureRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 3: Context Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of screenshots to test")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    product_recognizer = ProductRecognizer()
    profile = product_recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    print(f"  Stages: {len(structure.stages)}")
    
    # Layer 3 (limited test)
    print(f"\n[Layer 3] Classification (testing {args.limit} screenshots)...")
    classifier = ContextClassifier(concurrent=2)
    
    # 只测试前几张
    screens_folder = os.path.join(project_path, "Screens")
    screenshots = sorted([
        f for f in os.listdir(screens_folder)
        if f.lower().endswith('.png')
    ])[:args.limit]
    
    for idx, filename in enumerate(screenshots, 1):
        image_path = os.path.join(screens_folder, filename)
        result = classifier.classify_single(
            image_path, idx, len(screenshots), profile, structure
        )
        print(f"\n  [{idx}] {filename}")
        print(f"      Type: {result.screen_type} ({result.sub_type})")
        print(f"      Stage: {result.stage_name}")
        print(f"      Reason: {result.reasoning}")


Layer 3: 精确分类模块
结合产品画像和流程结构，带上下文地分析每张截图
"""

import os
import sys
import json
import base64
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image
import io

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1和2
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage

# Few-shot学习
try:
    from few_shot_examples import get_onboarding_examples, get_examples_prompt
    FEWSHOT_AVAILABLE = True
except ImportError:
    FEWSHOT_AVAILABLE = False


# ============================================================
# 配置
# ============================================================

DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10

# 递进压缩配置（失败时逐级压缩）
COMPRESSION_LEVELS = [
    {"max_size": 4 * 1024 * 1024, "width": 800, "quality": 85},   # Level 0: 轻度压缩
    {"max_size": 2 * 1024 * 1024, "width": 600, "quality": 75},   # Level 1: 中度压缩
    {"max_size": 1 * 1024 * 1024, "width": 400, "quality": 65},   # Level 2: 强压缩
]

MAX_RETRIES = 3  # 最大重试次数


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ScreenClassification:
    """单张截图的分类结果"""
    filename: str
    index: int                          # 1-based索引
    screen_type: str
    sub_type: str
    
    # 双语命名
    naming: Dict[str, str]
    
    # 核心功能
    core_function: Dict[str, str]
    
    # 设计亮点
    design_highlights: List[Dict]
    
    # 产品洞察
    product_insight: Dict[str, str]
    
    # 标签
    tags: List[Dict[str, str]]
    
    # 上下文信息
    stage_name: str
    position_in_stage: str              # "early" / "middle" / "late"
    
    # 元数据
    confidence: float
    reasoning: str                       # AI的判断理由
    ui_elements: List[str]
    keywords_found: List[str]
    
    # 兼容字段
    description_cn: str = ""
    description_en: str = ""
    error: Optional[str] = None


# ============================================================
# 上下文增强提示词
# ============================================================

CONTEXT_CLASSIFICATION_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。

## 产品背景
- App名称: {app_name}
- App类型: {app_category} / {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 视觉风格: {visual_style}

## 当前截图位置
- 这是第 {position} 张截图（共 {total} 张）
- 所属阶段: {stage_name}（第 {stage_start}-{stage_end} 张）
- 阶段描述: {stage_description}
- 在阶段中的位置: {position_in_stage}

## 上下文信息
- 前一张: {prev_info}
- 后一张: {next_info}

## 阶段约束
当前处于 "{stage_name}" 阶段，该阶段通常包含以下类型：
{expected_types}

# ⭐ 核心判断原则（最重要！）

**问自己：这个页面的主要目的是「帮助用户成功使用产品」还是「向用户索取价值」？**

| 受益方 | 页面目的 | 分类方向 |
|--------|----------|----------|
| 用户 | 教会用户怎么用、收集信息以更好服务用户、获取使用所需权限 | Onboarding |
| 产品 | 付费、分享、评分、邀请好友 | Paywall/Referral |

---

## 页面类型定义

### Onboarding（用户引导）⭐ 核心类型
**定义**：帮助用户从下载到首次体验核心价值的引导流程

属于Onboarding：
- 价值展示（产品能为你做什么）
- 目标设定（你想达成什么）
- 偏好收集（你喜欢什么）
- 场景选择（你想在什么场景使用）
- 功能教学（教你怎么用）
- 情感铺垫（如深呼吸引导，为体验做心理准备）
- 权限请求（使用产品所需的系统权限）

**不属于**Onboarding：
- 付费相关 → Paywall
- 邀请好友/分享 → Referral
- 评分请求 → Other

典型特征：
- 进度指示器、Continue/Next/Skip按钮
- 无底部导航栏（还在引导流程中）
- 通常在前20张截图

### Launch（启动页）
- 显示App logo和品牌名
- 通常是第1张截图
- 页面简洁，无交互元素

### Welcome（欢迎页）
- 属于Onboarding的一部分
- 介绍产品价值主张
- 大图/插图 + 简短文字
- "Get Started"按钮

### Permission（权限请求）
- 属于Onboarding的一部分
- iOS/Android系统弹窗样式
- 请求通知/位置/健康/相机权限

### SignUp（注册登录）
- 邮箱/手机号/密码输入框
- 社交登录按钮
- 可以归入Onboarding也可独立

### Paywall（付费墙）⚠️ 不属于Onboarding
- 明确显示价格（$X.XX/月）
- 订阅套餐选项、试用期说明
- 目的是转化付费，受益方是产品

### Referral（邀请增长）⚠️ 不属于Onboarding  
- 邀请好友、分享奖励
- "Invite Friends"、"Share to get rewards"
- 目的是获客增长，受益方是产品
- 用户尚未体验价值就被要求分享

### Home（首页）
- 有底部导航栏（Tab Bar）
- App的主界面/仪表盘

### Feature（功能页）
- 有底部导航栏
- App的常规功能页面
⚠️ 没有底部导航栏且在前20张 → 很可能不是Feature

### Content（内容页）
- 音频/视频播放界面
- 文章/故事阅读界面

### Profile（个人中心）
- 用户头像、昵称、账户信息

### Settings（设置页）
- 设置选项列表、开关项

### Social（社交页）
- 好友列表、社区动态
⚠️ 注意与Referral区分：Social是功能，Referral是增长手段

### Tracking（记录页）
- 数据输入、添加记录

### Progress（进度页）
- 图表、统计、成就

### Other（其他）
- 不属于以上任何类型

---

## 分类决策流程

```
1. 先问：受益方是谁？
   - 向用户索取（付费/分享/评分）→ Paywall/Referral/Other
   - 帮助用户 → 继续判断

2. 再问：有底部导航栏吗？
   - 有 → Home/Feature/Content/Profile/Settings/Tracking/Progress
   - 无 → 继续判断

3. 最后问：在前20张吗？
   - 是 → Launch/Welcome/Onboarding/Permission/SignUp
   - 否 → Feature/Content/Other
```

## 设计亮点分类
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 输出要求
请严格按以下JSON格式输出：

```json
{{
  "screen_type": "类型名",
  "sub_type": "子类型（如goal_selection, breathing_guide等）",
  "naming": {{
    "cn": "页面中文名（2-6字）",
    "en": "Page Name (2-4 words)"
  }},
  "core_function": {{
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  }},
  "design_highlights": [
    {{"category": "visual", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "interaction", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "emotional", "cn": "亮点描述", "en": "Highlight"}}
  ],
  "product_insight": {{
    "cn": "产品洞察（30-60字）",
    "en": "Product insight (15-40 words)"
  }},
  "tags": [
    {{"cn": "标签1", "en": "Tag1"}},
    {{"cn": "标签2", "en": "Tag2"}}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95,
  "reasoning": "简短说明为什么判断为这个类型（考虑位置和上下文）"
}}
```

只输出JSON，不要有任何解释文字。"""


class ContextClassifier:
    """上下文感知分类器 - Layer 3"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5
    ):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        self.client = None
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
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
    
    def _compress_image(self, image_path: str, compression_level: int = 0) -> Tuple[str, str]:
        """
        压缩图片并返回base64和媒体类型
        
        Args:
            image_path: 图片路径
            compression_level: 压缩等级 (0=轻度, 1=中度, 2=强压缩)
        """
        try:
            # 获取压缩配置
            level = min(compression_level, len(COMPRESSION_LEVELS) - 1)
            config = COMPRESSION_LEVELS[level]
            max_size = config["max_size"]
            target_width = config["width"]
            quality = config["quality"]
            
            file_size = os.path.getsize(image_path)
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 如果文件太大或指定了压缩等级，进行压缩
            if file_size > max_size or compression_level > 0:
                img = Image.open(io.BytesIO(image_data))
                
                # 缩小
                if img.width > target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # 转RGB
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality, optimize=True)
                img.close()
                
                compressed_size = buffer.tell()
                if compression_level > 0:
                    print(f"    [COMPRESS L{level}] {file_size//1024}KB -> {compressed_size//1024}KB")
                
                return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
            
            # 不需要压缩，直接返回
            ext = os.path.splitext(image_path)[1].lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/png")
            
            return base64.standard_b64encode(image_data).decode('utf-8'), media_type
            
        except Exception as e:
            raise Exception(f"Image processing error: {e}")
    
    def _get_position_in_stage(self, index: int, stage: FlowStage) -> str:
        """计算在阶段中的位置"""
        stage_length = stage.end_index - stage.start_index + 1
        position_in_stage = index - stage.start_index + 1
        
        if stage_length <= 2:
            return "single"
        
        ratio = position_in_stage / stage_length
        if ratio <= 0.33:
            return "early (阶段开始)"
        elif ratio <= 0.66:
            return "middle (阶段中部)"
        else:
            return "late (阶段结束)"
    
    def classify_single(
        self,
        image_path: str,
        index: int,
        total: int,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        prev_result: Optional[Dict] = None,
        next_filename: Optional[str] = None,
        retry_count: int = 0
    ) -> ScreenClassification:
        """
        分类单张截图（带上下文，自动重试）
        
        Args:
            retry_count: 当前重试次数，用于递进压缩
        """
        filename = os.path.basename(image_path)
        
        # 找到当前所属阶段
        current_stage = None
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                current_stage = stage
                break
        
        if not current_stage:
            current_stage = FlowStage(
                name="Unknown",
                start_index=1,
                end_index=total,
                description="未识别阶段",
                expected_types=["Feature"],
                screenshot_count=total
            )
        
        # 构建上下文信息
        prev_info = "无（这是第一张）"
        if prev_result:
            prev_info = f"{prev_result.get('screen_type', 'Unknown')} - {prev_result.get('naming', {}).get('cn', '')}"
        
        next_info = "无（这是最后一张）"
        if next_filename:
            next_info = f"待分析: {next_filename}"
        
        position_in_stage = self._get_position_in_stage(index, current_stage)
        expected_types_str = "\n".join([f"  - {t}" for t in current_stage.expected_types])
        
        # 构建提示词
        prompt = CONTEXT_CLASSIFICATION_PROMPT.format(
            app_name=product_profile.app_name,
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            visual_style=product_profile.visual_style,
            position=index,
            total=total,
            stage_name=current_stage.name,
            stage_start=current_stage.start_index,
            stage_end=current_stage.end_index,
            stage_description=current_stage.description,
            position_in_stage=position_in_stage,
            prev_info=prev_info,
            next_info=next_info,
            expected_types=expected_types_str
        )
        
        # 添加Few-shot示例（从其他产品学习）
        if FEWSHOT_AVAILABLE and index <= 30:  # 前30张最容易混淆，添加示例
            project_name = os.path.basename(os.path.dirname(image_path))
            few_shot = get_onboarding_examples(exclude_product=project_name)
            if few_shot:
                prompt = few_shot + "\n" + prompt
        
        # 调用API（带自动重试和递进压缩）
        try:
            # 根据重试次数决定压缩等级
            compression_level = retry_count
            image_base64, media_type = self._compress_image(image_path, compression_level)
            
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
                                "data": image_base64
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
                with self.lock:
                    self.success_count += 1
                
                return ScreenClassification(
                    filename=filename,
                    index=index,
                    screen_type=parsed.get("screen_type", "Unknown"),
                    sub_type=parsed.get("sub_type", ""),
                    naming=parsed.get("naming", {"cn": "", "en": ""}),
                    core_function=parsed.get("core_function", {"cn": "", "en": ""}),
                    design_highlights=parsed.get("design_highlights", []),
                    product_insight=parsed.get("product_insight", {"cn": "", "en": ""}),
                    tags=parsed.get("tags", []),
                    stage_name=current_stage.name,
                    position_in_stage=position_in_stage.split(" ")[0],
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", ""),
                    ui_elements=parsed.get("ui_elements", []),
                    keywords_found=parsed.get("keywords_found", []),
                    description_cn=parsed.get("core_function", {}).get("cn", ""),
                    description_en=parsed.get("core_function", {}).get("en", "")
                )
            else:
                # JSON解析失败，重试
                if retry_count < MAX_RETRIES:
                    time.sleep(1)
                    return self.classify_single(
                        image_path, index, total, product_profile, flow_structure,
                        prev_result, next_filename, retry_count + 1
                    )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检查是否是图片大小/格式相关的错误，自动重试
            is_image_error = any(x in error_str for x in [
                'image', 'size', 'too large', 'invalid_request', '400', 'base64'
            ])
            
            if is_image_error and retry_count < MAX_RETRIES:
                # 使用更强的压缩重试
                time.sleep(1)
                return self.classify_single(
                    image_path, index, total, product_profile, flow_structure,
                    prev_result, next_filename, retry_count + 1
                )
            
            with self.lock:
                self.fail_count += 1
            
            return ScreenClassification(
                filename=filename,
                index=index,
                screen_type="Unknown",
                sub_type="",
                naming={"cn": "分析失败", "en": "Analysis Failed"},
                core_function={"cn": str(e), "en": "Error"},
                design_highlights=[],
                product_insight={"cn": "", "en": ""},
                tags=[],
                stage_name=current_stage.name,
                position_in_stage="unknown",
                confidence=0.0,
                reasoning="",
                ui_elements=[],
                keywords_found=[],
                error=str(e)
            )
        
        # 解析失败且重试耗尽
        with self.lock:
            self.fail_count += 1
        
        return ScreenClassification(
            filename=filename,
            index=index,
            screen_type="Unknown",
            sub_type="",
            naming={"cn": "解析失败", "en": "Parse Failed"},
            core_function={"cn": "JSON解析失败", "en": "JSON parse error"},
            design_highlights=[],
            product_insight={"cn": "", "en": ""},
            tags=[],
            stage_name=current_stage.name,
            position_in_stage="unknown",
            confidence=0.0,
            reasoning="",
            ui_elements=[],
            keywords_found=[],
            error="JSON parse error"
        )
    
    def classify_all(
        self,
        project_path: str,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        分类所有截图（并行处理）
        
        Returns:
            {filename: classification_dict}
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return {}
        
        # 获取所有截图
        screenshots = sorted([
            f for f in os.listdir(screens_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(screenshots)
        if total == 0:
            return {}
        
        print(f"  [Layer 3] Classifying {total} screenshots (concurrent: {self.concurrent})...")
        
        results = {}
        start_time = datetime.now()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交任务
            futures = {}
            for idx, filename in enumerate(screenshots, 1):
                image_path = os.path.join(screens_folder, filename)
                
                # 获取前一个结果（如果有）
                prev_result = None
                if idx > 1:
                    prev_filename = screenshots[idx - 2]
                    prev_result = results.get(prev_filename)
                
                # 获取下一个文件名
                next_filename = None
                if idx < total:
                    next_filename = screenshots[idx]
                
                future = executor.submit(
                    self.classify_single,
                    image_path,
                    idx,
                    total,
                    product_profile,
                    flow_structure,
                    prev_result,
                    next_filename
                )
                futures[future] = (filename, idx)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures):
                filename, idx = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = asdict(result)
                    
                    # 进度显示
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total - completed)
                    
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r  [{bar}] {completed}/{total} ({pct:.0%}) | {int(remaining)}s left')
                    sys.stdout.flush()
                    
                    if progress_callback:
                        progress_callback(completed, total, filename, result)
                    
                except Exception as e:
                    print(f"\n  [ERROR] {filename}: {e}")
                    results[filename] = {
                        "filename": filename,
                        "index": idx,
                        "screen_type": "Unknown",
                        "error": str(e)
                    }
        
        print()  # 换行
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  [Layer 3] Complete: {self.success_count} success, {self.fail_count} failed")
        print(f"  [Layer 3] Time: {elapsed:.1f}s ({elapsed/total:.2f}s per image)")
        
        return results
    
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


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    from layer2_structure import StructureRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 3: Context Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of screenshots to test")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    product_recognizer = ProductRecognizer()
    profile = product_recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    print(f"  Stages: {len(structure.stages)}")
    
    # Layer 3 (limited test)
    print(f"\n[Layer 3] Classification (testing {args.limit} screenshots)...")
    classifier = ContextClassifier(concurrent=2)
    
    # 只测试前几张
    screens_folder = os.path.join(project_path, "Screens")
    screenshots = sorted([
        f for f in os.listdir(screens_folder)
        if f.lower().endswith('.png')
    ])[:args.limit]
    
    for idx, filename in enumerate(screenshots, 1):
        image_path = os.path.join(screens_folder, filename)
        result = classifier.classify_single(
            image_path, idx, len(screenshots), profile, structure
        )
        print(f"\n  [{idx}] {filename}")
        print(f"      Type: {result.screen_type} ({result.sub_type})")
        print(f"      Stage: {result.stage_name}")
        print(f"      Reason: {result.reasoning}")


Layer 3: 精确分类模块
结合产品画像和流程结构，带上下文地分析每张截图
"""

import os
import sys
import json
import base64
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image
import io

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1和2
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage

# Few-shot学习
try:
    from few_shot_examples import get_onboarding_examples, get_examples_prompt
    FEWSHOT_AVAILABLE = True
except ImportError:
    FEWSHOT_AVAILABLE = False


# ============================================================
# 配置
# ============================================================

DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10

# 递进压缩配置（失败时逐级压缩）
COMPRESSION_LEVELS = [
    {"max_size": 4 * 1024 * 1024, "width": 800, "quality": 85},   # Level 0: 轻度压缩
    {"max_size": 2 * 1024 * 1024, "width": 600, "quality": 75},   # Level 1: 中度压缩
    {"max_size": 1 * 1024 * 1024, "width": 400, "quality": 65},   # Level 2: 强压缩
]

MAX_RETRIES = 3  # 最大重试次数


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ScreenClassification:
    """单张截图的分类结果"""
    filename: str
    index: int                          # 1-based索引
    screen_type: str
    sub_type: str
    
    # 双语命名
    naming: Dict[str, str]
    
    # 核心功能
    core_function: Dict[str, str]
    
    # 设计亮点
    design_highlights: List[Dict]
    
    # 产品洞察
    product_insight: Dict[str, str]
    
    # 标签
    tags: List[Dict[str, str]]
    
    # 上下文信息
    stage_name: str
    position_in_stage: str              # "early" / "middle" / "late"
    
    # 元数据
    confidence: float
    reasoning: str                       # AI的判断理由
    ui_elements: List[str]
    keywords_found: List[str]
    
    # 兼容字段
    description_cn: str = ""
    description_en: str = ""
    error: Optional[str] = None


# ============================================================
# 上下文增强提示词
# ============================================================

CONTEXT_CLASSIFICATION_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。

## 产品背景
- App名称: {app_name}
- App类型: {app_category} / {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 视觉风格: {visual_style}

## 当前截图位置
- 这是第 {position} 张截图（共 {total} 张）
- 所属阶段: {stage_name}（第 {stage_start}-{stage_end} 张）
- 阶段描述: {stage_description}
- 在阶段中的位置: {position_in_stage}

## 上下文信息
- 前一张: {prev_info}
- 后一张: {next_info}

## 阶段约束
当前处于 "{stage_name}" 阶段，该阶段通常包含以下类型：
{expected_types}

# ⭐ 核心判断原则（最重要！）

**问自己：这个页面的主要目的是「帮助用户成功使用产品」还是「向用户索取价值」？**

| 受益方 | 页面目的 | 分类方向 |
|--------|----------|----------|
| 用户 | 教会用户怎么用、收集信息以更好服务用户、获取使用所需权限 | Onboarding |
| 产品 | 付费、分享、评分、邀请好友 | Paywall/Referral |

---

## 页面类型定义

### Onboarding（用户引导）⭐ 核心类型
**定义**：帮助用户从下载到首次体验核心价值的引导流程

属于Onboarding：
- 价值展示（产品能为你做什么）
- 目标设定（你想达成什么）
- 偏好收集（你喜欢什么）
- 场景选择（你想在什么场景使用）
- 功能教学（教你怎么用）
- 情感铺垫（如深呼吸引导，为体验做心理准备）
- 权限请求（使用产品所需的系统权限）

**不属于**Onboarding：
- 付费相关 → Paywall
- 邀请好友/分享 → Referral
- 评分请求 → Other

典型特征：
- 进度指示器、Continue/Next/Skip按钮
- 无底部导航栏（还在引导流程中）
- 通常在前20张截图

### Launch（启动页）
- 显示App logo和品牌名
- 通常是第1张截图
- 页面简洁，无交互元素

### Welcome（欢迎页）
- 属于Onboarding的一部分
- 介绍产品价值主张
- 大图/插图 + 简短文字
- "Get Started"按钮

### Permission（权限请求）
- 属于Onboarding的一部分
- iOS/Android系统弹窗样式
- 请求通知/位置/健康/相机权限

### SignUp（注册登录）
- 邮箱/手机号/密码输入框
- 社交登录按钮
- 可以归入Onboarding也可独立

### Paywall（付费墙）⚠️ 不属于Onboarding
- 明确显示价格（$X.XX/月）
- 订阅套餐选项、试用期说明
- 目的是转化付费，受益方是产品

### Referral（邀请增长）⚠️ 不属于Onboarding  
- 邀请好友、分享奖励
- "Invite Friends"、"Share to get rewards"
- 目的是获客增长，受益方是产品
- 用户尚未体验价值就被要求分享

### Home（首页）
- 有底部导航栏（Tab Bar）
- App的主界面/仪表盘

### Feature（功能页）
- 有底部导航栏
- App的常规功能页面
⚠️ 没有底部导航栏且在前20张 → 很可能不是Feature

### Content（内容页）
- 音频/视频播放界面
- 文章/故事阅读界面

### Profile（个人中心）
- 用户头像、昵称、账户信息

### Settings（设置页）
- 设置选项列表、开关项

### Social（社交页）
- 好友列表、社区动态
⚠️ 注意与Referral区分：Social是功能，Referral是增长手段

### Tracking（记录页）
- 数据输入、添加记录

### Progress（进度页）
- 图表、统计、成就

### Other（其他）
- 不属于以上任何类型

---

## 分类决策流程

```
1. 先问：受益方是谁？
   - 向用户索取（付费/分享/评分）→ Paywall/Referral/Other
   - 帮助用户 → 继续判断

2. 再问：有底部导航栏吗？
   - 有 → Home/Feature/Content/Profile/Settings/Tracking/Progress
   - 无 → 继续判断

3. 最后问：在前20张吗？
   - 是 → Launch/Welcome/Onboarding/Permission/SignUp
   - 否 → Feature/Content/Other
```

## 设计亮点分类
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 输出要求
请严格按以下JSON格式输出：

```json
{{
  "screen_type": "类型名",
  "sub_type": "子类型（如goal_selection, breathing_guide等）",
  "naming": {{
    "cn": "页面中文名（2-6字）",
    "en": "Page Name (2-4 words)"
  }},
  "core_function": {{
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  }},
  "design_highlights": [
    {{"category": "visual", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "interaction", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "emotional", "cn": "亮点描述", "en": "Highlight"}}
  ],
  "product_insight": {{
    "cn": "产品洞察（30-60字）",
    "en": "Product insight (15-40 words)"
  }},
  "tags": [
    {{"cn": "标签1", "en": "Tag1"}},
    {{"cn": "标签2", "en": "Tag2"}}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95,
  "reasoning": "简短说明为什么判断为这个类型（考虑位置和上下文）"
}}
```

只输出JSON，不要有任何解释文字。"""


class ContextClassifier:
    """上下文感知分类器 - Layer 3"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5
    ):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        self.client = None
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
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
    
    def _compress_image(self, image_path: str, compression_level: int = 0) -> Tuple[str, str]:
        """
        压缩图片并返回base64和媒体类型
        
        Args:
            image_path: 图片路径
            compression_level: 压缩等级 (0=轻度, 1=中度, 2=强压缩)
        """
        try:
            # 获取压缩配置
            level = min(compression_level, len(COMPRESSION_LEVELS) - 1)
            config = COMPRESSION_LEVELS[level]
            max_size = config["max_size"]
            target_width = config["width"]
            quality = config["quality"]
            
            file_size = os.path.getsize(image_path)
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 如果文件太大或指定了压缩等级，进行压缩
            if file_size > max_size or compression_level > 0:
                img = Image.open(io.BytesIO(image_data))
                
                # 缩小
                if img.width > target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # 转RGB
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality, optimize=True)
                img.close()
                
                compressed_size = buffer.tell()
                if compression_level > 0:
                    print(f"    [COMPRESS L{level}] {file_size//1024}KB -> {compressed_size//1024}KB")
                
                return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
            
            # 不需要压缩，直接返回
            ext = os.path.splitext(image_path)[1].lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/png")
            
            return base64.standard_b64encode(image_data).decode('utf-8'), media_type
            
        except Exception as e:
            raise Exception(f"Image processing error: {e}")
    
    def _get_position_in_stage(self, index: int, stage: FlowStage) -> str:
        """计算在阶段中的位置"""
        stage_length = stage.end_index - stage.start_index + 1
        position_in_stage = index - stage.start_index + 1
        
        if stage_length <= 2:
            return "single"
        
        ratio = position_in_stage / stage_length
        if ratio <= 0.33:
            return "early (阶段开始)"
        elif ratio <= 0.66:
            return "middle (阶段中部)"
        else:
            return "late (阶段结束)"
    
    def classify_single(
        self,
        image_path: str,
        index: int,
        total: int,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        prev_result: Optional[Dict] = None,
        next_filename: Optional[str] = None,
        retry_count: int = 0
    ) -> ScreenClassification:
        """
        分类单张截图（带上下文，自动重试）
        
        Args:
            retry_count: 当前重试次数，用于递进压缩
        """
        filename = os.path.basename(image_path)
        
        # 找到当前所属阶段
        current_stage = None
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                current_stage = stage
                break
        
        if not current_stage:
            current_stage = FlowStage(
                name="Unknown",
                start_index=1,
                end_index=total,
                description="未识别阶段",
                expected_types=["Feature"],
                screenshot_count=total
            )
        
        # 构建上下文信息
        prev_info = "无（这是第一张）"
        if prev_result:
            prev_info = f"{prev_result.get('screen_type', 'Unknown')} - {prev_result.get('naming', {}).get('cn', '')}"
        
        next_info = "无（这是最后一张）"
        if next_filename:
            next_info = f"待分析: {next_filename}"
        
        position_in_stage = self._get_position_in_stage(index, current_stage)
        expected_types_str = "\n".join([f"  - {t}" for t in current_stage.expected_types])
        
        # 构建提示词
        prompt = CONTEXT_CLASSIFICATION_PROMPT.format(
            app_name=product_profile.app_name,
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            visual_style=product_profile.visual_style,
            position=index,
            total=total,
            stage_name=current_stage.name,
            stage_start=current_stage.start_index,
            stage_end=current_stage.end_index,
            stage_description=current_stage.description,
            position_in_stage=position_in_stage,
            prev_info=prev_info,
            next_info=next_info,
            expected_types=expected_types_str
        )
        
        # 添加Few-shot示例（从其他产品学习）
        if FEWSHOT_AVAILABLE and index <= 30:  # 前30张最容易混淆，添加示例
            project_name = os.path.basename(os.path.dirname(image_path))
            few_shot = get_onboarding_examples(exclude_product=project_name)
            if few_shot:
                prompt = few_shot + "\n" + prompt
        
        # 调用API（带自动重试和递进压缩）
        try:
            # 根据重试次数决定压缩等级
            compression_level = retry_count
            image_base64, media_type = self._compress_image(image_path, compression_level)
            
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
                                "data": image_base64
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
                with self.lock:
                    self.success_count += 1
                
                return ScreenClassification(
                    filename=filename,
                    index=index,
                    screen_type=parsed.get("screen_type", "Unknown"),
                    sub_type=parsed.get("sub_type", ""),
                    naming=parsed.get("naming", {"cn": "", "en": ""}),
                    core_function=parsed.get("core_function", {"cn": "", "en": ""}),
                    design_highlights=parsed.get("design_highlights", []),
                    product_insight=parsed.get("product_insight", {"cn": "", "en": ""}),
                    tags=parsed.get("tags", []),
                    stage_name=current_stage.name,
                    position_in_stage=position_in_stage.split(" ")[0],
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", ""),
                    ui_elements=parsed.get("ui_elements", []),
                    keywords_found=parsed.get("keywords_found", []),
                    description_cn=parsed.get("core_function", {}).get("cn", ""),
                    description_en=parsed.get("core_function", {}).get("en", "")
                )
            else:
                # JSON解析失败，重试
                if retry_count < MAX_RETRIES:
                    time.sleep(1)
                    return self.classify_single(
                        image_path, index, total, product_profile, flow_structure,
                        prev_result, next_filename, retry_count + 1
                    )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检查是否是图片大小/格式相关的错误，自动重试
            is_image_error = any(x in error_str for x in [
                'image', 'size', 'too large', 'invalid_request', '400', 'base64'
            ])
            
            if is_image_error and retry_count < MAX_RETRIES:
                # 使用更强的压缩重试
                time.sleep(1)
                return self.classify_single(
                    image_path, index, total, product_profile, flow_structure,
                    prev_result, next_filename, retry_count + 1
                )
            
            with self.lock:
                self.fail_count += 1
            
            return ScreenClassification(
                filename=filename,
                index=index,
                screen_type="Unknown",
                sub_type="",
                naming={"cn": "分析失败", "en": "Analysis Failed"},
                core_function={"cn": str(e), "en": "Error"},
                design_highlights=[],
                product_insight={"cn": "", "en": ""},
                tags=[],
                stage_name=current_stage.name,
                position_in_stage="unknown",
                confidence=0.0,
                reasoning="",
                ui_elements=[],
                keywords_found=[],
                error=str(e)
            )
        
        # 解析失败且重试耗尽
        with self.lock:
            self.fail_count += 1
        
        return ScreenClassification(
            filename=filename,
            index=index,
            screen_type="Unknown",
            sub_type="",
            naming={"cn": "解析失败", "en": "Parse Failed"},
            core_function={"cn": "JSON解析失败", "en": "JSON parse error"},
            design_highlights=[],
            product_insight={"cn": "", "en": ""},
            tags=[],
            stage_name=current_stage.name,
            position_in_stage="unknown",
            confidence=0.0,
            reasoning="",
            ui_elements=[],
            keywords_found=[],
            error="JSON parse error"
        )
    
    def classify_all(
        self,
        project_path: str,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        分类所有截图（并行处理）
        
        Returns:
            {filename: classification_dict}
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return {}
        
        # 获取所有截图
        screenshots = sorted([
            f for f in os.listdir(screens_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(screenshots)
        if total == 0:
            return {}
        
        print(f"  [Layer 3] Classifying {total} screenshots (concurrent: {self.concurrent})...")
        
        results = {}
        start_time = datetime.now()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交任务
            futures = {}
            for idx, filename in enumerate(screenshots, 1):
                image_path = os.path.join(screens_folder, filename)
                
                # 获取前一个结果（如果有）
                prev_result = None
                if idx > 1:
                    prev_filename = screenshots[idx - 2]
                    prev_result = results.get(prev_filename)
                
                # 获取下一个文件名
                next_filename = None
                if idx < total:
                    next_filename = screenshots[idx]
                
                future = executor.submit(
                    self.classify_single,
                    image_path,
                    idx,
                    total,
                    product_profile,
                    flow_structure,
                    prev_result,
                    next_filename
                )
                futures[future] = (filename, idx)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures):
                filename, idx = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = asdict(result)
                    
                    # 进度显示
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total - completed)
                    
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r  [{bar}] {completed}/{total} ({pct:.0%}) | {int(remaining)}s left')
                    sys.stdout.flush()
                    
                    if progress_callback:
                        progress_callback(completed, total, filename, result)
                    
                except Exception as e:
                    print(f"\n  [ERROR] {filename}: {e}")
                    results[filename] = {
                        "filename": filename,
                        "index": idx,
                        "screen_type": "Unknown",
                        "error": str(e)
                    }
        
        print()  # 换行
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  [Layer 3] Complete: {self.success_count} success, {self.fail_count} failed")
        print(f"  [Layer 3] Time: {elapsed:.1f}s ({elapsed/total:.2f}s per image)")
        
        return results
    
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


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    from layer2_structure import StructureRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 3: Context Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of screenshots to test")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    product_recognizer = ProductRecognizer()
    profile = product_recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    print(f"  Stages: {len(structure.stages)}")
    
    # Layer 3 (limited test)
    print(f"\n[Layer 3] Classification (testing {args.limit} screenshots)...")
    classifier = ContextClassifier(concurrent=2)
    
    # 只测试前几张
    screens_folder = os.path.join(project_path, "Screens")
    screenshots = sorted([
        f for f in os.listdir(screens_folder)
        if f.lower().endswith('.png')
    ])[:args.limit]
    
    for idx, filename in enumerate(screenshots, 1):
        image_path = os.path.join(screens_folder, filename)
        result = classifier.classify_single(
            image_path, idx, len(screenshots), profile, structure
        )
        print(f"\n  [{idx}] {filename}")
        print(f"      Type: {result.screen_type} ({result.sub_type})")
        print(f"      Stage: {result.stage_name}")
        print(f"      Reason: {result.reasoning}")


Layer 3: 精确分类模块
结合产品画像和流程结构，带上下文地分析每张截图
"""

import os
import sys
import json
import base64
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image
import io

# API相关
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# 导入Layer 1和2
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage

# Few-shot学习
try:
    from few_shot_examples import get_onboarding_examples, get_examples_prompt
    FEWSHOT_AVAILABLE = True
except ImportError:
    FEWSHOT_AVAILABLE = False


# ============================================================
# 配置
# ============================================================

DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10

# 递进压缩配置（失败时逐级压缩）
COMPRESSION_LEVELS = [
    {"max_size": 4 * 1024 * 1024, "width": 800, "quality": 85},   # Level 0: 轻度压缩
    {"max_size": 2 * 1024 * 1024, "width": 600, "quality": 75},   # Level 1: 中度压缩
    {"max_size": 1 * 1024 * 1024, "width": 400, "quality": 65},   # Level 2: 强压缩
]

MAX_RETRIES = 3  # 最大重试次数


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ScreenClassification:
    """单张截图的分类结果"""
    filename: str
    index: int                          # 1-based索引
    screen_type: str
    sub_type: str
    
    # 双语命名
    naming: Dict[str, str]
    
    # 核心功能
    core_function: Dict[str, str]
    
    # 设计亮点
    design_highlights: List[Dict]
    
    # 产品洞察
    product_insight: Dict[str, str]
    
    # 标签
    tags: List[Dict[str, str]]
    
    # 上下文信息
    stage_name: str
    position_in_stage: str              # "early" / "middle" / "late"
    
    # 元数据
    confidence: float
    reasoning: str                       # AI的判断理由
    ui_elements: List[str]
    keywords_found: List[str]
    
    # 兼容字段
    description_cn: str = ""
    description_en: str = ""
    error: Optional[str] = None


# ============================================================
# 上下文增强提示词
# ============================================================

CONTEXT_CLASSIFICATION_PROMPT = """你是一位资深产品经理和UX专家，正在分析移动App截图。

## 产品背景
- App名称: {app_name}
- App类型: {app_category} / {sub_category}
- 目标用户: {target_users}
- 核心价值: {core_value}
- 视觉风格: {visual_style}

## 当前截图位置
- 这是第 {position} 张截图（共 {total} 张）
- 所属阶段: {stage_name}（第 {stage_start}-{stage_end} 张）
- 阶段描述: {stage_description}
- 在阶段中的位置: {position_in_stage}

## 上下文信息
- 前一张: {prev_info}
- 后一张: {next_info}

## 阶段约束
当前处于 "{stage_name}" 阶段，该阶段通常包含以下类型：
{expected_types}

# ⭐ 核心判断原则（最重要！）

**问自己：这个页面的主要目的是「帮助用户成功使用产品」还是「向用户索取价值」？**

| 受益方 | 页面目的 | 分类方向 |
|--------|----------|----------|
| 用户 | 教会用户怎么用、收集信息以更好服务用户、获取使用所需权限 | Onboarding |
| 产品 | 付费、分享、评分、邀请好友 | Paywall/Referral |

---

## 页面类型定义

### Onboarding（用户引导）⭐ 核心类型
**定义**：帮助用户从下载到首次体验核心价值的引导流程

属于Onboarding：
- 价值展示（产品能为你做什么）
- 目标设定（你想达成什么）
- 偏好收集（你喜欢什么）
- 场景选择（你想在什么场景使用）
- 功能教学（教你怎么用）
- 情感铺垫（如深呼吸引导，为体验做心理准备）
- 权限请求（使用产品所需的系统权限）

**不属于**Onboarding：
- 付费相关 → Paywall
- 邀请好友/分享 → Referral
- 评分请求 → Other

典型特征：
- 进度指示器、Continue/Next/Skip按钮
- 无底部导航栏（还在引导流程中）
- 通常在前20张截图

### Launch（启动页）
- 显示App logo和品牌名
- 通常是第1张截图
- 页面简洁，无交互元素

### Welcome（欢迎页）
- 属于Onboarding的一部分
- 介绍产品价值主张
- 大图/插图 + 简短文字
- "Get Started"按钮

### Permission（权限请求）
- 属于Onboarding的一部分
- iOS/Android系统弹窗样式
- 请求通知/位置/健康/相机权限

### SignUp（注册登录）
- 邮箱/手机号/密码输入框
- 社交登录按钮
- 可以归入Onboarding也可独立

### Paywall（付费墙）⚠️ 不属于Onboarding
- 明确显示价格（$X.XX/月）
- 订阅套餐选项、试用期说明
- 目的是转化付费，受益方是产品

### Referral（邀请增长）⚠️ 不属于Onboarding  
- 邀请好友、分享奖励
- "Invite Friends"、"Share to get rewards"
- 目的是获客增长，受益方是产品
- 用户尚未体验价值就被要求分享

### Home（首页）
- 有底部导航栏（Tab Bar）
- App的主界面/仪表盘

### Feature（功能页）
- 有底部导航栏
- App的常规功能页面
⚠️ 没有底部导航栏且在前20张 → 很可能不是Feature

### Content（内容页）
- 音频/视频播放界面
- 文章/故事阅读界面

### Profile（个人中心）
- 用户头像、昵称、账户信息

### Settings（设置页）
- 设置选项列表、开关项

### Social（社交页）
- 好友列表、社区动态
⚠️ 注意与Referral区分：Social是功能，Referral是增长手段

### Tracking（记录页）
- 数据输入、添加记录

### Progress（进度页）
- 图表、统计、成就

### Other（其他）
- 不属于以上任何类型

---

## 分类决策流程

```
1. 先问：受益方是谁？
   - 向用户索取（付费/分享/评分）→ Paywall/Referral/Other
   - 帮助用户 → 继续判断

2. 再问：有底部导航栏吗？
   - 有 → Home/Feature/Content/Profile/Settings/Tracking/Progress
   - 无 → 继续判断

3. 最后问：在前20张吗？
   - 是 → Launch/Welcome/Onboarding/Permission/SignUp
   - 否 → Feature/Content/Other
```

## 设计亮点分类
- visual: 视觉设计（配色、排版、图标、插图）
- interaction: 交互设计（操作流程、反馈、手势）
- conversion: 转化策略（促销、引导、CTA）
- emotional: 情感化设计（文案、氛围、激励）

## 输出要求
请严格按以下JSON格式输出：

```json
{{
  "screen_type": "类型名",
  "sub_type": "子类型（如goal_selection, breathing_guide等）",
  "naming": {{
    "cn": "页面中文名（2-6字）",
    "en": "Page Name (2-4 words)"
  }},
  "core_function": {{
    "cn": "核心功能描述（10-20字）",
    "en": "Core function (5-15 words)"
  }},
  "design_highlights": [
    {{"category": "visual", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "interaction", "cn": "亮点描述", "en": "Highlight"}},
    {{"category": "emotional", "cn": "亮点描述", "en": "Highlight"}}
  ],
  "product_insight": {{
    "cn": "产品洞察（30-60字）",
    "en": "Product insight (15-40 words)"
  }},
  "tags": [
    {{"cn": "标签1", "en": "Tag1"}},
    {{"cn": "标签2", "en": "Tag2"}}
  ],
  "ui_elements": ["element1", "element2"],
  "keywords_found": ["keyword1", "keyword2"],
  "confidence": 0.95,
  "reasoning": "简短说明为什么判断为这个类型（考虑位置和上下文）"
}}
```

只输出JSON，不要有任何解释文字。"""


class ContextClassifier:
    """上下文感知分类器 - Layer 3"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5
    ):
        self.api_key = api_key or self._load_api_key()
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        self.client = None
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
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
    
    def _compress_image(self, image_path: str, compression_level: int = 0) -> Tuple[str, str]:
        """
        压缩图片并返回base64和媒体类型
        
        Args:
            image_path: 图片路径
            compression_level: 压缩等级 (0=轻度, 1=中度, 2=强压缩)
        """
        try:
            # 获取压缩配置
            level = min(compression_level, len(COMPRESSION_LEVELS) - 1)
            config = COMPRESSION_LEVELS[level]
            max_size = config["max_size"]
            target_width = config["width"]
            quality = config["quality"]
            
            file_size = os.path.getsize(image_path)
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            # 如果文件太大或指定了压缩等级，进行压缩
            if file_size > max_size or compression_level > 0:
                img = Image.open(io.BytesIO(image_data))
                
                # 缩小
                if img.width > target_width:
                    ratio = target_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                
                # 转RGB
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # 压缩为JPEG
                buffer = io.BytesIO()
                img.save(buffer, 'JPEG', quality=quality, optimize=True)
                img.close()
                
                compressed_size = buffer.tell()
                if compression_level > 0:
                    print(f"    [COMPRESS L{level}] {file_size//1024}KB -> {compressed_size//1024}KB")
                
                return base64.standard_b64encode(buffer.getvalue()).decode('utf-8'), "image/jpeg"
            
            # 不需要压缩，直接返回
            ext = os.path.splitext(image_path)[1].lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }
            media_type = media_types.get(ext, "image/png")
            
            return base64.standard_b64encode(image_data).decode('utf-8'), media_type
            
        except Exception as e:
            raise Exception(f"Image processing error: {e}")
    
    def _get_position_in_stage(self, index: int, stage: FlowStage) -> str:
        """计算在阶段中的位置"""
        stage_length = stage.end_index - stage.start_index + 1
        position_in_stage = index - stage.start_index + 1
        
        if stage_length <= 2:
            return "single"
        
        ratio = position_in_stage / stage_length
        if ratio <= 0.33:
            return "early (阶段开始)"
        elif ratio <= 0.66:
            return "middle (阶段中部)"
        else:
            return "late (阶段结束)"
    
    def classify_single(
        self,
        image_path: str,
        index: int,
        total: int,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        prev_result: Optional[Dict] = None,
        next_filename: Optional[str] = None,
        retry_count: int = 0
    ) -> ScreenClassification:
        """
        分类单张截图（带上下文，自动重试）
        
        Args:
            retry_count: 当前重试次数，用于递进压缩
        """
        filename = os.path.basename(image_path)
        
        # 找到当前所属阶段
        current_stage = None
        for stage in flow_structure.stages:
            if stage.start_index <= index <= stage.end_index:
                current_stage = stage
                break
        
        if not current_stage:
            current_stage = FlowStage(
                name="Unknown",
                start_index=1,
                end_index=total,
                description="未识别阶段",
                expected_types=["Feature"],
                screenshot_count=total
            )
        
        # 构建上下文信息
        prev_info = "无（这是第一张）"
        if prev_result:
            prev_info = f"{prev_result.get('screen_type', 'Unknown')} - {prev_result.get('naming', {}).get('cn', '')}"
        
        next_info = "无（这是最后一张）"
        if next_filename:
            next_info = f"待分析: {next_filename}"
        
        position_in_stage = self._get_position_in_stage(index, current_stage)
        expected_types_str = "\n".join([f"  - {t}" for t in current_stage.expected_types])
        
        # 构建提示词
        prompt = CONTEXT_CLASSIFICATION_PROMPT.format(
            app_name=product_profile.app_name,
            app_category=product_profile.app_category,
            sub_category=product_profile.sub_category,
            target_users=product_profile.target_users,
            core_value=product_profile.core_value,
            visual_style=product_profile.visual_style,
            position=index,
            total=total,
            stage_name=current_stage.name,
            stage_start=current_stage.start_index,
            stage_end=current_stage.end_index,
            stage_description=current_stage.description,
            position_in_stage=position_in_stage,
            prev_info=prev_info,
            next_info=next_info,
            expected_types=expected_types_str
        )
        
        # 添加Few-shot示例（从其他产品学习）
        if FEWSHOT_AVAILABLE and index <= 30:  # 前30张最容易混淆，添加示例
            project_name = os.path.basename(os.path.dirname(image_path))
            few_shot = get_onboarding_examples(exclude_product=project_name)
            if few_shot:
                prompt = few_shot + "\n" + prompt
        
        # 调用API（带自动重试和递进压缩）
        try:
            # 根据重试次数决定压缩等级
            compression_level = retry_count
            image_base64, media_type = self._compress_image(image_path, compression_level)
            
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
                                "data": image_base64
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
                with self.lock:
                    self.success_count += 1
                
                return ScreenClassification(
                    filename=filename,
                    index=index,
                    screen_type=parsed.get("screen_type", "Unknown"),
                    sub_type=parsed.get("sub_type", ""),
                    naming=parsed.get("naming", {"cn": "", "en": ""}),
                    core_function=parsed.get("core_function", {"cn": "", "en": ""}),
                    design_highlights=parsed.get("design_highlights", []),
                    product_insight=parsed.get("product_insight", {"cn": "", "en": ""}),
                    tags=parsed.get("tags", []),
                    stage_name=current_stage.name,
                    position_in_stage=position_in_stage.split(" ")[0],
                    confidence=float(parsed.get("confidence", 0.5)),
                    reasoning=parsed.get("reasoning", ""),
                    ui_elements=parsed.get("ui_elements", []),
                    keywords_found=parsed.get("keywords_found", []),
                    description_cn=parsed.get("core_function", {}).get("cn", ""),
                    description_en=parsed.get("core_function", {}).get("en", "")
                )
            else:
                # JSON解析失败，重试
                if retry_count < MAX_RETRIES:
                    time.sleep(1)
                    return self.classify_single(
                        image_path, index, total, product_profile, flow_structure,
                        prev_result, next_filename, retry_count + 1
                    )
            
        except Exception as e:
            error_str = str(e).lower()
            
            # 检查是否是图片大小/格式相关的错误，自动重试
            is_image_error = any(x in error_str for x in [
                'image', 'size', 'too large', 'invalid_request', '400', 'base64'
            ])
            
            if is_image_error and retry_count < MAX_RETRIES:
                # 使用更强的压缩重试
                time.sleep(1)
                return self.classify_single(
                    image_path, index, total, product_profile, flow_structure,
                    prev_result, next_filename, retry_count + 1
                )
            
            with self.lock:
                self.fail_count += 1
            
            return ScreenClassification(
                filename=filename,
                index=index,
                screen_type="Unknown",
                sub_type="",
                naming={"cn": "分析失败", "en": "Analysis Failed"},
                core_function={"cn": str(e), "en": "Error"},
                design_highlights=[],
                product_insight={"cn": "", "en": ""},
                tags=[],
                stage_name=current_stage.name,
                position_in_stage="unknown",
                confidence=0.0,
                reasoning="",
                ui_elements=[],
                keywords_found=[],
                error=str(e)
            )
        
        # 解析失败且重试耗尽
        with self.lock:
            self.fail_count += 1
        
        return ScreenClassification(
            filename=filename,
            index=index,
            screen_type="Unknown",
            sub_type="",
            naming={"cn": "解析失败", "en": "Parse Failed"},
            core_function={"cn": "JSON解析失败", "en": "JSON parse error"},
            design_highlights=[],
            product_insight={"cn": "", "en": ""},
            tags=[],
            stage_name=current_stage.name,
            position_in_stage="unknown",
            confidence=0.0,
            reasoning="",
            ui_elements=[],
            keywords_found=[],
            error="JSON parse error"
        )
    
    def classify_all(
        self,
        project_path: str,
        product_profile: ProductProfile,
        flow_structure: FlowStructure,
        progress_callback=None
    ) -> Dict[str, Dict]:
        """
        分类所有截图（并行处理）
        
        Returns:
            {filename: classification_dict}
        """
        screens_folder = os.path.join(project_path, "Screens")
        if not os.path.exists(screens_folder):
            screens_folder = os.path.join(project_path, "Downloads")
        
        if not os.path.exists(screens_folder):
            return {}
        
        # 获取所有截图
        screenshots = sorted([
            f for f in os.listdir(screens_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(screenshots)
        if total == 0:
            return {}
        
        print(f"  [Layer 3] Classifying {total} screenshots (concurrent: {self.concurrent})...")
        
        results = {}
        start_time = datetime.now()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交任务
            futures = {}
            for idx, filename in enumerate(screenshots, 1):
                image_path = os.path.join(screens_folder, filename)
                
                # 获取前一个结果（如果有）
                prev_result = None
                if idx > 1:
                    prev_filename = screenshots[idx - 2]
                    prev_result = results.get(prev_filename)
                
                # 获取下一个文件名
                next_filename = None
                if idx < total:
                    next_filename = screenshots[idx]
                
                future = executor.submit(
                    self.classify_single,
                    image_path,
                    idx,
                    total,
                    product_profile,
                    flow_structure,
                    prev_result,
                    next_filename
                )
                futures[future] = (filename, idx)
            
            # 收集结果
            completed = 0
            for future in as_completed(futures):
                filename, idx = futures[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = asdict(result)
                    
                    # 进度显示
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total - completed)
                    
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r  [{bar}] {completed}/{total} ({pct:.0%}) | {int(remaining)}s left')
                    sys.stdout.flush()
                    
                    if progress_callback:
                        progress_callback(completed, total, filename, result)
                    
                except Exception as e:
                    print(f"\n  [ERROR] {filename}: {e}")
                    results[filename] = {
                        "filename": filename,
                        "index": idx,
                        "screen_type": "Unknown",
                        "error": str(e)
                    }
        
        print()  # 换行
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  [Layer 3] Complete: {self.success_count} success, {self.fail_count} failed")
        print(f"  [Layer 3] Time: {elapsed:.1f}s ({elapsed/total:.2f}s per image)")
        
        return results
    
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


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    import argparse
    from layer1_product import ProductRecognizer
    from layer2_structure import StructureRecognizer
    
    parser = argparse.ArgumentParser(description="Layer 3: Context Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name or path")
    parser.add_argument("--limit", type=int, default=5, help="Limit number of screenshots to test")
    args = parser.parse_args()
    
    # 解析路径
    if os.path.isabs(args.project):
        project_path = args.project
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_path = os.path.join(base_dir, "projects", args.project)
    
    # Layer 1
    print("\n[Layer 1] Product Recognition...")
    product_recognizer = ProductRecognizer()
    profile = product_recognizer.analyze(project_path)
    print(f"  Category: {profile.app_category}")
    
    # Layer 2
    print("\n[Layer 2] Structure Recognition...")
    structure_recognizer = StructureRecognizer()
    structure = structure_recognizer.analyze(project_path, profile)
    print(f"  Stages: {len(structure.stages)}")
    
    # Layer 3 (limited test)
    print(f"\n[Layer 3] Classification (testing {args.limit} screenshots)...")
    classifier = ContextClassifier(concurrent=2)
    
    # 只测试前几张
    screens_folder = os.path.join(project_path, "Screens")
    screenshots = sorted([
        f for f in os.listdir(screens_folder)
        if f.lower().endswith('.png')
    ])[:args.limit]
    
    for idx, filename in enumerate(screenshots, 1):
        image_path = os.path.join(screens_folder, filename)
        result = classifier.classify_single(
            image_path, idx, len(screenshots), profile, structure
        )
        print(f"\n  [{idx}] {filename}")
        print(f"      Type: {result.screen_type} ({result.sub_type})")
        print(f"      Stage: {result.stage_name}")
        print(f"      Reason: {result.reasoning}")

