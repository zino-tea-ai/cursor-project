# -*- coding: utf-8 -*-
"""
异常检测模块
分析完成后自动检测分类结果是否合理
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


@dataclass
class Anomaly:
    """异常记录"""
    type: str           # 异常类型
    severity: str       # 严重程度: warning, error
    message: str        # 描述
    suggestion: str     # 建议
    affected_screens: List[str] = None  # 受影响的截图


class AnomalyDetector:
    """异常检测器"""
    
    # 健康/健身类App的预期分布
    HEALTH_APP_EXPECTATIONS = {
        'Onboarding': {'min_pct': 5, 'max_pct': 30},  # 至少5%应该是Onboarding
        'Paywall': {'min_pct': 1, 'max_pct': 10},
        'Feature': {'max_pct': 40},  # Feature不应该超过40%
    }
    
    # 通用规则
    GENERAL_RULES = {
        'Launch': {'max_count': 3},  # Launch最多3张
        'Welcome': {'max_count': 5},
        'Permission': {'max_count': 5},
    }
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self.anomalies: List[Anomaly] = []
    
    def detect(self, results: Dict, product_profile: Dict = None) -> List[Anomaly]:
        """
        检测分析结果中的异常
        
        Args:
            results: 分析结果 {filename: {screen_type, ...}}
            product_profile: 产品画像
        
        Returns:
            异常列表
        """
        self.anomalies = []
        
        if not results:
            return self.anomalies
        
        # 计算类型分布
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        total = len(results)
        type_pcts = {t: (c / total * 100) for t, c in type_counts.items()}
        
        # 检测1: 类型分布异常
        self._check_distribution(type_counts, type_pcts, total, product_profile)
        
        # 检测2: 位置异常
        self._check_position_anomalies(results)
        
        # 检测3: 与历史数据对比
        if self.db:
            self._check_against_history(type_pcts, product_profile)
        
        return self.anomalies
    
    def _check_distribution(self, type_counts: Dict, type_pcts: Dict, total: int, profile: Dict):
        """检测类型分布异常"""
        
        # 检查Onboarding
        onboarding_pct = type_pcts.get('Onboarding', 0)
        if onboarding_pct == 0 and total > 20:
            self.anomalies.append(Anomaly(
                type='missing_onboarding',
                severity='error',
                message=f'Onboarding占比0%，这对于大多数App来说不正常',
                suggestion='检查前20张截图，可能有Onboarding被误分类为Feature或Welcome'
            ))
        elif onboarding_pct < 5 and total > 50:
            self.anomalies.append(Anomaly(
                type='low_onboarding',
                severity='warning',
                message=f'Onboarding占比仅{onboarding_pct:.1f}%，低于预期',
                suggestion='检查是否有Onboarding被误分类'
            ))
        
        # 检查Feature是否过多
        feature_pct = type_pcts.get('Feature', 0)
        if feature_pct > 40:
            self.anomalies.append(Anomaly(
                type='high_feature',
                severity='warning',
                message=f'Feature占比{feature_pct:.1f}%，可能有其他类型被误分类为Feature',
                suggestion='Feature应该是"兜底"类型，检查是否有更具体的分类'
            ))
        
        # 检查Launch/Welcome数量
        for type_name, rules in self.GENERAL_RULES.items():
            count = type_counts.get(type_name, 0)
            if 'max_count' in rules and count > rules['max_count']:
                self.anomalies.append(Anomaly(
                    type=f'high_{type_name.lower()}',
                    severity='warning',
                    message=f'{type_name}有{count}张，超过正常范围（最多{rules["max_count"]}张）',
                    suggestion=f'检查是否有其他类型被误分类为{type_name}'
                ))
    
    def _check_position_anomalies(self, results: Dict):
        """检测位置异常"""
        
        # 按索引排序
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        anomalies_found = []
        
        for i, (filename, data) in enumerate(sorted_results):
            idx = data.get('index', i + 1)
            screen_type = data.get('screen_type', 'Unknown')
            
            # 前5张应该是 Launch/Welcome/Permission，不应该是Feature
            if idx <= 5 and screen_type == 'Feature':
                anomalies_found.append(filename)
            
            # 前20张出现Home说明可能有问题（通常Onboarding在前面）
            if idx <= 10 and screen_type == 'Home':
                # 这个可能是正常的，只记录不报错
                pass
        
        if anomalies_found:
            self.anomalies.append(Anomaly(
                type='early_feature',
                severity='warning',
                message=f'前5张截图中有{len(anomalies_found)}张被分类为Feature',
                suggestion='前几张通常是Launch/Welcome/Onboarding，检查这些截图',
                affected_screens=anomalies_found
            ))
    
    def _check_against_history(self, type_pcts: Dict, profile: Dict):
        """与历史数据对比"""
        if not self.db:
            return
        
        # 获取同类App的平均分布
        try:
            stats = self.db.get_screen_type_stats()
            total_historical = sum(stats.values())
            
            if total_historical < 100:
                return  # 历史数据不足
            
            historical_pcts = {t: (c / total_historical * 100) for t, c in stats.items()}
            
            # 对比Onboarding
            current_ob = type_pcts.get('Onboarding', 0)
            historical_ob = historical_pcts.get('Onboarding', 0)
            
            if historical_ob > 10 and current_ob < historical_ob * 0.3:
                self.anomalies.append(Anomaly(
                    type='below_average_onboarding',
                    severity='warning',
                    message=f'Onboarding占比({current_ob:.1f}%)远低于历史平均({historical_ob:.1f}%)',
                    suggestion='与已分析的其他产品相比，Onboarding明显偏少'
                ))
                
        except Exception as e:
            print(f"[AnomalyDetector] Error checking history: {e}")
    
    def get_summary(self) -> str:
        """获取异常摘要"""
        if not self.anomalies:
            return "✅ 未发现异常"
        
        errors = [a for a in self.anomalies if a.severity == 'error']
        warnings = [a for a in self.anomalies if a.severity == 'warning']
        
        lines = [f"发现 {len(errors)} 个错误, {len(warnings)} 个警告:"]
        
        for a in errors:
            lines.append(f"  ❌ {a.message}")
        for a in warnings:
            lines.append(f"  ⚠️ {a.message}")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """获取所有建议"""
        return [a.suggestion for a in self.anomalies if a.suggestion]


def detect_anomalies(results: Dict, product_profile: Dict = None) -> Tuple[List[Anomaly], str]:
    """
    便捷函数：检测异常并返回摘要
    
    Returns:
        (异常列表, 摘要文本)
    """
    detector = AnomalyDetector()
    anomalies = detector.detect(results, product_profile)
    summary = detector.get_summary()
    return anomalies, summary


"""
异常检测模块
分析完成后自动检测分类结果是否合理
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


