# -*- coding: utf-8 -*-
"""
知识学习器
从分析结果中学习模式，更新知识库
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict


class KnowledgeLearner:
    """
    知识学习器
    
    功能：
    1. 从分析结果中提取模式
    2. 更新行业基准数据
    3. 发现跨产品的共性和差异
    """
    
    def __init__(self):
        self.knowledge_dir = os.path.dirname(os.path.abspath(__file__))
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.benchmarks_file = os.path.join(self.knowledge_dir, "benchmarks.json")
        self.learned_file = os.path.join(self.knowledge_dir, "learned_patterns.json")
        
        # 加载现有知识
        self.patterns = self._load_json(self.patterns_file)
        self.benchmarks = self._load_json(self.benchmarks_file)
        self.learned = self._load_json(self.learned_file) or {
            "products_analyzed": [],
            "category_stats": {},
            "pattern_occurrences": {},
            "last_updated": None
        }
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """加载JSON文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(
        self,
        project_name: str,
        product_profile: Dict,
        flow_structure: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        从分析结果中学习
        
        Args:
            project_name: 项目名称
            product_profile: 产品画像
            flow_structure: 流程结构
            results: 分析结果
        
        Returns:
            学习报告
        """
        app_category = product_profile.get("app_category", "Other")
        
        # 记录已分析产品
        if project_name not in self.learned["products_analyzed"]:
            self.learned["products_analyzed"].append(project_name)
        
        # 更新类别统计
        if app_category not in self.learned["category_stats"]:
            self.learned["category_stats"][app_category] = {
                "count": 0,
                "avg_onboarding_steps": 0,
                "paywall_positions": [],
                "common_types": {},
                "products": []
            }
        
        cat_stats = self.learned["category_stats"][app_category]
        cat_stats["count"] += 1
        cat_stats["products"].append(project_name)
        
        # 分析Onboarding长度
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        # 更新平均值
        prev_avg = cat_stats["avg_onboarding_steps"]
        prev_count = cat_stats["count"] - 1
        cat_stats["avg_onboarding_steps"] = (
            (prev_avg * prev_count + onboarding_count) / cat_stats["count"]
        )
        
        # 记录Paywall位置
        paywall_pos = flow_structure.get("paywall_position", "none")
        cat_stats["paywall_positions"].append(paywall_pos)
        
        # 统计类型分布
        for r in results.values():
            screen_type = r.get("screen_type", "Unknown")
            cat_stats["common_types"][screen_type] = (
                cat_stats["common_types"].get(screen_type, 0) + 1
            )
        
        # 提取设计模式
        patterns_found = self._extract_patterns(results, flow_structure)
        
        # 更新模式出现次数
        for pattern_name in patterns_found:
            if pattern_name not in self.learned["pattern_occurrences"]:
                self.learned["pattern_occurrences"][pattern_name] = {
                    "count": 0,
                    "products": []
                }
            self.learned["pattern_occurrences"][pattern_name]["count"] += 1
            self.learned["pattern_occurrences"][pattern_name]["products"].append(project_name)
        
        # 更新时间戳
        self.learned["last_updated"] = datetime.now().isoformat()
        
        # 保存学习结果
        self._save_json(self.learned_file, self.learned)
        
        return {
            "patterns_found": patterns_found,
            "category_stats": cat_stats,
            "onboarding_steps": onboarding_count
        }
    
    def _extract_patterns(self, results: Dict[str, Dict], flow_structure: Dict) -> List[str]:
        """从分析结果中提取设计模式"""
        patterns = []
        
        # 检查Onboarding模式
        onboarding_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Onboarding"
        ]
        
        if len(onboarding_screens) >= 5:
            # 检查是否有渐进式披露
            patterns.append("progressive_disclosure")
        
        # 检查是否有目标优先
        if onboarding_screens:
            first_onboarding = min(onboarding_screens, key=lambda x: x.get("index", 999))
            sub_type = first_onboarding.get("sub_type", "").lower()
            if "goal" in sub_type or "objective" in sub_type:
                patterns.append("goal_first")
        
        # 检查Paywall模式
        paywall_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Paywall"
        ]
        
        if paywall_screens:
            for paywall in paywall_screens:
                keywords = paywall.get("keywords_found", [])
                keywords_lower = [k.lower() for k in keywords]
                
                if any("trial" in k or "free" in k for k in keywords_lower):
                    patterns.append("trial_first")
                
                if any("save" in k or "%" in k for k in keywords_lower):
                    patterns.append("price_anchoring")
        
        return list(set(patterns))
    
    def get_category_benchmark(self, category: str) -> Dict:
        """获取类别的基准数据"""
        # 优先使用学习到的数据
        learned_stats = self.learned.get("category_stats", {}).get(category, {})
        
        # 获取预设的基准
        preset_key = self._map_category_to_benchmark(category)
        preset_benchmark = self.benchmarks.get(preset_key, {})
        
        # 合并（学习数据优先）
        if learned_stats.get("count", 0) >= 3:
            # 如果已经分析了3个以上同类产品，使用学习数据
            return {
                "source": "learned",
                "products_analyzed": learned_stats.get("count", 0),
                "avg_onboarding_steps": learned_stats.get("avg_onboarding_steps", 8),
                "common_types": learned_stats.get("common_types", {}),
                "preset_benchmark": preset_benchmark
            }
        else:
            # 使用预设基准
            return {
                "source": "preset",
                "preset_benchmark": preset_benchmark,
                "learned_stats": learned_stats
            }
    
    def _map_category_to_benchmark(self, category: str) -> str:
        """将类别映射到基准数据键"""
        mapping = {
            "冥想正念": "meditation_apps",
            "Meditation": "meditation_apps",
            "健康健身": "fitness_apps",
            "Health & Fitness": "fitness_apps",
            "饮食营养": "nutrition_apps",
            "Nutrition & Diet": "nutrition_apps",
            "运动追踪": "running_apps",
            "Sports Tracking": "running_apps",
            "女性健康": "women_health_apps",
            "Women's Health": "women_health_apps",
            "睡眠改善": "sleep_apps",
            "Sleep": "sleep_apps"
        }
        return mapping.get(category, "general_benchmarks")
    
    def compare_with_benchmark(
        self,
        project_name: str,
        product_profile: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        与行业基准对比
        
        Returns:
            对比报告
        """
        category = product_profile.get("app_category", "Other")
        benchmark = self.get_category_benchmark(category)
        
        # 计算当前产品指标
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        total_screens = len(results)
        
        # 类型分布
        type_distribution = Counter(
            r.get("screen_type", "Unknown") for r in results.values()
        )
        
        # 对比
        comparison = {
            "project_name": project_name,
            "category": category,
            "metrics": {
                "onboarding_steps": {
                    "current": onboarding_count,
                    "benchmark": benchmark.get("preset_benchmark", {}).get("metrics", {}).get("avg_onboarding_steps", "N/A"),
                    "status": self._compare_value(
                        onboarding_count,
                        benchmark.get("preset_benchmark", {}).get("metrics", {}).get("onboarding_range", [5, 12])
                    )
                },
                "total_screens": total_screens,
                "type_distribution": dict(type_distribution)
            },
            "benchmark_source": benchmark.get("source", "preset")
        }
        
        return comparison
    
    def _compare_value(self, value: int, range_tuple: List[int]) -> str:
        """比较值是否在范围内"""
        if not range_tuple or len(range_tuple) < 2:
            return "unknown"
        
        if value < range_tuple[0]:
            return "below_average"
        elif value > range_tuple[1]:
            return "above_average"
        else:
            return "normal"
    
    def get_cross_product_insights(self) -> Dict:
        """获取跨产品洞察"""
        insights = {
            "total_products_analyzed": len(self.learned.get("products_analyzed", [])),
            "categories_covered": list(self.learned.get("category_stats", {}).keys()),
            "most_common_patterns": [],
            "category_comparisons": {}
        }
        
        # 最常见的模式
        pattern_counts = self.learned.get("pattern_occurrences", {})
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        insights["most_common_patterns"] = [
            {"pattern": p, "count": c.get("count", 0)}
            for p, c in sorted_patterns[:10]
        ]
        
        # 类别对比
        for cat, stats in self.learned.get("category_stats", {}).items():
            insights["category_comparisons"][cat] = {
                "products_count": stats.get("count", 0),
                "avg_onboarding": stats.get("avg_onboarding_steps", 0),
                "top_types": dict(
                    Counter(stats.get("common_types", {})).most_common(5)
                )
            }
        
        return insights


# ============================================================
# 便捷函数
# ============================================================

def learn_from_project(project_path: str) -> Dict:
    """从项目中学习"""
    # 加载分析结果
    analysis_file = os.path.join(project_path, "ai_analysis.json")
    profile_file = os.path.join(project_path, "product_profile.json")
    structure_file = os.path.join(project_path, "flow_structure.json")
    
    if not all(os.path.exists(f) for f in [analysis_file, profile_file, structure_file]):
        return {"error": "Missing analysis files"}
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    # 学习
    learner = KnowledgeLearner()
    return learner.learn_from_analysis(
        project_name=analysis.get("project_name", "Unknown"),
        product_profile=profile,
        flow_structure=structure,
        results=analysis.get("results", {})
    )


if __name__ == "__main__":
    # 测试
    learner = KnowledgeLearner()
    insights = learner.get_cross_product_insights()
    print(json.dumps(insights, ensure_ascii=False, indent=2))


"""
知识学习器
从分析结果中学习模式，更新知识库
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict


class KnowledgeLearner:
    """
    知识学习器
    
    功能：
    1. 从分析结果中提取模式
    2. 更新行业基准数据
    3. 发现跨产品的共性和差异
    """
    
    def __init__(self):
        self.knowledge_dir = os.path.dirname(os.path.abspath(__file__))
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.benchmarks_file = os.path.join(self.knowledge_dir, "benchmarks.json")
        self.learned_file = os.path.join(self.knowledge_dir, "learned_patterns.json")
        
        # 加载现有知识
        self.patterns = self._load_json(self.patterns_file)
        self.benchmarks = self._load_json(self.benchmarks_file)
        self.learned = self._load_json(self.learned_file) or {
            "products_analyzed": [],
            "category_stats": {},
            "pattern_occurrences": {},
            "last_updated": None
        }
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """加载JSON文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(
        self,
        project_name: str,
        product_profile: Dict,
        flow_structure: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        从分析结果中学习
        
        Args:
            project_name: 项目名称
            product_profile: 产品画像
            flow_structure: 流程结构
            results: 分析结果
        
        Returns:
            学习报告
        """
        app_category = product_profile.get("app_category", "Other")
        
        # 记录已分析产品
        if project_name not in self.learned["products_analyzed"]:
            self.learned["products_analyzed"].append(project_name)
        
        # 更新类别统计
        if app_category not in self.learned["category_stats"]:
            self.learned["category_stats"][app_category] = {
                "count": 0,
                "avg_onboarding_steps": 0,
                "paywall_positions": [],
                "common_types": {},
                "products": []
            }
        
        cat_stats = self.learned["category_stats"][app_category]
        cat_stats["count"] += 1
        cat_stats["products"].append(project_name)
        
        # 分析Onboarding长度
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        # 更新平均值
        prev_avg = cat_stats["avg_onboarding_steps"]
        prev_count = cat_stats["count"] - 1
        cat_stats["avg_onboarding_steps"] = (
            (prev_avg * prev_count + onboarding_count) / cat_stats["count"]
        )
        
        # 记录Paywall位置
        paywall_pos = flow_structure.get("paywall_position", "none")
        cat_stats["paywall_positions"].append(paywall_pos)
        
        # 统计类型分布
        for r in results.values():
            screen_type = r.get("screen_type", "Unknown")
            cat_stats["common_types"][screen_type] = (
                cat_stats["common_types"].get(screen_type, 0) + 1
            )
        
        # 提取设计模式
        patterns_found = self._extract_patterns(results, flow_structure)
        
        # 更新模式出现次数
        for pattern_name in patterns_found:
            if pattern_name not in self.learned["pattern_occurrences"]:
                self.learned["pattern_occurrences"][pattern_name] = {
                    "count": 0,
                    "products": []
                }
            self.learned["pattern_occurrences"][pattern_name]["count"] += 1
            self.learned["pattern_occurrences"][pattern_name]["products"].append(project_name)
        
        # 更新时间戳
        self.learned["last_updated"] = datetime.now().isoformat()
        
        # 保存学习结果
        self._save_json(self.learned_file, self.learned)
        
        return {
            "patterns_found": patterns_found,
            "category_stats": cat_stats,
            "onboarding_steps": onboarding_count
        }
    
    def _extract_patterns(self, results: Dict[str, Dict], flow_structure: Dict) -> List[str]:
        """从分析结果中提取设计模式"""
        patterns = []
        
        # 检查Onboarding模式
        onboarding_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Onboarding"
        ]
        
        if len(onboarding_screens) >= 5:
            # 检查是否有渐进式披露
            patterns.append("progressive_disclosure")
        
        # 检查是否有目标优先
        if onboarding_screens:
            first_onboarding = min(onboarding_screens, key=lambda x: x.get("index", 999))
            sub_type = first_onboarding.get("sub_type", "").lower()
            if "goal" in sub_type or "objective" in sub_type:
                patterns.append("goal_first")
        
        # 检查Paywall模式
        paywall_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Paywall"
        ]
        
        if paywall_screens:
            for paywall in paywall_screens:
                keywords = paywall.get("keywords_found", [])
                keywords_lower = [k.lower() for k in keywords]
                
                if any("trial" in k or "free" in k for k in keywords_lower):
                    patterns.append("trial_first")
                
                if any("save" in k or "%" in k for k in keywords_lower):
                    patterns.append("price_anchoring")
        
        return list(set(patterns))
    
    def get_category_benchmark(self, category: str) -> Dict:
        """获取类别的基准数据"""
        # 优先使用学习到的数据
        learned_stats = self.learned.get("category_stats", {}).get(category, {})
        
        # 获取预设的基准
        preset_key = self._map_category_to_benchmark(category)
        preset_benchmark = self.benchmarks.get(preset_key, {})
        
        # 合并（学习数据优先）
        if learned_stats.get("count", 0) >= 3:
            # 如果已经分析了3个以上同类产品，使用学习数据
            return {
                "source": "learned",
                "products_analyzed": learned_stats.get("count", 0),
                "avg_onboarding_steps": learned_stats.get("avg_onboarding_steps", 8),
                "common_types": learned_stats.get("common_types", {}),
                "preset_benchmark": preset_benchmark
            }
        else:
            # 使用预设基准
            return {
                "source": "preset",
                "preset_benchmark": preset_benchmark,
                "learned_stats": learned_stats
            }
    
    def _map_category_to_benchmark(self, category: str) -> str:
        """将类别映射到基准数据键"""
        mapping = {
            "冥想正念": "meditation_apps",
            "Meditation": "meditation_apps",
            "健康健身": "fitness_apps",
            "Health & Fitness": "fitness_apps",
            "饮食营养": "nutrition_apps",
            "Nutrition & Diet": "nutrition_apps",
            "运动追踪": "running_apps",
            "Sports Tracking": "running_apps",
            "女性健康": "women_health_apps",
            "Women's Health": "women_health_apps",
            "睡眠改善": "sleep_apps",
            "Sleep": "sleep_apps"
        }
        return mapping.get(category, "general_benchmarks")
    
    def compare_with_benchmark(
        self,
        project_name: str,
        product_profile: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        与行业基准对比
        
        Returns:
            对比报告
        """
        category = product_profile.get("app_category", "Other")
        benchmark = self.get_category_benchmark(category)
        
        # 计算当前产品指标
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        total_screens = len(results)
        
        # 类型分布
        type_distribution = Counter(
            r.get("screen_type", "Unknown") for r in results.values()
        )
        
        # 对比
        comparison = {
            "project_name": project_name,
            "category": category,
            "metrics": {
                "onboarding_steps": {
                    "current": onboarding_count,
                    "benchmark": benchmark.get("preset_benchmark", {}).get("metrics", {}).get("avg_onboarding_steps", "N/A"),
                    "status": self._compare_value(
                        onboarding_count,
                        benchmark.get("preset_benchmark", {}).get("metrics", {}).get("onboarding_range", [5, 12])
                    )
                },
                "total_screens": total_screens,
                "type_distribution": dict(type_distribution)
            },
            "benchmark_source": benchmark.get("source", "preset")
        }
        
        return comparison
    
    def _compare_value(self, value: int, range_tuple: List[int]) -> str:
        """比较值是否在范围内"""
        if not range_tuple or len(range_tuple) < 2:
            return "unknown"
        
        if value < range_tuple[0]:
            return "below_average"
        elif value > range_tuple[1]:
            return "above_average"
        else:
            return "normal"
    
    def get_cross_product_insights(self) -> Dict:
        """获取跨产品洞察"""
        insights = {
            "total_products_analyzed": len(self.learned.get("products_analyzed", [])),
            "categories_covered": list(self.learned.get("category_stats", {}).keys()),
            "most_common_patterns": [],
            "category_comparisons": {}
        }
        
        # 最常见的模式
        pattern_counts = self.learned.get("pattern_occurrences", {})
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        insights["most_common_patterns"] = [
            {"pattern": p, "count": c.get("count", 0)}
            for p, c in sorted_patterns[:10]
        ]
        
        # 类别对比
        for cat, stats in self.learned.get("category_stats", {}).items():
            insights["category_comparisons"][cat] = {
                "products_count": stats.get("count", 0),
                "avg_onboarding": stats.get("avg_onboarding_steps", 0),
                "top_types": dict(
                    Counter(stats.get("common_types", {})).most_common(5)
                )
            }
        
        return insights


# ============================================================
# 便捷函数
# ============================================================

def learn_from_project(project_path: str) -> Dict:
    """从项目中学习"""
    # 加载分析结果
    analysis_file = os.path.join(project_path, "ai_analysis.json")
    profile_file = os.path.join(project_path, "product_profile.json")
    structure_file = os.path.join(project_path, "flow_structure.json")
    
    if not all(os.path.exists(f) for f in [analysis_file, profile_file, structure_file]):
        return {"error": "Missing analysis files"}
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    # 学习
    learner = KnowledgeLearner()
    return learner.learn_from_analysis(
        project_name=analysis.get("project_name", "Unknown"),
        product_profile=profile,
        flow_structure=structure,
        results=analysis.get("results", {})
    )


if __name__ == "__main__":
    # 测试
    learner = KnowledgeLearner()
    insights = learner.get_cross_product_insights()
    print(json.dumps(insights, ensure_ascii=False, indent=2))


"""
知识学习器
从分析结果中学习模式，更新知识库
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict


class KnowledgeLearner:
    """
    知识学习器
    
    功能：
    1. 从分析结果中提取模式
    2. 更新行业基准数据
    3. 发现跨产品的共性和差异
    """
    
    def __init__(self):
        self.knowledge_dir = os.path.dirname(os.path.abspath(__file__))
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.benchmarks_file = os.path.join(self.knowledge_dir, "benchmarks.json")
        self.learned_file = os.path.join(self.knowledge_dir, "learned_patterns.json")
        
        # 加载现有知识
        self.patterns = self._load_json(self.patterns_file)
        self.benchmarks = self._load_json(self.benchmarks_file)
        self.learned = self._load_json(self.learned_file) or {
            "products_analyzed": [],
            "category_stats": {},
            "pattern_occurrences": {},
            "last_updated": None
        }
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """加载JSON文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(
        self,
        project_name: str,
        product_profile: Dict,
        flow_structure: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        从分析结果中学习
        
        Args:
            project_name: 项目名称
            product_profile: 产品画像
            flow_structure: 流程结构
            results: 分析结果
        
        Returns:
            学习报告
        """
        app_category = product_profile.get("app_category", "Other")
        
        # 记录已分析产品
        if project_name not in self.learned["products_analyzed"]:
            self.learned["products_analyzed"].append(project_name)
        
        # 更新类别统计
        if app_category not in self.learned["category_stats"]:
            self.learned["category_stats"][app_category] = {
                "count": 0,
                "avg_onboarding_steps": 0,
                "paywall_positions": [],
                "common_types": {},
                "products": []
            }
        
        cat_stats = self.learned["category_stats"][app_category]
        cat_stats["count"] += 1
        cat_stats["products"].append(project_name)
        
        # 分析Onboarding长度
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        # 更新平均值
        prev_avg = cat_stats["avg_onboarding_steps"]
        prev_count = cat_stats["count"] - 1
        cat_stats["avg_onboarding_steps"] = (
            (prev_avg * prev_count + onboarding_count) / cat_stats["count"]
        )
        
        # 记录Paywall位置
        paywall_pos = flow_structure.get("paywall_position", "none")
        cat_stats["paywall_positions"].append(paywall_pos)
        
        # 统计类型分布
        for r in results.values():
            screen_type = r.get("screen_type", "Unknown")
            cat_stats["common_types"][screen_type] = (
                cat_stats["common_types"].get(screen_type, 0) + 1
            )
        
        # 提取设计模式
        patterns_found = self._extract_patterns(results, flow_structure)
        
        # 更新模式出现次数
        for pattern_name in patterns_found:
            if pattern_name not in self.learned["pattern_occurrences"]:
                self.learned["pattern_occurrences"][pattern_name] = {
                    "count": 0,
                    "products": []
                }
            self.learned["pattern_occurrences"][pattern_name]["count"] += 1
            self.learned["pattern_occurrences"][pattern_name]["products"].append(project_name)
        
        # 更新时间戳
        self.learned["last_updated"] = datetime.now().isoformat()
        
        # 保存学习结果
        self._save_json(self.learned_file, self.learned)
        
        return {
            "patterns_found": patterns_found,
            "category_stats": cat_stats,
            "onboarding_steps": onboarding_count
        }
    
    def _extract_patterns(self, results: Dict[str, Dict], flow_structure: Dict) -> List[str]:
        """从分析结果中提取设计模式"""
        patterns = []
        
        # 检查Onboarding模式
        onboarding_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Onboarding"
        ]
        
        if len(onboarding_screens) >= 5:
            # 检查是否有渐进式披露
            patterns.append("progressive_disclosure")
        
        # 检查是否有目标优先
        if onboarding_screens:
            first_onboarding = min(onboarding_screens, key=lambda x: x.get("index", 999))
            sub_type = first_onboarding.get("sub_type", "").lower()
            if "goal" in sub_type or "objective" in sub_type:
                patterns.append("goal_first")
        
        # 检查Paywall模式
        paywall_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Paywall"
        ]
        
        if paywall_screens:
            for paywall in paywall_screens:
                keywords = paywall.get("keywords_found", [])
                keywords_lower = [k.lower() for k in keywords]
                
                if any("trial" in k or "free" in k for k in keywords_lower):
                    patterns.append("trial_first")
                
                if any("save" in k or "%" in k for k in keywords_lower):
                    patterns.append("price_anchoring")
        
        return list(set(patterns))
    
    def get_category_benchmark(self, category: str) -> Dict:
        """获取类别的基准数据"""
        # 优先使用学习到的数据
        learned_stats = self.learned.get("category_stats", {}).get(category, {})
        
        # 获取预设的基准
        preset_key = self._map_category_to_benchmark(category)
        preset_benchmark = self.benchmarks.get(preset_key, {})
        
        # 合并（学习数据优先）
        if learned_stats.get("count", 0) >= 3:
            # 如果已经分析了3个以上同类产品，使用学习数据
            return {
                "source": "learned",
                "products_analyzed": learned_stats.get("count", 0),
                "avg_onboarding_steps": learned_stats.get("avg_onboarding_steps", 8),
                "common_types": learned_stats.get("common_types", {}),
                "preset_benchmark": preset_benchmark
            }
        else:
            # 使用预设基准
            return {
                "source": "preset",
                "preset_benchmark": preset_benchmark,
                "learned_stats": learned_stats
            }
    
    def _map_category_to_benchmark(self, category: str) -> str:
        """将类别映射到基准数据键"""
        mapping = {
            "冥想正念": "meditation_apps",
            "Meditation": "meditation_apps",
            "健康健身": "fitness_apps",
            "Health & Fitness": "fitness_apps",
            "饮食营养": "nutrition_apps",
            "Nutrition & Diet": "nutrition_apps",
            "运动追踪": "running_apps",
            "Sports Tracking": "running_apps",
            "女性健康": "women_health_apps",
            "Women's Health": "women_health_apps",
            "睡眠改善": "sleep_apps",
            "Sleep": "sleep_apps"
        }
        return mapping.get(category, "general_benchmarks")
    
    def compare_with_benchmark(
        self,
        project_name: str,
        product_profile: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        与行业基准对比
        
        Returns:
            对比报告
        """
        category = product_profile.get("app_category", "Other")
        benchmark = self.get_category_benchmark(category)
        
        # 计算当前产品指标
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        total_screens = len(results)
        
        # 类型分布
        type_distribution = Counter(
            r.get("screen_type", "Unknown") for r in results.values()
        )
        
        # 对比
        comparison = {
            "project_name": project_name,
            "category": category,
            "metrics": {
                "onboarding_steps": {
                    "current": onboarding_count,
                    "benchmark": benchmark.get("preset_benchmark", {}).get("metrics", {}).get("avg_onboarding_steps", "N/A"),
                    "status": self._compare_value(
                        onboarding_count,
                        benchmark.get("preset_benchmark", {}).get("metrics", {}).get("onboarding_range", [5, 12])
                    )
                },
                "total_screens": total_screens,
                "type_distribution": dict(type_distribution)
            },
            "benchmark_source": benchmark.get("source", "preset")
        }
        
        return comparison
    
    def _compare_value(self, value: int, range_tuple: List[int]) -> str:
        """比较值是否在范围内"""
        if not range_tuple or len(range_tuple) < 2:
            return "unknown"
        
        if value < range_tuple[0]:
            return "below_average"
        elif value > range_tuple[1]:
            return "above_average"
        else:
            return "normal"
    
    def get_cross_product_insights(self) -> Dict:
        """获取跨产品洞察"""
        insights = {
            "total_products_analyzed": len(self.learned.get("products_analyzed", [])),
            "categories_covered": list(self.learned.get("category_stats", {}).keys()),
            "most_common_patterns": [],
            "category_comparisons": {}
        }
        
        # 最常见的模式
        pattern_counts = self.learned.get("pattern_occurrences", {})
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        insights["most_common_patterns"] = [
            {"pattern": p, "count": c.get("count", 0)}
            for p, c in sorted_patterns[:10]
        ]
        
        # 类别对比
        for cat, stats in self.learned.get("category_stats", {}).items():
            insights["category_comparisons"][cat] = {
                "products_count": stats.get("count", 0),
                "avg_onboarding": stats.get("avg_onboarding_steps", 0),
                "top_types": dict(
                    Counter(stats.get("common_types", {})).most_common(5)
                )
            }
        
        return insights


# ============================================================
# 便捷函数
# ============================================================

def learn_from_project(project_path: str) -> Dict:
    """从项目中学习"""
    # 加载分析结果
    analysis_file = os.path.join(project_path, "ai_analysis.json")
    profile_file = os.path.join(project_path, "product_profile.json")
    structure_file = os.path.join(project_path, "flow_structure.json")
    
    if not all(os.path.exists(f) for f in [analysis_file, profile_file, structure_file]):
        return {"error": "Missing analysis files"}
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    # 学习
    learner = KnowledgeLearner()
    return learner.learn_from_analysis(
        project_name=analysis.get("project_name", "Unknown"),
        product_profile=profile,
        flow_structure=structure,
        results=analysis.get("results", {})
    )


if __name__ == "__main__":
    # 测试
    learner = KnowledgeLearner()
    insights = learner.get_cross_product_insights()
    print(json.dumps(insights, ensure_ascii=False, indent=2))


"""
知识学习器
从分析结果中学习模式，更新知识库
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict


class KnowledgeLearner:
    """
    知识学习器
    
    功能：
    1. 从分析结果中提取模式
    2. 更新行业基准数据
    3. 发现跨产品的共性和差异
    """
    
    def __init__(self):
        self.knowledge_dir = os.path.dirname(os.path.abspath(__file__))
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.benchmarks_file = os.path.join(self.knowledge_dir, "benchmarks.json")
        self.learned_file = os.path.join(self.knowledge_dir, "learned_patterns.json")
        
        # 加载现有知识
        self.patterns = self._load_json(self.patterns_file)
        self.benchmarks = self._load_json(self.benchmarks_file)
        self.learned = self._load_json(self.learned_file) or {
            "products_analyzed": [],
            "category_stats": {},
            "pattern_occurrences": {},
            "last_updated": None
        }
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """加载JSON文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(
        self,
        project_name: str,
        product_profile: Dict,
        flow_structure: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        从分析结果中学习
        
        Args:
            project_name: 项目名称
            product_profile: 产品画像
            flow_structure: 流程结构
            results: 分析结果
        
        Returns:
            学习报告
        """
        app_category = product_profile.get("app_category", "Other")
        
        # 记录已分析产品
        if project_name not in self.learned["products_analyzed"]:
            self.learned["products_analyzed"].append(project_name)
        
        # 更新类别统计
        if app_category not in self.learned["category_stats"]:
            self.learned["category_stats"][app_category] = {
                "count": 0,
                "avg_onboarding_steps": 0,
                "paywall_positions": [],
                "common_types": {},
                "products": []
            }
        
        cat_stats = self.learned["category_stats"][app_category]
        cat_stats["count"] += 1
        cat_stats["products"].append(project_name)
        
        # 分析Onboarding长度
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        # 更新平均值
        prev_avg = cat_stats["avg_onboarding_steps"]
        prev_count = cat_stats["count"] - 1
        cat_stats["avg_onboarding_steps"] = (
            (prev_avg * prev_count + onboarding_count) / cat_stats["count"]
        )
        
        # 记录Paywall位置
        paywall_pos = flow_structure.get("paywall_position", "none")
        cat_stats["paywall_positions"].append(paywall_pos)
        
        # 统计类型分布
        for r in results.values():
            screen_type = r.get("screen_type", "Unknown")
            cat_stats["common_types"][screen_type] = (
                cat_stats["common_types"].get(screen_type, 0) + 1
            )
        
        # 提取设计模式
        patterns_found = self._extract_patterns(results, flow_structure)
        
        # 更新模式出现次数
        for pattern_name in patterns_found:
            if pattern_name not in self.learned["pattern_occurrences"]:
                self.learned["pattern_occurrences"][pattern_name] = {
                    "count": 0,
                    "products": []
                }
            self.learned["pattern_occurrences"][pattern_name]["count"] += 1
            self.learned["pattern_occurrences"][pattern_name]["products"].append(project_name)
        
        # 更新时间戳
        self.learned["last_updated"] = datetime.now().isoformat()
        
        # 保存学习结果
        self._save_json(self.learned_file, self.learned)
        
        return {
            "patterns_found": patterns_found,
            "category_stats": cat_stats,
            "onboarding_steps": onboarding_count
        }
    
    def _extract_patterns(self, results: Dict[str, Dict], flow_structure: Dict) -> List[str]:
        """从分析结果中提取设计模式"""
        patterns = []
        
        # 检查Onboarding模式
        onboarding_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Onboarding"
        ]
        
        if len(onboarding_screens) >= 5:
            # 检查是否有渐进式披露
            patterns.append("progressive_disclosure")
        
        # 检查是否有目标优先
        if onboarding_screens:
            first_onboarding = min(onboarding_screens, key=lambda x: x.get("index", 999))
            sub_type = first_onboarding.get("sub_type", "").lower()
            if "goal" in sub_type or "objective" in sub_type:
                patterns.append("goal_first")
        
        # 检查Paywall模式
        paywall_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Paywall"
        ]
        
        if paywall_screens:
            for paywall in paywall_screens:
                keywords = paywall.get("keywords_found", [])
                keywords_lower = [k.lower() for k in keywords]
                
                if any("trial" in k or "free" in k for k in keywords_lower):
                    patterns.append("trial_first")
                
                if any("save" in k or "%" in k for k in keywords_lower):
                    patterns.append("price_anchoring")
        
        return list(set(patterns))
    
    def get_category_benchmark(self, category: str) -> Dict:
        """获取类别的基准数据"""
        # 优先使用学习到的数据
        learned_stats = self.learned.get("category_stats", {}).get(category, {})
        
        # 获取预设的基准
        preset_key = self._map_category_to_benchmark(category)
        preset_benchmark = self.benchmarks.get(preset_key, {})
        
        # 合并（学习数据优先）
        if learned_stats.get("count", 0) >= 3:
            # 如果已经分析了3个以上同类产品，使用学习数据
            return {
                "source": "learned",
                "products_analyzed": learned_stats.get("count", 0),
                "avg_onboarding_steps": learned_stats.get("avg_onboarding_steps", 8),
                "common_types": learned_stats.get("common_types", {}),
                "preset_benchmark": preset_benchmark
            }
        else:
            # 使用预设基准
            return {
                "source": "preset",
                "preset_benchmark": preset_benchmark,
                "learned_stats": learned_stats
            }
    
    def _map_category_to_benchmark(self, category: str) -> str:
        """将类别映射到基准数据键"""
        mapping = {
            "冥想正念": "meditation_apps",
            "Meditation": "meditation_apps",
            "健康健身": "fitness_apps",
            "Health & Fitness": "fitness_apps",
            "饮食营养": "nutrition_apps",
            "Nutrition & Diet": "nutrition_apps",
            "运动追踪": "running_apps",
            "Sports Tracking": "running_apps",
            "女性健康": "women_health_apps",
            "Women's Health": "women_health_apps",
            "睡眠改善": "sleep_apps",
            "Sleep": "sleep_apps"
        }
        return mapping.get(category, "general_benchmarks")
    
    def compare_with_benchmark(
        self,
        project_name: str,
        product_profile: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        与行业基准对比
        
        Returns:
            对比报告
        """
        category = product_profile.get("app_category", "Other")
        benchmark = self.get_category_benchmark(category)
        
        # 计算当前产品指标
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        total_screens = len(results)
        
        # 类型分布
        type_distribution = Counter(
            r.get("screen_type", "Unknown") for r in results.values()
        )
        
        # 对比
        comparison = {
            "project_name": project_name,
            "category": category,
            "metrics": {
                "onboarding_steps": {
                    "current": onboarding_count,
                    "benchmark": benchmark.get("preset_benchmark", {}).get("metrics", {}).get("avg_onboarding_steps", "N/A"),
                    "status": self._compare_value(
                        onboarding_count,
                        benchmark.get("preset_benchmark", {}).get("metrics", {}).get("onboarding_range", [5, 12])
                    )
                },
                "total_screens": total_screens,
                "type_distribution": dict(type_distribution)
            },
            "benchmark_source": benchmark.get("source", "preset")
        }
        
        return comparison
    
    def _compare_value(self, value: int, range_tuple: List[int]) -> str:
        """比较值是否在范围内"""
        if not range_tuple or len(range_tuple) < 2:
            return "unknown"
        
        if value < range_tuple[0]:
            return "below_average"
        elif value > range_tuple[1]:
            return "above_average"
        else:
            return "normal"
    
    def get_cross_product_insights(self) -> Dict:
        """获取跨产品洞察"""
        insights = {
            "total_products_analyzed": len(self.learned.get("products_analyzed", [])),
            "categories_covered": list(self.learned.get("category_stats", {}).keys()),
            "most_common_patterns": [],
            "category_comparisons": {}
        }
        
        # 最常见的模式
        pattern_counts = self.learned.get("pattern_occurrences", {})
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        insights["most_common_patterns"] = [
            {"pattern": p, "count": c.get("count", 0)}
            for p, c in sorted_patterns[:10]
        ]
        
        # 类别对比
        for cat, stats in self.learned.get("category_stats", {}).items():
            insights["category_comparisons"][cat] = {
                "products_count": stats.get("count", 0),
                "avg_onboarding": stats.get("avg_onboarding_steps", 0),
                "top_types": dict(
                    Counter(stats.get("common_types", {})).most_common(5)
                )
            }
        
        return insights


# ============================================================
# 便捷函数
# ============================================================

def learn_from_project(project_path: str) -> Dict:
    """从项目中学习"""
    # 加载分析结果
    analysis_file = os.path.join(project_path, "ai_analysis.json")
    profile_file = os.path.join(project_path, "product_profile.json")
    structure_file = os.path.join(project_path, "flow_structure.json")
    
    if not all(os.path.exists(f) for f in [analysis_file, profile_file, structure_file]):
        return {"error": "Missing analysis files"}
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    # 学习
    learner = KnowledgeLearner()
    return learner.learn_from_analysis(
        project_name=analysis.get("project_name", "Unknown"),
        product_profile=profile,
        flow_structure=structure,
        results=analysis.get("results", {})
    )


if __name__ == "__main__":
    # 测试
    learner = KnowledgeLearner()
    insights = learner.get_cross_product_insights()
    print(json.dumps(insights, ensure_ascii=False, indent=2))



"""
知识学习器
从分析结果中学习模式，更新知识库
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict


class KnowledgeLearner:
    """
    知识学习器
    
    功能：
    1. 从分析结果中提取模式
    2. 更新行业基准数据
    3. 发现跨产品的共性和差异
    """
    
    def __init__(self):
        self.knowledge_dir = os.path.dirname(os.path.abspath(__file__))
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.benchmarks_file = os.path.join(self.knowledge_dir, "benchmarks.json")
        self.learned_file = os.path.join(self.knowledge_dir, "learned_patterns.json")
        
        # 加载现有知识
        self.patterns = self._load_json(self.patterns_file)
        self.benchmarks = self._load_json(self.benchmarks_file)
        self.learned = self._load_json(self.learned_file) or {
            "products_analyzed": [],
            "category_stats": {},
            "pattern_occurrences": {},
            "last_updated": None
        }
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """加载JSON文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(
        self,
        project_name: str,
        product_profile: Dict,
        flow_structure: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        从分析结果中学习
        
        Args:
            project_name: 项目名称
            product_profile: 产品画像
            flow_structure: 流程结构
            results: 分析结果
        
        Returns:
            学习报告
        """
        app_category = product_profile.get("app_category", "Other")
        
        # 记录已分析产品
        if project_name not in self.learned["products_analyzed"]:
            self.learned["products_analyzed"].append(project_name)
        
        # 更新类别统计
        if app_category not in self.learned["category_stats"]:
            self.learned["category_stats"][app_category] = {
                "count": 0,
                "avg_onboarding_steps": 0,
                "paywall_positions": [],
                "common_types": {},
                "products": []
            }
        
        cat_stats = self.learned["category_stats"][app_category]
        cat_stats["count"] += 1
        cat_stats["products"].append(project_name)
        
        # 分析Onboarding长度
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        # 更新平均值
        prev_avg = cat_stats["avg_onboarding_steps"]
        prev_count = cat_stats["count"] - 1
        cat_stats["avg_onboarding_steps"] = (
            (prev_avg * prev_count + onboarding_count) / cat_stats["count"]
        )
        
        # 记录Paywall位置
        paywall_pos = flow_structure.get("paywall_position", "none")
        cat_stats["paywall_positions"].append(paywall_pos)
        
        # 统计类型分布
        for r in results.values():
            screen_type = r.get("screen_type", "Unknown")
            cat_stats["common_types"][screen_type] = (
                cat_stats["common_types"].get(screen_type, 0) + 1
            )
        
        # 提取设计模式
        patterns_found = self._extract_patterns(results, flow_structure)
        
        # 更新模式出现次数
        for pattern_name in patterns_found:
            if pattern_name not in self.learned["pattern_occurrences"]:
                self.learned["pattern_occurrences"][pattern_name] = {
                    "count": 0,
                    "products": []
                }
            self.learned["pattern_occurrences"][pattern_name]["count"] += 1
            self.learned["pattern_occurrences"][pattern_name]["products"].append(project_name)
        
        # 更新时间戳
        self.learned["last_updated"] = datetime.now().isoformat()
        
        # 保存学习结果
        self._save_json(self.learned_file, self.learned)
        
        return {
            "patterns_found": patterns_found,
            "category_stats": cat_stats,
            "onboarding_steps": onboarding_count
        }
    
    def _extract_patterns(self, results: Dict[str, Dict], flow_structure: Dict) -> List[str]:
        """从分析结果中提取设计模式"""
        patterns = []
        
        # 检查Onboarding模式
        onboarding_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Onboarding"
        ]
        
        if len(onboarding_screens) >= 5:
            # 检查是否有渐进式披露
            patterns.append("progressive_disclosure")
        
        # 检查是否有目标优先
        if onboarding_screens:
            first_onboarding = min(onboarding_screens, key=lambda x: x.get("index", 999))
            sub_type = first_onboarding.get("sub_type", "").lower()
            if "goal" in sub_type or "objective" in sub_type:
                patterns.append("goal_first")
        
        # 检查Paywall模式
        paywall_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Paywall"
        ]
        
        if paywall_screens:
            for paywall in paywall_screens:
                keywords = paywall.get("keywords_found", [])
                keywords_lower = [k.lower() for k in keywords]
                
                if any("trial" in k or "free" in k for k in keywords_lower):
                    patterns.append("trial_first")
                
                if any("save" in k or "%" in k for k in keywords_lower):
                    patterns.append("price_anchoring")
        
        return list(set(patterns))
    
    def get_category_benchmark(self, category: str) -> Dict:
        """获取类别的基准数据"""
        # 优先使用学习到的数据
        learned_stats = self.learned.get("category_stats", {}).get(category, {})
        
        # 获取预设的基准
        preset_key = self._map_category_to_benchmark(category)
        preset_benchmark = self.benchmarks.get(preset_key, {})
        
        # 合并（学习数据优先）
        if learned_stats.get("count", 0) >= 3:
            # 如果已经分析了3个以上同类产品，使用学习数据
            return {
                "source": "learned",
                "products_analyzed": learned_stats.get("count", 0),
                "avg_onboarding_steps": learned_stats.get("avg_onboarding_steps", 8),
                "common_types": learned_stats.get("common_types", {}),
                "preset_benchmark": preset_benchmark
            }
        else:
            # 使用预设基准
            return {
                "source": "preset",
                "preset_benchmark": preset_benchmark,
                "learned_stats": learned_stats
            }
    
    def _map_category_to_benchmark(self, category: str) -> str:
        """将类别映射到基准数据键"""
        mapping = {
            "冥想正念": "meditation_apps",
            "Meditation": "meditation_apps",
            "健康健身": "fitness_apps",
            "Health & Fitness": "fitness_apps",
            "饮食营养": "nutrition_apps",
            "Nutrition & Diet": "nutrition_apps",
            "运动追踪": "running_apps",
            "Sports Tracking": "running_apps",
            "女性健康": "women_health_apps",
            "Women's Health": "women_health_apps",
            "睡眠改善": "sleep_apps",
            "Sleep": "sleep_apps"
        }
        return mapping.get(category, "general_benchmarks")
    
    def compare_with_benchmark(
        self,
        project_name: str,
        product_profile: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        与行业基准对比
        
        Returns:
            对比报告
        """
        category = product_profile.get("app_category", "Other")
        benchmark = self.get_category_benchmark(category)
        
        # 计算当前产品指标
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        total_screens = len(results)
        
        # 类型分布
        type_distribution = Counter(
            r.get("screen_type", "Unknown") for r in results.values()
        )
        
        # 对比
        comparison = {
            "project_name": project_name,
            "category": category,
            "metrics": {
                "onboarding_steps": {
                    "current": onboarding_count,
                    "benchmark": benchmark.get("preset_benchmark", {}).get("metrics", {}).get("avg_onboarding_steps", "N/A"),
                    "status": self._compare_value(
                        onboarding_count,
                        benchmark.get("preset_benchmark", {}).get("metrics", {}).get("onboarding_range", [5, 12])
                    )
                },
                "total_screens": total_screens,
                "type_distribution": dict(type_distribution)
            },
            "benchmark_source": benchmark.get("source", "preset")
        }
        
        return comparison
    
    def _compare_value(self, value: int, range_tuple: List[int]) -> str:
        """比较值是否在范围内"""
        if not range_tuple or len(range_tuple) < 2:
            return "unknown"
        
        if value < range_tuple[0]:
            return "below_average"
        elif value > range_tuple[1]:
            return "above_average"
        else:
            return "normal"
    
    def get_cross_product_insights(self) -> Dict:
        """获取跨产品洞察"""
        insights = {
            "total_products_analyzed": len(self.learned.get("products_analyzed", [])),
            "categories_covered": list(self.learned.get("category_stats", {}).keys()),
            "most_common_patterns": [],
            "category_comparisons": {}
        }
        
        # 最常见的模式
        pattern_counts = self.learned.get("pattern_occurrences", {})
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        insights["most_common_patterns"] = [
            {"pattern": p, "count": c.get("count", 0)}
            for p, c in sorted_patterns[:10]
        ]
        
        # 类别对比
        for cat, stats in self.learned.get("category_stats", {}).items():
            insights["category_comparisons"][cat] = {
                "products_count": stats.get("count", 0),
                "avg_onboarding": stats.get("avg_onboarding_steps", 0),
                "top_types": dict(
                    Counter(stats.get("common_types", {})).most_common(5)
                )
            }
        
        return insights


# ============================================================
# 便捷函数
# ============================================================

def learn_from_project(project_path: str) -> Dict:
    """从项目中学习"""
    # 加载分析结果
    analysis_file = os.path.join(project_path, "ai_analysis.json")
    profile_file = os.path.join(project_path, "product_profile.json")
    structure_file = os.path.join(project_path, "flow_structure.json")
    
    if not all(os.path.exists(f) for f in [analysis_file, profile_file, structure_file]):
        return {"error": "Missing analysis files"}
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    # 学习
    learner = KnowledgeLearner()
    return learner.learn_from_analysis(
        project_name=analysis.get("project_name", "Unknown"),
        product_profile=profile,
        flow_structure=structure,
        results=analysis.get("results", {})
    )


if __name__ == "__main__":
    # 测试
    learner = KnowledgeLearner()
    insights = learner.get_cross_product_insights()
    print(json.dumps(insights, ensure_ascii=False, indent=2))


"""
知识学习器
从分析结果中学习模式，更新知识库
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter, defaultdict


class KnowledgeLearner:
    """
    知识学习器
    
    功能：
    1. 从分析结果中提取模式
    2. 更新行业基准数据
    3. 发现跨产品的共性和差异
    """
    
    def __init__(self):
        self.knowledge_dir = os.path.dirname(os.path.abspath(__file__))
        self.patterns_file = os.path.join(self.knowledge_dir, "patterns.json")
        self.benchmarks_file = os.path.join(self.knowledge_dir, "benchmarks.json")
        self.learned_file = os.path.join(self.knowledge_dir, "learned_patterns.json")
        
        # 加载现有知识
        self.patterns = self._load_json(self.patterns_file)
        self.benchmarks = self._load_json(self.benchmarks_file)
        self.learned = self._load_json(self.learned_file) or {
            "products_analyzed": [],
            "category_stats": {},
            "pattern_occurrences": {},
            "last_updated": None
        }
    
    def _load_json(self, filepath: str) -> Optional[Dict]:
        """加载JSON文件"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    def _save_json(self, filepath: str, data: Dict):
        """保存JSON文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def learn_from_analysis(
        self,
        project_name: str,
        product_profile: Dict,
        flow_structure: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        从分析结果中学习
        
        Args:
            project_name: 项目名称
            product_profile: 产品画像
            flow_structure: 流程结构
            results: 分析结果
        
        Returns:
            学习报告
        """
        app_category = product_profile.get("app_category", "Other")
        
        # 记录已分析产品
        if project_name not in self.learned["products_analyzed"]:
            self.learned["products_analyzed"].append(project_name)
        
        # 更新类别统计
        if app_category not in self.learned["category_stats"]:
            self.learned["category_stats"][app_category] = {
                "count": 0,
                "avg_onboarding_steps": 0,
                "paywall_positions": [],
                "common_types": {},
                "products": []
            }
        
        cat_stats = self.learned["category_stats"][app_category]
        cat_stats["count"] += 1
        cat_stats["products"].append(project_name)
        
        # 分析Onboarding长度
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        # 更新平均值
        prev_avg = cat_stats["avg_onboarding_steps"]
        prev_count = cat_stats["count"] - 1
        cat_stats["avg_onboarding_steps"] = (
            (prev_avg * prev_count + onboarding_count) / cat_stats["count"]
        )
        
        # 记录Paywall位置
        paywall_pos = flow_structure.get("paywall_position", "none")
        cat_stats["paywall_positions"].append(paywall_pos)
        
        # 统计类型分布
        for r in results.values():
            screen_type = r.get("screen_type", "Unknown")
            cat_stats["common_types"][screen_type] = (
                cat_stats["common_types"].get(screen_type, 0) + 1
            )
        
        # 提取设计模式
        patterns_found = self._extract_patterns(results, flow_structure)
        
        # 更新模式出现次数
        for pattern_name in patterns_found:
            if pattern_name not in self.learned["pattern_occurrences"]:
                self.learned["pattern_occurrences"][pattern_name] = {
                    "count": 0,
                    "products": []
                }
            self.learned["pattern_occurrences"][pattern_name]["count"] += 1
            self.learned["pattern_occurrences"][pattern_name]["products"].append(project_name)
        
        # 更新时间戳
        self.learned["last_updated"] = datetime.now().isoformat()
        
        # 保存学习结果
        self._save_json(self.learned_file, self.learned)
        
        return {
            "patterns_found": patterns_found,
            "category_stats": cat_stats,
            "onboarding_steps": onboarding_count
        }
    
    def _extract_patterns(self, results: Dict[str, Dict], flow_structure: Dict) -> List[str]:
        """从分析结果中提取设计模式"""
        patterns = []
        
        # 检查Onboarding模式
        onboarding_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Onboarding"
        ]
        
        if len(onboarding_screens) >= 5:
            # 检查是否有渐进式披露
            patterns.append("progressive_disclosure")
        
        # 检查是否有目标优先
        if onboarding_screens:
            first_onboarding = min(onboarding_screens, key=lambda x: x.get("index", 999))
            sub_type = first_onboarding.get("sub_type", "").lower()
            if "goal" in sub_type or "objective" in sub_type:
                patterns.append("goal_first")
        
        # 检查Paywall模式
        paywall_screens = [
            r for r in results.values()
            if r.get("screen_type") == "Paywall"
        ]
        
        if paywall_screens:
            for paywall in paywall_screens:
                keywords = paywall.get("keywords_found", [])
                keywords_lower = [k.lower() for k in keywords]
                
                if any("trial" in k or "free" in k for k in keywords_lower):
                    patterns.append("trial_first")
                
                if any("save" in k or "%" in k for k in keywords_lower):
                    patterns.append("price_anchoring")
        
        return list(set(patterns))
    
    def get_category_benchmark(self, category: str) -> Dict:
        """获取类别的基准数据"""
        # 优先使用学习到的数据
        learned_stats = self.learned.get("category_stats", {}).get(category, {})
        
        # 获取预设的基准
        preset_key = self._map_category_to_benchmark(category)
        preset_benchmark = self.benchmarks.get(preset_key, {})
        
        # 合并（学习数据优先）
        if learned_stats.get("count", 0) >= 3:
            # 如果已经分析了3个以上同类产品，使用学习数据
            return {
                "source": "learned",
                "products_analyzed": learned_stats.get("count", 0),
                "avg_onboarding_steps": learned_stats.get("avg_onboarding_steps", 8),
                "common_types": learned_stats.get("common_types", {}),
                "preset_benchmark": preset_benchmark
            }
        else:
            # 使用预设基准
            return {
                "source": "preset",
                "preset_benchmark": preset_benchmark,
                "learned_stats": learned_stats
            }
    
    def _map_category_to_benchmark(self, category: str) -> str:
        """将类别映射到基准数据键"""
        mapping = {
            "冥想正念": "meditation_apps",
            "Meditation": "meditation_apps",
            "健康健身": "fitness_apps",
            "Health & Fitness": "fitness_apps",
            "饮食营养": "nutrition_apps",
            "Nutrition & Diet": "nutrition_apps",
            "运动追踪": "running_apps",
            "Sports Tracking": "running_apps",
            "女性健康": "women_health_apps",
            "Women's Health": "women_health_apps",
            "睡眠改善": "sleep_apps",
            "Sleep": "sleep_apps"
        }
        return mapping.get(category, "general_benchmarks")
    
    def compare_with_benchmark(
        self,
        project_name: str,
        product_profile: Dict,
        results: Dict[str, Dict]
    ) -> Dict:
        """
        与行业基准对比
        
        Returns:
            对比报告
        """
        category = product_profile.get("app_category", "Other")
        benchmark = self.get_category_benchmark(category)
        
        # 计算当前产品指标
        onboarding_count = sum(
            1 for r in results.values()
            if r.get("screen_type") == "Onboarding"
        )
        
        total_screens = len(results)
        
        # 类型分布
        type_distribution = Counter(
            r.get("screen_type", "Unknown") for r in results.values()
        )
        
        # 对比
        comparison = {
            "project_name": project_name,
            "category": category,
            "metrics": {
                "onboarding_steps": {
                    "current": onboarding_count,
                    "benchmark": benchmark.get("preset_benchmark", {}).get("metrics", {}).get("avg_onboarding_steps", "N/A"),
                    "status": self._compare_value(
                        onboarding_count,
                        benchmark.get("preset_benchmark", {}).get("metrics", {}).get("onboarding_range", [5, 12])
                    )
                },
                "total_screens": total_screens,
                "type_distribution": dict(type_distribution)
            },
            "benchmark_source": benchmark.get("source", "preset")
        }
        
        return comparison
    
    def _compare_value(self, value: int, range_tuple: List[int]) -> str:
        """比较值是否在范围内"""
        if not range_tuple or len(range_tuple) < 2:
            return "unknown"
        
        if value < range_tuple[0]:
            return "below_average"
        elif value > range_tuple[1]:
            return "above_average"
        else:
            return "normal"
    
    def get_cross_product_insights(self) -> Dict:
        """获取跨产品洞察"""
        insights = {
            "total_products_analyzed": len(self.learned.get("products_analyzed", [])),
            "categories_covered": list(self.learned.get("category_stats", {}).keys()),
            "most_common_patterns": [],
            "category_comparisons": {}
        }
        
        # 最常见的模式
        pattern_counts = self.learned.get("pattern_occurrences", {})
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )
        insights["most_common_patterns"] = [
            {"pattern": p, "count": c.get("count", 0)}
            for p, c in sorted_patterns[:10]
        ]
        
        # 类别对比
        for cat, stats in self.learned.get("category_stats", {}).items():
            insights["category_comparisons"][cat] = {
                "products_count": stats.get("count", 0),
                "avg_onboarding": stats.get("avg_onboarding_steps", 0),
                "top_types": dict(
                    Counter(stats.get("common_types", {})).most_common(5)
                )
            }
        
        return insights


# ============================================================
# 便捷函数
# ============================================================

def learn_from_project(project_path: str) -> Dict:
    """从项目中学习"""
    # 加载分析结果
    analysis_file = os.path.join(project_path, "ai_analysis.json")
    profile_file = os.path.join(project_path, "product_profile.json")
    structure_file = os.path.join(project_path, "flow_structure.json")
    
    if not all(os.path.exists(f) for f in [analysis_file, profile_file, structure_file]):
        return {"error": "Missing analysis files"}
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile = json.load(f)
    
    with open(structure_file, 'r', encoding='utf-8') as f:
        structure = json.load(f)
    
    # 学习
    learner = KnowledgeLearner()
    return learner.learn_from_analysis(
        project_name=analysis.get("project_name", "Unknown"),
        product_profile=profile,
        flow_structure=structure,
        results=analysis.get("results", {})
    )


if __name__ == "__main__":
    # 测试
    learner = KnowledgeLearner()
    insights = learner.get_cross_product_insights()
    print(json.dumps(insights, ensure_ascii=False, indent=2))


















