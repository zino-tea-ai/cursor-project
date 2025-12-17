# -*- coding: utf-8 -*-
"""
验证器模块 - 自动回测和验证AI分析结果
实现三层验证：关键词验证、位置验证、序列验证
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter

from validation_rules import (
    SCREEN_TYPES, KEYWORD_RULES, POSITION_RULES, SEQUENCE_RULES,
    CONFIDENCE_THRESHOLDS, get_keywords_for_type, get_negative_keywords_for_type,
    validate_position, check_sequence
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationResult:
    """单个截图的验证结果"""
    filename: str
    original_type: str
    original_confidence: float
    
    # 验证结果
    keyword_score: float          # 关键词匹配分数 0-1
    position_score: float         # 位置合理性分数 0-1
    consistency_score: float      # 一致性分数 0-1
    
    # 最终结果
    final_confidence: float       # 综合置信度 0-1
    validation_status: str        # "pass" | "review" | "fail"
    suggested_type: Optional[str] # 建议的类型（如果有）
    issues: List[str] = field(default_factory=list)  # 发现的问题


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    project_name: str
    total_screenshots: int
    
    # 统计
    pass_count: int               # 高置信度通过
    review_count: int             # 需要复查
    fail_count: int               # 低置信度需人工
    
    # 详细结果
    results: Dict[str, ValidationResult]
    
    # 序列验证
    sequence_valid: bool
    sequence_issues: List[str]
    
    # 类型分布
    type_distribution: Dict[str, int]
    
    # 问题汇总
    all_issues: List[str]


# ============================================================
# 验证器类
# ============================================================

class ResultValidator:
    """AI分析结果验证器"""
    
    def __init__(self, analysis_results: Dict):
        """
        初始化验证器
        
        Args:
            analysis_results: AI分析结果字典，格式为 {filename: result_dict}
        """
        self.results = analysis_results
        self.filenames = sorted(analysis_results.keys())
        self.total = len(self.filenames)
    
    def _calculate_keyword_score(self, result: Dict) -> Tuple[float, List[str]]:
        """
        计算关键词匹配分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        keywords_found = result.get("keywords_found", [])
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        ui_elements = result.get("ui_elements", [])
        
        issues = []
        
        # 获取该类型应该有的关键词
        expected_keywords = get_keywords_for_type(screen_type)
        negative_keywords = get_negative_keywords_for_type(screen_type)
        
        if not expected_keywords:
            return 0.5, ["No keyword rules for this type"]
        
        # 检查正面关键词
        found_positive = 0
        for kw in expected_keywords:
            kw_lower = kw.lower()
            if (kw_lower in description or 
                kw_lower in [k.lower() for k in keywords_found] or
                kw_lower in [e.lower() for e in ui_elements]):
                found_positive += 1
        
        positive_ratio = found_positive / min(5, len(expected_keywords))  # 最多检查5个
        
        # 检查负面关键词
        found_negative = 0
        for kw in negative_keywords:
            kw_lower = kw.lower()
            if kw_lower in description or kw_lower in [k.lower() for k in keywords_found]:
                found_negative += 1
                issues.append(f"Found unexpected keyword '{kw}' for {screen_type}")
        
        negative_penalty = found_negative * 0.15
        
        # 计算最终分数
        score = max(0, min(1, positive_ratio - negative_penalty))
        
        if positive_ratio < 0.3:
            issues.append(f"Few expected keywords found for {screen_type}")
        
        return score, issues
    
    def _calculate_position_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算位置合理性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        
        # 获取位置（从1开始）
        position = self.filenames.index(filename) + 1
        
        is_valid, adjustment, reason = validate_position(screen_type, position, self.total)
        
        issues = []
        if not is_valid:
            issues.append(reason)
        
        # 基础分 + 调整
        score = 0.7 + adjustment if is_valid else 0.5 + adjustment
        score = max(0, min(1, score))
        
        return score, issues
    
    def _calculate_consistency_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算与相邻截图的一致性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        position = self.filenames.index(filename)
        
        issues = []
        
        # 获取相邻截图的类型
        neighbors = []
        for offset in [-2, -1, 1, 2]:
            neighbor_pos = position + offset
            if 0 <= neighbor_pos < self.total:
                neighbor_file = self.filenames[neighbor_pos]
                neighbor_type = self.results[neighbor_file].get("screen_type", "Unknown")
                neighbors.append(neighbor_type)
        
        if not neighbors:
            return 0.7, []
        
        # 检查是否与相邻截图类型一致
        same_type_count = sum(1 for t in neighbors if t == screen_type)
        consistency = same_type_count / len(neighbors)
        
        # 检查是否是合理的类型变化
        # 例如：Onboarding -> Paywall 是合理的
        # 但 Home -> Launch 是不合理的
        reasonable_transitions = {
            ("Launch", "Welcome"), ("Launch", "Permission"), ("Launch", "SignUp"),
            ("Welcome", "SignUp"), ("Welcome", "Onboarding"), ("Welcome", "Permission"),
            ("SignUp", "Onboarding"), ("SignUp", "Home"),
            ("Permission", "Onboarding"), ("Permission", "Home"),
            ("Onboarding", "Paywall"), ("Onboarding", "Home"),
            ("Paywall", "Home"), ("Paywall", "Feature"),
            ("Home", "Feature"), ("Home", "Settings"), ("Home", "Profile"),
            ("Feature", "Feature"), ("Feature", "Home"),
        }
        
        unreasonable_transitions = {
            ("Home", "Launch"), ("Home", "Onboarding"),
            ("Settings", "Launch"), ("Settings", "Onboarding"),
            ("Feature", "Launch"),
        }
        
        # 检查与前一个截图的转换
        if position > 0:
            prev_file = self.filenames[position - 1]
            prev_type = self.results[prev_file].get("screen_type", "Unknown")
            
            transition = (prev_type, screen_type)
            if transition in unreasonable_transitions:
                issues.append(f"Unusual transition: {prev_type} -> {screen_type}")
                consistency -= 0.3
        
        score = max(0, min(1, 0.5 + consistency * 0.5))
        
        return score, issues
    
    def validate_single(self, filename: str) -> ValidationResult:
        """
        验证单个截图的分析结果
        
        信任AI判断：AI原始置信度是最重要的指标
        其他验证只作为辅助参考
        """
        result = self.results.get(filename, {})
        
        original_type = result.get("screen_type", "Unknown")
        original_confidence = result.get("confidence", 0.5)
        
        # 如果AI原始置信度很高(>=88%)，直接通过
        if original_confidence >= 0.88:
            return ValidationResult(
                filename=filename,
                original_type=original_type,
                original_confidence=original_confidence,
                keyword_score=1.0,
                position_score=1.0,
                consistency_score=1.0,
                final_confidence=original_confidence,
                validation_status="pass",
                suggested_type=None,
                issues=[]
            )
        
        # 对于较低置信度的结果，进行辅助验证
        keyword_score, keyword_issues = self._calculate_keyword_score(result)
        position_score, position_issues = self._calculate_position_score(filename, result)
        consistency_score, consistency_issues = self._calculate_consistency_score(filename, result)
        
        # 合并问题（仅作为参考，不影响主要判断）
        all_issues = keyword_issues + position_issues + consistency_issues
        
        # 计算综合置信度
        # 权重: AI原始置信度 80%, 其他验证 20%
        aux_score = (keyword_score * 0.4 + position_score * 0.3 + consistency_score * 0.3)
        final_confidence = original_confidence * 0.80 + aux_score * 0.20
        
        # 确定验证状态（基于AI原始置信度）
        if original_confidence >= 0.85:
            status = "pass"
        elif original_confidence >= 0.70:
            status = "review"
        else:
            status = "fail"
        
        # 建议类型（仅当置信度很低时）
        suggested_type = None
        if original_confidence < 0.60:
            suggested_type = self._suggest_better_type(result)
        
        return ValidationResult(
            filename=filename,
            original_type=original_type,
            original_confidence=original_confidence,
            keyword_score=keyword_score,
            position_score=position_score,
            consistency_score=consistency_score,
            final_confidence=final_confidence,
            validation_status=status,
            suggested_type=suggested_type,
            issues=all_issues
        )
    
    def _suggest_better_type(self, result: Dict) -> Optional[str]:
        """根据关键词建议更好的类型"""
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        keywords_found = [k.lower() for k in result.get("keywords_found", [])]
        
        best_type = None
        best_score = 0
        
        for screen_type, rules in KEYWORD_RULES.items():
            score = 0
            for kw in rules.get("visual_keywords", []):
                if kw.lower() in description or kw.lower() in keywords_found:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_type = screen_type
        
        return best_type if best_score >= 2 else None
    
    def validate_sequence(self) -> Tuple[bool, List[str]]:
        """验证整体序列是否合理"""
        # 获取所有类型按顺序
        types_in_order = []
        for filename in self.filenames:
            screen_type = self.results[filename].get("screen_type", "Unknown")
            if not types_in_order or types_in_order[-1] != screen_type:
                types_in_order.append(screen_type)
        
        return check_sequence(types_in_order)
    
    def validate_all(self) -> BatchValidationResult:
        """验证所有分析结果"""
        results = {}
        pass_count = 0
        review_count = 0
        fail_count = 0
        all_issues = []
        
        print("\n[VALIDATE] Starting validation...")
        print("-" * 50)
        
        for filename in self.filenames:
            validation = self.validate_single(filename)
            results[filename] = validation
            
            if validation.validation_status == "pass":
                pass_count += 1
                status_icon = "PASS"
            elif validation.validation_status == "review":
                review_count += 1
                status_icon = "REVW"
            else:
                fail_count += 1
                status_icon = "FAIL"
            
            # 收集问题
            for issue in validation.issues:
                all_issues.append(f"{filename}: {issue}")
            
            # 打印状态
            conf_str = f"{validation.final_confidence:.0%}"
            print(f"[{status_icon}] {filename[:35]:35s} {validation.original_type:15s} -> {conf_str}")
        
        # 序列验证
        sequence_valid, sequence_issues = self.validate_sequence()
        all_issues.extend([f"[Sequence] {issue}" for issue in sequence_issues])
        
        # 类型分布
        type_distribution = Counter(
            self.results[f].get("screen_type", "Unknown") 
            for f in self.filenames
        )
        
        print("-" * 50)
        print(f"Validation done: PASS {pass_count} | REVIEW {review_count} | FAIL {fail_count}")
        
        return BatchValidationResult(
            project_name="",  # 由调用者填充
            total_screenshots=self.total,
            pass_count=pass_count,
            review_count=review_count,
            fail_count=fail_count,
            results={k: asdict(v) for k, v in results.items()},
            sequence_valid=sequence_valid,
            sequence_issues=sequence_issues,
            type_distribution=dict(type_distribution),
            all_issues=all_issues
        )


# ============================================================
# 交叉验证（使用AI二次确认）
# ============================================================