@dataclass
class Anomaly:
    """异常记录"""
    type: str           # 异常类型
    severity: str       # 严重程度: warning, error
    message: str        # 描述
    suggestion: str     # 建议
    affected_screens: List[str] = None  # 受影响的截图


class AnomalyDetector:
    """异常检测器"""
    
    # 健康/健身类App的预期分布
    HEALTH_APP_EXPECTATIONS = {
        'Onboarding': {'min_pct': 5, 'max_pct': 30},  # 至少5%应该是Onboarding
        'Paywall': {'min_pct': 1, 'max_pct': 10},
        'Feature': {'max_pct': 40},  # Feature不应该超过40%
    }
    
    # 通用规则
    GENERAL_RULES = {
        'Launch': {'max_count': 3},  # Launch最多3张
        'Welcome': {'max_count': 5},
        'Permission': {'max_count': 5},
    }
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self.anomalies: List[Anomaly] = []
    
    def detect(self, results: Dict, product_profile: Dict = None) -> List[Anomaly]:
        """
        检测分析结果中的异常
        
        Args:
            results: 分析结果 {filename: {screen_type, ...}}
            product_profile: 产品画像
        
        Returns:
            异常列表
        """
        self.anomalies = []
        
        if not results:
            return self.anomalies
        
        # 计算类型分布
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        total = len(results)
        type_pcts = {t: (c / total * 100) for t, c in type_counts.items()}
        
        # 检测1: 类型分布异常
        self._check_distribution(type_counts, type_pcts, total, product_profile)
        
        # 检测2: 位置异常
        self._check_position_anomalies(results)
        
        # 检测3: 与历史数据对比
        if self.db:
            self._check_against_history(type_pcts, product_profile)
        
        return self.anomalies
    
    def _check_distribution(self, type_counts: Dict, type_pcts: Dict, total: int, profile: Dict):
        """检测类型分布异常"""
        
        # 检查Onboarding
        onboarding_pct = type_pcts.get('Onboarding', 0)
        if onboarding_pct == 0 and total > 20:
            self.anomalies.append(Anomaly(
                type='missing_onboarding',
                severity='error',
                message=f'Onboarding占比0%，这对于大多数App来说不正常',
                suggestion='检查前20张截图，可能有Onboarding被误分类为Feature或Welcome'
            ))
        elif onboarding_pct < 5 and total > 50:
            self.anomalies.append(Anomaly(
                type='low_onboarding',
                severity='warning',
                message=f'Onboarding占比仅{onboarding_pct:.1f}%，低于预期',
                suggestion='检查是否有Onboarding被误分类'
            ))
        
        # 检查Feature是否过多
        feature_pct = type_pcts.get('Feature', 0)
        if feature_pct > 40:
            self.anomalies.append(Anomaly(
                type='high_feature',
                severity='warning',
                message=f'Feature占比{feature_pct:.1f}%，可能有其他类型被误分类为Feature',
                suggestion='Feature应该是"兜底"类型，检查是否有更具体的分类'
            ))
        
        # 检查Launch/Welcome数量
        for type_name, rules in self.GENERAL_RULES.items():
            count = type_counts.get(type_name, 0)
            if 'max_count' in rules and count > rules['max_count']:
                self.anomalies.append(Anomaly(
                    type=f'high_{type_name.lower()}',
                    severity='warning',
                    message=f'{type_name}有{count}张，超过正常范围（最多{rules["max_count"]}张）',
                    suggestion=f'检查是否有其他类型被误分类为{type_name}'
                ))
    
    def _check_position_anomalies(self, results: Dict):
        """检测位置异常"""
        
        # 按索引排序
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        anomalies_found = []
        
        for i, (filename, data) in enumerate(sorted_results):
            idx = data.get('index', i + 1)
            screen_type = data.get('screen_type', 'Unknown')
            
            # 前5张应该是 Launch/Welcome/Permission，不应该是Feature
            if idx <= 5 and screen_type == 'Feature':
                anomalies_found.append(filename)
            
            # 前20张出现Home说明可能有问题（通常Onboarding在前面）
            if idx <= 10 and screen_type == 'Home':
                # 这个可能是正常的，只记录不报错
                pass
        
        if anomalies_found:
            self.anomalies.append(Anomaly(
                type='early_feature',
                severity='warning',
                message=f'前5张截图中有{len(anomalies_found)}张被分类为Feature',
                suggestion='前几张通常是Launch/Welcome/Onboarding，检查这些截图',
                affected_screens=anomalies_found
            ))
    
    def _check_against_history(self, type_pcts: Dict, profile: Dict):
        """与历史数据对比"""
        if not self.db:
            return
        
        # 获取同类App的平均分布
        try:
            stats = self.db.get_screen_type_stats()
            total_historical = sum(stats.values())
            
            if total_historical < 100:
                return  # 历史数据不足
            
            historical_pcts = {t: (c / total_historical * 100) for t, c in stats.items()}
            
            # 对比Onboarding
            current_ob = type_pcts.get('Onboarding', 0)
            historical_ob = historical_pcts.get('Onboarding', 0)
            
            if historical_ob > 10 and current_ob < historical_ob * 0.3:
                self.anomalies.append(Anomaly(
                    type='below_average_onboarding',
                    severity='warning',
                    message=f'Onboarding占比({current_ob:.1f}%)远低于历史平均({historical_ob:.1f}%)',
                    suggestion='与已分析的其他产品相比，Onboarding明显偏少'
                ))
                
        except Exception as e:
            print(f"[AnomalyDetector] Error checking history: {e}")
    
    def get_summary(self) -> str:
        """获取异常摘要"""
        if not self.anomalies:
            return "✅ 未发现异常"
        
        errors = [a for a in self.anomalies if a.severity == 'error']
        warnings = [a for a in self.anomalies if a.severity == 'warning']
        
        lines = [f"发现 {len(errors)} 个错误, {len(warnings)} 个警告:"]
        
        for a in errors:
            lines.append(f"  ❌ {a.message}")
        for a in warnings:
            lines.append(f"  ⚠️ {a.message}")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """获取所有建议"""
        return [a.suggestion for a in self.anomalies if a.suggestion]


