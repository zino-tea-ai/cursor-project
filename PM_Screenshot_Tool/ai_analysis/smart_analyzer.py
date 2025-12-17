# -*- coding: utf-8 -*-
"""
智能分析器 - 主控模块
整合三层分析架构：产品认知 → 结构识别 → 精确分类 → 自我校验
支持三层分类体系：Stage / Module / Feature
"""

import os
import sys
import json

# 确保UTF-8输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict
from datetime import datetime

# 导入各层模块
from layer1_product import ProductRecognizer, ProductProfile
from layer2_structure import StructureRecognizer, FlowStructure
from layer3_classify import ContextClassifier
from self_validator import SelfValidator, ValidationResult
from anomaly_detector import AnomalyDetector, detect_anomalies

# 导入验证规则（用于三层分类）
try:
    from validation_rules import (
        STAGES, MODULES, FEATURES, ROLES,
        get_stage_for_module, get_module_for_feature
    )
    TAXONOMY_AVAILABLE = True
except ImportError:
    TAXONOMY_AVAILABLE = False

# 数据库模块
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from data.db_manager import get_db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class SmartAnalyzer:
    """
    智能分析器
    
    三层架构：
    1. Layer 1 - 产品认知：快速理解产品类型和目标用户
    2. Layer 2 - 结构识别：识别流程阶段边界
    3. Layer 3 - 精确分类：带上下文分析每张截图
    4. 校验层 - 自我校验：检查并修复异常
    
    输出三层分类：Stage / Module / Feature
    """
    
    def __init__(
        self,
        project_name: str,
        model: str = "claude-opus-4-5-20251101",
        concurrent: int = 5,
        auto_fix: bool = True,
        verbose: bool = True
    ):
        """
        初始化智能分析器
        
        Args:
            project_name: 项目名称
            model: AI模型
            concurrent: Layer 3并发数
            auto_fix: 是否自动修复问题
            verbose: 是否输出详细日志
        """
        self.project_name = project_name
        self.model = model
        self.concurrent = concurrent
        self.auto_fix = auto_fix
        self.verbose = verbose
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        
        # 输出文件
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        self.profile_file = os.path.join(self.project_path, "product_profile.json")
        self.structure_file = os.path.join(self.project_path, "flow_structure.json")
        
        # 各层分析器（延迟初始化）
        self._product_recognizer = None
        self._structure_recognizer = None
        self._classifier = None
        self._validator = None
        
        # 分析结果
        self.product_profile: Optional[ProductProfile] = None
        self.flow_structure: Optional[FlowStructure] = None
        self.results: Dict[str, Dict] = {}
        self.validation: Optional[ValidationResult] = None
    
    @property
    def product_recognizer(self) -> ProductRecognizer:
        if self._product_recognizer is None:
            self._product_recognizer = ProductRecognizer(model=self.model)
        return self._product_recognizer
    
    @property
    def structure_recognizer(self) -> StructureRecognizer:
        if self._structure_recognizer is None:
            self._structure_recognizer = StructureRecognizer(model=self.model)
        return self._structure_recognizer
    
    @property
    def classifier(self) -> ContextClassifier:
        if self._classifier is None:
            self._classifier = ContextClassifier(model=self.model, concurrent=self.concurrent)
        return self._classifier
    
    @property
    def validator(self) -> SelfValidator:
        if self._validator is None:
            self._validator = SelfValidator(verbose=self.verbose)
        return self._validator
    
    def _convert_to_three_layer(self, results: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        将旧的screen_type转换为新的三层分类（Stage/Module/Feature）
        """
        if not TAXONOMY_AVAILABLE:
            return results
        
        # screen_type到Module的映射
        type_to_module = {
            "Launch": ("Onboarding", "Welcome"),
            "Welcome": ("Onboarding", "Welcome"),
            "Permission": ("Onboarding", "Permission"),
            "SignUp": ("Onboarding", "Registration"),
            "Onboarding": ("Onboarding", "Profile"),
            "Paywall": ("Onboarding", "Paywall"),
            "Home": ("Core", "Dashboard"),
            "Dashboard": ("Core", "Dashboard"),
            "Tracking": ("Core", "Tracking"),
            "Progress": ("Core", "Progress"),
            "Content": ("Core", "Content"),
            "Social": ("Core", "Social"),
            "Profile": ("Core", "Profile_Core"),
            "Settings": ("Core", "Settings"),
            "Feature": ("Core", "Dashboard"),
            "Other": ("Core", "Dashboard"),
        }
        
        for filename, data in results.items():
            screen_type = data.get("screen_type", "Other")
            
            # 转换为三层分类
            stage, module = type_to_module.get(screen_type, ("Core", "Dashboard"))
            
            # 添加新字段
            data["stage"] = stage
            data["module"] = module
            data["feature"] = data.get("feature") or self._infer_feature(data, module)
            data["role"] = data.get("role") or self._infer_role(data)
        
        return results
    
    def _infer_feature(self, data: Dict, module: str) -> Optional[str]:
        """根据内容推断Feature"""
        naming_cn = data.get("naming", {}).get("cn", "").lower()
        core_func = data.get("core_function", {}).get("cn", "").lower()
        
        # 基于关键词推断
        feature_keywords = {
            "Welcome": {"启动": "Splash", "价值": "ValueProp", "介绍": "FeaturePreview"},
            "Profile": {"性别": "GenderSelect", "年龄": "AgeInput", "身高": "HeightInput", "体重": "WeightInput"},
            "Goal": {"目标": "DirectionSelect", "减重": "DirectionSelect", "时间": "TimelineSelect"},
            "Paywall": {"价格": "PriceDisplay", "套餐": "PlanSelect", "试用": "TrialOffer"},
            "Registration": {"邮箱": "EmailInput", "密码": "PasswordInput", "apple": "OAuthApple", "google": "OAuthGoogle"},
            "Tracking": {"搜索": "FoodSearch", "记录": "FoodLog", "扫描": "PhotoScan"},
            "Progress": {"周": "WeeklyChart", "月": "MonthlyChart", "趋势": "TrendAnalysis"},
        }
        
        keywords = feature_keywords.get(module, {})
        for keyword, feature in keywords.items():
            if keyword in naming_cn or keyword in core_func:
                return feature
        
        return None
    
    def _infer_role(self, data: Dict) -> str:
        """根据内容推断页面角色"""
        screen_type = data.get("screen_type", "")
        naming_cn = data.get("naming", {}).get("cn", "").lower()
        
        # 基于关键词判断角色
        if "列表" in naming_cn or "浏览" in naming_cn:
            return "Browse"
        elif "详情" in naming_cn or "查看" in naming_cn:
            return "Detail"
        elif "选择" in naming_cn or "输入" in naming_cn or "设置" in naming_cn:
            return "Action"
        elif "完成" in naming_cn or "成功" in naming_cn or "结果" in naming_cn:
            return "Result"
        elif "弹窗" in naming_cn or "提示" in naming_cn:
            return "Modal"
        else:
            return "Entry"
    
    def run(self) -> Dict[str, Dict]:
        """
        执行完整的智能分析流程
        
        Returns:
            分析结果 {filename: classification_dict}
        """
        start_time = datetime.now()
        
        print("\n" + "=" * 70)
        print(f"  SMART ANALYZER 2.1 - {self.project_name}")
        print("  (3-Layer Classification: Stage / Module / Feature)")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.project_path):
            print(f"[ERROR] Project not found: {self.project_path}")
            return {}
        
        # ==================== Layer 1 ====================
        print("\n" + "-" * 70)
        print("  LAYER 1: Product Recognition")
        print("-" * 70)
        
        app_name = self.project_name.replace("_Analysis", "").replace("_", " ")
        self.product_profile = self.product_recognizer.analyze(self.project_path, app_name)
        
        print(f"  App Category:    {self.product_profile.app_category}")
        print(f"  Sub Category:    {self.product_profile.sub_category}")
        print(f"  Target Users:    {self.product_profile.target_users}")
        print(f"  Core Value:      {self.product_profile.core_value}")
        print(f"  Business Model:  {self.product_profile.business_model}")
        print(f"  Visual Style:    {self.product_profile.visual_style}")
        print(f"  Confidence:      {self.product_profile.confidence:.0%}")
        
        # 保存产品画像
        self._save_profile()
        
        # ==================== Layer 2 ====================
        print("\n" + "-" * 70)
        print("  LAYER 2: Structure Recognition")
        print("-" * 70)
        
        self.flow_structure = self.structure_recognizer.analyze(
            self.project_path, 
            self.product_profile
        )
        
        print(f"  Total Screenshots: {self.flow_structure.total_screenshots}")
        print(f"  Stages Found:      {len(self.flow_structure.stages)}")
        print(f"  Paywall Position:  {self.flow_structure.paywall_position}")
        print(f"  Onboarding Length: {self.flow_structure.onboarding_length}")
        print(f"  Confidence:        {self.flow_structure.confidence:.0%}")
        print()
        
        for stage in self.flow_structure.stages:
            print(f"    [{stage.start_index:2d}-{stage.end_index:2d}] {stage.name}: {stage.description}")
        
        # 保存流程结构
        self._save_structure()
        
        # ==================== Layer 3 ====================
        print("\n" + "-" * 70)
        print("  LAYER 3: Context Classification")
        print("-" * 70)
        
        self.results = self.classifier.classify_all(
            self.project_path,
            self.product_profile,
            self.flow_structure
        )
        
        # ==================== 三层分类转换 ====================
        print("\n" + "-" * 70)
        print("  3-LAYER CLASSIFICATION")
        print("-" * 70)
        
        self.results = self._convert_to_three_layer(self.results)
        
        # 统计三层分类
        stage_counts = {}
        module_counts = {}
        for data in self.results.values():
            stage = data.get("stage", "Unknown")
            module = data.get("module", "Unknown")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            module_counts[module] = module_counts.get(module, 0) + 1
        
        print(f"\n  Stage Distribution:")
        for stage, count in sorted(stage_counts.items(), key=lambda x: -x[1]):
            print(f"    {stage:15s} {count:3d}")
        
        print(f"\n  Module Distribution (top 10):")
        for module, count in sorted(module_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"    {module:15s} {count:3d}")
        
        # ==================== Validation ====================
        print("\n" + "-" * 70)
        print("  VALIDATION & AUTO-FIX")
        print("-" * 70)
        
        if self.auto_fix:
            self.results, self.validation = self.validator.validate_and_fix(
                self.results,
                self.product_profile,
                self.flow_structure
            )
        else:
            self.validation = self.validator.validate(
                self.results,
                self.product_profile,
                self.flow_structure
            )
        
        # 输出统计
        stats = self.validation.stats
        print(f"\n  Type Distribution:")
        for type_name, count in sorted(stats.get("type_distribution", {}).items(), key=lambda x: -x[1]):
            pct = count / stats.get("total_screenshots", 1) * 100
            print(f"    {type_name:15s} {count:3d} ({pct:5.1f}%)")
        
        print(f"\n  Avg Confidence:    {stats.get('avg_confidence', 0):.0%}")
        print(f"  Low Confidence:    {stats.get('low_confidence_count', 0)}")
        
        # ==================== Anomaly Detection ====================
        print("\n" + "-" * 70)
        print("  ANOMALY DETECTION")
        print("-" * 70)
        
        anomalies, anomaly_summary = detect_anomalies(
            self.results,
            asdict(self.product_profile) if self.product_profile else None
        )
        
        print(f"\n  {anomaly_summary}")
        
        if anomalies:
            print("\n  Suggestions:")
            for a in anomalies:
                if a.suggestion:
                    print(f"    → {a.suggestion}")
        
        # 保存结果
        self._save_results()
        
        # 完成
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print(f"  ANALYSIS COMPLETE")
        print("=" * 70)
        print(f"  Total Time:        {total_time:.1f}s")
        print(f"  Screenshots:       {len(self.results)}")
        print(f"  Issues Found:      {len(self.validation.issues)}")
        print(f"  Fixes Applied:     {len(self.validation.fixes_applied)}")
        print(f"  Output:            {self.analysis_file}")
        print("=" * 70)
        
        return self.results
    
    def _save_profile(self):
        """保存产品画像"""
        profile_dict = asdict(self.product_profile)
        # 移除raw_analysis以减小文件大小
        profile_dict.pop('raw_analysis', None)
        
        with open(self.profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile_dict, f, ensure_ascii=False, indent=2)
    
    def _save_structure(self):
        """保存流程结构"""
        structure_dict = {
            "total_screenshots": self.flow_structure.total_screenshots,
            "stages": [
                {
                    "name": s.name,
                    "start_index": s.start_index,
                    "end_index": s.end_index,
                    "description": s.description,
                    "expected_types": s.expected_types,
                    "screenshot_count": s.screenshot_count
                }
                for s in self.flow_structure.stages
            ],
            "paywall_position": self.flow_structure.paywall_position,
            "onboarding_length": self.flow_structure.onboarding_length,
            "has_signup": self.flow_structure.has_signup,
            "has_social": self.flow_structure.has_social,
            "confidence": self.flow_structure.confidence
        }
        
        with open(self.structure_file, 'w', encoding='utf-8') as f:
            json.dump(structure_dict, f, ensure_ascii=False, indent=2)
    
    def _save_results(self):
        """保存分析结果"""
        output = {
            "project_name": self.project_name,
            "total_screenshots": len(self.results),
            "model": self.model,
            "analysis_version": "2.1",
            "classification_version": "3-layer",
            "product_profile": {
                "app_category": self.product_profile.app_category,
                "sub_category": self.product_profile.sub_category,
                "target_users": self.product_profile.target_users,
                "core_value": self.product_profile.core_value,
                "business_model": self.product_profile.business_model,
                "visual_style": self.product_profile.visual_style
            },
            "flow_structure": {
                "stages": [s.name for s in self.flow_structure.stages],
                "paywall_position": self.flow_structure.paywall_position,
                "onboarding_length": self.flow_structure.onboarding_length
            },
            "validation": {
                "is_valid": self.validation.is_valid,
                "issues_count": len(self.validation.issues),
                "fixes_applied": len(self.validation.fixes_applied),
                "stats": self.validation.stats
            },
            "results": self.results,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        # 同时生成兼容格式的 descriptions.json
        self._generate_descriptions()
        
        # 生成 structured_descriptions.json
        self._generate_structured_descriptions()
        
        # 写入数据库
        self._save_to_database()
    
    def _generate_descriptions(self):
        """生成兼容格式的 descriptions.json"""
        descriptions = {}
        
        for filename, data in self.results.items():
            naming = data.get("naming", {})
            core_func = data.get("core_function", {})
            
            cn_name = naming.get("cn", "")
            cn_func = core_func.get("cn", "")
            
            if cn_name and cn_func:
                desc = f"{cn_name}：{cn_func}"
            else:
                desc = cn_func or cn_name or data.get("description_cn", "")
            
            descriptions[filename] = desc
        
        desc_file = os.path.join(self.project_path, "descriptions.json")
        with open(desc_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
    
    def _generate_structured_descriptions(self):
        """生成 structured_descriptions.json（含三层分类）"""
        structured = {}
        
        for filename, data in self.results.items():
            structured[filename] = {
                "screen_type": data.get("screen_type", "Unknown"),
                "stage": data.get("stage"),
                "module": data.get("module"),
                "feature": data.get("feature"),
                "role": data.get("role"),
                "naming": data.get("naming", {}),
                "core_function": data.get("core_function", {}),
                "design_highlights": data.get("design_highlights", []),
                "product_insight": data.get("product_insight", {}),
                "tags": data.get("tags", []),
                "confidence": data.get("confidence", 0),
                "stage_name": data.get("stage_name", ""),
                "reasoning": data.get("reasoning", "")
            }
        
        struct_file = os.path.join(self.project_path, "structured_descriptions.json")
        with open(struct_file, 'w', encoding='utf-8') as f:
            json.dump(structured, f, ensure_ascii=False, indent=2)
    
    def _save_to_database(self):
        """保存分析结果到数据库（含三层分类）"""
        if not DB_AVAILABLE:
            if self.verbose:
                print("[DB] Database not available, skipping...")
            return
        
        try:
            db = get_db()
            
            # 产品名从项目名提取
            product_name = self.project_name.replace('_Analysis', '').replace('_', ' ')
            
            # 保存产品信息
            product_data = {
                'name': product_name,
                'folder_name': self.project_name,
                'category': self.product_profile.app_category if self.product_profile else None,
                'sub_category': self.product_profile.sub_category if self.product_profile else None,
                'target_users': self.product_profile.target_users if self.product_profile else None,
                'core_value': self.product_profile.core_value if self.product_profile else None,
                'business_model': self.product_profile.business_model if self.product_profile else None,
                'visual_style': self.product_profile.visual_style if self.product_profile else None,
                'paywall_position': self.flow_structure.paywall_position if self.flow_structure else None,
                'onboarding_length': self.flow_structure.onboarding_length if self.flow_structure else None,
                'total_screenshots': len(self.results),
                'model': self.model
            }
            
            product_id = db.save_product(product_data)
            
            # 保存截图（含三层分类）
            for filename, data in self.results.items():
                data['filename'] = filename
                db.save_screenshot(product_id, data)
            
            # 保存流程阶段
            if self.flow_structure and self.flow_structure.stages:
                stages = [{'name': s.name, 'start': s.start_index, 'end': s.end_index, 'description': s.description} 
                          for s in self.flow_structure.stages]
                db.save_flow_stages(product_id, stages)
            
            if self.verbose:
                print(f"[DB] Saved to database (product_id: {product_id})")
                
        except Exception as e:
            print(f"[DB] Error saving to database: {e}")
    
    def get_summary(self) -> Dict:
        """获取分析摘要"""
        if not self.results:
            return {}
        
        # 三层分类统计
        stage_dist = {}
        module_dist = {}
        for data in self.results.values():
            stage = data.get("stage", "Unknown")
            module = data.get("module", "Unknown")
            stage_dist[stage] = stage_dist.get(stage, 0) + 1
            module_dist[module] = module_dist.get(module, 0) + 1
        
        return {
            "project_name": self.project_name,
            "app_category": self.product_profile.app_category if self.product_profile else "",
            "total_screenshots": len(self.results),
            "stages": [s.name for s in self.flow_structure.stages] if self.flow_structure else [],
            "stage_distribution": stage_dist,
            "module_distribution": module_dist,
            "type_distribution": self.validation.stats.get("type_distribution", {}) if self.validation else {},
            "avg_confidence": self.validation.stats.get("avg_confidence", 0) if self.validation else 0
        }


# ============================================================
# 命令行入口
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Analyzer 2.1 - Context-Aware Screenshot Analysis with 3-Layer Classification")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--model", type=str, default="claude-opus-4-5-20251101", help="AI model")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--no-fix", action="store_true", help="Disable auto-fix")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    
    args = parser.parse_args()
    
    # 加载API Key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                api_key = config.get("ANTHROPIC_API_KEY", "")
        
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    # 运行分析
    analyzer = SmartAnalyzer(
        project_name=args.project,
        model=args.model,
        concurrent=args.concurrent,
        auto_fix=not args.no_fix,
        verbose=not args.quiet
    )
    
    results = analyzer.run()
    
    if results:
        print(f"\n[OK] Analysis complete: {len(results)} screenshots processed")
    else:
        print("\n[ERROR] Analysis failed")


if __name__ == "__main__":
    main()