class CrossValidator:
    """交叉验证器 - 使用AI二次确认低置信度结果"""
    
    def __init__(self, analyzer, threshold: float = 0.7):
        """
        Args:
            analyzer: AIScreenshotAnalyzer 实例
            threshold: 需要二次验证的置信度阈值
        """
        self.analyzer = analyzer
        self.threshold = threshold
    
    def cross_validate(
        self, 
        validation_results: Dict[str, ValidationResult],
        image_folder: str,
        max_verify: int = 20
    ) -> Dict[str, Dict]:
        """
        对低置信度结果进行交叉验证
        
        Args:
            validation_results: 验证结果
            image_folder: 图片文件夹
            max_verify: 最多验证多少张
        
        Returns:
            交叉验证结果
        """
        # 找出需要二次验证的截图
        to_verify = []
        for filename, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get("final_confidence", 1.0)
            else:
                confidence = result.final_confidence
            
            if confidence < self.threshold:
                to_verify.append(filename)
        
        if not to_verify:
            print("[OK] All results have high confidence, no cross-validation needed")
            return {}
        
        # 限制数量
        to_verify = to_verify[:max_verify]
        
        print(f"\n[CROSS] Starting cross-validation ({len(to_verify)} low-confidence screenshots)...")
        
        cross_results = {}
        for filename in to_verify:
            image_path = os.path.join(image_folder, filename)
            
            if isinstance(validation_results[filename], dict):
                original_type = validation_results[filename].get("original_type", "Unknown")
            else:
                original_type = validation_results[filename].original_type
            
            verify_result = self.analyzer.verify_result(image_path, original_type)
            cross_results[filename] = verify_result
            
            is_correct = verify_result.get("is_correct")
            if is_correct is True:
                print(f"  [OK] {filename}: confirmed as {original_type}")
            elif is_correct is False:
                suggested = verify_result.get("suggested_type", "?")
                print(f"  [CHANGE] {filename}: suggest change to {suggested}")
            else:
                print(f"  [WARN] {filename}: verification failed")
        
        return cross_results


# ============================================================
# 便捷函数
# ============================================================

def validate_analysis_results(analysis_file: str) -> BatchValidationResult:
    """
    验证分析结果文件
    
    Args:
        analysis_file: AI分析结果JSON文件路径
    
    Returns:
        BatchValidationResult
    """
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取结果部分
    if "results" in data:
        results = data["results"]
        project_name = data.get("project_name", "Unknown")
    else:
        results = data
        project_name = "Unknown"
    
    validator = ResultValidator(results)
    batch_result = validator.validate_all()
    batch_result.project_name = project_name
    
    return batch_result


def save_validation_report(validation_result: BatchValidationResult, output_file: str):
    """保存验证报告为JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(validation_result), f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Validation report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI分析结果验证器")
    parser.add_argument("analysis_file", type=str, help="AI分析结果JSON文件")
    parser.add_argument("--output", type=str, help="输出验证报告文件")
    
    args = parser.parse_args()
    
    result = validate_analysis_results(args.analysis_file)
    
    if args.output:
        save_validation_report(result, args.output)
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("验证摘要")
    print("=" * 50)
    print(f"总截图数: {result.total_screenshots}")
    print(f"PASS (high confidence): {result.pass_count} ({result.pass_count/result.total_screenshots:.0%})")
    print(f"REVIEW (medium): {result.review_count} ({result.review_count/result.total_screenshots:.0%})")
    print(f"FAIL (low): {result.fail_count} ({result.fail_count/result.total_screenshots:.0%})")
    print(f"Sequence validation: {'PASS' if result.sequence_valid else 'ISSUES FOUND'}")
    
    if result.all_issues:
        print(f"\n发现 {len(result.all_issues)} 个问题")


验证器模块 - 自动回测和验证AI分析结果
实现三层验证：关键词验证、位置验证、序列验证
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter

from validation_rules import (
    SCREEN_TYPES, KEYWORD_RULES, POSITION_RULES, SEQUENCE_RULES,
    CONFIDENCE_THRESHOLDS, get_keywords_for_type, get_negative_keywords_for_type,
    validate_position, check_sequence
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationResult:
    """单个截图的验证结果"""
    filename: str
    original_type: str
    original_confidence: float
    
    # 验证结果
    keyword_score: float          # 关键词匹配分数 0-1
    position_score: float         # 位置合理性分数 0-1
    consistency_score: float      # 一致性分数 0-1
    
    # 最终结果
    final_confidence: float       # 综合置信度 0-1
    validation_status: str        # "pass" | "review" | "fail"
    suggested_type: Optional[str] # 建议的类型（如果有）
    issues: List[str] = field(default_factory=list)  # 发现的问题


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    project_name: str
    total_screenshots: int
    
    # 统计
    pass_count: int               # 高置信度通过
    review_count: int             # 需要复查
    fail_count: int               # 低置信度需人工
    
    # 详细结果
    results: Dict[str, ValidationResult]
    
    # 序列验证
    sequence_valid: bool
    sequence_issues: List[str]
    
    # 类型分布
    type_distribution: Dict[str, int]
    
    # 问题汇总
    all_issues: List[str]


# ============================================================
# 验证器类
# ============================================================

class ResultValidator:
    """AI分析结果验证器"""
    
    def __init__(self, analysis_results: Dict):
        """
        初始化验证器
        
        Args:
            analysis_results: AI分析结果字典，格式为 {filename: result_dict}
        """
        self.results = analysis_results
        self.filenames = sorted(analysis_results.keys())
        self.total = len(self.filenames)
    
    def _calculate_keyword_score(self, result: Dict) -> Tuple[float, List[str]]:
        """
        计算关键词匹配分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        keywords_found = result.get("keywords_found", [])
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        ui_elements = result.get("ui_elements", [])
        
        issues = []
        
        # 获取该类型应该有的关键词
        expected_keywords = get_keywords_for_type(screen_type)
        negative_keywords = get_negative_keywords_for_type(screen_type)
        
        if not expected_keywords:
            return 0.5, ["No keyword rules for this type"]
        
        # 检查正面关键词
        found_positive = 0
        for kw in expected_keywords:
            kw_lower = kw.lower()
            if (kw_lower in description or 
                kw_lower in [k.lower() for k in keywords_found] or
                kw_lower in [e.lower() for e in ui_elements]):
                found_positive += 1
        
        positive_ratio = found_positive / min(5, len(expected_keywords))  # 最多检查5个
        
        # 检查负面关键词
        found_negative = 0
        for kw in negative_keywords:
            kw_lower = kw.lower()
            if kw_lower in description or kw_lower in [k.lower() for k in keywords_found]:
                found_negative += 1
                issues.append(f"Found unexpected keyword '{kw}' for {screen_type}")
        
        negative_penalty = found_negative * 0.15
        
        # 计算最终分数
        score = max(0, min(1, positive_ratio - negative_penalty))
        
        if positive_ratio < 0.3:
            issues.append(f"Few expected keywords found for {screen_type}")
        
        return score, issues
    
    def _calculate_position_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算位置合理性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        
        # 获取位置（从1开始）
        position = self.filenames.index(filename) + 1
        
        is_valid, adjustment, reason = validate_position(screen_type, position, self.total)
        
        issues = []
        if not is_valid:
            issues.append(reason)
        
        # 基础分 + 调整
        score = 0.7 + adjustment if is_valid else 0.5 + adjustment
        score = max(0, min(1, score))
        
        return score, issues
    
    def _calculate_consistency_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算与相邻截图的一致性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        position = self.filenames.index(filename)
        
        issues = []
        
        # 获取相邻截图的类型
        neighbors = []
        for offset in [-2, -1, 1, 2]:
            neighbor_pos = position + offset
            if 0 <= neighbor_pos < self.total:
                neighbor_file = self.filenames[neighbor_pos]
                neighbor_type = self.results[neighbor_file].get("screen_type", "Unknown")
                neighbors.append(neighbor_type)
        
        if not neighbors:
            return 0.7, []
        
        # 检查是否与相邻截图类型一致
        same_type_count = sum(1 for t in neighbors if t == screen_type)
        consistency = same_type_count / len(neighbors)
        
        # 检查是否是合理的类型变化
        # 例如：Onboarding -> Paywall 是合理的
        # 但 Home -> Launch 是不合理的
        reasonable_transitions = {
            ("Launch", "Welcome"), ("Launch", "Permission"), ("Launch", "SignUp"),
            ("Welcome", "SignUp"), ("Welcome", "Onboarding"), ("Welcome", "Permission"),
            ("SignUp", "Onboarding"), ("SignUp", "Home"),
            ("Permission", "Onboarding"), ("Permission", "Home"),
            ("Onboarding", "Paywall"), ("Onboarding", "Home"),
            ("Paywall", "Home"), ("Paywall", "Feature"),
            ("Home", "Feature"), ("Home", "Settings"), ("Home", "Profile"),
            ("Feature", "Feature"), ("Feature", "Home"),
        }
        
        unreasonable_transitions = {
            ("Home", "Launch"), ("Home", "Onboarding"),
            ("Settings", "Launch"), ("Settings", "Onboarding"),
            ("Feature", "Launch"),
        }
        
        # 检查与前一个截图的转换
        if position > 0:
            prev_file = self.filenames[position - 1]
            prev_type = self.results[prev_file].get("screen_type", "Unknown")
            
            transition = (prev_type, screen_type)
            if transition in unreasonable_transitions:
                issues.append(f"Unusual transition: {prev_type} -> {screen_type}")
                consistency -= 0.3
        
        score = max(0, min(1, 0.5 + consistency * 0.5))
        
        return score, issues
    
    def validate_single(self, filename: str) -> ValidationResult:
        """
        验证单个截图的分析结果
        
        信任AI判断：AI原始置信度是最重要的指标
        其他验证只作为辅助参考
        """
        result = self.results.get(filename, {})
        
        original_type = result.get("screen_type", "Unknown")
        original_confidence = result.get("confidence", 0.5)
        
        # 如果AI原始置信度很高(>=88%)，直接通过
        if original_confidence >= 0.88:
            return ValidationResult(
                filename=filename,
                original_type=original_type,
                original_confidence=original_confidence,
                keyword_score=1.0,
                position_score=1.0,
                consistency_score=1.0,
                final_confidence=original_confidence,
                validation_status="pass",
                suggested_type=None,
                issues=[]
            )
        
        # 对于较低置信度的结果，进行辅助验证
        keyword_score, keyword_issues = self._calculate_keyword_score(result)
        position_score, position_issues = self._calculate_position_score(filename, result)
        consistency_score, consistency_issues = self._calculate_consistency_score(filename, result)
        
        # 合并问题（仅作为参考，不影响主要判断）
        all_issues = keyword_issues + position_issues + consistency_issues
        
        # 计算综合置信度
        # 权重: AI原始置信度 80%, 其他验证 20%
        aux_score = (keyword_score * 0.4 + position_score * 0.3 + consistency_score * 0.3)
        final_confidence = original_confidence * 0.80 + aux_score * 0.20
        
        # 确定验证状态（基于AI原始置信度）
        if original_confidence >= 0.85:
            status = "pass"
        elif original_confidence >= 0.70:
            status = "review"
        else:
            status = "fail"
        
        # 建议类型（仅当置信度很低时）
        suggested_type = None
        if original_confidence < 0.60:
            suggested_type = self._suggest_better_type(result)
        
        return ValidationResult(
            filename=filename,
            original_type=original_type,
            original_confidence=original_confidence,
            keyword_score=keyword_score,
            position_score=position_score,
            consistency_score=consistency_score,
            final_confidence=final_confidence,
            validation_status=status,
            suggested_type=suggested_type,
            issues=all_issues
        )
    
    def _suggest_better_type(self, result: Dict) -> Optional[str]:
        """根据关键词建议更好的类型"""
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        keywords_found = [k.lower() for k in result.get("keywords_found", [])]
        
        best_type = None
        best_score = 0
        
        for screen_type, rules in KEYWORD_RULES.items():
            score = 0
            for kw in rules.get("visual_keywords", []):
                if kw.lower() in description or kw.lower() in keywords_found:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_type = screen_type
        
        return best_type if best_score >= 2 else None
    
    def validate_sequence(self) -> Tuple[bool, List[str]]:
        """验证整体序列是否合理"""
        # 获取所有类型按顺序
        types_in_order = []
        for filename in self.filenames:
            screen_type = self.results[filename].get("screen_type", "Unknown")
            if not types_in_order or types_in_order[-1] != screen_type:
                types_in_order.append(screen_type)
        
        return check_sequence(types_in_order)
    
    def validate_all(self) -> BatchValidationResult:
        """验证所有分析结果"""
        results = {}
        pass_count = 0
        review_count = 0
        fail_count = 0
        all_issues = []
        
        print("\n[VALIDATE] Starting validation...")
        print("-" * 50)
        
        for filename in self.filenames:
            validation = self.validate_single(filename)
            results[filename] = validation
            
            if validation.validation_status == "pass":
                pass_count += 1
                status_icon = "PASS"
            elif validation.validation_status == "review":
                review_count += 1
                status_icon = "REVW"
            else:
                fail_count += 1
                status_icon = "FAIL"
            
            # 收集问题
            for issue in validation.issues:
                all_issues.append(f"{filename}: {issue}")
            
            # 打印状态
            conf_str = f"{validation.final_confidence:.0%}"
            print(f"[{status_icon}] {filename[:35]:35s} {validation.original_type:15s} -> {conf_str}")
        
        # 序列验证
        sequence_valid, sequence_issues = self.validate_sequence()
        all_issues.extend([f"[Sequence] {issue}" for issue in sequence_issues])
        
        # 类型分布
        type_distribution = Counter(
            self.results[f].get("screen_type", "Unknown") 
            for f in self.filenames
        )
        
        print("-" * 50)
        print(f"Validation done: PASS {pass_count} | REVIEW {review_count} | FAIL {fail_count}")
        
        return BatchValidationResult(
            project_name="",  # 由调用者填充
            total_screenshots=self.total,
            pass_count=pass_count,
            review_count=review_count,
            fail_count=fail_count,
            results={k: asdict(v) for k, v in results.items()},
            sequence_valid=sequence_valid,
            sequence_issues=sequence_issues,
            type_distribution=dict(type_distribution),
            all_issues=all_issues
        )


