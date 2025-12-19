"""
流程对齐引擎 - Flow Aligner

功能：
- 加载所有竞品的 ai_analysis.json
- 按 screen_type 分组（Welcome, Onboarding, Paywall...）
- 在每个类型内，按 sub_type 或文件名中的步骤号进一步对齐
- 输出对齐后的矩阵结构
"""

import os
import json
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


class FlowAligner:
    """多竞品流程对齐引擎"""
    
    # 定义 screen_type 的标准顺序
    SCREEN_TYPE_ORDER = [
        "Launch", "Welcome", "Permission", "SignUp", "Onboarding",
        "Paywall", "Home", "Feature", "Content", "Profile",
        "Settings", "Social", "Tracking", "Progress", "Other"
    ]
    
    def __init__(self, projects_dir: str = None):
        """
        初始化流程对齐引擎
        
        Args:
            projects_dir: 项目目录路径，默认为 ../projects
        """
        if projects_dir is None:
            projects_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "projects"
            )
        self.projects_dir = projects_dir
        self.competitors: Dict[str, Dict] = {}  # 竞品名 -> 分析数据
        self.aligned_flows: Dict = {}  # 对齐后的流程数据
        
    def load_all_competitors(self, competitor_names: List[str] = None) -> Dict[str, Dict]:
        """
        加载所有竞品的分析数据
        
        Args:
            competitor_names: 指定竞品名称列表，None表示加载全部
            
        Returns:
            竞品名 -> 分析数据的字典
        """
        print("[INFO] Loading competitor analysis data...")
        
        # 扫描 projects 目录
        if not os.path.exists(self.projects_dir):
            print(f"[ERROR] Projects directory not found: {self.projects_dir}")
            return {}
            
        for folder in os.listdir(self.projects_dir):
            folder_path = os.path.join(self.projects_dir, folder)
            if not os.path.isdir(folder_path):
                continue
                
            # 提取竞品名称（去掉 _Analysis 后缀）
            competitor_name = folder.replace("_Analysis", "")
            
            # 如果指定了竞品列表，只加载指定的
            if competitor_names and competitor_name not in competitor_names:
                continue
                
            # 查找 ai_analysis.json
            analysis_file = os.path.join(folder_path, "ai_analysis.json")
            if not os.path.exists(analysis_file):
                print(f"  [SKIP] {competitor_name}: No ai_analysis.json found")
                continue
                
            try:
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.competitors[competitor_name] = data
                    screen_count = len(data.get("results", {}))
                    print(f"  [OK] {competitor_name}: {screen_count} screens loaded")
            except Exception as e:
                print(f"  [ERROR] {competitor_name}: {str(e)}")
                
        print(f"[INFO] Total {len(self.competitors)} competitors loaded")
        return self.competitors
    
    def _extract_step_number(self, filename: str) -> Tuple[int, int]:
        """
        从文件名提取阶段号和步骤号
        
        格式: XX_Type_NN.png -> (XX, NN)
        例如: 04_Onboarding_03.png -> (4, 3)
        
        Returns:
            (阶段号, 步骤号) 元组
        """
        # 匹配 数字_任意内容_数字.扩展名
        match = re.match(r'^(\d+)_[^_]+_(\d+)\.', filename)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        
        # 备用匹配：只有一个数字
        match = re.match(r'^(\d+)_', filename)
        if match:
            return (int(match.group(1)), 0)
            
        return (999, 999)  # 无法解析时放到最后
    
    def _normalize_sub_type(self, sub_type: str) -> str:
        """
        标准化 sub_type，用于对齐匹配
        
        将各种表述统一为标准形式
        """
        if not sub_type:
            return "unknown"
            
        sub_type = sub_type.lower().strip()
        
        # 标准化映射
        mappings = {
            # 目标相关
            "goal": ["goal_selection", "goal_single_select", "goal_multi_select", "goal setting", "goals"],
            # 个人信息
            "personal_info": ["personal_information", "user_info", "profile_setup", "age", "gender", "height", "weight"],
            # 权限相关
            "notification": ["notification_permission", "push_notification", "notifications"],
            "tracking": ["tracking_permission", "att_permission", "privacy"],
            # 付费相关
            "subscription": ["subscription_offer", "premium", "pro", "plus", "paywall_main"],
            "trial": ["free_trial", "trial_offer", "trial"],
            # 功能引导
            "feature_intro": ["feature_introduction", "feature_highlight", "feature introduction"],
            # 进度/结果
            "progress": ["progress_indicator", "loading", "analyzing"],
            "result": ["personalized_result", "recommendation", "plan_ready"],
        }
        
        for standard, variants in mappings.items():
            if sub_type in variants or any(v in sub_type for v in variants):
                return standard
                
        return sub_type
    
    def align_flows(self) -> Dict:
        """
        执行流程对齐
        
        Returns:
            对齐后的流程数据结构：
            {
                "screen_type": {
                    "step_1": {
                        "competitor_name": {screen_data},
                        ...
                    },
                    ...
                }
            }
        """
        if not self.competitors:
            self.load_all_competitors()
            
        print("\n[INFO] Aligning flows across competitors...")
        
        # 第一步：按 screen_type 分组所有截图
        type_groups: Dict[str, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        
        for competitor, data in self.competitors.items():
            results = data.get("results", {})
            for filename, screen_data in results.items():
                screen_type = screen_data.get("screen_type", "Other")
                sub_type = screen_data.get("sub_type", "")
                
                # 提取步骤号用于排序
                phase, step = self._extract_step_number(filename)
                
                type_groups[screen_type][competitor].append({
                    "filename": filename,
                    "phase": phase,
                    "step": step,
                    "sub_type": sub_type,
                    "normalized_sub_type": self._normalize_sub_type(sub_type),
                    "data": screen_data
                })
        
        # 第二步：在每个 screen_type 内对齐
        self.aligned_flows = {}
        
        for screen_type in self.SCREEN_TYPE_ORDER:
            if screen_type not in type_groups:
                continue
                
            competitor_screens = type_groups[screen_type]
            aligned_steps = self._align_within_type(screen_type, competitor_screens)
            
            if aligned_steps:
                self.aligned_flows[screen_type] = aligned_steps
                step_count = len(aligned_steps)
                competitor_count = len(competitor_screens)
                print(f"  [OK] {screen_type}: {step_count} aligned steps from {competitor_count} competitors")
        
        # 添加未在标准顺序中的类型
        for screen_type, competitor_screens in type_groups.items():
            if screen_type not in self.aligned_flows:
                aligned_steps = self._align_within_type(screen_type, competitor_screens)
                if aligned_steps:
                    self.aligned_flows[screen_type] = aligned_steps
                    print(f"  [OK] {screen_type}: {len(aligned_steps)} aligned steps")
        
        print(f"\n[INFO] Total {len(self.aligned_flows)} screen types aligned")
        return self.aligned_flows
    
    def _align_within_type(self, screen_type: str, competitor_screens: Dict[str, List]) -> Dict:
        """
        在单个 screen_type 内对齐各竞品的截图
        
        策略：
        1. 首先按 normalized_sub_type 分组
        2. 在同一 sub_type 内按步骤号排序
        3. 生成统一的步骤编号
        """
        # 收集所有 sub_type
        all_sub_types = set()
        for competitor, screens in competitor_screens.items():
            for screen in screens:
                all_sub_types.add(screen["normalized_sub_type"])
        
        # 为每个 sub_type 收集各竞品的截图
        sub_type_alignment: Dict[str, Dict] = defaultdict(dict)
        
        for competitor, screens in competitor_screens.items():
            # 按步骤号排序
            sorted_screens = sorted(screens, key=lambda x: (x["phase"], x["step"]))
            
            # 按 sub_type 分组
            sub_type_groups = defaultdict(list)
            for screen in sorted_screens:
                sub_type_groups[screen["normalized_sub_type"]].append(screen)
            
            # 对于每个 sub_type，将竞品的截图加入对齐结构
            for sub_type, group_screens in sub_type_groups.items():
                if sub_type not in sub_type_alignment:
                    sub_type_alignment[sub_type] = {}
                    
                # 如果一个竞品在同一 sub_type 有多个截图，保留所有
                sub_type_alignment[sub_type][competitor] = group_screens
        
        # 生成最终的步骤对齐结构
        aligned_steps = {}
        step_index = 1
        
        # 按 sub_type 的平均步骤号排序
        def get_avg_step(sub_type_data):
            all_steps = []
            for competitor, screens in sub_type_data.items():
                for s in screens:
                    all_steps.append(s["step"])
            return sum(all_steps) / len(all_steps) if all_steps else 999
        
        sorted_sub_types = sorted(
            sub_type_alignment.items(),
            key=lambda x: get_avg_step(x[1])
        )
        
        for sub_type, competitors_data in sorted_sub_types:
            step_key = f"step_{step_index}"
            aligned_steps[step_key] = {
                "sub_type": sub_type,
                "competitors": {}
            }
            
            for competitor, screens in competitors_data.items():
                # 每个竞品可能有多个截图属于同一步骤
                aligned_steps[step_key]["competitors"][competitor] = [
                    {
                        "filename": s["filename"],
                        "original_sub_type": s["sub_type"],
                        "naming": s["data"].get("naming", {}),
                        "core_function": s["data"].get("core_function", {}),
                        "design_highlights": s["data"].get("design_highlights", []),
                        "ui_elements": s["data"].get("ui_elements", []),
                        "tags": s["data"].get("tags", []),
                        "product_insight": s["data"].get("product_insight", {})
                    }
                    for s in screens
                ]
            
            step_index += 1
        
        return aligned_steps
    
    def get_flow_summary(self) -> Dict:
        """
        获取流程对齐的摘要信息
        
        Returns:
            摘要数据，包含每个 screen_type 的统计信息
        """
        if not self.aligned_flows:
            self.align_flows()
            
        summary = {
            "competitors": list(self.competitors.keys()),
            "total_screen_types": len(self.aligned_flows),
            "flows": {}
        }
        
        for screen_type, steps in self.aligned_flows.items():
            step_count = len(steps)
            
            # 统计每个竞品在此流程中的截图数
            competitor_counts = defaultdict(int)
            for step_key, step_data in steps.items():
                for competitor, screens in step_data.get("competitors", {}).items():
                    competitor_counts[competitor] += len(screens)
            
            summary["flows"][screen_type] = {
                "total_steps": step_count,
                "competitor_screen_counts": dict(competitor_counts)
            }
        
        return summary
    
    def export_alignment(self, output_path: str = None) -> str:
        """
        导出对齐结果到 JSON 文件
        
        Args:
            output_path: 输出路径，默认为 projects/flow_alignment.json
            
        Returns:
            输出文件路径
        """
        if not self.aligned_flows:
            self.align_flows()
            
        if output_path is None:
            output_path = os.path.join(self.projects_dir, "flow_alignment.json")
        
        output_data = {
            "summary": self.get_flow_summary(),
            "aligned_flows": self.aligned_flows
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[OK] Alignment exported to: {output_path}")
        return output_path


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Flow Aligner - Align competitor flows")
    parser.add_argument("--projects", "-p", type=str, help="Comma-separated competitor names")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary only")
    
    args = parser.parse_args()
    
    aligner = FlowAligner()
    
    # 加载竞品
    competitor_names = None
    if args.projects:
        competitor_names = [n.strip() for n in args.projects.split(",")]
    
    aligner.load_all_competitors(competitor_names)
    
    # 对齐流程
    aligner.align_flows()
    
    if args.summary:
        # 只打印摘要
        summary = aligner.get_flow_summary()
        print("\n" + "="*60)
        print("FLOW ALIGNMENT SUMMARY")
        print("="*60)
        print(f"Competitors: {', '.join(summary['competitors'])}")
        print(f"Screen Types: {summary['total_screen_types']}")
        print("\nFlow Details:")
        for flow_type, details in summary["flows"].items():
            print(f"\n  {flow_type}:")
            print(f"    Steps: {details['total_steps']}")
            for comp, count in details['competitor_screen_counts'].items():
                print(f"    {comp}: {count} screens")
    else:
        # 导出完整结果
        aligner.export_alignment(args.output)


if __name__ == "__main__":
    main()









