def detect_anomalies(results: Dict, product_profile: Dict = None) -> Tuple[List[Anomaly], str]:
    """
    便捷函数：检测异常并返回摘要
    
    Returns:
        (异常列表, 摘要文本)
    """
    detector = AnomalyDetector()
    anomalies = detector.detect(results, product_profile)
    summary = detector.get_summary()
    return anomalies, summary


"""
异常检测模块
分析完成后自动检测分类结果是否合理
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


@dataclass
class Anomaly:
    """异常记录"""
    type: str           # 异常类型
    severity: str       # 严重程度: warning, error
    message: str        # 描述
    suggestion: str     # 建议
    affected_screens: List[str] = None  # 受影响的截图


class AnomalyDetector:
    """异常检测器"""
    
    # 健康/健身类App的预期分布
    HEALTH_APP_EXPECTATIONS = {
        'Onboarding': {'min_pct': 5, 'max_pct': 30},  # 至少5%应该是Onboarding
        'Paywall': {'min_pct': 1, 'max_pct': 10},
        'Feature': {'max_pct': 40},  # Feature不应该超过40%
    }
    
    # 通用规则
    GENERAL_RULES = {
        'Launch': {'max_count': 3},  # Launch最多3张
        'Welcome': {'max_count': 5},
        'Permission': {'max_count': 5},
    }
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self.anomalies: List[Anomaly] = []
    
    def detect(self, results: Dict, product_profile: Dict = None) -> List[Anomaly]:
        """
        检测分析结果中的异常
        
        Args:
            results: 分析结果 {filename: {screen_type, ...}}
            product_profile: 产品画像
        
        Returns:
            异常列表
        """
        self.anomalies = []
        
        if not results:
            return self.anomalies
        
        # 计算类型分布
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        total = len(results)
        type_pcts = {t: (c / total * 100) for t, c in type_counts.items()}
        
        # 检测1: 类型分布异常
        self._check_distribution(type_counts, type_pcts, total, product_profile)
        
        # 检测2: 位置异常
        self._check_position_anomalies(results)
        
        # 检测3: 与历史数据对比
        if self.db:
            self._check_against_history(type_pcts, product_profile)
        
        return self.anomalies
    
    def _check_distribution(self, type_counts: Dict, type_pcts: Dict, total: int, profile: Dict):
        """检测类型分布异常"""
        
        # 检查Onboarding
        onboarding_pct = type_pcts.get('Onboarding', 0)
        if onboarding_pct == 0 and total > 20:
            self.anomalies.append(Anomaly(
                type='missing_onboarding',
                severity='error',
                message=f'Onboarding占比0%，这对于大多数App来说不正常',
                suggestion='检查前20张截图，可能有Onboarding被误分类为Feature或Welcome'
            ))
        elif onboarding_pct < 5 and total > 50:
            self.anomalies.append(Anomaly(
                type='low_onboarding',
                severity='warning',
                message=f'Onboarding占比仅{onboarding_pct:.1f}%，低于预期',
                suggestion='检查是否有Onboarding被误分类'
            ))
        
        # 检查Feature是否过多
        feature_pct = type_pcts.get('Feature', 0)
        if feature_pct > 40:
            self.anomalies.append(Anomaly(
                type='high_feature',
                severity='warning',
                message=f'Feature占比{feature_pct:.1f}%，可能有其他类型被误分类为Feature',
                suggestion='Feature应该是"兜底"类型，检查是否有更具体的分类'
            ))
        
        # 检查Launch/Welcome数量
        for type_name, rules in self.GENERAL_RULES.items():
            count = type_counts.get(type_name, 0)
            if 'max_count' in rules and count > rules['max_count']:
                self.anomalies.append(Anomaly(
                    type=f'high_{type_name.lower()}',
                    severity='warning',
                    message=f'{type_name}有{count}张，超过正常范围（最多{rules["max_count"]}张）',
                    suggestion=f'检查是否有其他类型被误分类为{type_name}'
                ))
    
    def _check_position_anomalies(self, results: Dict):
        """检测位置异常"""
        
        # 按索引排序
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        anomalies_found = []
        
        for i, (filename, data) in enumerate(sorted_results):
            idx = data.get('index', i + 1)
            screen_type = data.get('screen_type', 'Unknown')
            
            # 前5张应该是 Launch/Welcome/Permission，不应该是Feature
            if idx <= 5 and screen_type == 'Feature':
                anomalies_found.append(filename)
            
            # 前20张出现Home说明可能有问题（通常Onboarding在前面）
            if idx <= 10 and screen_type == 'Home':
                # 这个可能是正常的，只记录不报错
                pass
        
        if anomalies_found:
            self.anomalies.append(Anomaly(
                type='early_feature',
                severity='warning',
                message=f'前5张截图中有{len(anomalies_found)}张被分类为Feature',
                suggestion='前几张通常是Launch/Welcome/Onboarding，检查这些截图',
                affected_screens=anomalies_found
            ))
    
    def _check_against_history(self, type_pcts: Dict, profile: Dict):
        """与历史数据对比"""
        if not self.db:
            return
        
        # 获取同类App的平均分布
        try:
            stats = self.db.get_screen_type_stats()
            total_historical = sum(stats.values())
            
            if total_historical < 100:
                return  # 历史数据不足
            
            historical_pcts = {t: (c / total_historical * 100) for t, c in stats.items()}
            
            # 对比Onboarding
            current_ob = type_pcts.get('Onboarding', 0)
            historical_ob = historical_pcts.get('Onboarding', 0)
            
            if historical_ob > 10 and current_ob < historical_ob * 0.3:
                self.anomalies.append(Anomaly(
                    type='below_average_onboarding',
                    severity='warning',
                    message=f'Onboarding占比({current_ob:.1f}%)远低于历史平均({historical_ob:.1f}%)',
                    suggestion='与已分析的其他产品相比，Onboarding明显偏少'
                ))
                
        except Exception as e:
            print(f"[AnomalyDetector] Error checking history: {e}")
    
    def get_summary(self) -> str:
        """获取异常摘要"""
        if not self.anomalies:
            return "✅ 未发现异常"
        
        errors = [a for a in self.anomalies if a.severity == 'error']
        warnings = [a for a in self.anomalies if a.severity == 'warning']
        
        lines = [f"发现 {len(errors)} 个错误, {len(warnings)} 个警告:"]
        
        for a in errors:
            lines.append(f"  ❌ {a.message}")
        for a in warnings:
            lines.append(f"  ⚠️ {a.message}")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """获取所有建议"""
        return [a.suggestion for a in self.anomalies if a.suggestion]


def detect_anomalies(results: Dict, product_profile: Dict = None) -> Tuple[List[Anomaly], str]:
    """
    便捷函数：检测异常并返回摘要
    
    Returns:
        (异常列表, 摘要文本)
    """
    detector = AnomalyDetector()
    anomalies = detector.detect(results, product_profile)
    summary = detector.get_summary()
    return anomalies, summary


"""
异常检测模块
分析完成后自动检测分类结果是否合理
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