# ============================================================
# 交叉验证（使用AI二次确认）
# ============================================================

class CrossValidator:
    """交叉验证器 - 使用AI二次确认低置信度结果"""
    
    def __init__(self, analyzer, threshold: float = 0.7):
        """
        Args:
            analyzer: AIScreenshotAnalyzer 实例
            threshold: 需要二次验证的置信度阈值
        """
        self.analyzer = analyzer
        self.threshold = threshold
    
    def cross_validate(
        self, 
        validation_results: Dict[str, ValidationResult],
        image_folder: str,
        max_verify: int = 20
    ) -> Dict[str, Dict]:
        """
        对低置信度结果进行交叉验证
        
        Args:
            validation_results: 验证结果
            image_folder: 图片文件夹
            max_verify: 最多验证多少张
        
        Returns:
            交叉验证结果
        """
        # 找出需要二次验证的截图
        to_verify = []
        for filename, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get("final_confidence", 1.0)
            else:
                confidence = result.final_confidence
            
            if confidence < self.threshold:
                to_verify.append(filename)
        
        if not to_verify:
            print("[OK] All results have high confidence, no cross-validation needed")
            return {}
        
        # 限制数量
        to_verify = to_verify[:max_verify]
        
        print(f"\n[CROSS] Starting cross-validation ({len(to_verify)} low-confidence screenshots)...")
        
        cross_results = {}
        for filename in to_verify:
            image_path = os.path.join(image_folder, filename)
            
            if isinstance(validation_results[filename], dict):
                original_type = validation_results[filename].get("original_type", "Unknown")
            else:
                original_type = validation_results[filename].original_type
            
            verify_result = self.analyzer.verify_result(image_path, original_type)
            cross_results[filename] = verify_result
            
            is_correct = verify_result.get("is_correct")
            if is_correct is True:
                print(f"  [OK] {filename}: confirmed as {original_type}")
            elif is_correct is False:
                suggested = verify_result.get("suggested_type", "?")
                print(f"  [CHANGE] {filename}: suggest change to {suggested}")
            else:
                print(f"  [WARN] {filename}: verification failed")
        
        return cross_results


# ============================================================
# 便捷函数
# ============================================================

def validate_analysis_results(analysis_file: str) -> BatchValidationResult:
    """
    验证分析结果文件
    
    Args:
        analysis_file: AI分析结果JSON文件路径
    
    Returns:
        BatchValidationResult
    """
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取结果部分
    if "results" in data:
        results = data["results"]
        project_name = data.get("project_name", "Unknown")
    else:
        results = data
        project_name = "Unknown"
    
    validator = ResultValidator(results)
    batch_result = validator.validate_all()
    batch_result.project_name = project_name
    
    return batch_result


