"""
对比报告生成器 - Comparison Report Generator

功能：
- 整合对齐、矩阵、理由
- 生成 JSON 格式的完整对比报告
- 生成 Markdown 格式的可读报告
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional


class ComparisonReportGenerator:
    """对比报告生成器"""
    
    def __init__(self, projects_dir: str = None):
        """
        初始化报告生成器
        
        Args:
            projects_dir: 项目目录路径
        """
        if projects_dir is None:
            projects_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "projects"
            )
        self.projects_dir = projects_dir
        
        # 数据文件路径
        self.alignment_file = os.path.join(projects_dir, "flow_alignment.json")
        self.matrix_file = os.path.join(projects_dir, "decision_matrix.json")
        self.reasons_file = os.path.join(projects_dir, "decision_reasons.json")
        
        # 加载的数据
        self.alignment = None
        self.matrix = None
        self.reasons = None
        
    def load_data(self):
        """加载所有必要的数据"""
        print("[INFO] Loading data files...")
        
        # 加载对齐数据
        if os.path.exists(self.alignment_file):
            with open(self.alignment_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.alignment = data.get("aligned_flows", data)
            print(f"  [OK] Alignment: {len(self.alignment)} screen types")
        else:
            print(f"  [WARN] Alignment file not found: {self.alignment_file}")
            
        # 加载决策矩阵
        if os.path.exists(self.matrix_file):
            with open(self.matrix_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.matrix = data.get("matrix", data)
            print(f"  [OK] Matrix: {len(self.matrix)} entries")
        else:
            print(f"  [WARN] Matrix file not found: {self.matrix_file}")
            
        # 加载理由数据
        if os.path.exists(self.reasons_file):
            with open(self.reasons_file, 'r', encoding='utf-8') as f:
                self.reasons = json.load(f)
            print(f"  [OK] Reasons: {len(self.reasons)} entries")
        else:
            print(f"  [WARN] Reasons file not found: {self.reasons_file}")
    
    def generate_report(self, flow_filter: str = None) -> Dict:
        """
        生成完整的对比报告
        
        Args:
            flow_filter: 只生成指定流程的报告（如 "Onboarding"）
            
        Returns:
            完整的报告数据
        """
        if not self.alignment:
            self.load_data()
        
        print("\n[INFO] Generating comparison report...")
        
        # 收集竞品列表
        competitors = set()
        if self.alignment:
            for screen_type, steps in self.alignment.items():
                for step_key, step_data in steps.items():
                    competitors.update(step_data.get("competitors", {}).keys())
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "competitors": sorted(list(competitors)),
            "total_screen_types": len(self.alignment) if self.alignment else 0,
            "flows": {}
        }
        
        # 按 screen_type 构建报告
        screen_types = list(self.alignment.keys()) if self.alignment else []
        
        # 应用过滤器
        if flow_filter:
            screen_types = [st for st in screen_types if flow_filter.lower() in st.lower()]
        
        for screen_type in screen_types:
            steps_data = self.alignment.get(screen_type, {})
            
            # 统计每个竞品在此流程中的步骤数
            total_steps_per_competitor = {}
            for step_key, step_data in steps_data.items():
                for competitor, screens in step_data.get("competitors", {}).items():
                    if competitor not in total_steps_per_competitor:
                        total_steps_per_competitor[competitor] = 0
                    total_steps_per_competitor[competitor] += len(screens) if isinstance(screens, list) else 1
            
            flow_report = {
                "total_steps": len(steps_data),
                "competitor_step_counts": total_steps_per_competitor,
                "steps": []
            }
            
            # 处理每个步骤
            for step_key, step_data in steps_data.items():
                step_report = self._build_step_report(screen_type, step_key, step_data)
                flow_report["steps"].append(step_report)
            
            # 按步骤号排序
            flow_report["steps"].sort(key=lambda x: x.get("step_number", 0))
            
            report["flows"][screen_type] = flow_report
        
        print(f"[OK] Report generated with {len(report['flows'])} flows")
        return report
    
    def _build_step_report(self, screen_type: str, step_key: str, step_data: Dict) -> Dict:
        """构建单个步骤的报告"""
        # 提取步骤号
        step_number = int(step_key.replace("step_", "")) if "step_" in step_key else 0
        
        step_report = {
            "step_number": step_number,
            "step_key": step_key,
            "sub_type": step_data.get("sub_type", ""),
            "purpose": self._infer_purpose(step_data),
            "competitors": {}
        }
        
        # 处理每个竞品的数据
        for competitor, screens in step_data.get("competitors", {}).items():
            if not screens:
                continue
            
            # 取第一个截图作为代表
            screen = screens[0] if isinstance(screens, list) else screens
            
            step_report["competitors"][competitor] = {
                "filename": screen.get("filename", ""),
                "sub_type": screen.get("original_sub_type", ""),
                "naming": screen.get("naming", {}),
                "core_function": screen.get("core_function", {}),
                "design_highlights": screen.get("design_highlights", []),
                "screen_count": len(screens) if isinstance(screens, list) else 1
            }
        
        # 添加统计数据
        matrix_key = f"{screen_type}_{step_key}"
        if self.matrix and matrix_key in self.matrix:
            matrix_entry = self.matrix[matrix_key]
            step_report["statistics"] = matrix_entry.get("statistics", {})
            step_report["design_choices"] = matrix_entry.get("design_choices", {})
        
        # 添加推荐数据
        if self.reasons and matrix_key in self.reasons:
            reason_entry = self.reasons[matrix_key]
            step_report["recommendation"] = {
                "claude": self._extract_recommendation(reason_entry.get("claude", {})),
                "openai": self._extract_recommendation(reason_entry.get("openai", {})),
                "model_comparison": reason_entry.get("model_comparison", {}),
                "final_suggestion": reason_entry.get("final_suggestion", "")
            }
        
        return step_report
    
    def _infer_purpose(self, step_data: Dict) -> str:
        """推断步骤的目的"""
        sub_type = step_data.get("sub_type", "")
        
        purpose_mappings = {
            "goal": "收集用户目标和期望",
            "personal_info": "收集用户个人信息",
            "notification": "请求通知权限",
            "tracking": "请求数据追踪权限",
            "subscription": "展示订阅选项",
            "trial": "提供免费试用",
            "feature_intro": "功能特性介绍",
            "progress": "显示处理进度",
            "result": "展示个性化结果",
            "welcome": "欢迎用户",
            "login": "用户登录",
            "signup": "用户注册",
        }
        
        for key, purpose in purpose_mappings.items():
            if key in sub_type.lower():
                return purpose
        
        return sub_type or "未知"
    
    def _extract_recommendation(self, model_result: Dict) -> Dict:
        """提取模型推荐的关键信息"""
        if "error" in model_result:
            return {"error": model_result["error"]}
        
        return {
            "choice": model_result.get("recommended_choice", ""),
            "reasons": model_result.get("reasons", []),
            "risks": model_result.get("risks", []),
            "confidence": model_result.get("confidence", 0)
        }
    
    def export_json(self, report: Dict = None, output_path: str = None) -> str:
        """导出 JSON 格式报告"""
        if report is None:
            report = self.generate_report()
        
        if output_path is None:
            output_path = os.path.join(self.projects_dir, "comparison_report.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"[OK] JSON report exported to: {output_path}")
        return output_path
    
    def export_markdown(self, report: Dict = None, output_path: str = None) -> str:
        """导出 Markdown 格式报告"""
        if report is None:
            report = self.generate_report()
        
        if output_path is None:
            output_path = os.path.join(self.projects_dir, "comparison_report.md")
        
        md_content = self._generate_markdown(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"[OK] Markdown report exported to: {output_path}")
        return output_path
    
    def _generate_markdown(self, report: Dict) -> str:
        """生成 Markdown 内容"""
        lines = []
        
        # 标题
        lines.append("# 竞品流程对比分析报告")
        lines.append("")
        lines.append(f"**生成时间**: {report.get('generated_at', '')}")
        lines.append(f"**参与竞品**: {', '.join(report.get('competitors', []))}")
        lines.append(f"**分析流程数**: {report.get('total_screen_types', 0)}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 目录
        lines.append("## 目录")
        lines.append("")
        for flow_name in report.get("flows", {}).keys():
            anchor = flow_name.lower().replace(" ", "-")
            lines.append(f"- [{flow_name}](#{anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 各流程详情
        for flow_name, flow_data in report.get("flows", {}).items():
            lines.extend(self._generate_flow_markdown(flow_name, flow_data))
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_flow_markdown(self, flow_name: str, flow_data: Dict) -> List[str]:
        """生成单个流程的 Markdown"""
        lines = []
        
        lines.append(f"## {flow_name}")
        lines.append("")
        
        # 概览
        lines.append("### 概览")
        lines.append("")
        lines.append(f"- **总步骤数**: {flow_data.get('total_steps', 0)}")
        lines.append("")
        
        # 各竞品步骤数
        step_counts = flow_data.get("competitor_step_counts", {})
        if step_counts:
            lines.append("**各竞品截图数**:")
            lines.append("")
            lines.append("| 竞品 | 截图数 |")
            lines.append("|------|--------|")
            for competitor, count in sorted(step_counts.items()):
                lines.append(f"| {competitor} | {count} |")
            lines.append("")
        
        # 各步骤详情
        lines.append("### 步骤详情")
        lines.append("")
        
        for step in flow_data.get("steps", []):
            lines.extend(self._generate_step_markdown(step))
            lines.append("")
        
        lines.append("---")
        return lines
    
    def _generate_step_markdown(self, step: Dict) -> List[str]:
        """生成单个步骤的 Markdown"""
        lines = []
        
        step_num = step.get("step_number", 0)
        sub_type = step.get("sub_type", "")
        purpose = step.get("purpose", "")
        
        lines.append(f"#### 步骤 {step_num}: {sub_type}")
        lines.append("")
        lines.append(f"**目的**: {purpose}")
        lines.append("")
        
        # 竞品设计对比表格
        competitors = step.get("competitors", {})
        if competitors:
            lines.append("**竞品设计对比**:")
            lines.append("")
            lines.append("| 竞品 | 截图 | 设计亮点 |")
            lines.append("|------|------|----------|")
            
            for competitor, data in competitors.items():
                filename = data.get("filename", "")
                highlights = data.get("design_highlights", [])
                
                # 提取第一个设计亮点
                highlight_text = ""
                if highlights and len(highlights) > 0:
                    h = highlights[0]
                    if isinstance(h, dict):
                        highlight_text = h.get("cn", h.get("en", ""))
                    else:
                        highlight_text = str(h)
                
                # 截断过长的内容
                if len(highlight_text) > 50:
                    highlight_text = highlight_text[:50] + "..."
                
                lines.append(f"| {competitor} | {filename} | {highlight_text} |")
            
            lines.append("")
        
        # 统计数据
        statistics = step.get("statistics", {})
        if statistics:
            lines.append("**设计决策统计**:")
            lines.append("")
            
            for dimension, stats in statistics.items():
                majority = stats.get("majority", "")
                percentage = stats.get("percentage", 0)
                is_consensus = stats.get("is_consensus", False)
                
                consensus_badge = " [共识]" if is_consensus else ""
                lines.append(f"- **{dimension}**: {majority} ({percentage}%){consensus_badge}")
            
            lines.append("")
        
        # 推荐建议
        recommendation = step.get("recommendation", {})
        if recommendation:
            lines.append("**AI 推荐分析**:")
            lines.append("")
            
            # Claude 推荐
            claude = recommendation.get("claude", {})
            if claude and "error" not in claude:
                lines.append(f"*Claude Opus 4.5*:")
                lines.append(f"- 推荐: {claude.get('choice', 'N/A')}")
                reasons = claude.get("reasons", [])
                if reasons:
                    lines.append(f"- 理由: {reasons[0] if reasons else 'N/A'}")
                lines.append(f"- 置信度: {claude.get('confidence', 0)}")
                lines.append("")
            
            # OpenAI 推荐
            openai = recommendation.get("openai", {})
            if openai and "error" not in openai:
                lines.append(f"*GPT-4o*:")
                lines.append(f"- 推荐: {openai.get('choice', 'N/A')}")
                reasons = openai.get("reasons", [])
                if reasons:
                    lines.append(f"- 理由: {reasons[0] if reasons else 'N/A'}")
                lines.append(f"- 置信度: {openai.get('confidence', 0)}")
                lines.append("")
            
            # 模型对比
            comparison = recommendation.get("model_comparison", {})
            if comparison:
                agreement = comparison.get("agreement", "unknown")
                confidence = comparison.get("combined_confidence", 0)
                
                agreement_labels = {
                    "full": "完全一致",
                    "partial": "部分一致",
                    "divergent": "存在分歧",
                    "incomplete": "数据不完整",
                    "unknown": "未知"
                }
                
                lines.append(f"*模型对比*: {agreement_labels.get(agreement, agreement)} (综合置信度: {confidence})")
                lines.append("")
            
            # 最终建议
            final = recommendation.get("final_suggestion", "")
            if final:
                lines.append(f"> **最终建议**: {final}")
                lines.append("")
        
        return lines


def run_full_pipeline(
    projects_dir: str = None,
    competitor_names: List[str] = None,
    flow_filter: str = None,
    skip_reasons: bool = False
):
    """
    运行完整的分析流水线
    
    Args:
        projects_dir: 项目目录
        competitor_names: 指定竞品列表
        flow_filter: 只分析指定流程
        skip_reasons: 跳过 AI 理由生成（节省 API 调用）
    """
    print("="*60)
    print("COMPETITIVE ANALYSIS PIPELINE")
    print("="*60)
    
    # 设置项目目录
    if projects_dir is None:
        projects_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "projects"
        )
    
    # Step 1: 流程对齐
    print("\n[STEP 1/4] Flow Alignment")
    print("-"*40)
    from flow_aligner import FlowAligner
    
    aligner = FlowAligner(projects_dir)
    aligner.load_all_competitors(competitor_names)
    aligner.align_flows()
    aligner.export_alignment()
    
    # Step 2: 决策矩阵
    print("\n[STEP 2/4] Decision Matrix")
    print("-"*40)
    from decision_matrix import DecisionMatrixGenerator
    
    alignment_file = os.path.join(projects_dir, "flow_alignment.json")
    matrix_gen = DecisionMatrixGenerator(alignment_file=alignment_file)
    matrix_gen.generate_matrix()
    matrix_gen.export_matrix()
    
    # Step 3: AI 理由生成
    if not skip_reasons:
        print("\n[STEP 3/4] AI Reason Generation")
        print("-"*40)
        from reason_generator import DualModelReasonGenerator
        
        matrix_file = os.path.join(projects_dir, "decision_matrix.json")
        with open(matrix_file, 'r', encoding='utf-8') as f:
            matrix_data = json.load(f)
        
        matrix = matrix_data.get("matrix", matrix_data)
        
        # 可选：只处理部分条目
        if flow_filter:
            matrix = {k: v for k, v in matrix.items() if flow_filter.lower() in k.lower()}
        
        reason_gen = DualModelReasonGenerator()
        results = reason_gen.generate_all_reasons(matrix)
        reason_gen.export_reasons(results)
    else:
        print("\n[STEP 3/4] AI Reason Generation - SKIPPED")
    
    # Step 4: 生成报告
    print("\n[STEP 4/4] Report Generation")
    print("-"*40)
    
    report_gen = ComparisonReportGenerator(projects_dir)
    report = report_gen.generate_report(flow_filter)
    report_gen.export_json(report)
    report_gen.export_markdown(report)
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETE")
    print("="*60)
    print(f"\nOutput files:")
    print(f"  - {os.path.join(projects_dir, 'flow_alignment.json')}")
    print(f"  - {os.path.join(projects_dir, 'decision_matrix.json')}")
    if not skip_reasons:
        print(f"  - {os.path.join(projects_dir, 'decision_reasons.json')}")
    print(f"  - {os.path.join(projects_dir, 'comparison_report.json')}")
    print(f"  - {os.path.join(projects_dir, 'comparison_report.md')}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Comparison Report Generator")
    parser.add_argument("--all", "-a", action="store_true", help="Run full pipeline")
    parser.add_argument("--flow", "-f", type=str, help="Filter by flow type")
    parser.add_argument("--projects", "-p", type=str, help="Comma-separated competitor names")
    parser.add_argument("--output", "-o", type=str, help="Output directory")
    parser.add_argument("--json-only", action="store_true", help="Export JSON only")
    parser.add_argument("--md-only", action="store_true", help="Export Markdown only")
    parser.add_argument("--skip-reasons", action="store_true", help="Skip AI reason generation")
    
    args = parser.parse_args()
    
    if args.all:
        # 运行完整流水线
        competitor_names = None
        if args.projects:
            competitor_names = [n.strip() for n in args.projects.split(",")]
        
        run_full_pipeline(
            projects_dir=args.output,
            competitor_names=competitor_names,
            flow_filter=args.flow,
            skip_reasons=args.skip_reasons
        )
    else:
        # 只生成报告（需要已有数据文件）
        report_gen = ComparisonReportGenerator(args.output)
        report = report_gen.generate_report(args.flow)
        
        if args.json_only:
            report_gen.export_json(report)
        elif args.md_only:
            report_gen.export_markdown(report)
        else:
            report_gen.export_json(report)
            report_gen.export_markdown(report)


if __name__ == "__main__":
    main()









