@dataclass
class Anomaly:
    """异常记录"""
    type: str           # 异常类型
    severity: str       # 严重程度: warning, error
    message: str        # 描述
    suggestion: str     # 建议
    affected_screens: List[str] = None  # 受影响的截图


class AnomalyDetector:
    """异常检测器"""
    
    # 健康/健身类App的预期分布
    HEALTH_APP_EXPECTATIONS = {
        'Onboarding': {'min_pct': 5, 'max_pct': 30},  # 至少5%应该是Onboarding
        'Paywall': {'min_pct': 1, 'max_pct': 10},
        'Feature': {'max_pct': 40},  # Feature不应该超过40%
    }
    
    # 通用规则
    GENERAL_RULES = {
        'Launch': {'max_count': 3},  # Launch最多3张
        'Welcome': {'max_count': 5},
        'Permission': {'max_count': 5},
    }
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self.anomalies: List[Anomaly] = []
    
    def detect(self, results: Dict, product_profile: Dict = None) -> List[Anomaly]:
        """
        检测分析结果中的异常
        
        Args:
            results: 分析结果 {filename: {screen_type, ...}}
            product_profile: 产品画像
        
        Returns:
            异常列表
        """
        self.anomalies = []
        
        if not results:
            return self.anomalies
        
        # 计算类型分布
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        total = len(results)
        type_pcts = {t: (c / total * 100) for t, c in type_counts.items()}
        
        # 检测1: 类型分布异常
        self._check_distribution(type_counts, type_pcts, total, product_profile)
        
        # 检测2: 位置异常
        self._check_position_anomalies(results)
        
        # 检测3: 与历史数据对比
        if self.db:
            self._check_against_history(type_pcts, product_profile)
        
        return self.anomalies
    
    def _check_distribution(self, type_counts: Dict, type_pcts: Dict, total: int, profile: Dict):
        """检测类型分布异常"""
        
        # 检查Onboarding
        onboarding_pct = type_pcts.get('Onboarding', 0)
        if onboarding_pct == 0 and total > 20:
            self.anomalies.append(Anomaly(
                type='missing_onboarding',
                severity='error',
                message=f'Onboarding占比0%，这对于大多数App来说不正常',
                suggestion='检查前20张截图，可能有Onboarding被误分类为Feature或Welcome'
            ))
        elif onboarding_pct < 5 and total > 50:
            self.anomalies.append(Anomaly(
                type='low_onboarding',
                severity='warning',
                message=f'Onboarding占比仅{onboarding_pct:.1f}%，低于预期',
                suggestion='检查是否有Onboarding被误分类'
            ))
        
        # 检查Feature是否过多
        feature_pct = type_pcts.get('Feature', 0)
        if feature_pct > 40:
            self.anomalies.append(Anomaly(
                type='high_feature',
                severity='warning',
                message=f'Feature占比{feature_pct:.1f}%，可能有其他类型被误分类为Feature',
                suggestion='Feature应该是"兜底"类型，检查是否有更具体的分类'
            ))
        
        # 检查Launch/Welcome数量
        for type_name, rules in self.GENERAL_RULES.items():
            count = type_counts.get(type_name, 0)
            if 'max_count' in rules and count > rules['max_count']:
                self.anomalies.append(Anomaly(
                    type=f'high_{type_name.lower()}',
                    severity='warning',
                    message=f'{type_name}有{count}张，超过正常范围（最多{rules["max_count"]}张）',
                    suggestion=f'检查是否有其他类型被误分类为{type_name}'
                ))
    
    def _check_position_anomalies(self, results: Dict):
        """检测位置异常"""
        
        # 按索引排序
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        anomalies_found = []
        
        for i, (filename, data) in enumerate(sorted_results):
            idx = data.get('index', i + 1)
            screen_type = data.get('screen_type', 'Unknown')
            
            # 前5张应该是 Launch/Welcome/Permission，不应该是Feature
            if idx <= 5 and screen_type == 'Feature':
                anomalies_found.append(filename)
            
            # 前20张出现Home说明可能有问题（通常Onboarding在前面）
            if idx <= 10 and screen_type == 'Home':
                # 这个可能是正常的，只记录不报错
                pass
        
        if anomalies_found:
            self.anomalies.append(Anomaly(
                type='early_feature',
                severity='warning',
                message=f'前5张截图中有{len(anomalies_found)}张被分类为Feature',
                suggestion='前几张通常是Launch/Welcome/Onboarding，检查这些截图',
                affected_screens=anomalies_found
            ))
    
    def _check_against_history(self, type_pcts: Dict, profile: Dict):
        """与历史数据对比"""
        if not self.db:
            return
        
        # 获取同类App的平均分布
        try:
            stats = self.db.get_screen_type_stats()
            total_historical = sum(stats.values())
            
            if total_historical < 100:
                return  # 历史数据不足
            
            historical_pcts = {t: (c / total_historical * 100) for t, c in stats.items()}
            
            # 对比Onboarding
            current_ob = type_pcts.get('Onboarding', 0)
            historical_ob = historical_pcts.get('Onboarding', 0)
            
            if historical_ob > 10 and current_ob < historical_ob * 0.3:
                self.anomalies.append(Anomaly(
                    type='below_average_onboarding',
                    severity='warning',
                    message=f'Onboarding占比({current_ob:.1f}%)远低于历史平均({historical_ob:.1f}%)',
                    suggestion='与已分析的其他产品相比，Onboarding明显偏少'
                ))
                
        except Exception as e:
            print(f"[AnomalyDetector] Error checking history: {e}")
    
    def get_summary(self) -> str:
        """获取异常摘要"""
        if not self.anomalies:
            return "✅ 未发现异常"
        
        errors = [a for a in self.anomalies if a.severity == 'error']
        warnings = [a for a in self.anomalies if a.severity == 'warning']
        
        lines = [f"发现 {len(errors)} 个错误, {len(warnings)} 个警告:"]
        
        for a in errors:
            lines.append(f"  ❌ {a.message}")
        for a in warnings:
            lines.append(f"  ⚠️ {a.message}")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """获取所有建议"""
        return [a.suggestion for a in self.anomalies if a.suggestion]