def save_validation_report(validation_result: BatchValidationResult, output_file: str):
    """保存验证报告为JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(validation_result), f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Validation report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI分析结果验证器")
    parser.add_argument("analysis_file", type=str, help="AI分析结果JSON文件")
    parser.add_argument("--output", type=str, help="输出验证报告文件")
    
    args = parser.parse_args()
    
    result = validate_analysis_results(args.analysis_file)
    
    if args.output:
        save_validation_report(result, args.output)
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("验证摘要")
    print("=" * 50)
    print(f"总截图数: {result.total_screenshots}")
    print(f"PASS (high confidence): {result.pass_count} ({result.pass_count/result.total_screenshots:.0%})")
    print(f"REVIEW (medium): {result.review_count} ({result.review_count/result.total_screenshots:.0%})")
    print(f"FAIL (low): {result.fail_count} ({result.fail_count/result.total_screenshots:.0%})")
    print(f"Sequence validation: {'PASS' if result.sequence_valid else 'ISSUES FOUND'}")
    
    if result.all_issues:
        print(f"\n发现 {len(result.all_issues)} 个问题")


验证器模块 - 自动回测和验证AI分析结果
实现三层验证：关键词验证、位置验证、序列验证
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter

from validation_rules import (
    SCREEN_TYPES, KEYWORD_RULES, POSITION_RULES, SEQUENCE_RULES,
    CONFIDENCE_THRESHOLDS, get_keywords_for_type, get_negative_keywords_for_type,
    validate_position, check_sequence
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationResult:
    """单个截图的验证结果"""
    filename: str
    original_type: str
    original_confidence: float
    
    # 验证结果
    keyword_score: float          # 关键词匹配分数 0-1
    position_score: float         # 位置合理性分数 0-1
    consistency_score: float      # 一致性分数 0-1
    
    # 最终结果
    final_confidence: float       # 综合置信度 0-1
    validation_status: str        # "pass" | "review" | "fail"
    suggested_type: Optional[str] # 建议的类型（如果有）
    issues: List[str] = field(default_factory=list)  # 发现的问题


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    project_name: str
    total_screenshots: int
    
    # 统计
    pass_count: int               # 高置信度通过
    review_count: int             # 需要复查
    fail_count: int               # 低置信度需人工
    
    # 详细结果
    results: Dict[str, ValidationResult]
    
    # 序列验证
    sequence_valid: bool
    sequence_issues: List[str]
    
    # 类型分布
    type_distribution: Dict[str, int]
    
    # 问题汇总
    all_issues: List[str]


# ============================================================
# 验证器类
# ============================================================

class ResultValidator:
    """AI分析结果验证器"""
    
    def __init__(self, analysis_results: Dict):
        """
        初始化验证器
        
        Args:
            analysis_results: AI分析结果字典，格式为 {filename: result_dict}
        """
        self.results = analysis_results
        self.filenames = sorted(analysis_results.keys())
        self.total = len(self.filenames)
    
    def _calculate_keyword_score(self, result: Dict) -> Tuple[float, List[str]]:
        """
        计算关键词匹配分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        keywords_found = result.get("keywords_found", [])
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        ui_elements = result.get("ui_elements", [])
        
        issues = []
        
        # 获取该类型应该有的关键词
        expected_keywords = get_keywords_for_type(screen_type)
        negative_keywords = get_negative_keywords_for_type(screen_type)
        
        if not expected_keywords:
            return 0.5, ["No keyword rules for this type"]
        
        # 检查正面关键词
        found_positive = 0
        for kw in expected_keywords:
            kw_lower = kw.lower()
            if (kw_lower in description or 
                kw_lower in [k.lower() for k in keywords_found] or
                kw_lower in [e.lower() for e in ui_elements]):
                found_positive += 1
        
        positive_ratio = found_positive / min(5, len(expected_keywords))  # 最多检查5个
        
        # 检查负面关键词
        found_negative = 0
        for kw in negative_keywords:
            kw_lower = kw.lower()
            if kw_lower in description or kw_lower in [k.lower() for k in keywords_found]:
                found_negative += 1
                issues.append(f"Found unexpected keyword '{kw}' for {screen_type}")
        
        negative_penalty = found_negative * 0.15
        
        # 计算最终分数
        score = max(0, min(1, positive_ratio - negative_penalty))
        
        if positive_ratio < 0.3:
            issues.append(f"Few expected keywords found for {screen_type}")
        
        return score, issues
    
    def _calculate_position_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算位置合理性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        
        # 获取位置（从1开始）
        position = self.filenames.index(filename) + 1
        
        is_valid, adjustment, reason = validate_position(screen_type, position, self.total)
        
        issues = []
        if not is_valid:
            issues.append(reason)
        
        # 基础分 + 调整
        score = 0.7 + adjustment if is_valid else 0.5 + adjustment
        score = max(0, min(1, score))
        
        return score, issues
    
    def _calculate_consistency_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算与相邻截图的一致性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        position = self.filenames.index(filename)
        
        issues = []
        
        # 获取相邻截图的类型
        neighbors = []
        for offset in [-2, -1, 1, 2]:
            neighbor_pos = position + offset
            if 0 <= neighbor_pos < self.total:
                neighbor_file = self.filenames[neighbor_pos]
                neighbor_type = self.results[neighbor_file].get("screen_type", "Unknown")
                neighbors.append(neighbor_type)
        
        if not neighbors:
            return 0.7, []
        
        # 检查是否与相邻截图类型一致
        same_type_count = sum(1 for t in neighbors if t == screen_type)
        consistency = same_type_count / len(neighbors)
        
        # 检查是否是合理的类型变化
        # 例如：Onboarding -> Paywall 是合理的
        # 但 Home -> Launch 是不合理的
        reasonable_transitions = {
            ("Launch", "Welcome"), ("Launch", "Permission"), ("Launch", "SignUp"),
            ("Welcome", "SignUp"), ("Welcome", "Onboarding"), ("Welcome", "Permission"),
            ("SignUp", "Onboarding"), ("SignUp", "Home"),
            ("Permission", "Onboarding"), ("Permission", "Home"),
            ("Onboarding", "Paywall"), ("Onboarding", "Home"),
            ("Paywall", "Home"), ("Paywall", "Feature"),
            ("Home", "Feature"), ("Home", "Settings"), ("Home", "Profile"),
            ("Feature", "Feature"), ("Feature", "Home"),
        }
        
        unreasonable_transitions = {
            ("Home", "Launch"), ("Home", "Onboarding"),
            ("Settings", "Launch"), ("Settings", "Onboarding"),
            ("Feature", "Launch"),
        }
        
        # 检查与前一个截图的转换
        if position > 0:
            prev_file = self.filenames[position - 1]
            prev_type = self.results[prev_file].get("screen_type", "Unknown")
            
            transition = (prev_type, screen_type)
            if transition in unreasonable_transitions:
                issues.append(f"Unusual transition: {prev_type} -> {screen_type}")
                consistency -= 0.3
        
        score = max(0, min(1, 0.5 + consistency * 0.5))
        
        return score, issues
    
    def validate_single(self, filename: str) -> ValidationResult:
        """
        验证单个截图的分析结果
        
        信任AI判断：AI原始置信度是最重要的指标
        其他验证只作为辅助参考
        """
        result = self.results.get(filename, {})
        
        original_type = result.get("screen_type", "Unknown")
        original_confidence = result.get("confidence", 0.5)
        
        # 如果AI原始置信度很高(>=88%)，直接通过
        if original_confidence >= 0.88:
            return ValidationResult(
                filename=filename,
                original_type=original_type,
                original_confidence=original_confidence,
                keyword_score=1.0,
                position_score=1.0,
                consistency_score=1.0,
                final_confidence=original_confidence,
                validation_status="pass",
                suggested_type=None,
                issues=[]
            )
        
        # 对于较低置信度的结果，进行辅助验证
        keyword_score, keyword_issues = self._calculate_keyword_score(result)
        position_score, position_issues = self._calculate_position_score(filename, result)
        consistency_score, consistency_issues = self._calculate_consistency_score(filename, result)
        
        # 合并问题（仅作为参考，不影响主要判断）
        all_issues = keyword_issues + position_issues + consistency_issues
        
        # 计算综合置信度
        # 权重: AI原始置信度 80%, 其他验证 20%
        aux_score = (keyword_score * 0.4 + position_score * 0.3 + consistency_score * 0.3)
        final_confidence = original_confidence * 0.80 + aux_score * 0.20
        
        # 确定验证状态（基于AI原始置信度）
        if original_confidence >= 0.85:
            status = "pass"
        elif original_confidence >= 0.70:
            status = "review"
        else:
            status = "fail"
        
        # 建议类型（仅当置信度很低时）
        suggested_type = None
        if original_confidence < 0.60:
            suggested_type = self._suggest_better_type(result)
        
        return ValidationResult(
            filename=filename,
            original_type=original_type,
            original_confidence=original_confidence,
            keyword_score=keyword_score,
            position_score=position_score,
            consistency_score=consistency_score,
            final_confidence=final_confidence,
            validation_status=status,
            suggested_type=suggested_type,
            issues=all_issues
        )
    
    def _suggest_better_type(self, result: Dict) -> Optional[str]:
        """根据关键词建议更好的类型"""
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        keywords_found = [k.lower() for k in result.get("keywords_found", [])]
        
        best_type = None
        best_score = 0
        
        for screen_type, rules in KEYWORD_RULES.items():
            score = 0
            for kw in rules.get("visual_keywords", []):
                if kw.lower() in description or kw.lower() in keywords_found:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_type = screen_type
        
        return best_type if best_score >= 2 else None
    
    def validate_sequence(self) -> Tuple[bool, List[str]]:
        """验证整体序列是否合理"""
        # 获取所有类型按顺序
        types_in_order = []
        for filename in self.filenames:
            screen_type = self.results[filename].get("screen_type", "Unknown")
            if not types_in_order or types_in_order[-1] != screen_type:
                types_in_order.append(screen_type)
        
        return check_sequence(types_in_order)
    
    def validate_all(self) -> BatchValidationResult:
        """验证所有分析结果"""
        results = {}
        pass_count = 0
        review_count = 0
        fail_count = 0
        all_issues = []
        
        print("\n[VALIDATE] Starting validation...")
        print("-" * 50)
        
        for filename in self.filenames:
            validation = self.validate_single(filename)
            results[filename] = validation
            
            if validation.validation_status == "pass":
                pass_count += 1
                status_icon = "PASS"
            elif validation.validation_status == "review":
                review_count += 1
                status_icon = "REVW"
            else:
                fail_count += 1
                status_icon = "FAIL"
            
            # 收集问题
            for issue in validation.issues:
                all_issues.append(f"{filename}: {issue}")
            
            # 打印状态
            conf_str = f"{validation.final_confidence:.0%}"
            print(f"[{status_icon}] {filename[:35]:35s} {validation.original_type:15s} -> {conf_str}")
        
        # 序列验证
        sequence_valid, sequence_issues = self.validate_sequence()
        all_issues.extend([f"[Sequence] {issue}" for issue in sequence_issues])
        
        # 类型分布
        type_distribution = Counter(
            self.results[f].get("screen_type", "Unknown") 
            for f in self.filenames
        )
        
        print("-" * 50)
        print(f"Validation done: PASS {pass_count} | REVIEW {review_count} | FAIL {fail_count}")
        
        return BatchValidationResult(
            project_name="",  # 由调用者填充
            total_screenshots=self.total,
            pass_count=pass_count,
            review_count=review_count,
            fail_count=fail_count,
            results={k: asdict(v) for k, v in results.items()},
            sequence_valid=sequence_valid,
            sequence_issues=sequence_issues,
            type_distribution=dict(type_distribution),
            all_issues=all_issues
        )


# ============================================================
# 交叉验证（使用AI二次确认）
# ============================================================

class CrossValidator:
    """交叉验证器 - 使用AI二次确认低置信度结果"""
    
    def __init__(self, analyzer, threshold: float = 0.7):
        """
        Args:
            analyzer: AIScreenshotAnalyzer 实例
            threshold: 需要二次验证的置信度阈值
        """
        self.analyzer = analyzer
        self.threshold = threshold
    
    def cross_validate(
        self, 
        validation_results: Dict[str, ValidationResult],
        image_folder: str,
        max_verify: int = 20
    ) -> Dict[str, Dict]:
        """
        对低置信度结果进行交叉验证
        
        Args:
            validation_results: 验证结果
            image_folder: 图片文件夹
            max_verify: 最多验证多少张
        
        Returns:
            交叉验证结果
        """
        # 找出需要二次验证的截图
        to_verify = []
        for filename, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get("final_confidence", 1.0)
            else:
                confidence = result.final_confidence
            
            if confidence < self.threshold:
                to_verify.append(filename)
        
        if not to_verify:
            print("[OK] All results have high confidence, no cross-validation needed")
            return {}
        
        # 限制数量
        to_verify = to_verify[:max_verify]
        
        print(f"\n[CROSS] Starting cross-validation ({len(to_verify)} low-confidence screenshots)...")
        
        cross_results = {}
        for filename in to_verify:
            image_path = os.path.join(image_folder, filename)
            
            if isinstance(validation_results[filename], dict):
                original_type = validation_results[filename].get("original_type", "Unknown")
            else:
                original_type = validation_results[filename].original_type
            
            verify_result = self.analyzer.verify_result(image_path, original_type)
            cross_results[filename] = verify_result
            
            is_correct = verify_result.get("is_correct")
            if is_correct is True:
                print(f"  [OK] {filename}: confirmed as {original_type}")
            elif is_correct is False:
                suggested = verify_result.get("suggested_type", "?")
                print(f"  [CHANGE] {filename}: suggest change to {suggested}")
            else:
                print(f"  [WARN] {filename}: verification failed")
        
        return cross_results


# ============================================================
# 便捷函数
# ============================================================

def validate_analysis_results(analysis_file: str) -> BatchValidationResult:
    """
    验证分析结果文件
    
    Args:
        analysis_file: AI分析结果JSON文件路径
    
    Returns:
        BatchValidationResult
    """
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取结果部分
    if "results" in data:
        results = data["results"]
        project_name = data.get("project_name", "Unknown")
    else:
        results = data
        project_name = "Unknown"
    
    validator = ResultValidator(results)
    batch_result = validator.validate_all()
    batch_result.project_name = project_name
    
    return batch_result


