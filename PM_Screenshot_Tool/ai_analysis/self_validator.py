# -*- coding: utf-8 -*-
"""
自我校验模块
分析完成后检查结果的合理性，自动修正异常
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# 导入层级模块
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage


# ============================================================
# 校验规则配置
# ============================================================

# 流程连贯性规则：不应该出现的转换
INVALID_TRANSITIONS = {
    "Welcome": ["Settings", "Profile"],           # Welcome后不应直接到Settings
    "Launch": ["Settings", "Profile", "Feature"], # Launch后不应直接到功能页
    "Onboarding": ["Settings"],                   # Onboarding中间不应出现Settings
}

# 阶段预期类型
STAGE_EXPECTED_TYPES = {
    "Welcome": ["Welcome", "Launch"],
    "Launch": ["Launch", "Welcome"],
    "Onboarding": ["Onboarding", "Permission", "SignUp", "Referral"],  # Referral可能穿插
    "SignUp": ["SignUp", "Onboarding"],
    "Paywall": ["Paywall"],
    "Referral": ["Referral", "Social"],  # 新增Referral阶段
    "Home": ["Home", "Feature", "Referral"],  # Home阶段可能有Referral弹窗
    "Core Features": ["Feature", "Content", "Tracking", "Progress", "Home", "Referral"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social", "Feature", "Referral"],  # Social和Referral相关
    "Profile": ["Profile", "Settings"],
    "Settings": ["Settings", "Profile"],
}

# 所有有效的页面类型
VALID_SCREEN_TYPES = [
    "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
    "Paywall", "Referral",  # 新增Referral
    "Home", "Feature", "Content", "Profile", "Settings",
    "Social", "Tracking", "Progress", "Other"
]

# 分布阈值
MAX_SINGLE_TYPE_RATIO = 0.7      # 单一类型不应超过70%
MIN_TYPES_COUNT = 3              # 至少应有3种不同类型


@dataclass
class ValidationIssue:
    """校验问题"""
    issue_type: str              # continuity / distribution / position / stage_mismatch
    severity: str                # error / warning / info
    filename: str
    index: int
    current_type: str
    suggested_type: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    stats: Dict
    fixes_applied: List[Dict]


class SelfValidator:
    """自我校验器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> ValidationResult:
        """
        执行所有校验
        
        Args:
            results: {filename: classification_dict}
            product_profile: 产品画像
            flow_structure: 流程结构
        
        Returns:
            ValidationResult
        """
        self.issues = []
        
        # 转换为有序列表
        sorted_results = sorted(results.items(), key=lambda x: x[1].get('index', 0))
        
        if self.verbose:
            print("\n  [Validator] Running checks...")
        
        # 1. 流程连贯性检查
        self._check_continuity(sorted_results)
        
        # 2. 分布合理性检查
        self._check_distribution(sorted_results)
        
        # 3. 位置合理性检查
        self._check_position(sorted_results, flow_structure)
        
        # 4. 阶段匹配检查
        self._check_stage_match(sorted_results, flow_structure)
        
        # 统计
        stats = self._calculate_stats(sorted_results)
        
        # 汇总
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        if self.verbose:
            print(f"  [Validator] Found {error_count} errors, {warning_count} warnings")
        
        return ValidationResult(
            is_valid=(error_count == 0),
            issues=self.issues,
            stats=stats,
            fixes_applied=[]
        )
    
    def validate_and_fix(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> Tuple[Dict[str, Dict], ValidationResult]:
        """
        校验并自动修复
        
        Returns:
            (修复后的results, ValidationResult)
        """
        # 先校验
        validation = self.validate(results, product_profile, flow_structure)
        
        if validation.is_valid:
            return results, validation
        
        # 自动修复
        fixes_applied = []
        fixed_results = dict(results)
        
        # 保护类型：这些类型不应被自动修改（AI的判断通常是正确的）
        # Onboarding是核心类型，AI基于"受益方判断"识别，不应被覆盖
        PROTECTED_TYPES = ["Onboarding", "Referral", "Paywall"]
        
        for issue in validation.issues:
            if issue.severity == "error" and issue.suggested_type:
                # 应用修复
                if issue.filename in fixed_results:
                    old_type = fixed_results[issue.filename].get("screen_type")
                    
                    # 跳过保护类型
                    if old_type in PROTECTED_TYPES:
                        if self.verbose:
                            print(f"    [SKIP] {issue.filename}: {old_type} is protected")
                        continue
                    
                    fixed_results[issue.filename]["screen_type"] = issue.suggested_type
                    fixed_results[issue.filename]["auto_fixed"] = True
                    fixed_results[issue.filename]["original_type"] = old_type
                    
                    fixes_applied.append({
                        "filename": issue.filename,
                        "old_type": old_type,
                        "new_type": issue.suggested_type,
                        "reason": issue.reason
                    })
                    
                    if self.verbose:
                        print(f"    [FIX] {issue.filename}: {old_type} -> {issue.suggested_type}")
        
        validation.fixes_applied = fixes_applied
        
        if self.verbose:
            print(f"  [Validator] Applied {len(fixes_applied)} fixes")
        
        return fixed_results, validation
    
    def _check_continuity(self, sorted_results: List[Tuple[str, Dict]]):
        """检查流程连贯性"""
        prev_type = None
        prev_filename = None
        
        for filename, data in sorted_results:
            current_type = data.get("screen_type", "Unknown")
            
            if prev_type and prev_type in INVALID_TRANSITIONS:
                invalid_next = INVALID_TRANSITIONS[prev_type]
                if current_type in invalid_next:
                    self.issues.append(ValidationIssue(
                        issue_type="continuity",
                        severity="warning",
                        filename=filename,
                        index=data.get("index", 0),
                        current_type=current_type,
                        suggested_type=None,
                        reason=f"{prev_type}后通常不直接接{current_type}"
                    ))
            
            prev_type = current_type
            prev_filename = filename
    
    def _check_distribution(self, sorted_results: List[Tuple[str, Dict]]):
        """检查类型分布"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        if total == 0:
            return
        
        # 检查单一类型占比
        for type_name, count in counter.items():
            if type_name == "Unknown":
                continue
            ratio = count / total
            if ratio > MAX_SINGLE_TYPE_RATIO:
                self.issues.append(ValidationIssue(
                    issue_type="distribution",
                    severity="warning",
                    filename="",
                    index=0,
                    current_type=type_name,
                    suggested_type=None,
                    reason=f"{type_name}占比{ratio:.0%}，超过{MAX_SINGLE_TYPE_RATIO:.0%}阈值"
                ))
        
        # 检查类型多样性
        unique_types = len([t for t in counter.keys() if t != "Unknown"])
        if unique_types < MIN_TYPES_COUNT and total > 10:
            self.issues.append(ValidationIssue(
                issue_type="distribution",
                severity="info",
                filename="",
                index=0,
                current_type="",
                suggested_type=None,
                reason=f"类型多样性不足：只有{unique_types}种类型"
            ))
    
    def _check_position(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查位置合理性"""
        total = len(sorted_results)
        if total == 0:
            return
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            position_ratio = idx / total
            
            # 检查Welcome/Launch是否在开头
            if current_type in ["Welcome", "Launch"] and position_ratio > 0.2:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="warning",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type="Feature",
                    reason=f"{current_type}通常在开头，当前在{position_ratio:.0%}位置"
                ))
            
            # 检查Settings是否在末尾
            if current_type == "Settings" and position_ratio < 0.7:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="info",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=None,
                    reason=f"Settings通常在末尾，当前在{position_ratio:.0%}位置"
                ))
    
    def _check_stage_match(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查类型是否与所属阶段匹配"""
        # 这些类型可以出现在任何阶段，不应被强制修正
        # Onboarding内容可能穿插在各阶段（如目标选择在Welcome阶段、来源调查在Paywall阶段）
        FLEXIBLE_TYPES = ["Onboarding", "Referral", "Paywall", "Permission", "Other"]
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            stage_name = data.get("stage_name", "Unknown")
            
            # 灵活类型可以出现在任何阶段，跳过检查
            if current_type in FLEXIBLE_TYPES:
                continue
            
            # 获取阶段预期类型
            expected_types = STAGE_EXPECTED_TYPES.get(stage_name, [])
            
            if expected_types and current_type not in expected_types and current_type != "Unknown":
                # 计算最可能的正确类型（排除掉灵活类型作为建议）
                suggested = expected_types[0] if expected_types else None
                
                self.issues.append(ValidationIssue(
                    issue_type="stage_mismatch",
                    severity="error",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=suggested,
                    reason=f"在{stage_name}阶段，{current_type}不太符合，预期{expected_types}"
                ))
    
    def _calculate_stats(self, sorted_results: List[Tuple[str, Dict]]) -> Dict:
        """计算统计信息"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        # 计算置信度分布
        confidences = [data.get("confidence", 0) for _, data in sorted_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_screenshots": total,
            "type_distribution": dict(counter),
            "unique_types": len(counter),
            "avg_confidence": avg_confidence,
            "low_confidence_count": sum(1 for c in confidences if c < 0.7)
        }


# ============================================================
# 高级校验：基于AI的二次验证
# ============================================================

class AIValidator:
    """AI辅助校验器（用于可疑结果的二次验证）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key
        self.model = model
        # 延迟初始化
        self.client = None
    
    def verify_suspicious(
        self,
        results: Dict[str, Dict],
        issues: List[ValidationIssue],
        screens_folder: str
    ) -> Dict[str, str]:
        """
        对可疑结果进行AI二次验证
        
        Returns:
            {filename: verified_type}
        """
        # 找出需要验证的文件
        suspicious_files = set()
        for issue in issues:
            if issue.severity == "error" and issue.filename:
                suspicious_files.add(issue.filename)
        
        # TODO: 实现AI二次验证
        # 目前先返回空，表示不进行额外验证
        return {}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = {
        "Screen_001.png": {"index": 1, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.95},
        "Screen_002.png": {"index": 2, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.90},
        "Screen_003.png": {"index": 3, "screen_type": "Feature", "stage_name": "Onboarding", "confidence": 0.85},  # 问题：应该是Onboarding
        "Screen_004.png": {"index": 4, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.92},
        "Screen_005.png": {"index": 5, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.88},
        "Screen_006.png": {"index": 6, "screen_type": "Settings", "stage_name": "Onboarding", "confidence": 0.75},  # 问题：Onboarding阶段不应有Settings
        "Screen_007.png": {"index": 7, "screen_type": "Paywall", "stage_name": "Paywall", "confidence": 0.95},
        "Screen_008.png": {"index": 8, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.90},
        "Screen_009.png": {"index": 9, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.88},
        "Screen_010.png": {"index": 10, "screen_type": "Settings", "stage_name": "Settings", "confidence": 0.92},
    }
    
    # 模拟产品画像和流程结构
    from layer1_product import ProductProfile
    from layer2_structure import FlowStructure, FlowStage
    
    profile = ProductProfile(
        app_name="TestApp",
        app_category="Health",
        sub_category="Meditation",
        target_users="General",
        core_value="Help relax",
        business_model="Subscription",
        estimated_stages=["Welcome", "Onboarding", "Paywall", "Core"],
        visual_style="Minimalist",
        primary_color="Blue",
        confidence=0.9
    )
    
    structure = FlowStructure(
        total_screenshots=10,
        stages=[
            FlowStage(name="Welcome", start_index=1, end_index=2, description="Welcome", expected_types=["Welcome"], screenshot_count=2),
            FlowStage(name="Onboarding", start_index=3, end_index=6, description="Onboarding", expected_types=["Onboarding"], screenshot_count=4),
            FlowStage(name="Paywall", start_index=7, end_index=7, description="Paywall", expected_types=["Paywall"], screenshot_count=1),
            FlowStage(name="Core Features", start_index=8, end_index=9, description="Core", expected_types=["Feature"], screenshot_count=2),
            FlowStage(name="Settings", start_index=10, end_index=10, description="Settings", expected_types=["Settings"], screenshot_count=1),
        ],
        paywall_position="middle",
        onboarding_length="medium",
        has_signup=False,
        has_social=False,
        confidence=0.85
    )
    
    # 运行校验
    validator = SelfValidator(verbose=True)
    fixed_results, validation = validator.validate_and_fix(test_results, profile, structure)
    
    print("\n" + "=" * 60)
    print("Validation Result")
    print("=" * 60)
    print(f"Valid: {validation.is_valid}")
    print(f"Issues: {len(validation.issues)}")
    print(f"Fixes Applied: {len(validation.fixes_applied)}")
    
    for issue in validation.issues:
        print(f"\n  [{issue.severity.upper()}] {issue.filename}")
        print(f"    Type: {issue.issue_type}")
        print(f"    Current: {issue.current_type}")
        print(f"    Suggested: {issue.suggested_type}")
        print(f"    Reason: {issue.reason}")


自我校验模块
分析完成后检查结果的合理性，自动修正异常
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# 导入层级模块
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage


# ============================================================
# 校验规则配置
# ============================================================

# 流程连贯性规则：不应该出现的转换
INVALID_TRANSITIONS = {
    "Welcome": ["Settings", "Profile"],           # Welcome后不应直接到Settings
    "Launch": ["Settings", "Profile", "Feature"], # Launch后不应直接到功能页
    "Onboarding": ["Settings"],                   # Onboarding中间不应出现Settings
}

# 阶段预期类型
STAGE_EXPECTED_TYPES = {
    "Welcome": ["Welcome", "Launch"],
    "Launch": ["Launch", "Welcome"],
    "Onboarding": ["Onboarding", "Permission", "SignUp", "Referral"],  # Referral可能穿插
    "SignUp": ["SignUp", "Onboarding"],
    "Paywall": ["Paywall"],
    "Referral": ["Referral", "Social"],  # 新增Referral阶段
    "Home": ["Home", "Feature", "Referral"],  # Home阶段可能有Referral弹窗
    "Core Features": ["Feature", "Content", "Tracking", "Progress", "Home", "Referral"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social", "Feature", "Referral"],  # Social和Referral相关
    "Profile": ["Profile", "Settings"],
    "Settings": ["Settings", "Profile"],
}

# 所有有效的页面类型
VALID_SCREEN_TYPES = [
    "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
    "Paywall", "Referral",  # 新增Referral
    "Home", "Feature", "Content", "Profile", "Settings",
    "Social", "Tracking", "Progress", "Other"
]

# 分布阈值
MAX_SINGLE_TYPE_RATIO = 0.7      # 单一类型不应超过70%
MIN_TYPES_COUNT = 3              # 至少应有3种不同类型


@dataclass
class ValidationIssue:
    """校验问题"""
    issue_type: str              # continuity / distribution / position / stage_mismatch
    severity: str                # error / warning / info
    filename: str
    index: int
    current_type: str
    suggested_type: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    stats: Dict
    fixes_applied: List[Dict]


class SelfValidator:
    """自我校验器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> ValidationResult:
        """
        执行所有校验
        
        Args:
            results: {filename: classification_dict}
            product_profile: 产品画像
            flow_structure: 流程结构
        
        Returns:
            ValidationResult
        """
        self.issues = []
        
        # 转换为有序列表
        sorted_results = sorted(results.items(), key=lambda x: x[1].get('index', 0))
        
        if self.verbose:
            print("\n  [Validator] Running checks...")
        
        # 1. 流程连贯性检查
        self._check_continuity(sorted_results)
        
        # 2. 分布合理性检查
        self._check_distribution(sorted_results)
        
        # 3. 位置合理性检查
        self._check_position(sorted_results, flow_structure)
        
        # 4. 阶段匹配检查
        self._check_stage_match(sorted_results, flow_structure)
        
        # 统计
        stats = self._calculate_stats(sorted_results)
        
        # 汇总
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        if self.verbose:
            print(f"  [Validator] Found {error_count} errors, {warning_count} warnings")
        
        return ValidationResult(
            is_valid=(error_count == 0),
            issues=self.issues,
            stats=stats,
            fixes_applied=[]
        )
    
    def validate_and_fix(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> Tuple[Dict[str, Dict], ValidationResult]:
        """
        校验并自动修复
        
        Returns:
            (修复后的results, ValidationResult)
        """
        # 先校验
        validation = self.validate(results, product_profile, flow_structure)
        
        if validation.is_valid:
            return results, validation
        
        # 自动修复
        fixes_applied = []
        fixed_results = dict(results)
        
        # 保护类型：这些类型不应被自动修改（AI的判断通常是正确的）
        # Onboarding是核心类型，AI基于"受益方判断"识别，不应被覆盖
        PROTECTED_TYPES = ["Onboarding", "Referral", "Paywall"]
        
        for issue in validation.issues:
            if issue.severity == "error" and issue.suggested_type:
                # 应用修复
                if issue.filename in fixed_results:
                    old_type = fixed_results[issue.filename].get("screen_type")
                    
                    # 跳过保护类型
                    if old_type in PROTECTED_TYPES:
                        if self.verbose:
                            print(f"    [SKIP] {issue.filename}: {old_type} is protected")
                        continue
                    
                    fixed_results[issue.filename]["screen_type"] = issue.suggested_type
                    fixed_results[issue.filename]["auto_fixed"] = True
                    fixed_results[issue.filename]["original_type"] = old_type
                    
                    fixes_applied.append({
                        "filename": issue.filename,
                        "old_type": old_type,
                        "new_type": issue.suggested_type,
                        "reason": issue.reason
                    })
                    
                    if self.verbose:
                        print(f"    [FIX] {issue.filename}: {old_type} -> {issue.suggested_type}")
        
        validation.fixes_applied = fixes_applied
        
        if self.verbose:
            print(f"  [Validator] Applied {len(fixes_applied)} fixes")
        
        return fixed_results, validation
    
    def _check_continuity(self, sorted_results: List[Tuple[str, Dict]]):
        """检查流程连贯性"""
        prev_type = None
        prev_filename = None
        
        for filename, data in sorted_results:
            current_type = data.get("screen_type", "Unknown")
            
            if prev_type and prev_type in INVALID_TRANSITIONS:
                invalid_next = INVALID_TRANSITIONS[prev_type]
                if current_type in invalid_next:
                    self.issues.append(ValidationIssue(
                        issue_type="continuity",
                        severity="warning",
                        filename=filename,
                        index=data.get("index", 0),
                        current_type=current_type,
                        suggested_type=None,
                        reason=f"{prev_type}后通常不直接接{current_type}"
                    ))
            
            prev_type = current_type
            prev_filename = filename
    
    def _check_distribution(self, sorted_results: List[Tuple[str, Dict]]):
        """检查类型分布"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        if total == 0:
            return
        
        # 检查单一类型占比
        for type_name, count in counter.items():
            if type_name == "Unknown":
                continue
            ratio = count / total
            if ratio > MAX_SINGLE_TYPE_RATIO:
                self.issues.append(ValidationIssue(
                    issue_type="distribution",
                    severity="warning",
                    filename="",
                    index=0,
                    current_type=type_name,
                    suggested_type=None,
                    reason=f"{type_name}占比{ratio:.0%}，超过{MAX_SINGLE_TYPE_RATIO:.0%}阈值"
                ))
        
        # 检查类型多样性
        unique_types = len([t for t in counter.keys() if t != "Unknown"])
        if unique_types < MIN_TYPES_COUNT and total > 10:
            self.issues.append(ValidationIssue(
                issue_type="distribution",
                severity="info",
                filename="",
                index=0,
                current_type="",
                suggested_type=None,
                reason=f"类型多样性不足：只有{unique_types}种类型"
            ))
    
    def _check_position(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查位置合理性"""
        total = len(sorted_results)
        if total == 0:
            return
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            position_ratio = idx / total
            
            # 检查Welcome/Launch是否在开头
            if current_type in ["Welcome", "Launch"] and position_ratio > 0.2:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="warning",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type="Feature",
                    reason=f"{current_type}通常在开头，当前在{position_ratio:.0%}位置"
                ))
            
            # 检查Settings是否在末尾
            if current_type == "Settings" and position_ratio < 0.7:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="info",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=None,
                    reason=f"Settings通常在末尾，当前在{position_ratio:.0%}位置"
                ))
    
    def _check_stage_match(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查类型是否与所属阶段匹配"""
        # 这些类型可以出现在任何阶段，不应被强制修正
        # Onboarding内容可能穿插在各阶段（如目标选择在Welcome阶段、来源调查在Paywall阶段）
        FLEXIBLE_TYPES = ["Onboarding", "Referral", "Paywall", "Permission", "Other"]
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            stage_name = data.get("stage_name", "Unknown")
            
            # 灵活类型可以出现在任何阶段，跳过检查
            if current_type in FLEXIBLE_TYPES:
                continue
            
            # 获取阶段预期类型
            expected_types = STAGE_EXPECTED_TYPES.get(stage_name, [])
            
            if expected_types and current_type not in expected_types and current_type != "Unknown":
                # 计算最可能的正确类型（排除掉灵活类型作为建议）
                suggested = expected_types[0] if expected_types else None
                
                self.issues.append(ValidationIssue(
                    issue_type="stage_mismatch",
                    severity="error",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=suggested,
                    reason=f"在{stage_name}阶段，{current_type}不太符合，预期{expected_types}"
                ))
    
    def _calculate_stats(self, sorted_results: List[Tuple[str, Dict]]) -> Dict:
        """计算统计信息"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        # 计算置信度分布
        confidences = [data.get("confidence", 0) for _, data in sorted_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_screenshots": total,
            "type_distribution": dict(counter),
            "unique_types": len(counter),
            "avg_confidence": avg_confidence,
            "low_confidence_count": sum(1 for c in confidences if c < 0.7)
        }


# ============================================================
# 高级校验：基于AI的二次验证
# ============================================================

class AIValidator:
    """AI辅助校验器（用于可疑结果的二次验证）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key
        self.model = model
        # 延迟初始化
        self.client = None
    
    def verify_suspicious(
        self,
        results: Dict[str, Dict],
        issues: List[ValidationIssue],
        screens_folder: str
    ) -> Dict[str, str]:
        """
        对可疑结果进行AI二次验证
        
        Returns:
            {filename: verified_type}
        """
        # 找出需要验证的文件
        suspicious_files = set()
        for issue in issues:
            if issue.severity == "error" and issue.filename:
                suspicious_files.add(issue.filename)
        
        # TODO: 实现AI二次验证
        # 目前先返回空，表示不进行额外验证
        return {}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = {
        "Screen_001.png": {"index": 1, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.95},
        "Screen_002.png": {"index": 2, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.90},
        "Screen_003.png": {"index": 3, "screen_type": "Feature", "stage_name": "Onboarding", "confidence": 0.85},  # 问题：应该是Onboarding
        "Screen_004.png": {"index": 4, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.92},
        "Screen_005.png": {"index": 5, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.88},
        "Screen_006.png": {"index": 6, "screen_type": "Settings", "stage_name": "Onboarding", "confidence": 0.75},  # 问题：Onboarding阶段不应有Settings
        "Screen_007.png": {"index": 7, "screen_type": "Paywall", "stage_name": "Paywall", "confidence": 0.95},
        "Screen_008.png": {"index": 8, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.90},
        "Screen_009.png": {"index": 9, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.88},
        "Screen_010.png": {"index": 10, "screen_type": "Settings", "stage_name": "Settings", "confidence": 0.92},
    }
    
    # 模拟产品画像和流程结构
    from layer1_product import ProductProfile
    from layer2_structure import FlowStructure, FlowStage
    
    profile = ProductProfile(
        app_name="TestApp",
        app_category="Health",
        sub_category="Meditation",
        target_users="General",
        core_value="Help relax",
        business_model="Subscription",
        estimated_stages=["Welcome", "Onboarding", "Paywall", "Core"],
        visual_style="Minimalist",
        primary_color="Blue",
        confidence=0.9
    )
    
    structure = FlowStructure(
        total_screenshots=10,
        stages=[
            FlowStage(name="Welcome", start_index=1, end_index=2, description="Welcome", expected_types=["Welcome"], screenshot_count=2),
            FlowStage(name="Onboarding", start_index=3, end_index=6, description="Onboarding", expected_types=["Onboarding"], screenshot_count=4),
            FlowStage(name="Paywall", start_index=7, end_index=7, description="Paywall", expected_types=["Paywall"], screenshot_count=1),
            FlowStage(name="Core Features", start_index=8, end_index=9, description="Core", expected_types=["Feature"], screenshot_count=2),
            FlowStage(name="Settings", start_index=10, end_index=10, description="Settings", expected_types=["Settings"], screenshot_count=1),
        ],
        paywall_position="middle",
        onboarding_length="medium",
        has_signup=False,
        has_social=False,
        confidence=0.85
    )
    
    # 运行校验
    validator = SelfValidator(verbose=True)
    fixed_results, validation = validator.validate_and_fix(test_results, profile, structure)
    
    print("\n" + "=" * 60)
    print("Validation Result")
    print("=" * 60)
    print(f"Valid: {validation.is_valid}")
    print(f"Issues: {len(validation.issues)}")
    print(f"Fixes Applied: {len(validation.fixes_applied)}")
    
    for issue in validation.issues:
        print(f"\n  [{issue.severity.upper()}] {issue.filename}")
        print(f"    Type: {issue.issue_type}")
        print(f"    Current: {issue.current_type}")
        print(f"    Suggested: {issue.suggested_type}")
        print(f"    Reason: {issue.reason}")


自我校验模块
分析完成后检查结果的合理性，自动修正异常
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# 导入层级模块
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage


# ============================================================
# 校验规则配置
# ============================================================

# 流程连贯性规则：不应该出现的转换
INVALID_TRANSITIONS = {
    "Welcome": ["Settings", "Profile"],           # Welcome后不应直接到Settings
    "Launch": ["Settings", "Profile", "Feature"], # Launch后不应直接到功能页
    "Onboarding": ["Settings"],                   # Onboarding中间不应出现Settings
}

# 阶段预期类型
STAGE_EXPECTED_TYPES = {
    "Welcome": ["Welcome", "Launch"],
    "Launch": ["Launch", "Welcome"],
    "Onboarding": ["Onboarding", "Permission", "SignUp", "Referral"],  # Referral可能穿插
    "SignUp": ["SignUp", "Onboarding"],
    "Paywall": ["Paywall"],
    "Referral": ["Referral", "Social"],  # 新增Referral阶段
    "Home": ["Home", "Feature", "Referral"],  # Home阶段可能有Referral弹窗
    "Core Features": ["Feature", "Content", "Tracking", "Progress", "Home", "Referral"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social", "Feature", "Referral"],  # Social和Referral相关
    "Profile": ["Profile", "Settings"],
    "Settings": ["Settings", "Profile"],
}

# 所有有效的页面类型
VALID_SCREEN_TYPES = [
    "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
    "Paywall", "Referral",  # 新增Referral
    "Home", "Feature", "Content", "Profile", "Settings",
    "Social", "Tracking", "Progress", "Other"
]

# 分布阈值
MAX_SINGLE_TYPE_RATIO = 0.7      # 单一类型不应超过70%
MIN_TYPES_COUNT = 3              # 至少应有3种不同类型


@dataclass
class ValidationIssue:
    """校验问题"""
    issue_type: str              # continuity / distribution / position / stage_mismatch
    severity: str                # error / warning / info
    filename: str
    index: int
    current_type: str
    suggested_type: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    stats: Dict
    fixes_applied: List[Dict]


class SelfValidator:
    """自我校验器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> ValidationResult:
        """
        执行所有校验
        
        Args:
            results: {filename: classification_dict}
            product_profile: 产品画像
            flow_structure: 流程结构
        
        Returns:
            ValidationResult
        """
        self.issues = []
        
        # 转换为有序列表
        sorted_results = sorted(results.items(), key=lambda x: x[1].get('index', 0))
        
        if self.verbose:
            print("\n  [Validator] Running checks...")
        
        # 1. 流程连贯性检查
        self._check_continuity(sorted_results)
        
        # 2. 分布合理性检查
        self._check_distribution(sorted_results)
        
        # 3. 位置合理性检查
        self._check_position(sorted_results, flow_structure)
        
        # 4. 阶段匹配检查
        self._check_stage_match(sorted_results, flow_structure)
        
        # 统计
        stats = self._calculate_stats(sorted_results)
        
        # 汇总
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        if self.verbose:
            print(f"  [Validator] Found {error_count} errors, {warning_count} warnings")
        
        return ValidationResult(
            is_valid=(error_count == 0),
            issues=self.issues,
            stats=stats,
            fixes_applied=[]
        )
    
    def validate_and_fix(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> Tuple[Dict[str, Dict], ValidationResult]:
        """
        校验并自动修复
        
        Returns:
            (修复后的results, ValidationResult)
        """
        # 先校验
        validation = self.validate(results, product_profile, flow_structure)
        
        if validation.is_valid:
            return results, validation
        
        # 自动修复
        fixes_applied = []
        fixed_results = dict(results)
        
        # 保护类型：这些类型不应被自动修改（AI的判断通常是正确的）
        # Onboarding是核心类型，AI基于"受益方判断"识别，不应被覆盖
        PROTECTED_TYPES = ["Onboarding", "Referral", "Paywall"]
        
        for issue in validation.issues:
            if issue.severity == "error" and issue.suggested_type:
                # 应用修复
                if issue.filename in fixed_results:
                    old_type = fixed_results[issue.filename].get("screen_type")
                    
                    # 跳过保护类型
                    if old_type in PROTECTED_TYPES:
                        if self.verbose:
                            print(f"    [SKIP] {issue.filename}: {old_type} is protected")
                        continue
                    
                    fixed_results[issue.filename]["screen_type"] = issue.suggested_type
                    fixed_results[issue.filename]["auto_fixed"] = True
                    fixed_results[issue.filename]["original_type"] = old_type
                    
                    fixes_applied.append({
                        "filename": issue.filename,
                        "old_type": old_type,
                        "new_type": issue.suggested_type,
                        "reason": issue.reason
                    })
                    
                    if self.verbose:
                        print(f"    [FIX] {issue.filename}: {old_type} -> {issue.suggested_type}")
        
        validation.fixes_applied = fixes_applied
        
        if self.verbose:
            print(f"  [Validator] Applied {len(fixes_applied)} fixes")
        
        return fixed_results, validation
    
    def _check_continuity(self, sorted_results: List[Tuple[str, Dict]]):
        """检查流程连贯性"""
        prev_type = None
        prev_filename = None
        
        for filename, data in sorted_results:
            current_type = data.get("screen_type", "Unknown")
            
            if prev_type and prev_type in INVALID_TRANSITIONS:
                invalid_next = INVALID_TRANSITIONS[prev_type]
                if current_type in invalid_next:
                    self.issues.append(ValidationIssue(
                        issue_type="continuity",
                        severity="warning",
                        filename=filename,
                        index=data.get("index", 0),
                        current_type=current_type,
                        suggested_type=None,
                        reason=f"{prev_type}后通常不直接接{current_type}"
                    ))
            
            prev_type = current_type
            prev_filename = filename
    
    def _check_distribution(self, sorted_results: List[Tuple[str, Dict]]):
        """检查类型分布"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        if total == 0:
            return
        
        # 检查单一类型占比
        for type_name, count in counter.items():
            if type_name == "Unknown":
                continue
            ratio = count / total
            if ratio > MAX_SINGLE_TYPE_RATIO:
                self.issues.append(ValidationIssue(
                    issue_type="distribution",
                    severity="warning",
                    filename="",
                    index=0,
                    current_type=type_name,
                    suggested_type=None,
                    reason=f"{type_name}占比{ratio:.0%}，超过{MAX_SINGLE_TYPE_RATIO:.0%}阈值"
                ))
        
        # 检查类型多样性
        unique_types = len([t for t in counter.keys() if t != "Unknown"])
        if unique_types < MIN_TYPES_COUNT and total > 10:
            self.issues.append(ValidationIssue(
                issue_type="distribution",
                severity="info",
                filename="",
                index=0,
                current_type="",
                suggested_type=None,
                reason=f"类型多样性不足：只有{unique_types}种类型"
            ))
    
    def _check_position(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查位置合理性"""
        total = len(sorted_results)
        if total == 0:
            return
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            position_ratio = idx / total
            
            # 检查Welcome/Launch是否在开头
            if current_type in ["Welcome", "Launch"] and position_ratio > 0.2:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="warning",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type="Feature",
                    reason=f"{current_type}通常在开头，当前在{position_ratio:.0%}位置"
                ))
            
            # 检查Settings是否在末尾
            if current_type == "Settings" and position_ratio < 0.7:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="info",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=None,
                    reason=f"Settings通常在末尾，当前在{position_ratio:.0%}位置"
                ))
    
    def _check_stage_match(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查类型是否与所属阶段匹配"""
        # 这些类型可以出现在任何阶段，不应被强制修正
        # Onboarding内容可能穿插在各阶段（如目标选择在Welcome阶段、来源调查在Paywall阶段）
        FLEXIBLE_TYPES = ["Onboarding", "Referral", "Paywall", "Permission", "Other"]
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            stage_name = data.get("stage_name", "Unknown")
            
            # 灵活类型可以出现在任何阶段，跳过检查
            if current_type in FLEXIBLE_TYPES:
                continue
            
            # 获取阶段预期类型
            expected_types = STAGE_EXPECTED_TYPES.get(stage_name, [])
            
            if expected_types and current_type not in expected_types and current_type != "Unknown":
                # 计算最可能的正确类型（排除掉灵活类型作为建议）
                suggested = expected_types[0] if expected_types else None
                
                self.issues.append(ValidationIssue(
                    issue_type="stage_mismatch",
                    severity="error",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=suggested,
                    reason=f"在{stage_name}阶段，{current_type}不太符合，预期{expected_types}"
                ))
    
    def _calculate_stats(self, sorted_results: List[Tuple[str, Dict]]) -> Dict:
        """计算统计信息"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        # 计算置信度分布
        confidences = [data.get("confidence", 0) for _, data in sorted_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_screenshots": total,
            "type_distribution": dict(counter),
            "unique_types": len(counter),
            "avg_confidence": avg_confidence,
            "low_confidence_count": sum(1 for c in confidences if c < 0.7)
        }


# ============================================================
# 高级校验：基于AI的二次验证
# ============================================================

class AIValidator:
    """AI辅助校验器（用于可疑结果的二次验证）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key
        self.model = model
        # 延迟初始化
        self.client = None
    
    def verify_suspicious(
        self,
        results: Dict[str, Dict],
        issues: List[ValidationIssue],
        screens_folder: str
    ) -> Dict[str, str]:
        """
        对可疑结果进行AI二次验证
        
        Returns:
            {filename: verified_type}
        """
        # 找出需要验证的文件
        suspicious_files = set()
        for issue in issues:
            if issue.severity == "error" and issue.filename:
                suspicious_files.add(issue.filename)
        
        # TODO: 实现AI二次验证
        # 目前先返回空，表示不进行额外验证
        return {}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = {
        "Screen_001.png": {"index": 1, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.95},
        "Screen_002.png": {"index": 2, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.90},
        "Screen_003.png": {"index": 3, "screen_type": "Feature", "stage_name": "Onboarding", "confidence": 0.85},  # 问题：应该是Onboarding
        "Screen_004.png": {"index": 4, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.92},
        "Screen_005.png": {"index": 5, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.88},
        "Screen_006.png": {"index": 6, "screen_type": "Settings", "stage_name": "Onboarding", "confidence": 0.75},  # 问题：Onboarding阶段不应有Settings
        "Screen_007.png": {"index": 7, "screen_type": "Paywall", "stage_name": "Paywall", "confidence": 0.95},
        "Screen_008.png": {"index": 8, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.90},
        "Screen_009.png": {"index": 9, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.88},
        "Screen_010.png": {"index": 10, "screen_type": "Settings", "stage_name": "Settings", "confidence": 0.92},
    }
    
    # 模拟产品画像和流程结构
    from layer1_product import ProductProfile
    from layer2_structure import FlowStructure, FlowStage
    
    profile = ProductProfile(
        app_name="TestApp",
        app_category="Health",
        sub_category="Meditation",
        target_users="General",
        core_value="Help relax",
        business_model="Subscription",
        estimated_stages=["Welcome", "Onboarding", "Paywall", "Core"],
        visual_style="Minimalist",
        primary_color="Blue",
        confidence=0.9
    )
    
    structure = FlowStructure(
        total_screenshots=10,
        stages=[
            FlowStage(name="Welcome", start_index=1, end_index=2, description="Welcome", expected_types=["Welcome"], screenshot_count=2),
            FlowStage(name="Onboarding", start_index=3, end_index=6, description="Onboarding", expected_types=["Onboarding"], screenshot_count=4),
            FlowStage(name="Paywall", start_index=7, end_index=7, description="Paywall", expected_types=["Paywall"], screenshot_count=1),
            FlowStage(name="Core Features", start_index=8, end_index=9, description="Core", expected_types=["Feature"], screenshot_count=2),
            FlowStage(name="Settings", start_index=10, end_index=10, description="Settings", expected_types=["Settings"], screenshot_count=1),
        ],
        paywall_position="middle",
        onboarding_length="medium",
        has_signup=False,
        has_social=False,
        confidence=0.85
    )
    
    # 运行校验
    validator = SelfValidator(verbose=True)
    fixed_results, validation = validator.validate_and_fix(test_results, profile, structure)
    
    print("\n" + "=" * 60)
    print("Validation Result")
    print("=" * 60)
    print(f"Valid: {validation.is_valid}")
    print(f"Issues: {len(validation.issues)}")
    print(f"Fixes Applied: {len(validation.fixes_applied)}")
    
    for issue in validation.issues:
        print(f"\n  [{issue.severity.upper()}] {issue.filename}")
        print(f"    Type: {issue.issue_type}")
        print(f"    Current: {issue.current_type}")
        print(f"    Suggested: {issue.suggested_type}")
        print(f"    Reason: {issue.reason}")


自我校验模块
分析完成后检查结果的合理性，自动修正异常
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# 导入层级模块
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage


# ============================================================
# 校验规则配置
# ============================================================

# 流程连贯性规则：不应该出现的转换
INVALID_TRANSITIONS = {
    "Welcome": ["Settings", "Profile"],           # Welcome后不应直接到Settings
    "Launch": ["Settings", "Profile", "Feature"], # Launch后不应直接到功能页
    "Onboarding": ["Settings"],                   # Onboarding中间不应出现Settings
}

# 阶段预期类型
STAGE_EXPECTED_TYPES = {
    "Welcome": ["Welcome", "Launch"],
    "Launch": ["Launch", "Welcome"],
    "Onboarding": ["Onboarding", "Permission", "SignUp", "Referral"],  # Referral可能穿插
    "SignUp": ["SignUp", "Onboarding"],
    "Paywall": ["Paywall"],
    "Referral": ["Referral", "Social"],  # 新增Referral阶段
    "Home": ["Home", "Feature", "Referral"],  # Home阶段可能有Referral弹窗
    "Core Features": ["Feature", "Content", "Tracking", "Progress", "Home", "Referral"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social", "Feature", "Referral"],  # Social和Referral相关
    "Profile": ["Profile", "Settings"],
    "Settings": ["Settings", "Profile"],
}

# 所有有效的页面类型
VALID_SCREEN_TYPES = [
    "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
    "Paywall", "Referral",  # 新增Referral
    "Home", "Feature", "Content", "Profile", "Settings",
    "Social", "Tracking", "Progress", "Other"
]

# 分布阈值
MAX_SINGLE_TYPE_RATIO = 0.7      # 单一类型不应超过70%
MIN_TYPES_COUNT = 3              # 至少应有3种不同类型


@dataclass
class ValidationIssue:
    """校验问题"""
    issue_type: str              # continuity / distribution / position / stage_mismatch
    severity: str                # error / warning / info
    filename: str
    index: int
    current_type: str
    suggested_type: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    stats: Dict
    fixes_applied: List[Dict]


class SelfValidator:
    """自我校验器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> ValidationResult:
        """
        执行所有校验
        
        Args:
            results: {filename: classification_dict}
            product_profile: 产品画像
            flow_structure: 流程结构
        
        Returns:
            ValidationResult
        """
        self.issues = []
        
        # 转换为有序列表
        sorted_results = sorted(results.items(), key=lambda x: x[1].get('index', 0))
        
        if self.verbose:
            print("\n  [Validator] Running checks...")
        
        # 1. 流程连贯性检查
        self._check_continuity(sorted_results)
        
        # 2. 分布合理性检查
        self._check_distribution(sorted_results)
        
        # 3. 位置合理性检查
        self._check_position(sorted_results, flow_structure)
        
        # 4. 阶段匹配检查
        self._check_stage_match(sorted_results, flow_structure)
        
        # 统计
        stats = self._calculate_stats(sorted_results)
        
        # 汇总
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        if self.verbose:
            print(f"  [Validator] Found {error_count} errors, {warning_count} warnings")
        
        return ValidationResult(
            is_valid=(error_count == 0),
            issues=self.issues,
            stats=stats,
            fixes_applied=[]
        )
    
    def validate_and_fix(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> Tuple[Dict[str, Dict], ValidationResult]:
        """
        校验并自动修复
        
        Returns:
            (修复后的results, ValidationResult)
        """
        # 先校验
        validation = self.validate(results, product_profile, flow_structure)
        
        if validation.is_valid:
            return results, validation
        
        # 自动修复
        fixes_applied = []
        fixed_results = dict(results)
        
        # 保护类型：这些类型不应被自动修改（AI的判断通常是正确的）
        # Onboarding是核心类型，AI基于"受益方判断"识别，不应被覆盖
        PROTECTED_TYPES = ["Onboarding", "Referral", "Paywall"]
        
        for issue in validation.issues:
            if issue.severity == "error" and issue.suggested_type:
                # 应用修复
                if issue.filename in fixed_results:
                    old_type = fixed_results[issue.filename].get("screen_type")
                    
                    # 跳过保护类型
                    if old_type in PROTECTED_TYPES:
                        if self.verbose:
                            print(f"    [SKIP] {issue.filename}: {old_type} is protected")
                        continue
                    
                    fixed_results[issue.filename]["screen_type"] = issue.suggested_type
                    fixed_results[issue.filename]["auto_fixed"] = True
                    fixed_results[issue.filename]["original_type"] = old_type
                    
                    fixes_applied.append({
                        "filename": issue.filename,
                        "old_type": old_type,
                        "new_type": issue.suggested_type,
                        "reason": issue.reason
                    })
                    
                    if self.verbose:
                        print(f"    [FIX] {issue.filename}: {old_type} -> {issue.suggested_type}")
        
        validation.fixes_applied = fixes_applied
        
        if self.verbose:
            print(f"  [Validator] Applied {len(fixes_applied)} fixes")
        
        return fixed_results, validation
    
    def _check_continuity(self, sorted_results: List[Tuple[str, Dict]]):
        """检查流程连贯性"""
        prev_type = None
        prev_filename = None
        
        for filename, data in sorted_results:
            current_type = data.get("screen_type", "Unknown")
            
            if prev_type and prev_type in INVALID_TRANSITIONS:
                invalid_next = INVALID_TRANSITIONS[prev_type]
                if current_type in invalid_next:
                    self.issues.append(ValidationIssue(
                        issue_type="continuity",
                        severity="warning",
                        filename=filename,
                        index=data.get("index", 0),
                        current_type=current_type,
                        suggested_type=None,
                        reason=f"{prev_type}后通常不直接接{current_type}"
                    ))
            
            prev_type = current_type
            prev_filename = filename
    
    def _check_distribution(self, sorted_results: List[Tuple[str, Dict]]):
        """检查类型分布"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        if total == 0:
            return
        
        # 检查单一类型占比
        for type_name, count in counter.items():
            if type_name == "Unknown":
                continue
            ratio = count / total
            if ratio > MAX_SINGLE_TYPE_RATIO:
                self.issues.append(ValidationIssue(
                    issue_type="distribution",
                    severity="warning",
                    filename="",
                    index=0,
                    current_type=type_name,
                    suggested_type=None,
                    reason=f"{type_name}占比{ratio:.0%}，超过{MAX_SINGLE_TYPE_RATIO:.0%}阈值"
                ))
        
        # 检查类型多样性
        unique_types = len([t for t in counter.keys() if t != "Unknown"])
        if unique_types < MIN_TYPES_COUNT and total > 10:
            self.issues.append(ValidationIssue(
                issue_type="distribution",
                severity="info",
                filename="",
                index=0,
                current_type="",
                suggested_type=None,
                reason=f"类型多样性不足：只有{unique_types}种类型"
            ))
    
    def _check_position(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查位置合理性"""
        total = len(sorted_results)
        if total == 0:
            return
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            position_ratio = idx / total
            
            # 检查Welcome/Launch是否在开头
            if current_type in ["Welcome", "Launch"] and position_ratio > 0.2:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="warning",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type="Feature",
                    reason=f"{current_type}通常在开头，当前在{position_ratio:.0%}位置"
                ))
            
            # 检查Settings是否在末尾
            if current_type == "Settings" and position_ratio < 0.7:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="info",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=None,
                    reason=f"Settings通常在末尾，当前在{position_ratio:.0%}位置"
                ))
    
    def _check_stage_match(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查类型是否与所属阶段匹配"""
        # 这些类型可以出现在任何阶段，不应被强制修正
        # Onboarding内容可能穿插在各阶段（如目标选择在Welcome阶段、来源调查在Paywall阶段）
        FLEXIBLE_TYPES = ["Onboarding", "Referral", "Paywall", "Permission", "Other"]
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            stage_name = data.get("stage_name", "Unknown")
            
            # 灵活类型可以出现在任何阶段，跳过检查
            if current_type in FLEXIBLE_TYPES:
                continue
            
            # 获取阶段预期类型
            expected_types = STAGE_EXPECTED_TYPES.get(stage_name, [])
            
            if expected_types and current_type not in expected_types and current_type != "Unknown":
                # 计算最可能的正确类型（排除掉灵活类型作为建议）
                suggested = expected_types[0] if expected_types else None
                
                self.issues.append(ValidationIssue(
                    issue_type="stage_mismatch",
                    severity="error",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=suggested,
                    reason=f"在{stage_name}阶段，{current_type}不太符合，预期{expected_types}"
                ))
    
    def _calculate_stats(self, sorted_results: List[Tuple[str, Dict]]) -> Dict:
        """计算统计信息"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        # 计算置信度分布
        confidences = [data.get("confidence", 0) for _, data in sorted_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_screenshots": total,
            "type_distribution": dict(counter),
            "unique_types": len(counter),
            "avg_confidence": avg_confidence,
            "low_confidence_count": sum(1 for c in confidences if c < 0.7)
        }


# ============================================================
# 高级校验：基于AI的二次验证
# ============================================================

class AIValidator:
    """AI辅助校验器（用于可疑结果的二次验证）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key
        self.model = model
        # 延迟初始化
        self.client = None
    
    def verify_suspicious(
        self,
        results: Dict[str, Dict],
        issues: List[ValidationIssue],
        screens_folder: str
    ) -> Dict[str, str]:
        """
        对可疑结果进行AI二次验证
        
        Returns:
            {filename: verified_type}
        """
        # 找出需要验证的文件
        suspicious_files = set()
        for issue in issues:
            if issue.severity == "error" and issue.filename:
                suspicious_files.add(issue.filename)
        
        # TODO: 实现AI二次验证
        # 目前先返回空，表示不进行额外验证
        return {}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = {
        "Screen_001.png": {"index": 1, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.95},
        "Screen_002.png": {"index": 2, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.90},
        "Screen_003.png": {"index": 3, "screen_type": "Feature", "stage_name": "Onboarding", "confidence": 0.85},  # 问题：应该是Onboarding
        "Screen_004.png": {"index": 4, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.92},
        "Screen_005.png": {"index": 5, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.88},
        "Screen_006.png": {"index": 6, "screen_type": "Settings", "stage_name": "Onboarding", "confidence": 0.75},  # 问题：Onboarding阶段不应有Settings
        "Screen_007.png": {"index": 7, "screen_type": "Paywall", "stage_name": "Paywall", "confidence": 0.95},
        "Screen_008.png": {"index": 8, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.90},
        "Screen_009.png": {"index": 9, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.88},
        "Screen_010.png": {"index": 10, "screen_type": "Settings", "stage_name": "Settings", "confidence": 0.92},
    }
    
    # 模拟产品画像和流程结构
    from layer1_product import ProductProfile
    from layer2_structure import FlowStructure, FlowStage
    
    profile = ProductProfile(
        app_name="TestApp",
        app_category="Health",
        sub_category="Meditation",
        target_users="General",
        core_value="Help relax",
        business_model="Subscription",
        estimated_stages=["Welcome", "Onboarding", "Paywall", "Core"],
        visual_style="Minimalist",
        primary_color="Blue",
        confidence=0.9
    )
    
    structure = FlowStructure(
        total_screenshots=10,
        stages=[
            FlowStage(name="Welcome", start_index=1, end_index=2, description="Welcome", expected_types=["Welcome"], screenshot_count=2),
            FlowStage(name="Onboarding", start_index=3, end_index=6, description="Onboarding", expected_types=["Onboarding"], screenshot_count=4),
            FlowStage(name="Paywall", start_index=7, end_index=7, description="Paywall", expected_types=["Paywall"], screenshot_count=1),
            FlowStage(name="Core Features", start_index=8, end_index=9, description="Core", expected_types=["Feature"], screenshot_count=2),
            FlowStage(name="Settings", start_index=10, end_index=10, description="Settings", expected_types=["Settings"], screenshot_count=1),
        ],
        paywall_position="middle",
        onboarding_length="medium",
        has_signup=False,
        has_social=False,
        confidence=0.85
    )
    
    # 运行校验
    validator = SelfValidator(verbose=True)
    fixed_results, validation = validator.validate_and_fix(test_results, profile, structure)
    
    print("\n" + "=" * 60)
    print("Validation Result")
    print("=" * 60)
    print(f"Valid: {validation.is_valid}")
    print(f"Issues: {len(validation.issues)}")
    print(f"Fixes Applied: {len(validation.fixes_applied)}")
    
    for issue in validation.issues:
        print(f"\n  [{issue.severity.upper()}] {issue.filename}")
        print(f"    Type: {issue.issue_type}")
        print(f"    Current: {issue.current_type}")
        print(f"    Suggested: {issue.suggested_type}")
        print(f"    Reason: {issue.reason}")


自我校验模块
分析完成后检查结果的合理性，自动修正异常
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# 导入层级模块
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage


# ============================================================
# 校验规则配置
# ============================================================

# 流程连贯性规则：不应该出现的转换
INVALID_TRANSITIONS = {
    "Welcome": ["Settings", "Profile"],           # Welcome后不应直接到Settings
    "Launch": ["Settings", "Profile", "Feature"], # Launch后不应直接到功能页
    "Onboarding": ["Settings"],                   # Onboarding中间不应出现Settings
}

# 阶段预期类型
STAGE_EXPECTED_TYPES = {
    "Welcome": ["Welcome", "Launch"],
    "Launch": ["Launch", "Welcome"],
    "Onboarding": ["Onboarding", "Permission", "SignUp", "Referral"],  # Referral可能穿插
    "SignUp": ["SignUp", "Onboarding"],
    "Paywall": ["Paywall"],
    "Referral": ["Referral", "Social"],  # 新增Referral阶段
    "Home": ["Home", "Feature", "Referral"],  # Home阶段可能有Referral弹窗
    "Core Features": ["Feature", "Content", "Tracking", "Progress", "Home", "Referral"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social", "Feature", "Referral"],  # Social和Referral相关
    "Profile": ["Profile", "Settings"],
    "Settings": ["Settings", "Profile"],
}

# 所有有效的页面类型
VALID_SCREEN_TYPES = [
    "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
    "Paywall", "Referral",  # 新增Referral
    "Home", "Feature", "Content", "Profile", "Settings",
    "Social", "Tracking", "Progress", "Other"
]

# 分布阈值
MAX_SINGLE_TYPE_RATIO = 0.7      # 单一类型不应超过70%
MIN_TYPES_COUNT = 3              # 至少应有3种不同类型


@dataclass
class ValidationIssue:
    """校验问题"""
    issue_type: str              # continuity / distribution / position / stage_mismatch
    severity: str                # error / warning / info
    filename: str
    index: int
    current_type: str
    suggested_type: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    stats: Dict
    fixes_applied: List[Dict]


class SelfValidator:
    """自我校验器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> ValidationResult:
        """
        执行所有校验
        
        Args:
            results: {filename: classification_dict}
            product_profile: 产品画像
            flow_structure: 流程结构
        
        Returns:
            ValidationResult
        """
        self.issues = []
        
        # 转换为有序列表
        sorted_results = sorted(results.items(), key=lambda x: x[1].get('index', 0))
        
        if self.verbose:
            print("\n  [Validator] Running checks...")
        
        # 1. 流程连贯性检查
        self._check_continuity(sorted_results)
        
        # 2. 分布合理性检查
        self._check_distribution(sorted_results)
        
        # 3. 位置合理性检查
        self._check_position(sorted_results, flow_structure)
        
        # 4. 阶段匹配检查
        self._check_stage_match(sorted_results, flow_structure)
        
        # 统计
        stats = self._calculate_stats(sorted_results)
        
        # 汇总
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        if self.verbose:
            print(f"  [Validator] Found {error_count} errors, {warning_count} warnings")
        
        return ValidationResult(
            is_valid=(error_count == 0),
            issues=self.issues,
            stats=stats,
            fixes_applied=[]
        )
    
    def validate_and_fix(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> Tuple[Dict[str, Dict], ValidationResult]:
        """
        校验并自动修复
        
        Returns:
            (修复后的results, ValidationResult)
        """
        # 先校验
        validation = self.validate(results, product_profile, flow_structure)
        
        if validation.is_valid:
            return results, validation
        
        # 自动修复
        fixes_applied = []
        fixed_results = dict(results)
        
        # 保护类型：这些类型不应被自动修改（AI的判断通常是正确的）
        # Onboarding是核心类型，AI基于"受益方判断"识别，不应被覆盖
        PROTECTED_TYPES = ["Onboarding", "Referral", "Paywall"]
        
        for issue in validation.issues:
            if issue.severity == "error" and issue.suggested_type:
                # 应用修复
                if issue.filename in fixed_results:
                    old_type = fixed_results[issue.filename].get("screen_type")
                    
                    # 跳过保护类型
                    if old_type in PROTECTED_TYPES:
                        if self.verbose:
                            print(f"    [SKIP] {issue.filename}: {old_type} is protected")
                        continue
                    
                    fixed_results[issue.filename]["screen_type"] = issue.suggested_type
                    fixed_results[issue.filename]["auto_fixed"] = True
                    fixed_results[issue.filename]["original_type"] = old_type
                    
                    fixes_applied.append({
                        "filename": issue.filename,
                        "old_type": old_type,
                        "new_type": issue.suggested_type,
                        "reason": issue.reason
                    })
                    
                    if self.verbose:
                        print(f"    [FIX] {issue.filename}: {old_type} -> {issue.suggested_type}")
        
        validation.fixes_applied = fixes_applied
        
        if self.verbose:
            print(f"  [Validator] Applied {len(fixes_applied)} fixes")
        
        return fixed_results, validation
    
    def _check_continuity(self, sorted_results: List[Tuple[str, Dict]]):
        """检查流程连贯性"""
        prev_type = None
        prev_filename = None
        
        for filename, data in sorted_results:
            current_type = data.get("screen_type", "Unknown")
            
            if prev_type and prev_type in INVALID_TRANSITIONS:
                invalid_next = INVALID_TRANSITIONS[prev_type]
                if current_type in invalid_next:
                    self.issues.append(ValidationIssue(
                        issue_type="continuity",
                        severity="warning",
                        filename=filename,
                        index=data.get("index", 0),
                        current_type=current_type,
                        suggested_type=None,
                        reason=f"{prev_type}后通常不直接接{current_type}"
                    ))
            
            prev_type = current_type
            prev_filename = filename
    
    def _check_distribution(self, sorted_results: List[Tuple[str, Dict]]):
        """检查类型分布"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        if total == 0:
            return
        
        # 检查单一类型占比
        for type_name, count in counter.items():
            if type_name == "Unknown":
                continue
            ratio = count / total
            if ratio > MAX_SINGLE_TYPE_RATIO:
                self.issues.append(ValidationIssue(
                    issue_type="distribution",
                    severity="warning",
                    filename="",
                    index=0,
                    current_type=type_name,
                    suggested_type=None,
                    reason=f"{type_name}占比{ratio:.0%}，超过{MAX_SINGLE_TYPE_RATIO:.0%}阈值"
                ))
        
        # 检查类型多样性
        unique_types = len([t for t in counter.keys() if t != "Unknown"])
        if unique_types < MIN_TYPES_COUNT and total > 10:
            self.issues.append(ValidationIssue(
                issue_type="distribution",
                severity="info",
                filename="",
                index=0,
                current_type="",
                suggested_type=None,
                reason=f"类型多样性不足：只有{unique_types}种类型"
            ))
    
    def _check_position(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查位置合理性"""
        total = len(sorted_results)
        if total == 0:
            return
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            position_ratio = idx / total
            
            # 检查Welcome/Launch是否在开头
            if current_type in ["Welcome", "Launch"] and position_ratio > 0.2:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="warning",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type="Feature",
                    reason=f"{current_type}通常在开头，当前在{position_ratio:.0%}位置"
                ))
            
            # 检查Settings是否在末尾
            if current_type == "Settings" and position_ratio < 0.7:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="info",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=None,
                    reason=f"Settings通常在末尾，当前在{position_ratio:.0%}位置"
                ))
    
    def _check_stage_match(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查类型是否与所属阶段匹配"""
        # 这些类型可以出现在任何阶段，不应被强制修正
        # Onboarding内容可能穿插在各阶段（如目标选择在Welcome阶段、来源调查在Paywall阶段）
        FLEXIBLE_TYPES = ["Onboarding", "Referral", "Paywall", "Permission", "Other"]
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            stage_name = data.get("stage_name", "Unknown")
            
            # 灵活类型可以出现在任何阶段，跳过检查
            if current_type in FLEXIBLE_TYPES:
                continue
            
            # 获取阶段预期类型
            expected_types = STAGE_EXPECTED_TYPES.get(stage_name, [])
            
            if expected_types and current_type not in expected_types and current_type != "Unknown":
                # 计算最可能的正确类型（排除掉灵活类型作为建议）
                suggested = expected_types[0] if expected_types else None
                
                self.issues.append(ValidationIssue(
                    issue_type="stage_mismatch",
                    severity="error",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=suggested,
                    reason=f"在{stage_name}阶段，{current_type}不太符合，预期{expected_types}"
                ))
    
    def _calculate_stats(self, sorted_results: List[Tuple[str, Dict]]) -> Dict:
        """计算统计信息"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        # 计算置信度分布
        confidences = [data.get("confidence", 0) for _, data in sorted_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_screenshots": total,
            "type_distribution": dict(counter),
            "unique_types": len(counter),
            "avg_confidence": avg_confidence,
            "low_confidence_count": sum(1 for c in confidences if c < 0.7)
        }


# ============================================================
# 高级校验：基于AI的二次验证
# ============================================================

class AIValidator:
    """AI辅助校验器（用于可疑结果的二次验证）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key
        self.model = model
        # 延迟初始化
        self.client = None
    
    def verify_suspicious(
        self,
        results: Dict[str, Dict],
        issues: List[ValidationIssue],
        screens_folder: str
    ) -> Dict[str, str]:
        """
        对可疑结果进行AI二次验证
        
        Returns:
            {filename: verified_type}
        """
        # 找出需要验证的文件
        suspicious_files = set()
        for issue in issues:
            if issue.severity == "error" and issue.filename:
                suspicious_files.add(issue.filename)
        
        # TODO: 实现AI二次验证
        # 目前先返回空，表示不进行额外验证
        return {}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = {
        "Screen_001.png": {"index": 1, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.95},
        "Screen_002.png": {"index": 2, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.90},
        "Screen_003.png": {"index": 3, "screen_type": "Feature", "stage_name": "Onboarding", "confidence": 0.85},  # 问题：应该是Onboarding
        "Screen_004.png": {"index": 4, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.92},
        "Screen_005.png": {"index": 5, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.88},
        "Screen_006.png": {"index": 6, "screen_type": "Settings", "stage_name": "Onboarding", "confidence": 0.75},  # 问题：Onboarding阶段不应有Settings
        "Screen_007.png": {"index": 7, "screen_type": "Paywall", "stage_name": "Paywall", "confidence": 0.95},
        "Screen_008.png": {"index": 8, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.90},
        "Screen_009.png": {"index": 9, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.88},
        "Screen_010.png": {"index": 10, "screen_type": "Settings", "stage_name": "Settings", "confidence": 0.92},
    }
    
    # 模拟产品画像和流程结构
    from layer1_product import ProductProfile
    from layer2_structure import FlowStructure, FlowStage
    
    profile = ProductProfile(
        app_name="TestApp",
        app_category="Health",
        sub_category="Meditation",
        target_users="General",
        core_value="Help relax",
        business_model="Subscription",
        estimated_stages=["Welcome", "Onboarding", "Paywall", "Core"],
        visual_style="Minimalist",
        primary_color="Blue",
        confidence=0.9
    )
    
    structure = FlowStructure(
        total_screenshots=10,
        stages=[
            FlowStage(name="Welcome", start_index=1, end_index=2, description="Welcome", expected_types=["Welcome"], screenshot_count=2),
            FlowStage(name="Onboarding", start_index=3, end_index=6, description="Onboarding", expected_types=["Onboarding"], screenshot_count=4),
            FlowStage(name="Paywall", start_index=7, end_index=7, description="Paywall", expected_types=["Paywall"], screenshot_count=1),
            FlowStage(name="Core Features", start_index=8, end_index=9, description="Core", expected_types=["Feature"], screenshot_count=2),
            FlowStage(name="Settings", start_index=10, end_index=10, description="Settings", expected_types=["Settings"], screenshot_count=1),
        ],
        paywall_position="middle",
        onboarding_length="medium",
        has_signup=False,
        has_social=False,
        confidence=0.85
    )
    
    # 运行校验
    validator = SelfValidator(verbose=True)
    fixed_results, validation = validator.validate_and_fix(test_results, profile, structure)
    
    print("\n" + "=" * 60)
    print("Validation Result")
    print("=" * 60)
    print(f"Valid: {validation.is_valid}")
    print(f"Issues: {len(validation.issues)}")
    print(f"Fixes Applied: {len(validation.fixes_applied)}")
    
    for issue in validation.issues:
        print(f"\n  [{issue.severity.upper()}] {issue.filename}")
        print(f"    Type: {issue.issue_type}")
        print(f"    Current: {issue.current_type}")
        print(f"    Suggested: {issue.suggested_type}")
        print(f"    Reason: {issue.reason}")


自我校验模块
分析完成后检查结果的合理性，自动修正异常
"""

import os
import sys
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import Counter

# 导入层级模块
from layer1_product import ProductProfile
from layer2_structure import FlowStructure, FlowStage


# ============================================================
# 校验规则配置
# ============================================================

# 流程连贯性规则：不应该出现的转换
INVALID_TRANSITIONS = {
    "Welcome": ["Settings", "Profile"],           # Welcome后不应直接到Settings
    "Launch": ["Settings", "Profile", "Feature"], # Launch后不应直接到功能页
    "Onboarding": ["Settings"],                   # Onboarding中间不应出现Settings
}

# 阶段预期类型
STAGE_EXPECTED_TYPES = {
    "Welcome": ["Welcome", "Launch"],
    "Launch": ["Launch", "Welcome"],
    "Onboarding": ["Onboarding", "Permission", "SignUp", "Referral"],  # Referral可能穿插
    "SignUp": ["SignUp", "Onboarding"],
    "Paywall": ["Paywall"],
    "Referral": ["Referral", "Social"],  # 新增Referral阶段
    "Home": ["Home", "Feature", "Referral"],  # Home阶段可能有Referral弹窗
    "Core Features": ["Feature", "Content", "Tracking", "Progress", "Home", "Referral"],
    "Content": ["Content", "Feature"],
    "Tracking": ["Tracking", "Feature"],
    "Progress": ["Progress", "Feature"],
    "Social": ["Social", "Feature", "Referral"],  # Social和Referral相关
    "Profile": ["Profile", "Settings"],
    "Settings": ["Settings", "Profile"],
}

# 所有有效的页面类型
VALID_SCREEN_TYPES = [
    "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
    "Paywall", "Referral",  # 新增Referral
    "Home", "Feature", "Content", "Profile", "Settings",
    "Social", "Tracking", "Progress", "Other"
]

# 分布阈值
MAX_SINGLE_TYPE_RATIO = 0.7      # 单一类型不应超过70%
MIN_TYPES_COUNT = 3              # 至少应有3种不同类型


@dataclass
class ValidationIssue:
    """校验问题"""
    issue_type: str              # continuity / distribution / position / stage_mismatch
    severity: str                # error / warning / info
    filename: str
    index: int
    current_type: str
    suggested_type: Optional[str]
    reason: str


@dataclass
class ValidationResult:
    """校验结果"""
    is_valid: bool
    issues: List[ValidationIssue]
    stats: Dict
    fixes_applied: List[Dict]


class SelfValidator:
    """自我校验器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.issues: List[ValidationIssue] = []
    
    def validate(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> ValidationResult:
        """
        执行所有校验
        
        Args:
            results: {filename: classification_dict}
            product_profile: 产品画像
            flow_structure: 流程结构
        
        Returns:
            ValidationResult
        """
        self.issues = []
        
        # 转换为有序列表
        sorted_results = sorted(results.items(), key=lambda x: x[1].get('index', 0))
        
        if self.verbose:
            print("\n  [Validator] Running checks...")
        
        # 1. 流程连贯性检查
        self._check_continuity(sorted_results)
        
        # 2. 分布合理性检查
        self._check_distribution(sorted_results)
        
        # 3. 位置合理性检查
        self._check_position(sorted_results, flow_structure)
        
        # 4. 阶段匹配检查
        self._check_stage_match(sorted_results, flow_structure)
        
        # 统计
        stats = self._calculate_stats(sorted_results)
        
        # 汇总
        error_count = sum(1 for i in self.issues if i.severity == "error")
        warning_count = sum(1 for i in self.issues if i.severity == "warning")
        
        if self.verbose:
            print(f"  [Validator] Found {error_count} errors, {warning_count} warnings")
        
        return ValidationResult(
            is_valid=(error_count == 0),
            issues=self.issues,
            stats=stats,
            fixes_applied=[]
        )
    
    def validate_and_fix(
        self,
        results: Dict[str, Dict],
        product_profile: ProductProfile,
        flow_structure: FlowStructure
    ) -> Tuple[Dict[str, Dict], ValidationResult]:
        """
        校验并自动修复
        
        Returns:
            (修复后的results, ValidationResult)
        """
        # 先校验
        validation = self.validate(results, product_profile, flow_structure)
        
        if validation.is_valid:
            return results, validation
        
        # 自动修复
        fixes_applied = []
        fixed_results = dict(results)
        
        # 保护类型：这些类型不应被自动修改（AI的判断通常是正确的）
        # Onboarding是核心类型，AI基于"受益方判断"识别，不应被覆盖
        PROTECTED_TYPES = ["Onboarding", "Referral", "Paywall"]
        
        for issue in validation.issues:
            if issue.severity == "error" and issue.suggested_type:
                # 应用修复
                if issue.filename in fixed_results:
                    old_type = fixed_results[issue.filename].get("screen_type")
                    
                    # 跳过保护类型
                    if old_type in PROTECTED_TYPES:
                        if self.verbose:
                            print(f"    [SKIP] {issue.filename}: {old_type} is protected")
                        continue
                    
                    fixed_results[issue.filename]["screen_type"] = issue.suggested_type
                    fixed_results[issue.filename]["auto_fixed"] = True
                    fixed_results[issue.filename]["original_type"] = old_type
                    
                    fixes_applied.append({
                        "filename": issue.filename,
                        "old_type": old_type,
                        "new_type": issue.suggested_type,
                        "reason": issue.reason
                    })
                    
                    if self.verbose:
                        print(f"    [FIX] {issue.filename}: {old_type} -> {issue.suggested_type}")
        
        validation.fixes_applied = fixes_applied
        
        if self.verbose:
            print(f"  [Validator] Applied {len(fixes_applied)} fixes")
        
        return fixed_results, validation
    
    def _check_continuity(self, sorted_results: List[Tuple[str, Dict]]):
        """检查流程连贯性"""
        prev_type = None
        prev_filename = None
        
        for filename, data in sorted_results:
            current_type = data.get("screen_type", "Unknown")
            
            if prev_type and prev_type in INVALID_TRANSITIONS:
                invalid_next = INVALID_TRANSITIONS[prev_type]
                if current_type in invalid_next:
                    self.issues.append(ValidationIssue(
                        issue_type="continuity",
                        severity="warning",
                        filename=filename,
                        index=data.get("index", 0),
                        current_type=current_type,
                        suggested_type=None,
                        reason=f"{prev_type}后通常不直接接{current_type}"
                    ))
            
            prev_type = current_type
            prev_filename = filename
    
    def _check_distribution(self, sorted_results: List[Tuple[str, Dict]]):
        """检查类型分布"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        if total == 0:
            return
        
        # 检查单一类型占比
        for type_name, count in counter.items():
            if type_name == "Unknown":
                continue
            ratio = count / total
            if ratio > MAX_SINGLE_TYPE_RATIO:
                self.issues.append(ValidationIssue(
                    issue_type="distribution",
                    severity="warning",
                    filename="",
                    index=0,
                    current_type=type_name,
                    suggested_type=None,
                    reason=f"{type_name}占比{ratio:.0%}，超过{MAX_SINGLE_TYPE_RATIO:.0%}阈值"
                ))
        
        # 检查类型多样性
        unique_types = len([t for t in counter.keys() if t != "Unknown"])
        if unique_types < MIN_TYPES_COUNT and total > 10:
            self.issues.append(ValidationIssue(
                issue_type="distribution",
                severity="info",
                filename="",
                index=0,
                current_type="",
                suggested_type=None,
                reason=f"类型多样性不足：只有{unique_types}种类型"
            ))
    
    def _check_position(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查位置合理性"""
        total = len(sorted_results)
        if total == 0:
            return
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            position_ratio = idx / total
            
            # 检查Welcome/Launch是否在开头
            if current_type in ["Welcome", "Launch"] and position_ratio > 0.2:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="warning",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type="Feature",
                    reason=f"{current_type}通常在开头，当前在{position_ratio:.0%}位置"
                ))
            
            # 检查Settings是否在末尾
            if current_type == "Settings" and position_ratio < 0.7:
                self.issues.append(ValidationIssue(
                    issue_type="position",
                    severity="info",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=None,
                    reason=f"Settings通常在末尾，当前在{position_ratio:.0%}位置"
                ))
    
    def _check_stage_match(self, sorted_results: List[Tuple[str, Dict]], flow_structure: FlowStructure):
        """检查类型是否与所属阶段匹配"""
        # 这些类型可以出现在任何阶段，不应被强制修正
        # Onboarding内容可能穿插在各阶段（如目标选择在Welcome阶段、来源调查在Paywall阶段）
        FLEXIBLE_TYPES = ["Onboarding", "Referral", "Paywall", "Permission", "Other"]
        
        for filename, data in sorted_results:
            idx = data.get("index", 0)
            current_type = data.get("screen_type", "Unknown")
            stage_name = data.get("stage_name", "Unknown")
            
            # 灵活类型可以出现在任何阶段，跳过检查
            if current_type in FLEXIBLE_TYPES:
                continue
            
            # 获取阶段预期类型
            expected_types = STAGE_EXPECTED_TYPES.get(stage_name, [])
            
            if expected_types and current_type not in expected_types and current_type != "Unknown":
                # 计算最可能的正确类型（排除掉灵活类型作为建议）
                suggested = expected_types[0] if expected_types else None
                
                self.issues.append(ValidationIssue(
                    issue_type="stage_mismatch",
                    severity="error",
                    filename=filename,
                    index=idx,
                    current_type=current_type,
                    suggested_type=suggested,
                    reason=f"在{stage_name}阶段，{current_type}不太符合，预期{expected_types}"
                ))
    
    def _calculate_stats(self, sorted_results: List[Tuple[str, Dict]]) -> Dict:
        """计算统计信息"""
        types = [data.get("screen_type", "Unknown") for _, data in sorted_results]
        counter = Counter(types)
        total = len(types)
        
        # 计算置信度分布
        confidences = [data.get("confidence", 0) for _, data in sorted_results]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_screenshots": total,
            "type_distribution": dict(counter),
            "unique_types": len(counter),
            "avg_confidence": avg_confidence,
            "low_confidence_count": sum(1 for c in confidences if c < 0.7)
        }


# ============================================================
# 高级校验：基于AI的二次验证
# ============================================================

class AIValidator:
    """AI辅助校验器（用于可疑结果的二次验证）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-opus-4-5-20251101"):
        self.api_key = api_key
        self.model = model
        # 延迟初始化
        self.client = None
    
    def verify_suspicious(
        self,
        results: Dict[str, Dict],
        issues: List[ValidationIssue],
        screens_folder: str
    ) -> Dict[str, str]:
        """
        对可疑结果进行AI二次验证
        
        Returns:
            {filename: verified_type}
        """
        # 找出需要验证的文件
        suspicious_files = set()
        for issue in issues:
            if issue.severity == "error" and issue.filename:
                suspicious_files.add(issue.filename)
        
        # TODO: 实现AI二次验证
        # 目前先返回空，表示不进行额外验证
        return {}


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    # 模拟测试数据
    test_results = {
        "Screen_001.png": {"index": 1, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.95},
        "Screen_002.png": {"index": 2, "screen_type": "Welcome", "stage_name": "Welcome", "confidence": 0.90},
        "Screen_003.png": {"index": 3, "screen_type": "Feature", "stage_name": "Onboarding", "confidence": 0.85},  # 问题：应该是Onboarding
        "Screen_004.png": {"index": 4, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.92},
        "Screen_005.png": {"index": 5, "screen_type": "Onboarding", "stage_name": "Onboarding", "confidence": 0.88},
        "Screen_006.png": {"index": 6, "screen_type": "Settings", "stage_name": "Onboarding", "confidence": 0.75},  # 问题：Onboarding阶段不应有Settings
        "Screen_007.png": {"index": 7, "screen_type": "Paywall", "stage_name": "Paywall", "confidence": 0.95},
        "Screen_008.png": {"index": 8, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.90},
        "Screen_009.png": {"index": 9, "screen_type": "Feature", "stage_name": "Core Features", "confidence": 0.88},
        "Screen_010.png": {"index": 10, "screen_type": "Settings", "stage_name": "Settings", "confidence": 0.92},
    }
    
    # 模拟产品画像和流程结构
    from layer1_product import ProductProfile
    from layer2_structure import FlowStructure, FlowStage
    
    profile = ProductProfile(
        app_name="TestApp",
        app_category="Health",
        sub_category="Meditation",
        target_users="General",
        core_value="Help relax",
        business_model="Subscription",
        estimated_stages=["Welcome", "Onboarding", "Paywall", "Core"],
        visual_style="Minimalist",
        primary_color="Blue",
        confidence=0.9
    )
    
    structure = FlowStructure(
        total_screenshots=10,
        stages=[
            FlowStage(name="Welcome", start_index=1, end_index=2, description="Welcome", expected_types=["Welcome"], screenshot_count=2),
            FlowStage(name="Onboarding", start_index=3, end_index=6, description="Onboarding", expected_types=["Onboarding"], screenshot_count=4),
            FlowStage(name="Paywall", start_index=7, end_index=7, description="Paywall", expected_types=["Paywall"], screenshot_count=1),
            FlowStage(name="Core Features", start_index=8, end_index=9, description="Core", expected_types=["Feature"], screenshot_count=2),
            FlowStage(name="Settings", start_index=10, end_index=10, description="Settings", expected_types=["Settings"], screenshot_count=1),
        ],
        paywall_position="middle",
        onboarding_length="medium",
        has_signup=False,
        has_social=False,
        confidence=0.85
    )
    
    # 运行校验
    validator = SelfValidator(verbose=True)
    fixed_results, validation = validator.validate_and_fix(test_results, profile, structure)
    
    print("\n" + "=" * 60)
    print("Validation Result")
    print("=" * 60)
    print(f"Valid: {validation.is_valid}")
    print(f"Issues: {len(validation.issues)}")
    print(f"Fixes Applied: {len(validation.fixes_applied)}")
    
    for issue in validation.issues:
        print(f"\n  [{issue.severity.upper()}] {issue.filename}")
        print(f"    Type: {issue.issue_type}")
        print(f"    Current: {issue.current_type}")
        print(f"    Suggested: {issue.suggested_type}")
        print(f"    Reason: {issue.reason}")

