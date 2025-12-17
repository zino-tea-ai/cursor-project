# -*- coding: utf-8 -*-
"""
验证规则配置 - 三层分类体系 (Stage / Module / Feature)
用于自动验证AI分析结果的准确性
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# ============================================================
# 加载标准词表
# ============================================================

CONFIG_DIR = Path(__file__).parent.parent / "config"

def load_taxonomy() -> Dict:
    """加载标准分类词表"""
    taxonomy_path = CONFIG_DIR / "taxonomy.json"
    if taxonomy_path.exists():
        with open(taxonomy_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def load_synonyms() -> Dict:
    """加载同义词映射"""
    synonyms_path = CONFIG_DIR / "synonyms.json"
    if synonyms_path.exists():
        with open(synonyms_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 全局缓存
_taxonomy = None
_synonyms = None

def get_taxonomy() -> Dict:
    global _taxonomy
    if _taxonomy is None:
        _taxonomy = load_taxonomy()
    return _taxonomy

def get_synonyms() -> Dict:
    global _synonyms
    if _synonyms is None:
        _synonyms = load_synonyms()
    return _synonyms

# ============================================================
# 三层分类定义
# ============================================================

# Stage（阶段）- 第一层
STAGES = {
    "Onboarding": {
        "cn": "引导阶段",
        "en": "Onboarding",
        "description": "从启动到首次使用核心功能前的所有页面",
    },
    "Core": {
        "cn": "核心阶段",
        "en": "Core",
        "description": "核心功能使用阶段",
    },
}

# Module（模块）- 第二层
MODULES = {
    # Onboarding阶段的Module
    "Welcome": {
        "cn": "欢迎模块",
        "stage": "Onboarding",
        "description": "启动页、价值主张、功能预览",
    },
    "Profile": {
        "cn": "身份信息",
        "stage": "Onboarding",
        "description": "用户身份信息收集（性别、年龄、身高体重等）",
    },
    "Goal": {
        "cn": "目标设定",
        "stage": "Onboarding",
        "description": "用户目标设定（方向、数值、时间线等）",
    },
    "Preference": {
        "cn": "偏好收集",
        "stage": "Onboarding",
        "description": "用户偏好和习惯收集",
    },
    "Permission": {
        "cn": "权限请求",
        "stage": "Onboarding",
        "description": "系统权限请求（通知、位置、追踪等）",
    },
    "Growth": {
        "cn": "增长运营",
        "stage": "Onboarding",
        "description": "增长和运营相关页面（来源、推荐码等）",
    },
    "Initialization": {
        "cn": "初始化",
        "stage": "Onboarding",
        "description": "数据初始化和加载",
    },
    "Paywall": {
        "cn": "付费墙",
        "stage": "Onboarding",
        "description": "订阅付费相关页面",
    },
    "Registration": {
        "cn": "注册",
        "stage": "Onboarding",
        "description": "账号注册和登录",
    },
    # Core阶段的Module
    "Dashboard": {
        "cn": "概览",
        "stage": "Core",
        "description": "数据概览和汇总",
    },
    "Tracking": {
        "cn": "记录",
        "stage": "Core",
        "description": "数据记录功能（食物、运动等）",
    },
    "Progress": {
        "cn": "进度",
        "stage": "Core",
        "description": "进度统计和趋势分析",
    },
    "Content": {
        "cn": "内容",
        "stage": "Core",
        "description": "内容展示（文章、教程等）",
    },
    "Social": {
        "cn": "社交",
        "stage": "Core",
        "description": "社交互动功能",
    },
    "Profile_Core": {
        "cn": "个人中心",
        "stage": "Core",
        "description": "用户个人中心",
    },
    "Settings": {
        "cn": "设置",
        "stage": "Core",
        "description": "应用设置",
    },
}

# Feature（功能）- 第三层
FEATURES = {
    # Onboarding Features
    "Splash": {"cn": "启动页", "module": "Welcome"},
    "ValueProp": {"cn": "价值主张", "module": "Welcome"},
    "FeaturePreview": {"cn": "功能预览", "module": "Welcome"},
    "GenderSelect": {"cn": "性别选择", "module": "Profile"},
    "BirthdayInput": {"cn": "生日输入", "module": "Profile"},
    "AgeInput": {"cn": "年龄输入", "module": "Profile"},
    "HeightInput": {"cn": "身高输入", "module": "Profile"},
    "WeightInput": {"cn": "体重输入", "module": "Profile"},
    "BodyMetrics": {"cn": "身体数据", "module": "Profile"},
    "DirectionSelect": {"cn": "目标方向", "module": "Goal"},
    "TargetInput": {"cn": "目标值", "module": "Goal"},
    "PaceSelect": {"cn": "速度选择", "module": "Goal"},
    "TimelineSelect": {"cn": "时间线", "module": "Goal"},
    "MotivationDisplay": {"cn": "激励展示", "module": "Goal"},
    "FrequencySelect": {"cn": "频率选择", "module": "Preference"},
    "TypeSelect": {"cn": "类型选择", "module": "Preference"},
    "BarrierIdentify": {"cn": "障碍识别", "module": "Preference"},
    "ExperienceCheck": {"cn": "经验检查", "module": "Preference"},
    "NotificationAsk": {"cn": "通知请求", "module": "Permission"},
    "LocationAsk": {"cn": "位置请求", "module": "Permission"},
    "TrackingAsk": {"cn": "追踪请求", "module": "Permission"},
    "HealthAsk": {"cn": "健康权限", "module": "Permission"},
    "ChannelSurvey": {"cn": "渠道调研", "module": "Growth"},
    "ReferralInput": {"cn": "推荐码输入", "module": "Growth"},
    "ReferralInvite": {"cn": "邀请好友", "module": "Growth"},
    "Loading": {"cn": "加载中", "module": "Initialization"},
    "Calculating": {"cn": "计算中", "module": "Initialization"},
    "SetupComplete": {"cn": "设置完成", "module": "Initialization"},
    "ValueReminder": {"cn": "价值提醒", "module": "Paywall"},
    "PlanSelect": {"cn": "套餐选择", "module": "Paywall"},
    "PriceDisplay": {"cn": "价格展示", "module": "Paywall"},
    "TrialOffer": {"cn": "试用优惠", "module": "Paywall"},
    "Confirmation": {"cn": "确认", "module": "Paywall"},
    "MethodSelect": {"cn": "方式选择", "module": "Registration"},
    "EmailInput": {"cn": "邮箱输入", "module": "Registration"},
    "PasswordInput": {"cn": "密码输入", "module": "Registration"},
    "OAuthApple": {"cn": "Apple登录", "module": "Registration"},
    "OAuthGoogle": {"cn": "Google登录", "module": "Registration"},
    "Verification": {"cn": "验证", "module": "Registration"},
    # Core Features
    "Overview": {"cn": "概览", "module": "Dashboard"},
    "Summary": {"cn": "汇总", "module": "Dashboard"},
    "FoodSearch": {"cn": "食物搜索", "module": "Tracking"},
    "FoodDetail": {"cn": "食物详情", "module": "Tracking"},
    "FoodLog": {"cn": "食物记录", "module": "Tracking"},
    "PhotoScan": {"cn": "拍照扫描", "module": "Tracking"},
    "ManualInput": {"cn": "手动输入", "module": "Tracking"},
    "WeeklyChart": {"cn": "周图表", "module": "Progress"},
    "MonthlyChart": {"cn": "月图表", "module": "Progress"},
    "TrendAnalysis": {"cn": "趋势分析", "module": "Progress"},
    "HistoryList": {"cn": "历史列表", "module": "Progress"},
    "ArticleList": {"cn": "文章列表", "module": "Content"},
    "ArticleDetail": {"cn": "文章详情", "module": "Content"},
    "FriendList": {"cn": "好友列表", "module": "Social"},
    "ActivityFeed": {"cn": "动态流", "module": "Social"},
    "AccountInfo": {"cn": "账户信息", "module": "Profile_Core"},
    "Achievements": {"cn": "成就", "module": "Profile_Core"},
    "Subscription": {"cn": "订阅管理", "module": "Settings"},
    "Notification": {"cn": "通知设置", "module": "Settings"},
    "Privacy": {"cn": "隐私设置", "module": "Settings"},
}

# 页面角色
ROLES = {
    "Entry": {"cn": "入口", "description": "功能入口页面"},
    "Browse": {"cn": "浏览", "description": "浏览列表"},
    "Detail": {"cn": "详情", "description": "详情页"},
    "Action": {"cn": "操作", "description": "操作页面"},
    "Result": {"cn": "结果", "description": "结果页"},
    "Modal": {"cn": "弹窗", "description": "弹窗/底部弹出"},
}

# 转场类型
TRANSITIONS = {
    "push": {"cn": "前进", "description": "前进到新页面（右滑入）"},
    "pop": {"cn": "返回", "description": "返回上一页（左滑出）"},
    "modal": {"cn": "弹窗", "description": "弹窗/底部弹出"},
    "tab": {"cn": "Tab切换", "description": "底部Tab切换"},
    "replace": {"cn": "替换", "description": "页面替换"},
}

# ============================================================
# 验证规则 - 关键词匹配
# ============================================================

KEYWORD_RULES = {
    # Onboarding Stage Keywords
    "Welcome": {
        "visual_keywords": [
            "welcome", "get started", "begin", "intro", "value",
            "欢迎", "开始", "介绍", "特色", "功能亮点",
            "swipe", "carousel", "logo", "brand", "splash"
        ],
        "negative_keywords": ["price", "subscribe", "form", "input"],
    },
    "Profile": {
        "visual_keywords": [
            "gender", "male", "female", "age", "birthday", "height", "weight",
            "性别", "年龄", "生日", "身高", "体重", "how old", "how tall"
        ],
        "negative_keywords": ["price", "subscribe"],
    },
    "Goal": {
        "visual_keywords": [
            "goal", "target", "lose weight", "gain", "maintain",
            "目标", "减重", "增重", "维持", "want to", "looking for"
        ],
        "negative_keywords": ["price", "subscribe"],
    },
    "Preference": {
        "visual_keywords": [
            "prefer", "habit", "diet", "frequency", "how often",
            "偏好", "习惯", "饮食", "多久", "barrier", "challenge"
        ],
        "negative_keywords": ["price", "subscribe"],
    },
    "Permission": {
        "visual_keywords": [
            "allow", "don't allow", "permission", "access", "enable",
            "notification", "location", "health", "tracking", "camera",
            "允许", "不允许", "权限", "通知", "位置", "健康"
        ],
        "negative_keywords": ["price", "subscribe"],
    },
    "Growth": {
        "visual_keywords": [
            "referral", "invite", "how did you hear", "where did you",
            "推荐码", "邀请", "从哪里", "来源"
        ],
        "negative_keywords": [],
    },
    "Paywall": {
        "visual_keywords": [
            "price", "subscribe", "subscription", "premium", "pro", "plus",
            "trial", "free trial", "start trial", "unlock", "upgrade",
            "$", "€", "¥", "/month", "/year", "per month", "per year",
            "plan", "pricing", "offer", "save", "discount", "best value",
            "付费", "订阅", "会员", "试用", "解锁", "升级", "价格"
        ],
        "negative_keywords": [],
    },
    "Registration": {
        "visual_keywords": [
            "sign up", "sign in", "login", "register", "create account",
            "email", "password", "continue with", "apple", "google",
            "注册", "登录", "邮箱", "密码", "继续"
        ],
        "negative_keywords": ["price", "subscribe", "trial"],
    },
    # Core Stage Keywords
    "Dashboard": {
        "visual_keywords": [
            "home", "dashboard", "today", "overview", "summary",
            "首页", "主页", "今日", "概览", "tab bar", "bottom navigation"
        ],
        "negative_keywords": ["sign up", "login", "price", "subscribe"],
    },
    "Tracking": {
        "visual_keywords": [
            "track", "log", "record", "add", "search food",
            "食物", "记录", "追踪", "添加", "scan", "barcode"
        ],
        "negative_keywords": [],
    },
    "Progress": {
        "visual_keywords": [
            "progress", "stats", "statistics", "chart", "graph", "history",
            "week", "month", "trend", "insight", "analytics",
            "进度", "统计", "图表", "历史", "趋势"
        ],
        "negative_keywords": [],
    },
    "Settings": {
        "visual_keywords": [
            "settings", "preferences", "account", "privacy", "notification",
            "help", "support", "about", "logout", "sign out",
            "设置", "偏好", "账户", "隐私", "通知", "帮助", "退出"
        ],
        "negative_keywords": [],
    },
}

# ============================================================
# 验证规则 - 顺序约束
# ============================================================

SEQUENCE_RULES = {
    # Stage级别的顺序规则
    "stage_order": ["Onboarding", "Core"],
    
    # Module级别的顺序（在Onboarding内）
    "onboarding_module_order": [
        "Welcome",
        "Profile",
        "Goal", 
        "Preference",
        "Permission",
        "Growth",
        "Initialization",
        "Paywall",
        "Registration"
    ],
    
    # 常见流程模式
    "typical_flows": [
        ["Welcome", "Profile", "Goal", "Preference", "Paywall", "Registration", "Dashboard"],
        ["Welcome", "Profile", "Goal", "Paywall", "Dashboard"],
        ["Welcome", "Permission", "Profile", "Goal", "Paywall", "Dashboard"],
    ],
}

# ============================================================
# 置信度阈值
# ============================================================

CONFIDENCE_THRESHOLDS = {
    "high": 0.90,      # >= 90% 自动通过
    "medium": 0.70,    # 70-90% 标记待确认
    "low": 0.70,       # < 70% 需要人工审核
}

# ============================================================
# 产品特定规则
# ============================================================

PRODUCT_SPECIFIC_RULES = {
    "health_fitness": {
        "expected_modules": ["Welcome", "Profile", "Goal", "Preference", "Paywall", "Dashboard", "Tracking", "Progress"],
        "keywords": ["goal", "weight", "height", "age", "activity", "diet", "exercise", "calories"],
    },
    "meditation": {
        "expected_modules": ["Welcome", "Profile", "Goal", "Paywall", "Dashboard", "Content"],
        "keywords": ["stress", "sleep", "anxiety", "relax", "meditation", "breathe"],
    },
    "social_fitness": {
        "expected_modules": ["Welcome", "Registration", "Permission", "Dashboard", "Social", "Tracking", "Progress"],
        "keywords": ["follow", "kudos", "club", "challenge", "segment", "activity"],
    },
}

# ============================================================
# 导出所有规则
# ============================================================

ALL_RULES = {
    "stages": STAGES,
    "modules": MODULES,
    "features": FEATURES,
    "roles": ROLES,
    "transitions": TRANSITIONS,
    "keyword_rules": KEYWORD_RULES,
    "sequence_rules": SEQUENCE_RULES,
    "confidence_thresholds": CONFIDENCE_THRESHOLDS,
    "product_specific": PRODUCT_SPECIFIC_RULES,
}

# ============================================================
# 辅助函数
# ============================================================

def get_modules_for_stage(stage: str) -> List[str]:
    """获取指定Stage下的所有Module"""
    return [name for name, info in MODULES.items() if info.get("stage") == stage]


def get_features_for_module(module: str) -> List[str]:
    """获取指定Module下的所有Feature"""
    return [name for name, info in FEATURES.items() if info.get("module") == module]


def get_stage_for_module(module: str) -> Optional[str]:
    """获取Module所属的Stage"""
    module_info = MODULES.get(module)
    return module_info.get("stage") if module_info else None


def get_module_for_feature(feature: str) -> Optional[str]:
    """获取Feature所属的Module"""
    feature_info = FEATURES.get(feature)
    return feature_info.get("module") if feature_info else None


def get_keywords_for_module(module: str) -> List[str]:
    """获取指定Module的所有关键词"""
    rule = KEYWORD_RULES.get(module, {})
    return rule.get("visual_keywords", [])


def get_negative_keywords_for_module(module: str) -> List[str]:
    """获取指定Module的负面关键词"""
    rule = KEYWORD_RULES.get(module, {})
    return rule.get("negative_keywords", [])


def validate_classification(stage: str, module: str, feature: str = None) -> Tuple[bool, str]:
    """
    验证分类是否合法
    
    Args:
        stage: 阶段
        module: 模块
        feature: 功能（可选）
        
    Returns:
        (is_valid, error_message)
    """
    # 验证Stage
    if stage not in STAGES:
        return False, f"Invalid stage: {stage}"
    
    # 验证Module
    if module not in MODULES:
        return False, f"Invalid module: {module}"
    
    # 验证Module属于Stage
    if MODULES[module].get("stage") != stage:
        expected_stage = MODULES[module].get("stage")
        return False, f"Module {module} belongs to {expected_stage}, not {stage}"
    
    # 验证Feature（如果提供）
    if feature:
        if feature not in FEATURES and feature != "Other":
            return False, f"Invalid feature: {feature}"
        if feature in FEATURES and FEATURES[feature].get("module") != module:
            expected_module = FEATURES[feature].get("module")
            return False, f"Feature {feature} belongs to {expected_module}, not {module}"
    
    return True, "Valid"


def check_sequence(classifications: List[Dict]) -> Tuple[bool, List[str]]:
    """
    检查分类序列是否符合流程规则
    
    Args:
        classifications: 分类列表，每个包含 stage, module
        
    Returns:
        (is_valid, issues)
    """
    issues = []
    
    # 检查Stage顺序
    seen_core = False
    for i, cls in enumerate(classifications):
        stage = cls.get("stage")
        if stage == "Core":
            seen_core = True
        elif stage == "Onboarding" and seen_core:
            # Onboarding出现在Core之后（允许一定的跳转）
            pass  # 不强制报错，因为视频可能有跳回
    
    # 检查Paywall位置（通常在Onboarding末期）
    paywall_positions = [i for i, cls in enumerate(classifications) if cls.get("module") == "Paywall"]
    if paywall_positions:
        first_paywall = paywall_positions[0]
        first_core = next((i for i, cls in enumerate(classifications) if cls.get("stage") == "Core"), len(classifications))
        if first_paywall > first_core:
            issues.append(f"Paywall at position {first_paywall} appears after Core stage starts at {first_core}")
    
    return len(issues) == 0, issues


def find_synonym(term: str) -> Optional[str]:
    """
    查找同义词对应的标准术语
    
    Args:
        term: 待查找的术语
        
    Returns:
        标准术语名称，如果没找到返回None
    """
    synonyms = get_synonyms()
    
    # 在features中查找
    for feature, syn_list in synonyms.get("features", {}).items():
        if term.lower() in [s.lower() for s in syn_list]:
            return feature
    
    # 在modules中查找
    for module, syn_list in synonyms.get("modules", {}).items():
        if term.lower() in [s.lower() for s in syn_list]:
            return module
    
    return None


# 兼容旧代码的别名
SCREEN_TYPES = {**MODULES, **{f"Feature_{k}": v for k, v in FEATURES.items()}}


def get_keywords_for_type(screen_type: str) -> List[str]:
    """兼容旧API：获取指定类型的所有关键词"""
    return get_keywords_for_module(screen_type)


def get_negative_keywords_for_type(screen_type: str) -> List[str]:
    """兼容旧API：获取指定类型的负面关键词"""
    return get_negative_keywords_for_module(screen_type)