def save_validation_report(validation_result: BatchValidationResult, output_file: str):
    """保存验证报告为JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(validation_result), f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Validation report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI分析结果验证器")
    parser.add_argument("analysis_file", type=str, help="AI分析结果JSON文件")
    parser.add_argument("--output", type=str, help="输出验证报告文件")
    
    args = parser.parse_args()
    
    result = validate_analysis_results(args.analysis_file)
    
    if args.output:
        save_validation_report(result, args.output)
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("验证摘要")
    print("=" * 50)
    print(f"总截图数: {result.total_screenshots}")
    print(f"PASS (high confidence): {result.pass_count} ({result.pass_count/result.total_screenshots:.0%})")
    print(f"REVIEW (medium): {result.review_count} ({result.review_count/result.total_screenshots:.0%})")
    print(f"FAIL (low): {result.fail_count} ({result.fail_count/result.total_screenshots:.0%})")
    print(f"Sequence validation: {'PASS' if result.sequence_valid else 'ISSUES FOUND'}")
    
    if result.all_issues:
        print(f"\n发现 {len(result.all_issues)} 个问题")


验证器模块 - 自动回测和验证AI分析结果
实现三层验证：关键词验证、位置验证、序列验证
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter

from validation_rules import (
    SCREEN_TYPES, KEYWORD_RULES, POSITION_RULES, SEQUENCE_RULES,
    CONFIDENCE_THRESHOLDS, get_keywords_for_type, get_negative_keywords_for_type,
    validate_position, check_sequence
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationResult:
    """单个截图的验证结果"""
    filename: str
    original_type: str
    original_confidence: float
    
    # 验证结果
    keyword_score: float          # 关键词匹配分数 0-1
    position_score: float         # 位置合理性分数 0-1
    consistency_score: float      # 一致性分数 0-1
    
    # 最终结果
    final_confidence: float       # 综合置信度 0-1
    validation_status: str        # "pass" | "review" | "fail"
    suggested_type: Optional[str] # 建议的类型（如果有）
    issues: List[str] = field(default_factory=list)  # 发现的问题


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    project_name: str
    total_screenshots: int
    
    # 统计
    pass_count: int               # 高置信度通过
    review_count: int             # 需要复查
    fail_count: int               # 低置信度需人工
    
    # 详细结果
    results: Dict[str, ValidationResult]
    
    # 序列验证
    sequence_valid: bool
    sequence_issues: List[str]
    
    # 类型分布
    type_distribution: Dict[str, int]
    
    # 问题汇总
    all_issues: List[str]


# ============================================================
# 验证器类
# ============================================================

class ResultValidator:
    """AI分析结果验证器"""
    
    def __init__(self, analysis_results: Dict):
        """
        初始化验证器
        
        Args:
            analysis_results: AI分析结果字典，格式为 {filename: result_dict}
        """
        self.results = analysis_results
        self.filenames = sorted(analysis_results.keys())
        self.total = len(self.filenames)
    
    def _calculate_keyword_score(self, result: Dict) -> Tuple[float, List[str]]:
        """
        计算关键词匹配分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        keywords_found = result.get("keywords_found", [])
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        ui_elements = result.get("ui_elements", [])
        
        issues = []
        
        # 获取该类型应该有的关键词
        expected_keywords = get_keywords_for_type(screen_type)
        negative_keywords = get_negative_keywords_for_type(screen_type)
        
        if not expected_keywords:
            return 0.5, ["No keyword rules for this type"]
        
        # 检查正面关键词
        found_positive = 0
        for kw in expected_keywords:
            kw_lower = kw.lower()
            if (kw_lower in description or 
                kw_lower in [k.lower() for k in keywords_found] or
                kw_lower in [e.lower() for e in ui_elements]):
                found_positive += 1
        
        positive_ratio = found_positive / min(5, len(expected_keywords))  # 最多检查5个
        
        # 检查负面关键词
        found_negative = 0
        for kw in negative_keywords:
            kw_lower = kw.lower()
            if kw_lower in description or kw_lower in [k.lower() for k in keywords_found]:
                found_negative += 1
                issues.append(f"Found unexpected keyword '{kw}' for {screen_type}")
        
        negative_penalty = found_negative * 0.15
        
        # 计算最终分数
        score = max(0, min(1, positive_ratio - negative_penalty))
        
        if positive_ratio < 0.3:
            issues.append(f"Few expected keywords found for {screen_type}")
        
        return score, issues
    
    def _calculate_position_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算位置合理性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        
        # 获取位置（从1开始）
        position = self.filenames.index(filename) + 1
        
        is_valid, adjustment, reason = validate_position(screen_type, position, self.total)
        
        issues = []
        if not is_valid:
            issues.append(reason)
        
        # 基础分 + 调整
        score = 0.7 + adjustment if is_valid else 0.5 + adjustment
        score = max(0, min(1, score))
        
        return score, issues
    
    def _calculate_consistency_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算与相邻截图的一致性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        position = self.filenames.index(filename)
        
        issues = []
        
        # 获取相邻截图的类型
        neighbors = []
        for offset in [-2, -1, 1, 2]:
            neighbor_pos = position + offset
            if 0 <= neighbor_pos < self.total:
                neighbor_file = self.filenames[neighbor_pos]
                neighbor_type = self.results[neighbor_file].get("screen_type", "Unknown")
                neighbors.append(neighbor_type)
        
        if not neighbors:
            return 0.7, []
        
        # 检查是否与相邻截图类型一致
        same_type_count = sum(1 for t in neighbors if t == screen_type)
        consistency = same_type_count / len(neighbors)
        
        # 检查是否是合理的类型变化
        # 例如：Onboarding -> Paywall 是合理的
        # 但 Home -> Launch 是不合理的
        reasonable_transitions = {
            ("Launch", "Welcome"), ("Launch", "Permission"), ("Launch", "SignUp"),
            ("Welcome", "SignUp"), ("Welcome", "Onboarding"), ("Welcome", "Permission"),
            ("SignUp", "Onboarding"), ("SignUp", "Home"),
            ("Permission", "Onboarding"), ("Permission", "Home"),
            ("Onboarding", "Paywall"), ("Onboarding", "Home"),
            ("Paywall", "Home"), ("Paywall", "Feature"),
            ("Home", "Feature"), ("Home", "Settings"), ("Home", "Profile"),
            ("Feature", "Feature"), ("Feature", "Home"),
        }
        
        unreasonable_transitions = {
            ("Home", "Launch"), ("Home", "Onboarding"),
            ("Settings", "Launch"), ("Settings", "Onboarding"),
            ("Feature", "Launch"),
        }
        
        # 检查与前一个截图的转换
        if position > 0:
            prev_file = self.filenames[position - 1]
            prev_type = self.results[prev_file].get("screen_type", "Unknown")
            
            transition = (prev_type, screen_type)
            if transition in unreasonable_transitions:
                issues.append(f"Unusual transition: {prev_type} -> {screen_type}")
                consistency -= 0.3
        
        score = max(0, min(1, 0.5 + consistency * 0.5))
        
        return score, issues
    
    def validate_single(self, filename: str) -> ValidationResult:
        """
        验证单个截图的分析结果
        
        信任AI判断：AI原始置信度是最重要的指标
        其他验证只作为辅助参考
        """
        result = self.results.get(filename, {})
        
        original_type = result.get("screen_type", "Unknown")
        original_confidence = result.get("confidence", 0.5)
        
        # 如果AI原始置信度很高(>=88%)，直接通过
        if original_confidence >= 0.88:
            return ValidationResult(
                filename=filename,
                original_type=original_type,
                original_confidence=original_confidence,
                keyword_score=1.0,
                position_score=1.0,
                consistency_score=1.0,
                final_confidence=original_confidence,
                validation_status="pass",
                suggested_type=None,
                issues=[]
            )
        
        # 对于较低置信度的结果，进行辅助验证
        keyword_score, keyword_issues = self._calculate_keyword_score(result)
        position_score, position_issues = self._calculate_position_score(filename, result)
        consistency_score, consistency_issues = self._calculate_consistency_score(filename, result)
        
        # 合并问题（仅作为参考，不影响主要判断）
        all_issues = keyword_issues + position_issues + consistency_issues
        
        # 计算综合置信度
        # 权重: AI原始置信度 80%, 其他验证 20%
        aux_score = (keyword_score * 0.4 + position_score * 0.3 + consistency_score * 0.3)
        final_confidence = original_confidence * 0.80 + aux_score * 0.20
        
        # 确定验证状态（基于AI原始置信度）
        if original_confidence >= 0.85:
            status = "pass"
        elif original_confidence >= 0.70:
            status = "review"
        else:
            status = "fail"
        
        # 建议类型（仅当置信度很低时）
        suggested_type = None
        if original_confidence < 0.60:
            suggested_type = self._suggest_better_type(result)
        
        return ValidationResult(
            filename=filename,
            original_type=original_type,
            original_confidence=original_confidence,
            keyword_score=keyword_score,
            position_score=position_score,
            consistency_score=consistency_score,
            final_confidence=final_confidence,
            validation_status=status,
            suggested_type=suggested_type,
            issues=all_issues
        )
    
    def _suggest_better_type(self, result: Dict) -> Optional[str]:
        """根据关键词建议更好的类型"""
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        keywords_found = [k.lower() for k in result.get("keywords_found", [])]
        
        best_type = None
        best_score = 0
        
        for screen_type, rules in KEYWORD_RULES.items():
            score = 0
            for kw in rules.get("visual_keywords", []):
                if kw.lower() in description or kw.lower() in keywords_found:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_type = screen_type
        
        return best_type if best_score >= 2 else None
    
    def validate_sequence(self) -> Tuple[bool, List[str]]:
        """验证整体序列是否合理"""
        # 获取所有类型按顺序
        types_in_order = []
        for filename in self.filenames:
            screen_type = self.results[filename].get("screen_type", "Unknown")
            if not types_in_order or types_in_order[-1] != screen_type:
                types_in_order.append(screen_type)
        
        return check_sequence(types_in_order)
    
    def validate_all(self) -> BatchValidationResult:
        """验证所有分析结果"""
        results = {}
        pass_count = 0
        review_count = 0
        fail_count = 0
        all_issues = []
        
        print("\n[VALIDATE] Starting validation...")
        print("-" * 50)
        
        for filename in self.filenames:
            validation = self.validate_single(filename)
            results[filename] = validation
            
            if validation.validation_status == "pass":
                pass_count += 1
                status_icon = "PASS"
            elif validation.validation_status == "review":
                review_count += 1
                status_icon = "REVW"
            else:
                fail_count += 1
                status_icon = "FAIL"
            
            # 收集问题
            for issue in validation.issues:
                all_issues.append(f"{filename}: {issue}")
            
            # 打印状态
            conf_str = f"{validation.final_confidence:.0%}"
            print(f"[{status_icon}] {filename[:35]:35s} {validation.original_type:15s} -> {conf_str}")
        
        # 序列验证
        sequence_valid, sequence_issues = self.validate_sequence()
        all_issues.extend([f"[Sequence] {issue}" for issue in sequence_issues])
        
        # 类型分布
        type_distribution = Counter(
            self.results[f].get("screen_type", "Unknown") 
            for f in self.filenames
        )
        
        print("-" * 50)
        print(f"Validation done: PASS {pass_count} | REVIEW {review_count} | FAIL {fail_count}")
        
        return BatchValidationResult(
            project_name="",  # 由调用者填充
            total_screenshots=self.total,
            pass_count=pass_count,
            review_count=review_count,
            fail_count=fail_count,
            results={k: asdict(v) for k, v in results.items()},
            sequence_valid=sequence_valid,
            sequence_issues=sequence_issues,
            type_distribution=dict(type_distribution),
            all_issues=all_issues
        )


# ============================================================
# 交叉验证（使用AI二次确认）
# ============================================================