def detect_anomalies(results: Dict, product_profile: Dict = None) -> Tuple[List[Anomaly], str]:
    """
    便捷函数：检测异常并返回摘要
    
    Returns:
        (异常列表, 摘要文本)
    """
    detector = AnomalyDetector()
    anomalies = detector.detect(results, product_profile)
    summary = detector.get_summary()
    return anomalies, summary



"""
异常检测模块
分析完成后自动检测分类结果是否合理
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


@dataclass
class Anomaly:
    """异常记录"""
    type: str           # 异常类型
    severity: str       # 严重程度: warning, error
    message: str        # 描述
    suggestion: str     # 建议
    affected_screens: List[str] = None  # 受影响的截图


class AnomalyDetector:
    """异常检测器"""
    
    # 健康/健身类App的预期分布
    HEALTH_APP_EXPECTATIONS = {
        'Onboarding': {'min_pct': 5, 'max_pct': 30},  # 至少5%应该是Onboarding
        'Paywall': {'min_pct': 1, 'max_pct': 10},
        'Feature': {'max_pct': 40},  # Feature不应该超过40%
    }
    
    # 通用规则
    GENERAL_RULES = {
        'Launch': {'max_count': 3},  # Launch最多3张
        'Welcome': {'max_count': 5},
        'Permission': {'max_count': 5},
    }
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self.anomalies: List[Anomaly] = []
    
    def detect(self, results: Dict, product_profile: Dict = None) -> List[Anomaly]:
        """
        检测分析结果中的异常
        
        Args:
            results: 分析结果 {filename: {screen_type, ...}}
            product_profile: 产品画像
        
        Returns:
            异常列表
        """
        self.anomalies = []
        
        if not results:
            return self.anomalies
        
        # 计算类型分布
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        total = len(results)
        type_pcts = {t: (c / total * 100) for t, c in type_counts.items()}
        
        # 检测1: 类型分布异常
        self._check_distribution(type_counts, type_pcts, total, product_profile)
        
        # 检测2: 位置异常
        self._check_position_anomalies(results)
        
        # 检测3: 与历史数据对比
        if self.db:
            self._check_against_history(type_pcts, product_profile)
        
        return self.anomalies
    
    def _check_distribution(self, type_counts: Dict, type_pcts: Dict, total: int, profile: Dict):
        """检测类型分布异常"""
        
        # 检查Onboarding
        onboarding_pct = type_pcts.get('Onboarding', 0)
        if onboarding_pct == 0 and total > 20:
            self.anomalies.append(Anomaly(
                type='missing_onboarding',
                severity='error',
                message=f'Onboarding占比0%，这对于大多数App来说不正常',
                suggestion='检查前20张截图，可能有Onboarding被误分类为Feature或Welcome'
            ))
        elif onboarding_pct < 5 and total > 50:
            self.anomalies.append(Anomaly(
                type='low_onboarding',
                severity='warning',
                message=f'Onboarding占比仅{onboarding_pct:.1f}%，低于预期',
                suggestion='检查是否有Onboarding被误分类'
            ))
        
        # 检查Feature是否过多
        feature_pct = type_pcts.get('Feature', 0)
        if feature_pct > 40:
            self.anomalies.append(Anomaly(
                type='high_feature',
                severity='warning',
                message=f'Feature占比{feature_pct:.1f}%，可能有其他类型被误分类为Feature',
                suggestion='Feature应该是"兜底"类型，检查是否有更具体的分类'
            ))
        
        # 检查Launch/Welcome数量
        for type_name, rules in self.GENERAL_RULES.items():
            count = type_counts.get(type_name, 0)
            if 'max_count' in rules and count > rules['max_count']:
                self.anomalies.append(Anomaly(
                    type=f'high_{type_name.lower()}',
                    severity='warning',
                    message=f'{type_name}有{count}张，超过正常范围（最多{rules["max_count"]}张）',
                    suggestion=f'检查是否有其他类型被误分类为{type_name}'
                ))
    
    def _check_position_anomalies(self, results: Dict):
        """检测位置异常"""
        
        # 按索引排序
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        anomalies_found = []
        
        for i, (filename, data) in enumerate(sorted_results):
            idx = data.get('index', i + 1)
            screen_type = data.get('screen_type', 'Unknown')
            
            # 前5张应该是 Launch/Welcome/Permission，不应该是Feature
            if idx <= 5 and screen_type == 'Feature':
                anomalies_found.append(filename)
            
            # 前20张出现Home说明可能有问题（通常Onboarding在前面）
            if idx <= 10 and screen_type == 'Home':
                # 这个可能是正常的，只记录不报错
                pass
        
        if anomalies_found:
            self.anomalies.append(Anomaly(
                type='early_feature',
                severity='warning',
                message=f'前5张截图中有{len(anomalies_found)}张被分类为Feature',
                suggestion='前几张通常是Launch/Welcome/Onboarding，检查这些截图',
                affected_screens=anomalies_found
            ))
    
    def _check_against_history(self, type_pcts: Dict, profile: Dict):
        """与历史数据对比"""
        if not self.db:
            return
        
        # 获取同类App的平均分布
        try:
            stats = self.db.get_screen_type_stats()
            total_historical = sum(stats.values())
            
            if total_historical < 100:
                return  # 历史数据不足
            
            historical_pcts = {t: (c / total_historical * 100) for t, c in stats.items()}
            
            # 对比Onboarding
            current_ob = type_pcts.get('Onboarding', 0)
            historical_ob = historical_pcts.get('Onboarding', 0)
            
            if historical_ob > 10 and current_ob < historical_ob * 0.3:
                self.anomalies.append(Anomaly(
                    type='below_average_onboarding',
                    severity='warning',
                    message=f'Onboarding占比({current_ob:.1f}%)远低于历史平均({historical_ob:.1f}%)',
                    suggestion='与已分析的其他产品相比，Onboarding明显偏少'
                ))
                
        except Exception as e:
            print(f"[AnomalyDetector] Error checking history: {e}")
    
    def get_summary(self) -> str:
        """获取异常摘要"""
        if not self.anomalies:
            return "✅ 未发现异常"
        
        errors = [a for a in self.anomalies if a.severity == 'error']
        warnings = [a for a in self.anomalies if a.severity == 'warning']
        
        lines = [f"发现 {len(errors)} 个错误, {len(warnings)} 个警告:"]
        
        for a in errors:
            lines.append(f"  ❌ {a.message}")
        for a in warnings:
            lines.append(f"  ⚠️ {a.message}")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """获取所有建议"""
        return [a.suggestion for a in self.anomalies if a.suggestion]


def detect_anomalies(results: Dict, product_profile: Dict = None) -> Tuple[List[Anomaly], str]:
    """
    便捷函数：检测异常并返回摘要
    
    Returns:
        (异常列表, 摘要文本)
    """
    detector = AnomalyDetector()
    anomalies = detector.detect(results, product_profile)
    summary = detector.get_summary()
    return anomalies, summary


"""
异常检测模块
分析完成后自动检测分类结果是否合理
"""

import os
import sys
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 数据库
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


@dataclass
class Anomaly:
    """异常记录"""
    type: str           # 异常类型
    severity: str       # 严重程度: warning, error
    message: str        # 描述
    suggestion: str     # 建议
    affected_screens: List[str] = None  # 受影响的截图


class AnomalyDetector:
    """异常检测器"""
    
    # 健康/健身类App的预期分布
    HEALTH_APP_EXPECTATIONS = {
        'Onboarding': {'min_pct': 5, 'max_pct': 30},  # 至少5%应该是Onboarding
        'Paywall': {'min_pct': 1, 'max_pct': 10},
        'Feature': {'max_pct': 40},  # Feature不应该超过40%
    }
    
    # 通用规则
    GENERAL_RULES = {
        'Launch': {'max_count': 3},  # Launch最多3张
        'Welcome': {'max_count': 5},
        'Permission': {'max_count': 5},
    }
    
    def __init__(self):
        self.db = get_db() if DB_AVAILABLE else None
        self.anomalies: List[Anomaly] = []
    
    def detect(self, results: Dict, product_profile: Dict = None) -> List[Anomaly]:
        """
        检测分析结果中的异常
        
        Args:
            results: 分析结果 {filename: {screen_type, ...}}
            product_profile: 产品画像
        
        Returns:
            异常列表
        """
        self.anomalies = []
        
        if not results:
            return self.anomalies
        
        # 计算类型分布
        type_counts = {}
        for filename, data in results.items():
            screen_type = data.get('screen_type', 'Unknown')
            type_counts[screen_type] = type_counts.get(screen_type, 0) + 1
        
        total = len(results)
        type_pcts = {t: (c / total * 100) for t, c in type_counts.items()}
        
        # 检测1: 类型分布异常
        self._check_distribution(type_counts, type_pcts, total, product_profile)
        
        # 检测2: 位置异常
        self._check_position_anomalies(results)
        
        # 检测3: 与历史数据对比
        if self.db:
            self._check_against_history(type_pcts, product_profile)
        
        return self.anomalies
    
    def _check_distribution(self, type_counts: Dict, type_pcts: Dict, total: int, profile: Dict):
        """检测类型分布异常"""
        
        # 检查Onboarding
        onboarding_pct = type_pcts.get('Onboarding', 0)
        if onboarding_pct == 0 and total > 20:
            self.anomalies.append(Anomaly(
                type='missing_onboarding',
                severity='error',
                message=f'Onboarding占比0%，这对于大多数App来说不正常',
                suggestion='检查前20张截图，可能有Onboarding被误分类为Feature或Welcome'
            ))
        elif onboarding_pct < 5 and total > 50:
            self.anomalies.append(Anomaly(
                type='low_onboarding',
                severity='warning',
                message=f'Onboarding占比仅{onboarding_pct:.1f}%，低于预期',
                suggestion='检查是否有Onboarding被误分类'
            ))
        
        # 检查Feature是否过多
        feature_pct = type_pcts.get('Feature', 0)
        if feature_pct > 40:
            self.anomalies.append(Anomaly(
                type='high_feature',
                severity='warning',
                message=f'Feature占比{feature_pct:.1f}%，可能有其他类型被误分类为Feature',
                suggestion='Feature应该是"兜底"类型，检查是否有更具体的分类'
            ))
        
        # 检查Launch/Welcome数量
        for type_name, rules in self.GENERAL_RULES.items():
            count = type_counts.get(type_name, 0)
            if 'max_count' in rules and count > rules['max_count']:
                self.anomalies.append(Anomaly(
                    type=f'high_{type_name.lower()}',
                    severity='warning',
                    message=f'{type_name}有{count}张，超过正常范围（最多{rules["max_count"]}张）',
                    suggestion=f'检查是否有其他类型被误分类为{type_name}'
                ))
    
    def _check_position_anomalies(self, results: Dict):
        """检测位置异常"""
        
        # 按索引排序
        sorted_results = sorted(
            [(f, d) for f, d in results.items()],
            key=lambda x: x[1].get('index', 0)
        )
        
        anomalies_found = []
        
        for i, (filename, data) in enumerate(sorted_results):
            idx = data.get('index', i + 1)
            screen_type = data.get('screen_type', 'Unknown')
            
            # 前5张应该是 Launch/Welcome/Permission，不应该是Feature
            if idx <= 5 and screen_type == 'Feature':
                anomalies_found.append(filename)
            
            # 前20张出现Home说明可能有问题（通常Onboarding在前面）
            if idx <= 10 and screen_type == 'Home':
                # 这个可能是正常的，只记录不报错
                pass
        
        if anomalies_found:
            self.anomalies.append(Anomaly(
                type='early_feature',
                severity='warning',
                message=f'前5张截图中有{len(anomalies_found)}张被分类为Feature',
                suggestion='前几张通常是Launch/Welcome/Onboarding，检查这些截图',
                affected_screens=anomalies_found
            ))
    
    def _check_against_history(self, type_pcts: Dict, profile: Dict):
        """与历史数据对比"""
        if not self.db:
            return
        
        # 获取同类App的平均分布
        try:
            stats = self.db.get_screen_type_stats()
            total_historical = sum(stats.values())
            
            if total_historical < 100:
                return  # 历史数据不足
            
            historical_pcts = {t: (c / total_historical * 100) for t, c in stats.items()}
            
            # 对比Onboarding
            current_ob = type_pcts.get('Onboarding', 0)
            historical_ob = historical_pcts.get('Onboarding', 0)
            
            if historical_ob > 10 and current_ob < historical_ob * 0.3:
                self.anomalies.append(Anomaly(
                    type='below_average_onboarding',
                    severity='warning',
                    message=f'Onboarding占比({current_ob:.1f}%)远低于历史平均({historical_ob:.1f}%)',
                    suggestion='与已分析的其他产品相比，Onboarding明显偏少'
                ))
                
        except Exception as e:
            print(f"[AnomalyDetector] Error checking history: {e}")
    
    def get_summary(self) -> str:
        """获取异常摘要"""
        if not self.anomalies:
            return "✅ 未发现异常"
        
        errors = [a for a in self.anomalies if a.severity == 'error']
        warnings = [a for a in self.anomalies if a.severity == 'warning']
        
        lines = [f"发现 {len(errors)} 个错误, {len(warnings)} 个警告:"]
        
        for a in errors:
            lines.append(f"  ❌ {a.message}")
        for a in warnings:
            lines.append(f"  ⚠️ {a.message}")
        
        return "\n".join(lines)
    
    def get_suggestions(self) -> List[str]:
        """获取所有建议"""
        return [a.suggestion for a in self.anomalies if a.suggestion]


def detect_anomalies(results: Dict, product_profile: Dict = None) -> Tuple[List[Anomaly], str]:
    """
    便捷函数：检测异常并返回摘要
    
    Returns:
        (异常列表, 摘要文本)
    """
    detector = AnomalyDetector()
    anomalies = detector.detect(results, product_profile)
    summary = detector.get_summary()
    return anomalies, summary










































