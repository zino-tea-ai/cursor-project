"""
决策矩阵生成器 - Decision Matrix Generator

功能：
- 基于对齐结果，统计每个步骤的设计选择分布
- 提取关键决策维度：交互类型、选项数量、视觉风格、文案策略
- 计算主流选择（>50%竞品采用）
"""

import os
import json
import re
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter


class DecisionMatrixGenerator:
    """决策矩阵生成器"""
    
    # 交互类型分类规则
    INTERACTION_PATTERNS = {
        "single_select": ["single", "radio", "one choice", "select one", "单选"],
        "multi_select": ["multi", "checkbox", "multiple", "多选", "select all"],
        "slider": ["slider", "range", "滑块", "拖动"],
        "input": ["input", "text field", "输入", "填写", "type"],
        "date_picker": ["date", "calendar", "日期", "日历"],
        "toggle": ["toggle", "switch", "开关"],
        "cards": ["card", "卡片", "tile"],
        "list": ["list", "列表", "options"],
        "wheel": ["wheel", "picker", "滚轮"],
        "button_only": ["button", "cta", "按钮", "continue", "next"],
    }
    
    # UI元素到交互类型的映射
    UI_ELEMENT_MAPPINGS = {
        "radio_buttons": "single_select",
        "checkboxes": "multi_select",
        "selection_cards": "cards",
        "option_cards": "cards",
        "input_field": "input",
        "text_input": "input",
        "slider": "slider",
        "toggle_switch": "toggle",
        "date_picker": "date_picker",
        "scroll_picker": "wheel",
        "cta_button": "button_only",
        "primary_button": "button_only",
    }
    
    def __init__(self, alignment_data: Dict = None, alignment_file: str = None):
        """
        初始化决策矩阵生成器
        
        Args:
            alignment_data: 对齐后的流程数据
            alignment_file: 对齐数据文件路径
        """
        if alignment_data:
            self.alignment = alignment_data
        elif alignment_file and os.path.exists(alignment_file):
            with open(alignment_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.alignment = data.get("aligned_flows", data)
        else:
            self.alignment = {}
            
        self.decision_matrix: Dict = {}
        
    def _detect_interaction_type(self, screen_data: Dict) -> str:
        """
        检测截图的主要交互类型
        
        基于 ui_elements、sub_type、design_highlights 推断
        """
        # 1. 从 ui_elements 推断
        ui_elements = screen_data.get("ui_elements", [])
        for element in ui_elements:
            element_lower = element.lower()
            if element_lower in self.UI_ELEMENT_MAPPINGS:
                return self.UI_ELEMENT_MAPPINGS[element_lower]
            # 模糊匹配
            for ui_key, interaction in self.UI_ELEMENT_MAPPINGS.items():
                if ui_key in element_lower or element_lower in ui_key:
                    return interaction
        
        # 2. 从 sub_type 推断
        sub_type = screen_data.get("original_sub_type", "") or screen_data.get("sub_type", "")
        sub_type_lower = sub_type.lower() if sub_type else ""
        
        for interaction, patterns in self.INTERACTION_PATTERNS.items():
            for pattern in patterns:
                if pattern in sub_type_lower:
                    return interaction
        
        # 3. 从 design_highlights 推断
        highlights = screen_data.get("design_highlights", [])
        for highlight in highlights:
            text = ""
            if isinstance(highlight, dict):
                text = highlight.get("cn", "") + " " + highlight.get("en", "")
            elif isinstance(highlight, str):
                text = highlight
            text_lower = text.lower()
            
            for interaction, patterns in self.INTERACTION_PATTERNS.items():
                for pattern in patterns:
                    if pattern in text_lower:
                        return interaction
        
        # 4. 从 tags 推断
        tags = screen_data.get("tags", [])
        for tag in tags:
            tag_text = ""
            if isinstance(tag, dict):
                tag_text = tag.get("cn", "") + " " + tag.get("en", "")
            elif isinstance(tag, str):
                tag_text = tag
            tag_lower = tag_text.lower()
            
            for interaction, patterns in self.INTERACTION_PATTERNS.items():
                for pattern in patterns:
                    if pattern in tag_lower:
                        return interaction
        
        return "unknown"
    
    def _extract_option_count(self, screen_data: Dict) -> Optional[int]:
        """
        提取选项数量（如果适用）
        """
        # 从 design_highlights 中查找数字
        highlights = screen_data.get("design_highlights", [])
        for highlight in highlights:
            text = ""
            if isinstance(highlight, dict):
                text = highlight.get("cn", "") + " " + highlight.get("en", "")
            elif isinstance(highlight, str):
                text = highlight
            
            # 匹配 "X个选项" 或 "X options"
            match = re.search(r'(\d+)\s*(?:个|种)?(?:选项|options?|choices?|cards?)', text, re.I)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_visual_style(self, screen_data: Dict) -> List[str]:
        """
        提取视觉风格特征
        """
        styles = []
        
        highlights = screen_data.get("design_highlights", [])
        for highlight in highlights:
            if isinstance(highlight, dict) and highlight.get("category") == "visual":
                # 提取关键词
                text = (highlight.get("cn", "") + " " + highlight.get("en", "")).lower()
                
                style_keywords = {
                    "gradient": ["渐变", "gradient"],
                    "dark_mode": ["深色", "dark", "暗色"],
                    "light_mode": ["浅色", "light", "亮色", "白色"],
                    "illustration": ["插画", "illustration", "图示"],
                    "icon": ["图标", "icon"],
                    "minimal": ["极简", "minimal", "简洁"],
                    "card_style": ["卡片", "card"],
                    "full_width": ["全宽", "full width", "full-width"],
                }
                
                for style, keywords in style_keywords.items():
                    if any(kw in text for kw in keywords):
                        styles.append(style)
        
        return list(set(styles))
    
    def _extract_cta_position(self, screen_data: Dict) -> str:
        """
        提取 CTA 按钮位置
        """
        ui_elements = screen_data.get("ui_elements", [])
        highlights = screen_data.get("design_highlights", [])
        
        all_text = " ".join(ui_elements)
        for h in highlights:
            if isinstance(h, dict):
                all_text += " " + h.get("cn", "") + " " + h.get("en", "")
        
        all_text = all_text.lower()
        
        if "bottom" in all_text or "底部" in all_text:
            return "bottom"
        elif "top" in all_text or "顶部" in all_text:
            return "top"
        elif "center" in all_text or "居中" in all_text:
            return "center"
        
        return "bottom"  # 默认底部
    
    def generate_matrix(self) -> Dict:
        """
        生成决策矩阵
        
        Returns:
            {
                "screen_type_step": {
                    "step_info": {...},
                    "design_choices": {
                        "dimension": {
                            "choice_value": ["competitor1", "competitor2"],
                            ...
                        }
                    },
                    "statistics": {
                        "dimension": {
                            "majority": "choice_value",
                            "percentage": 80,
                            "distribution": {...}
                        }
                    }
                }
            }
        """
        print("[INFO] Generating decision matrix...")
        
        self.decision_matrix = {}
        
        for screen_type, steps in self.alignment.items():
            for step_key, step_data in steps.items():
                matrix_key = f"{screen_type}_{step_key}"
                
                competitors_data = step_data.get("competitors", {})
                if not competitors_data:
                    continue
                
                # 收集各维度的选择
                choices = {
                    "interaction_type": defaultdict(list),
                    "option_count": defaultdict(list),
                    "visual_style": defaultdict(list),
                    "cta_position": defaultdict(list),
                }
                
                # 分析每个竞品的设计选择
                for competitor, screens in competitors_data.items():
                    # 取第一个截图作为代表（如果有多个）
                    if not screens:
                        continue
                    screen = screens[0] if isinstance(screens, list) else screens
                    
                    # 交互类型
                    interaction = self._detect_interaction_type(screen)
                    choices["interaction_type"][interaction].append(competitor)
                    
                    # 选项数量
                    option_count = self._extract_option_count(screen)
                    if option_count:
                        choices["option_count"][str(option_count)].append(competitor)
                    
                    # 视觉风格
                    styles = self._extract_visual_style(screen)
                    for style in styles:
                        choices["visual_style"][style].append(competitor)
                    
                    # CTA位置
                    cta_pos = self._extract_cta_position(screen)
                    choices["cta_position"][cta_pos].append(competitor)
                
                # 计算统计数据
                total_competitors = len(competitors_data)
                statistics = {}
                
                for dimension, dimension_choices in choices.items():
                    if not dimension_choices:
                        continue
                    
                    # 计算每个选择的分布
                    distribution = {
                        choice: len(comps)
                        for choice, comps in dimension_choices.items()
                    }
                    
                    # 找出主流选择
                    if distribution:
                        majority_choice = max(distribution, key=distribution.get)
                        majority_count = distribution[majority_choice]
                        percentage = round(majority_count / total_competitors * 100)
                        
                        statistics[dimension] = {
                            "majority": majority_choice,
                            "majority_count": majority_count,
                            "percentage": percentage,
                            "total_competitors": total_competitors,
                            "distribution": distribution,
                            "is_consensus": percentage >= 60  # 60%以上为共识
                        }
                
                # 构建矩阵条目
                self.decision_matrix[matrix_key] = {
                    "screen_type": screen_type,
                    "step": step_key,
                    "sub_type": step_data.get("sub_type", ""),
                    "competitors_count": total_competitors,
                    "design_choices": {
                        dim: dict(vals) for dim, vals in choices.items() if vals
                    },
                    "statistics": statistics
                }
                
        print(f"[OK] Generated decision matrix with {len(self.decision_matrix)} entries")
        return self.decision_matrix
    
    def get_consensus_decisions(self, min_percentage: int = 60) -> Dict:
        """
        获取达成共识的设计决策
        
        Args:
            min_percentage: 最低共识百分比，默认60%
            
        Returns:
            筛选后的决策字典
        """
        if not self.decision_matrix:
            self.generate_matrix()
            
        consensus = {}
        
        for key, entry in self.decision_matrix.items():
            consensus_stats = {}
            for dimension, stats in entry.get("statistics", {}).items():
                if stats.get("percentage", 0) >= min_percentage:
                    consensus_stats[dimension] = stats
                    
            if consensus_stats:
                consensus[key] = {
                    "screen_type": entry["screen_type"],
                    "step": entry["step"],
                    "sub_type": entry["sub_type"],
                    "consensus_decisions": consensus_stats
                }
        
        return consensus
    
    def get_divergent_decisions(self) -> Dict:
        """
        获取分歧较大的设计决策（无明显主流选择）
        
        Returns:
            分歧决策字典
        """
        if not self.decision_matrix:
            self.generate_matrix()
            
        divergent = {}
        
        for key, entry in self.decision_matrix.items():
            divergent_stats = {}
            for dimension, stats in entry.get("statistics", {}).items():
                # 主流选择低于50%，且有多种选择
                if (stats.get("percentage", 0) < 50 and 
                    len(stats.get("distribution", {})) > 1):
                    divergent_stats[dimension] = stats
                    
            if divergent_stats:
                divergent[key] = {
                    "screen_type": entry["screen_type"],
                    "step": entry["step"],
                    "sub_type": entry["sub_type"],
                    "divergent_decisions": divergent_stats
                }
        
        return divergent
    
    def export_matrix(self, output_path: str = None) -> str:
        """
        导出决策矩阵到 JSON 文件
        """
        if not self.decision_matrix:
            self.generate_matrix()
            
        if output_path is None:
            # 默认导出到 projects 目录
            projects_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "projects"
            )
            output_path = os.path.join(projects_dir, "decision_matrix.json")
        
        output_data = {
            "total_entries": len(self.decision_matrix),
            "consensus_count": len(self.get_consensus_decisions()),
            "divergent_count": len(self.get_divergent_decisions()),
            "matrix": self.decision_matrix
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] Decision matrix exported to: {output_path}")
        return output_path
    
    def print_summary(self):
        """打印决策矩阵摘要"""
        if not self.decision_matrix:
            self.generate_matrix()
            
        print("\n" + "="*60)
        print("DECISION MATRIX SUMMARY")
        print("="*60)
        
        # 按 screen_type 分组统计
        type_stats = defaultdict(list)
        for key, entry in self.decision_matrix.items():
            type_stats[entry["screen_type"]].append(entry)
        
        for screen_type, entries in type_stats.items():
            print(f"\n{screen_type}:")
            for entry in entries:
                step = entry["step"]
                sub_type = entry["sub_type"]
                print(f"  {step} ({sub_type}):")
                
                for dim, stats in entry.get("statistics", {}).items():
                    majority = stats["majority"]
                    pct = stats["percentage"]
                    consensus = "[CONSENSUS]" if stats["is_consensus"] else ""
                    print(f"    {dim}: {majority} ({pct}%) {consensus}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Decision Matrix Generator")
    parser.add_argument("--alignment", "-a", type=str, help="Path to alignment JSON file")
    parser.add_argument("--output", "-o", type=str, help="Output file path")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary")
    parser.add_argument("--consensus", "-c", action="store_true", help="Show consensus only")
    parser.add_argument("--divergent", "-d", action="store_true", help="Show divergent only")
    
    args = parser.parse_args()
    
    # 默认对齐文件路径
    if not args.alignment:
        projects_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "projects"
        )
        args.alignment = os.path.join(projects_dir, "flow_alignment.json")
    
    generator = DecisionMatrixGenerator(alignment_file=args.alignment)
    generator.generate_matrix()
    
    if args.summary:
        generator.print_summary()
    elif args.consensus:
        consensus = generator.get_consensus_decisions()
        print(json.dumps(consensus, ensure_ascii=False, indent=2))
    elif args.divergent:
        divergent = generator.get_divergent_decisions()
        print(json.dumps(divergent, ensure_ascii=False, indent=2))
    else:
        generator.export_matrix(args.output)


if __name__ == "__main__":
    main()









