class CrossValidator:
    """交叉验证器 - 使用AI二次确认低置信度结果"""
    
    def __init__(self, analyzer, threshold: float = 0.7):
        """
        Args:
            analyzer: AIScreenshotAnalyzer 实例
            threshold: 需要二次验证的置信度阈值
        """
        self.analyzer = analyzer
        self.threshold = threshold
    
    def cross_validate(
        self, 
        validation_results: Dict[str, ValidationResult],
        image_folder: str,
        max_verify: int = 20
    ) -> Dict[str, Dict]:
        """
        对低置信度结果进行交叉验证
        
        Args:
            validation_results: 验证结果
            image_folder: 图片文件夹
            max_verify: 最多验证多少张
        
        Returns:
            交叉验证结果
        """
        # 找出需要二次验证的截图
        to_verify = []
        for filename, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get("final_confidence", 1.0)
            else:
                confidence = result.final_confidence
            
            if confidence < self.threshold:
                to_verify.append(filename)
        
        if not to_verify:
            print("[OK] All results have high confidence, no cross-validation needed")
            return {}
        
        # 限制数量
        to_verify = to_verify[:max_verify]
        
        print(f"\n[CROSS] Starting cross-validation ({len(to_verify)} low-confidence screenshots)...")
        
        cross_results = {}
        for filename in to_verify:
            image_path = os.path.join(image_folder, filename)
            
            if isinstance(validation_results[filename], dict):
                original_type = validation_results[filename].get("original_type", "Unknown")
            else:
                original_type = validation_results[filename].original_type
            
            verify_result = self.analyzer.verify_result(image_path, original_type)
            cross_results[filename] = verify_result
            
            is_correct = verify_result.get("is_correct")
            if is_correct is True:
                print(f"  [OK] {filename}: confirmed as {original_type}")
            elif is_correct is False:
                suggested = verify_result.get("suggested_type", "?")
                print(f"  [CHANGE] {filename}: suggest change to {suggested}")
            else:
                print(f"  [WARN] {filename}: verification failed")
        
        return cross_results


# ============================================================
# 便捷函数
# ============================================================

def validate_analysis_results(analysis_file: str) -> BatchValidationResult:
    """
    验证分析结果文件
    
    Args:
        analysis_file: AI分析结果JSON文件路径
    
    Returns:
        BatchValidationResult
    """
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取结果部分
    if "results" in data:
        results = data["results"]
        project_name = data.get("project_name", "Unknown")
    else:
        results = data
        project_name = "Unknown"
    
    validator = ResultValidator(results)
    batch_result = validator.validate_all()
    batch_result.project_name = project_name
    
    return batch_result


def save_validation_report(validation_result: BatchValidationResult, output_file: str):
    """保存验证报告为JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(validation_result), f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Validation report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI分析结果验证器")
    parser.add_argument("analysis_file", type=str, help="AI分析结果JSON文件")
    parser.add_argument("--output", type=str, help="输出验证报告文件")
    
    args = parser.parse_args()
    
    result = validate_analysis_results(args.analysis_file)
    
    if args.output:
        save_validation_report(result, args.output)
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("验证摘要")
    print("=" * 50)
    print(f"总截图数: {result.total_screenshots}")
    print(f"PASS (high confidence): {result.pass_count} ({result.pass_count/result.total_screenshots:.0%})")
    print(f"REVIEW (medium): {result.review_count} ({result.review_count/result.total_screenshots:.0%})")
    print(f"FAIL (low): {result.fail_count} ({result.fail_count/result.total_screenshots:.0%})")
    print(f"Sequence validation: {'PASS' if result.sequence_valid else 'ISSUES FOUND'}")
    
    if result.all_issues:
        print(f"\n发现 {len(result.all_issues)} 个问题")


验证器模块 - 自动回测和验证AI分析结果
实现三层验证：关键词验证、位置验证、序列验证
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter

from validation_rules import (
    SCREEN_TYPES, KEYWORD_RULES, POSITION_RULES, SEQUENCE_RULES,
    CONFIDENCE_THRESHOLDS, get_keywords_for_type, get_negative_keywords_for_type,
    validate_position, check_sequence
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationResult:
    """单个截图的验证结果"""
    filename: str
    original_type: str
    original_confidence: float
    
    # 验证结果
    keyword_score: float          # 关键词匹配分数 0-1
    position_score: float         # 位置合理性分数 0-1
    consistency_score: float      # 一致性分数 0-1
    
    # 最终结果
    final_confidence: float       # 综合置信度 0-1
    validation_status: str        # "pass" | "review" | "fail"
    suggested_type: Optional[str] # 建议的类型（如果有）
    issues: List[str] = field(default_factory=list)  # 发现的问题


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    project_name: str
    total_screenshots: int
    
    # 统计
    pass_count: int               # 高置信度通过
    review_count: int             # 需要复查
    fail_count: int               # 低置信度需人工
    
    # 详细结果
    results: Dict[str, ValidationResult]
    
    # 序列验证
    sequence_valid: bool
    sequence_issues: List[str]
    
    # 类型分布
    type_distribution: Dict[str, int]
    
    # 问题汇总
    all_issues: List[str]


# ============================================================
# 验证器类
# ============================================================

class ResultValidator:
    """AI分析结果验证器"""
    
    def __init__(self, analysis_results: Dict):
        """
        初始化验证器
        
        Args:
            analysis_results: AI分析结果字典，格式为 {filename: result_dict}
        """
        self.results = analysis_results
        self.filenames = sorted(analysis_results.keys())
        self.total = len(self.filenames)
    
    def _calculate_keyword_score(self, result: Dict) -> Tuple[float, List[str]]:
        """
        计算关键词匹配分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        keywords_found = result.get("keywords_found", [])
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        ui_elements = result.get("ui_elements", [])
        
        issues = []
        
        # 获取该类型应该有的关键词
        expected_keywords = get_keywords_for_type(screen_type)
        negative_keywords = get_negative_keywords_for_type(screen_type)
        
        if not expected_keywords:
            return 0.5, ["No keyword rules for this type"]
        
        # 检查正面关键词
        found_positive = 0
        for kw in expected_keywords:
            kw_lower = kw.lower()
            if (kw_lower in description or 
                kw_lower in [k.lower() for k in keywords_found] or
                kw_lower in [e.lower() for e in ui_elements]):
                found_positive += 1
        
        positive_ratio = found_positive / min(5, len(expected_keywords))  # 最多检查5个
        
        # 检查负面关键词
        found_negative = 0
        for kw in negative_keywords:
            kw_lower = kw.lower()
            if kw_lower in description or kw_lower in [k.lower() for k in keywords_found]:
                found_negative += 1
                issues.append(f"Found unexpected keyword '{kw}' for {screen_type}")
        
        negative_penalty = found_negative * 0.15
        
        # 计算最终分数
        score = max(0, min(1, positive_ratio - negative_penalty))
        
        if positive_ratio < 0.3:
            issues.append(f"Few expected keywords found for {screen_type}")
        
        return score, issues
    
    def _calculate_position_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算位置合理性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        
        # 获取位置（从1开始）
        position = self.filenames.index(filename) + 1
        
        is_valid, adjustment, reason = validate_position(screen_type, position, self.total)
        
        issues = []
        if not is_valid:
            issues.append(reason)
        
        # 基础分 + 调整
        score = 0.7 + adjustment if is_valid else 0.5 + adjustment
        score = max(0, min(1, score))
        
        return score, issues
    
    def _calculate_consistency_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算与相邻截图的一致性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        position = self.filenames.index(filename)
        
        issues = []
        
        # 获取相邻截图的类型
        neighbors = []
        for offset in [-2, -1, 1, 2]:
            neighbor_pos = position + offset
            if 0 <= neighbor_pos < self.total:
                neighbor_file = self.filenames[neighbor_pos]
                neighbor_type = self.results[neighbor_file].get("screen_type", "Unknown")
                neighbors.append(neighbor_type)
        
        if not neighbors:
            return 0.7, []
        
        # 检查是否与相邻截图类型一致
        same_type_count = sum(1 for t in neighbors if t == screen_type)
        consistency = same_type_count / len(neighbors)
        
        # 检查是否是合理的类型变化
        # 例如：Onboarding -> Paywall 是合理的
        # 但 Home -> Launch 是不合理的
        reasonable_transitions = {
            ("Launch", "Welcome"), ("Launch", "Permission"), ("Launch", "SignUp"),
            ("Welcome", "SignUp"), ("Welcome", "Onboarding"), ("Welcome", "Permission"),
            ("SignUp", "Onboarding"), ("SignUp", "Home"),
            ("Permission", "Onboarding"), ("Permission", "Home"),
            ("Onboarding", "Paywall"), ("Onboarding", "Home"),
            ("Paywall", "Home"), ("Paywall", "Feature"),
            ("Home", "Feature"), ("Home", "Settings"), ("Home", "Profile"),
            ("Feature", "Feature"), ("Feature", "Home"),
        }
        
        unreasonable_transitions = {
            ("Home", "Launch"), ("Home", "Onboarding"),
            ("Settings", "Launch"), ("Settings", "Onboarding"),
            ("Feature", "Launch"),
        }
        
        # 检查与前一个截图的转换
        if position > 0:
            prev_file = self.filenames[position - 1]
            prev_type = self.results[prev_file].get("screen_type", "Unknown")
            
            transition = (prev_type, screen_type)
            if transition in unreasonable_transitions:
                issues.append(f"Unusual transition: {prev_type} -> {screen_type}")
                consistency -= 0.3
        
        score = max(0, min(1, 0.5 + consistency * 0.5))
        
        return score, issues
    
    def validate_single(self, filename: str) -> ValidationResult:
        """
        验证单个截图的分析结果
        
        信任AI判断：AI原始置信度是最重要的指标
        其他验证只作为辅助参考
        """
        result = self.results.get(filename, {})
        
        original_type = result.get("screen_type", "Unknown")
        original_confidence = result.get("confidence", 0.5)
        
        # 如果AI原始置信度很高(>=88%)，直接通过
        if original_confidence >= 0.88:
            return ValidationResult(
                filename=filename,
                original_type=original_type,
                original_confidence=original_confidence,
                keyword_score=1.0,
                position_score=1.0,
                consistency_score=1.0,
                final_confidence=original_confidence,
                validation_status="pass",
                suggested_type=None,
                issues=[]
            )
        
        # 对于较低置信度的结果，进行辅助验证
        keyword_score, keyword_issues = self._calculate_keyword_score(result)
        position_score, position_issues = self._calculate_position_score(filename, result)
        consistency_score, consistency_issues = self._calculate_consistency_score(filename, result)
        
        # 合并问题（仅作为参考，不影响主要判断）
        all_issues = keyword_issues + position_issues + consistency_issues
        
        # 计算综合置信度
        # 权重: AI原始置信度 80%, 其他验证 20%
        aux_score = (keyword_score * 0.4 + position_score * 0.3 + consistency_score * 0.3)
        final_confidence = original_confidence * 0.80 + aux_score * 0.20
        
        # 确定验证状态（基于AI原始置信度）
        if original_confidence >= 0.85:
            status = "pass"
        elif original_confidence >= 0.70:
            status = "review"
        else:
            status = "fail"
        
        # 建议类型（仅当置信度很低时）
        suggested_type = None
        if original_confidence < 0.60:
            suggested_type = self._suggest_better_type(result)
        
        return ValidationResult(
            filename=filename,
            original_type=original_type,
            original_confidence=original_confidence,
            keyword_score=keyword_score,
            position_score=position_score,
            consistency_score=consistency_score,
            final_confidence=final_confidence,
            validation_status=status,
            suggested_type=suggested_type,
            issues=all_issues
        )
    
    def _suggest_better_type(self, result: Dict) -> Optional[str]:
        """根据关键词建议更好的类型"""
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        keywords_found = [k.lower() for k in result.get("keywords_found", [])]
        
        best_type = None
        best_score = 0
        
        for screen_type, rules in KEYWORD_RULES.items():
            score = 0
            for kw in rules.get("visual_keywords", []):
                if kw.lower() in description or kw.lower() in keywords_found:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_type = screen_type
        
        return best_type if best_score >= 2 else None
    
    def validate_sequence(self) -> Tuple[bool, List[str]]:
        """验证整体序列是否合理"""
        # 获取所有类型按顺序
        types_in_order = []
        for filename in self.filenames:
            screen_type = self.results[filename].get("screen_type", "Unknown")
            if not types_in_order or types_in_order[-1] != screen_type:
                types_in_order.append(screen_type)
        
        return check_sequence(types_in_order)
    
    def validate_all(self) -> BatchValidationResult:
        """验证所有分析结果"""
        results = {}
        pass_count = 0
        review_count = 0
        fail_count = 0
        all_issues = []
        
        print("\n[VALIDATE] Starting validation...")
        print("-" * 50)
        
        for filename in self.filenames:
            validation = self.validate_single(filename)
            results[filename] = validation
            
            if validation.validation_status == "pass":
                pass_count += 1
                status_icon = "PASS"
            elif validation.validation_status == "review":
                review_count += 1
                status_icon = "REVW"
            else:
                fail_count += 1
                status_icon = "FAIL"
            
            # 收集问题
            for issue in validation.issues:
                all_issues.append(f"{filename}: {issue}")
            
            # 打印状态
            conf_str = f"{validation.final_confidence:.0%}"
            print(f"[{status_icon}] {filename[:35]:35s} {validation.original_type:15s} -> {conf_str}")
        
        # 序列验证
        sequence_valid, sequence_issues = self.validate_sequence()
        all_issues.extend([f"[Sequence] {issue}" for issue in sequence_issues])
        
        # 类型分布
        type_distribution = Counter(
            self.results[f].get("screen_type", "Unknown") 
            for f in self.filenames
        )
        
        print("-" * 50)
        print(f"Validation done: PASS {pass_count} | REVIEW {review_count} | FAIL {fail_count}")
        
        return BatchValidationResult(
            project_name="",  # 由调用者填充
            total_screenshots=self.total,
            pass_count=pass_count,
            review_count=review_count,
            fail_count=fail_count,
            results={k: asdict(v) for k, v in results.items()},
            sequence_valid=sequence_valid,
            sequence_issues=sequence_issues,
            type_distribution=dict(type_distribution),
            all_issues=all_issues
        )


# ============================================================
# 交叉验证（使用AI二次确认）
# ============================================================

class CrossValidator:
    """交叉验证器 - 使用AI二次确认低置信度结果"""
    
    def __init__(self, analyzer, threshold: float = 0.7):
        """
        Args:
            analyzer: AIScreenshotAnalyzer 实例
            threshold: 需要二次验证的置信度阈值
        """
        self.analyzer = analyzer
        self.threshold = threshold
    
    def cross_validate(
        self, 
        validation_results: Dict[str, ValidationResult],
        image_folder: str,
        max_verify: int = 20
    ) -> Dict[str, Dict]:
        """
        对低置信度结果进行交叉验证
        
        Args:
            validation_results: 验证结果
            image_folder: 图片文件夹
            max_verify: 最多验证多少张
        
        Returns:
            交叉验证结果
        """
        # 找出需要二次验证的截图
        to_verify = []
        for filename, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get("final_confidence", 1.0)
            else:
                confidence = result.final_confidence
            
            if confidence < self.threshold:
                to_verify.append(filename)
        
        if not to_verify:
            print("[OK] All results have high confidence, no cross-validation needed")
            return {}
        
        # 限制数量
        to_verify = to_verify[:max_verify]
        
        print(f"\n[CROSS] Starting cross-validation ({len(to_verify)} low-confidence screenshots)...")
        
        cross_results = {}
        for filename in to_verify:
            image_path = os.path.join(image_folder, filename)
            
            if isinstance(validation_results[filename], dict):
                original_type = validation_results[filename].get("original_type", "Unknown")
            else:
                original_type = validation_results[filename].original_type
            
            verify_result = self.analyzer.verify_result(image_path, original_type)
            cross_results[filename] = verify_result
            
            is_correct = verify_result.get("is_correct")
            if is_correct is True:
                print(f"  [OK] {filename}: confirmed as {original_type}")
            elif is_correct is False:
                suggested = verify_result.get("suggested_type", "?")
                print(f"  [CHANGE] {filename}: suggest change to {suggested}")
            else:
                print(f"  [WARN] {filename}: verification failed")
        
        return cross_results


# ============================================================
# 便捷函数
# ============================================================

def validate_analysis_results(analysis_file: str) -> BatchValidationResult:
    """
    验证分析结果文件
    
    Args:
        analysis_file: AI分析结果JSON文件路径
    
    Returns:
        BatchValidationResult
    """
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取结果部分
    if "results" in data:
        results = data["results"]
        project_name = data.get("project_name", "Unknown")
    else:
        results = data
        project_name = "Unknown"
    
    validator = ResultValidator(results)
    batch_result = validator.validate_all()
    batch_result.project_name = project_name
    
    return batch_result


def save_validation_report(validation_result: BatchValidationResult, output_file: str):
    """保存验证报告为JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(validation_result), f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Validation report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI分析结果验证器")
    parser.add_argument("analysis_file", type=str, help="AI分析结果JSON文件")
    parser.add_argument("--output", type=str, help="输出验证报告文件")
    
    args = parser.parse_args()
    
    result = validate_analysis_results(args.analysis_file)
    
    if args.output:
        save_validation_report(result, args.output)
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("验证摘要")
    print("=" * 50)
    print(f"总截图数: {result.total_screenshots}")
    print(f"PASS (high confidence): {result.pass_count} ({result.pass_count/result.total_screenshots:.0%})")
    print(f"REVIEW (medium): {result.review_count} ({result.review_count/result.total_screenshots:.0%})")
    print(f"FAIL (low): {result.fail_count} ({result.fail_count/result.total_screenshots:.0%})")
    print(f"Sequence validation: {'PASS' if result.sequence_valid else 'ISSUES FOUND'}")
    
    if result.all_issues:
        print(f"\n发现 {len(result.all_issues)} 个问题")


验证器模块 - 自动回测和验证AI分析结果
实现三层验证：关键词验证、位置验证、序列验证
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict, field
from collections import Counter

from validation_rules import (
    SCREEN_TYPES, KEYWORD_RULES, POSITION_RULES, SEQUENCE_RULES,
    CONFIDENCE_THRESHOLDS, get_keywords_for_type, get_negative_keywords_for_type,
    validate_position, check_sequence
)


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationResult:
    """单个截图的验证结果"""
    filename: str
    original_type: str
    original_confidence: float
    
    # 验证结果
    keyword_score: float          # 关键词匹配分数 0-1
    position_score: float         # 位置合理性分数 0-1
    consistency_score: float      # 一致性分数 0-1
    
    # 最终结果
    final_confidence: float       # 综合置信度 0-1
    validation_status: str        # "pass" | "review" | "fail"
    suggested_type: Optional[str] # 建议的类型（如果有）
    issues: List[str] = field(default_factory=list)  # 发现的问题


@dataclass
class BatchValidationResult:
    """批量验证结果"""
    project_name: str
    total_screenshots: int
    
    # 统计
    pass_count: int               # 高置信度通过
    review_count: int             # 需要复查
    fail_count: int               # 低置信度需人工
    
    # 详细结果
    results: Dict[str, ValidationResult]
    
    # 序列验证
    sequence_valid: bool
    sequence_issues: List[str]
    
    # 类型分布
    type_distribution: Dict[str, int]
    
    # 问题汇总
    all_issues: List[str]


# ============================================================
# 验证器类
# ============================================================

class ResultValidator:
    """AI分析结果验证器"""
    
    def __init__(self, analysis_results: Dict):
        """
        初始化验证器
        
        Args:
            analysis_results: AI分析结果字典，格式为 {filename: result_dict}
        """
        self.results = analysis_results
        self.filenames = sorted(analysis_results.keys())
        self.total = len(self.filenames)
    
    def _calculate_keyword_score(self, result: Dict) -> Tuple[float, List[str]]:
        """
        计算关键词匹配分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        keywords_found = result.get("keywords_found", [])
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        ui_elements = result.get("ui_elements", [])
        
        issues = []
        
        # 获取该类型应该有的关键词
        expected_keywords = get_keywords_for_type(screen_type)
        negative_keywords = get_negative_keywords_for_type(screen_type)
        
        if not expected_keywords:
            return 0.5, ["No keyword rules for this type"]
        
        # 检查正面关键词
        found_positive = 0
        for kw in expected_keywords:
            kw_lower = kw.lower()
            if (kw_lower in description or 
                kw_lower in [k.lower() for k in keywords_found] or
                kw_lower in [e.lower() for e in ui_elements]):
                found_positive += 1
        
        positive_ratio = found_positive / min(5, len(expected_keywords))  # 最多检查5个
        
        # 检查负面关键词
        found_negative = 0
        for kw in negative_keywords:
            kw_lower = kw.lower()
            if kw_lower in description or kw_lower in [k.lower() for k in keywords_found]:
                found_negative += 1
                issues.append(f"Found unexpected keyword '{kw}' for {screen_type}")
        
        negative_penalty = found_negative * 0.15
        
        # 计算最终分数
        score = max(0, min(1, positive_ratio - negative_penalty))
        
        if positive_ratio < 0.3:
            issues.append(f"Few expected keywords found for {screen_type}")
        
        return score, issues
    
    def _calculate_position_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算位置合理性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        
        # 获取位置（从1开始）
        position = self.filenames.index(filename) + 1
        
        is_valid, adjustment, reason = validate_position(screen_type, position, self.total)
        
        issues = []
        if not is_valid:
            issues.append(reason)
        
        # 基础分 + 调整
        score = 0.7 + adjustment if is_valid else 0.5 + adjustment
        score = max(0, min(1, score))
        
        return score, issues
    
    def _calculate_consistency_score(self, filename: str, result: Dict) -> Tuple[float, List[str]]:
        """
        计算与相邻截图的一致性分数
        
        Returns:
            (score, issues)
        """
        screen_type = result.get("screen_type", "Unknown")
        position = self.filenames.index(filename)
        
        issues = []
        
        # 获取相邻截图的类型
        neighbors = []
        for offset in [-2, -1, 1, 2]:
            neighbor_pos = position + offset
            if 0 <= neighbor_pos < self.total:
                neighbor_file = self.filenames[neighbor_pos]
                neighbor_type = self.results[neighbor_file].get("screen_type", "Unknown")
                neighbors.append(neighbor_type)
        
        if not neighbors:
            return 0.7, []
        
        # 检查是否与相邻截图类型一致
        same_type_count = sum(1 for t in neighbors if t == screen_type)
        consistency = same_type_count / len(neighbors)
        
        # 检查是否是合理的类型变化
        # 例如：Onboarding -> Paywall 是合理的
        # 但 Home -> Launch 是不合理的
        reasonable_transitions = {
            ("Launch", "Welcome"), ("Launch", "Permission"), ("Launch", "SignUp"),
            ("Welcome", "SignUp"), ("Welcome", "Onboarding"), ("Welcome", "Permission"),
            ("SignUp", "Onboarding"), ("SignUp", "Home"),
            ("Permission", "Onboarding"), ("Permission", "Home"),
            ("Onboarding", "Paywall"), ("Onboarding", "Home"),
            ("Paywall", "Home"), ("Paywall", "Feature"),
            ("Home", "Feature"), ("Home", "Settings"), ("Home", "Profile"),
            ("Feature", "Feature"), ("Feature", "Home"),
        }
        
        unreasonable_transitions = {
            ("Home", "Launch"), ("Home", "Onboarding"),
            ("Settings", "Launch"), ("Settings", "Onboarding"),
            ("Feature", "Launch"),
        }
        
        # 检查与前一个截图的转换
        if position > 0:
            prev_file = self.filenames[position - 1]
            prev_type = self.results[prev_file].get("screen_type", "Unknown")
            
            transition = (prev_type, screen_type)
            if transition in unreasonable_transitions:
                issues.append(f"Unusual transition: {prev_type} -> {screen_type}")
                consistency -= 0.3
        
        score = max(0, min(1, 0.5 + consistency * 0.5))
        
        return score, issues
    
    def validate_single(self, filename: str) -> ValidationResult:
        """
        验证单个截图的分析结果
        
        信任AI判断：AI原始置信度是最重要的指标
        其他验证只作为辅助参考
        """
        result = self.results.get(filename, {})
        
        original_type = result.get("screen_type", "Unknown")
        original_confidence = result.get("confidence", 0.5)
        
        # 如果AI原始置信度很高(>=88%)，直接通过
        if original_confidence >= 0.88:
            return ValidationResult(
                filename=filename,
                original_type=original_type,
                original_confidence=original_confidence,
                keyword_score=1.0,
                position_score=1.0,
                consistency_score=1.0,
                final_confidence=original_confidence,
                validation_status="pass",
                suggested_type=None,
                issues=[]
            )
        
        # 对于较低置信度的结果，进行辅助验证
        keyword_score, keyword_issues = self._calculate_keyword_score(result)
        position_score, position_issues = self._calculate_position_score(filename, result)
        consistency_score, consistency_issues = self._calculate_consistency_score(filename, result)
        
        # 合并问题（仅作为参考，不影响主要判断）
        all_issues = keyword_issues + position_issues + consistency_issues
        
        # 计算综合置信度
        # 权重: AI原始置信度 80%, 其他验证 20%
        aux_score = (keyword_score * 0.4 + position_score * 0.3 + consistency_score * 0.3)
        final_confidence = original_confidence * 0.80 + aux_score * 0.20
        
        # 确定验证状态（基于AI原始置信度）
        if original_confidence >= 0.85:
            status = "pass"
        elif original_confidence >= 0.70:
            status = "review"
        else:
            status = "fail"
        
        # 建议类型（仅当置信度很低时）
        suggested_type = None
        if original_confidence < 0.60:
            suggested_type = self._suggest_better_type(result)
        
        return ValidationResult(
            filename=filename,
            original_type=original_type,
            original_confidence=original_confidence,
            keyword_score=keyword_score,
            position_score=position_score,
            consistency_score=consistency_score,
            final_confidence=final_confidence,
            validation_status=status,
            suggested_type=suggested_type,
            issues=all_issues
        )
    
    def _suggest_better_type(self, result: Dict) -> Optional[str]:
        """根据关键词建议更好的类型"""
        description = (result.get("description_cn", "") + " " + result.get("description_en", "")).lower()
        keywords_found = [k.lower() for k in result.get("keywords_found", [])]
        
        best_type = None
        best_score = 0
        
        for screen_type, rules in KEYWORD_RULES.items():
            score = 0
            for kw in rules.get("visual_keywords", []):
                if kw.lower() in description or kw.lower() in keywords_found:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_type = screen_type
        
        return best_type if best_score >= 2 else None
    
    def validate_sequence(self) -> Tuple[bool, List[str]]:
        """验证整体序列是否合理"""
        # 获取所有类型按顺序
        types_in_order = []
        for filename in self.filenames:
            screen_type = self.results[filename].get("screen_type", "Unknown")
            if not types_in_order or types_in_order[-1] != screen_type:
                types_in_order.append(screen_type)
        
        return check_sequence(types_in_order)
    
    def validate_all(self) -> BatchValidationResult:
        """验证所有分析结果"""
        results = {}
        pass_count = 0
        review_count = 0
        fail_count = 0
        all_issues = []
        
        print("\n[VALIDATE] Starting validation...")
        print("-" * 50)
        
        for filename in self.filenames:
            validation = self.validate_single(filename)
            results[filename] = validation
            
            if validation.validation_status == "pass":
                pass_count += 1
                status_icon = "PASS"
            elif validation.validation_status == "review":
                review_count += 1
                status_icon = "REVW"
            else:
                fail_count += 1
                status_icon = "FAIL"
            
            # 收集问题
            for issue in validation.issues:
                all_issues.append(f"{filename}: {issue}")
            
            # 打印状态
            conf_str = f"{validation.final_confidence:.0%}"
            print(f"[{status_icon}] {filename[:35]:35s} {validation.original_type:15s} -> {conf_str}")
        
        # 序列验证
        sequence_valid, sequence_issues = self.validate_sequence()
        all_issues.extend([f"[Sequence] {issue}" for issue in sequence_issues])
        
        # 类型分布
        type_distribution = Counter(
            self.results[f].get("screen_type", "Unknown") 
            for f in self.filenames
        )
        
        print("-" * 50)
        print(f"Validation done: PASS {pass_count} | REVIEW {review_count} | FAIL {fail_count}")
        
        return BatchValidationResult(
            project_name="",  # 由调用者填充
            total_screenshots=self.total,
            pass_count=pass_count,
            review_count=review_count,
            fail_count=fail_count,
            results={k: asdict(v) for k, v in results.items()},
            sequence_valid=sequence_valid,
            sequence_issues=sequence_issues,
            type_distribution=dict(type_distribution),
            all_issues=all_issues
        )


# ============================================================
# 交叉验证（使用AI二次确认）
# ============================================================

class CrossValidator:
    """交叉验证器 - 使用AI二次确认低置信度结果"""
    
    def __init__(self, analyzer, threshold: float = 0.7):
        """
        Args:
            analyzer: AIScreenshotAnalyzer 实例
            threshold: 需要二次验证的置信度阈值
        """
        self.analyzer = analyzer
        self.threshold = threshold
    
    def cross_validate(
        self, 
        validation_results: Dict[str, ValidationResult],
        image_folder: str,
        max_verify: int = 20
    ) -> Dict[str, Dict]:
        """
        对低置信度结果进行交叉验证
        
        Args:
            validation_results: 验证结果
            image_folder: 图片文件夹
            max_verify: 最多验证多少张
        
        Returns:
            交叉验证结果
        """
        # 找出需要二次验证的截图
        to_verify = []
        for filename, result in validation_results.items():
            if isinstance(result, dict):
                confidence = result.get("final_confidence", 1.0)
            else:
                confidence = result.final_confidence
            
            if confidence < self.threshold:
                to_verify.append(filename)
        
        if not to_verify:
            print("[OK] All results have high confidence, no cross-validation needed")
            return {}
        
        # 限制数量
        to_verify = to_verify[:max_verify]
        
        print(f"\n[CROSS] Starting cross-validation ({len(to_verify)} low-confidence screenshots)...")
        
        cross_results = {}
        for filename in to_verify:
            image_path = os.path.join(image_folder, filename)
            
            if isinstance(validation_results[filename], dict):
                original_type = validation_results[filename].get("original_type", "Unknown")
            else:
                original_type = validation_results[filename].original_type
            
            verify_result = self.analyzer.verify_result(image_path, original_type)
            cross_results[filename] = verify_result
            
            is_correct = verify_result.get("is_correct")
            if is_correct is True:
                print(f"  [OK] {filename}: confirmed as {original_type}")
            elif is_correct is False:
                suggested = verify_result.get("suggested_type", "?")
                print(f"  [CHANGE] {filename}: suggest change to {suggested}")
            else:
                print(f"  [WARN] {filename}: verification failed")
        
        return cross_results


# ============================================================
# 便捷函数
# ============================================================

def validate_analysis_results(analysis_file: str) -> BatchValidationResult:
    """
    验证分析结果文件
    
    Args:
        analysis_file: AI分析结果JSON文件路径
    
    Returns:
        BatchValidationResult
    """
    with open(analysis_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取结果部分
    if "results" in data:
        results = data["results"]
        project_name = data.get("project_name", "Unknown")
    else:
        results = data
        project_name = "Unknown"
    
    validator = ResultValidator(results)
    batch_result = validator.validate_all()
    batch_result.project_name = project_name
    
    return batch_result


def save_validation_report(validation_result: BatchValidationResult, output_file: str):
    """保存验证报告为JSON"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(validation_result), f, ensure_ascii=False, indent=2)
    print(f"[SAVED] Validation report: {output_file}")


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI分析结果验证器")
    parser.add_argument("analysis_file", type=str, help="AI分析结果JSON文件")
    parser.add_argument("--output", type=str, help="输出验证报告文件")
    
    args = parser.parse_args()
    
    result = validate_analysis_results(args.analysis_file)
    
    if args.output:
        save_validation_report(result, args.output)
    
    # 打印摘要
    print("\n" + "=" * 50)
    print("验证摘要")
    print("=" * 50)
    print(f"总截图数: {result.total_screenshots}")
    print(f"PASS (high confidence): {result.pass_count} ({result.pass_count/result.total_screenshots:.0%})")
    print(f"REVIEW (medium): {result.review_count} ({result.review_count/result.total_screenshots:.0%})")
    print(f"FAIL (low): {result.fail_count} ({result.fail_count/result.total_screenshots:.0%})")
    print(f"Sequence validation: {'PASS' if result.sequence_valid else 'ISSUES FOUND'}")
    
    if result.all_issues:
        print(f"\n发现 {len(result.all_issues)} 个问题")

