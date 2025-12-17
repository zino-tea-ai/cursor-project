# -*- coding: utf-8 -*-
"""
报告生成器 - 生成可读的分析和验证报告
支持多种格式：终端输出、Markdown、JSON、CSV
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from validation_rules import SCREEN_TYPES


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self.analysis_data = None
        self.validation_data = None
    
    def load_analysis(self, analysis_file: Optional[str] = None):
        """加载分析结果"""
        if analysis_file is None:
            analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        return False
    
    def load_validation(self, validation_file: Optional[str] = None):
        """加载验证结果"""
        if validation_file is None:
            validation_file = os.path.join(self.project_path, "validation_report.json")
        
        if os.path.exists(validation_file):
            with open(validation_file, 'r', encoding='utf-8') as f:
                self.validation_data = json.load(f)
            return True
        return False
    
    def _get_type_cn(self, screen_type: str) -> str:
        """获取类型的中文名"""
        type_info = SCREEN_TYPES.get(screen_type, {})
        return type_info.get("cn", screen_type)
    
    def generate_terminal_report(self) -> str:
        """生成终端格式的报告"""
        if not self.analysis_data:
            return "Error: No analysis data"
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {self.project_name} AI Analysis Report")
        lines.append("=" * 70)
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        
        lines.append("")
        lines.append("Statistics")
        lines.append("-" * 70)
        lines.append(f"  Total: {total}")
        lines.append(f"  Analyzed: {analyzed}")
        lines.append(f"  Failed: {failed}")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("")
        lines.append("Type Distribution")
        lines.append("-" * 70)
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            bar = "#" * int(pct / 5)
            lines.append(f"  {cn_name:10s} ({screen_type:12s}): {bar:20s} {count:3d} ({pct:5.1f}%)")
        
        if self.validation_data:
            lines.append("")
            lines.append("Validation Results")
            lines.append("-" * 70)
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append(f"  PASS: {pass_count} ({pass_count/total*100:.1f}%)")
            lines.append(f"  REVIEW: {review_count} ({review_count/total*100:.1f}%)")
            lines.append(f"  FAIL: {fail_count} ({fail_count/total*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        if not self.analysis_data:
            return "# Error: No analysis data"
        
        lines = []
        lines.append(f"# {self.project_name} AI Analysis Report")
        lines.append("")
        lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        total_time = self.analysis_data.get("total_time", 0)
        
        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Screenshots | {total} |")
        lines.append(f"| Successfully Analyzed | {analyzed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Time | {total_time:.1f}s |")
        lines.append("")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("## Type Distribution")
        lines.append("")
        lines.append("| Type | Chinese | Count | Percentage |")
        lines.append("|------|---------|-------|------------|")
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            lines.append(f"| {screen_type} | {cn_name} | {count} | {pct:.1f}% |")
        lines.append("")
        
        if self.validation_data:
            lines.append("## Validation Results")
            lines.append("")
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append("| Status | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            lines.append(f"| PASS (High Confidence) | {pass_count} | {pass_count/total*100:.1f}% |")
            lines.append(f"| REVIEW (Medium) | {review_count} | {review_count/total*100:.1f}% |")
            lines.append(f"| FAIL (Low) | {fail_count} | {fail_count/total*100:.1f}% |")
            lines.append("")
        
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| # | Filename | Type | Description | Confidence |")
        lines.append("|---|----------|------|-------------|------------|")
        
        for i, (filename, result) in enumerate(sorted(results.items()), 1):
            screen_type = result.get("screen_type", "Unknown")
            desc_cn = result.get("description_cn", "")[:30]
            confidence = result.get("confidence", 0)
            lines.append(f"| {i} | {filename[:30]} | {screen_type} | {desc_cn} | {confidence:.0%} |")
        
        return "\n".join(lines)
    
    def generate_csv(self, output_file: str):
        """生成CSV格式的详细清单"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            headers = [
                "Index", "Filename", "Type", "Type_CN", "SubType",
                "Description_CN", "Description_EN", "Confidence"
            ]
            
            if self.validation_data:
                headers.extend(["ValidationStatus", "FinalConfidence", "SuggestedType"])
            
            writer.writerow(headers)
            
            val_results = self.validation_data.get("results", {}) if self.validation_data else {}
            
            for i, (filename, result) in enumerate(sorted(results.items()), 1):
                screen_type = result.get("screen_type", "Unknown")
                row = [
                    i,
                    filename,
                    screen_type,
                    self._get_type_cn(screen_type),
                    result.get("sub_type", ""),
                    result.get("description_cn", ""),
                    result.get("description_en", ""),
                    f"{result.get('confidence', 0):.0%}"
                ]
                
                if self.validation_data and filename in val_results:
                    val = val_results[filename]
                    row.extend([
                        val.get("validation_status", ""),
                        f"{val.get('final_confidence', 0):.0%}",
                        val.get("suggested_type", "")
                    ])
                
                writer.writerow(row)
        
        print(f"CSV saved: {output_file}")
    
    def generate_descriptions_json(self, output_file: str):
        """生成与现有系统兼容的 descriptions.json"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        descriptions = {}
        
        for filename, result in results.items():
            desc_cn = result.get("description_cn", "")
            descriptions[filename] = desc_cn
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        
        print(f"Descriptions saved: {output_file}")
    
    def save_all_reports(self):
        """保存所有格式的报告"""
        md_content = self.generate_markdown_report()
        md_file = os.path.join(self.project_path, f"{self.project_name}_AI_Report.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report: {md_file}")
        
        csv_file = os.path.join(self.project_path, f"{self.project_name}_AI_ScreenList.csv")
        self.generate_csv(csv_file)
        
        desc_file = os.path.join(self.project_path, "descriptions_ai.json")
        self.generate_descriptions_json(desc_file)
        
        print(self.generate_terminal_report())


def generate_report(project_path: str, project_name: Optional[str] = None):
    """为项目生成完整报告"""
    if project_name is None:
        project_name = os.path.basename(project_path)
    
    generator = ReportGenerator(project_name, project_path)
    
    if generator.load_analysis():
        generator.load_validation()
        generator.save_all_reports()
    else:
        print(f"No analysis found: {project_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Analysis Report Generator")
    parser.add_argument("project_path", type=str, help="Project path")
    parser.add_argument("--name", type=str, help="Project name")
    
    args = parser.parse_args()
    
    generate_report(args.project_path, args.name)




"""
报告生成器 - 生成可读的分析和验证报告
支持多种格式：终端输出、Markdown、JSON、CSV
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from validation_rules import SCREEN_TYPES


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self.analysis_data = None
        self.validation_data = None
    
    def load_analysis(self, analysis_file: Optional[str] = None):
        """加载分析结果"""
        if analysis_file is None:
            analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        return False
    
    def load_validation(self, validation_file: Optional[str] = None):
        """加载验证结果"""
        if validation_file is None:
            validation_file = os.path.join(self.project_path, "validation_report.json")
        
        if os.path.exists(validation_file):
            with open(validation_file, 'r', encoding='utf-8') as f:
                self.validation_data = json.load(f)
            return True
        return False
    
    def _get_type_cn(self, screen_type: str) -> str:
        """获取类型的中文名"""
        type_info = SCREEN_TYPES.get(screen_type, {})
        return type_info.get("cn", screen_type)
    
    def generate_terminal_report(self) -> str:
        """生成终端格式的报告"""
        if not self.analysis_data:
            return "Error: No analysis data"
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {self.project_name} AI Analysis Report")
        lines.append("=" * 70)
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        
        lines.append("")
        lines.append("Statistics")
        lines.append("-" * 70)
        lines.append(f"  Total: {total}")
        lines.append(f"  Analyzed: {analyzed}")
        lines.append(f"  Failed: {failed}")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("")
        lines.append("Type Distribution")
        lines.append("-" * 70)
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            bar = "#" * int(pct / 5)
            lines.append(f"  {cn_name:10s} ({screen_type:12s}): {bar:20s} {count:3d} ({pct:5.1f}%)")
        
        if self.validation_data:
            lines.append("")
            lines.append("Validation Results")
            lines.append("-" * 70)
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append(f"  PASS: {pass_count} ({pass_count/total*100:.1f}%)")
            lines.append(f"  REVIEW: {review_count} ({review_count/total*100:.1f}%)")
            lines.append(f"  FAIL: {fail_count} ({fail_count/total*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        if not self.analysis_data:
            return "# Error: No analysis data"
        
        lines = []
        lines.append(f"# {self.project_name} AI Analysis Report")
        lines.append("")
        lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        total_time = self.analysis_data.get("total_time", 0)
        
        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Screenshots | {total} |")
        lines.append(f"| Successfully Analyzed | {analyzed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Time | {total_time:.1f}s |")
        lines.append("")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("## Type Distribution")
        lines.append("")
        lines.append("| Type | Chinese | Count | Percentage |")
        lines.append("|------|---------|-------|------------|")
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            lines.append(f"| {screen_type} | {cn_name} | {count} | {pct:.1f}% |")
        lines.append("")
        
        if self.validation_data:
            lines.append("## Validation Results")
            lines.append("")
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append("| Status | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            lines.append(f"| PASS (High Confidence) | {pass_count} | {pass_count/total*100:.1f}% |")
            lines.append(f"| REVIEW (Medium) | {review_count} | {review_count/total*100:.1f}% |")
            lines.append(f"| FAIL (Low) | {fail_count} | {fail_count/total*100:.1f}% |")
            lines.append("")
        
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| # | Filename | Type | Description | Confidence |")
        lines.append("|---|----------|------|-------------|------------|")
        
        for i, (filename, result) in enumerate(sorted(results.items()), 1):
            screen_type = result.get("screen_type", "Unknown")
            desc_cn = result.get("description_cn", "")[:30]
            confidence = result.get("confidence", 0)
            lines.append(f"| {i} | {filename[:30]} | {screen_type} | {desc_cn} | {confidence:.0%} |")
        
        return "\n".join(lines)
    
    def generate_csv(self, output_file: str):
        """生成CSV格式的详细清单"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            headers = [
                "Index", "Filename", "Type", "Type_CN", "SubType",
                "Description_CN", "Description_EN", "Confidence"
            ]
            
            if self.validation_data:
                headers.extend(["ValidationStatus", "FinalConfidence", "SuggestedType"])
            
            writer.writerow(headers)
            
            val_results = self.validation_data.get("results", {}) if self.validation_data else {}
            
            for i, (filename, result) in enumerate(sorted(results.items()), 1):
                screen_type = result.get("screen_type", "Unknown")
                row = [
                    i,
                    filename,
                    screen_type,
                    self._get_type_cn(screen_type),
                    result.get("sub_type", ""),
                    result.get("description_cn", ""),
                    result.get("description_en", ""),
                    f"{result.get('confidence', 0):.0%}"
                ]
                
                if self.validation_data and filename in val_results:
                    val = val_results[filename]
                    row.extend([
                        val.get("validation_status", ""),
                        f"{val.get('final_confidence', 0):.0%}",
                        val.get("suggested_type", "")
                    ])
                
                writer.writerow(row)
        
        print(f"CSV saved: {output_file}")
    
    def generate_descriptions_json(self, output_file: str):
        """生成与现有系统兼容的 descriptions.json"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        descriptions = {}
        
        for filename, result in results.items():
            desc_cn = result.get("description_cn", "")
            descriptions[filename] = desc_cn
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        
        print(f"Descriptions saved: {output_file}")
    
    def save_all_reports(self):
        """保存所有格式的报告"""
        md_content = self.generate_markdown_report()
        md_file = os.path.join(self.project_path, f"{self.project_name}_AI_Report.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report: {md_file}")
        
        csv_file = os.path.join(self.project_path, f"{self.project_name}_AI_ScreenList.csv")
        self.generate_csv(csv_file)
        
        desc_file = os.path.join(self.project_path, "descriptions_ai.json")
        self.generate_descriptions_json(desc_file)
        
        print(self.generate_terminal_report())


def generate_report(project_path: str, project_name: Optional[str] = None):
    """为项目生成完整报告"""
    if project_name is None:
        project_name = os.path.basename(project_path)
    
    generator = ReportGenerator(project_name, project_path)
    
    if generator.load_analysis():
        generator.load_validation()
        generator.save_all_reports()
    else:
        print(f"No analysis found: {project_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Analysis Report Generator")
    parser.add_argument("project_path", type=str, help="Project path")
    parser.add_argument("--name", type=str, help="Project name")
    
    args = parser.parse_args()
    
    generate_report(args.project_path, args.name)




"""
报告生成器 - 生成可读的分析和验证报告
支持多种格式：终端输出、Markdown、JSON、CSV
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from validation_rules import SCREEN_TYPES


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self.analysis_data = None
        self.validation_data = None
    
    def load_analysis(self, analysis_file: Optional[str] = None):
        """加载分析结果"""
        if analysis_file is None:
            analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        return False
    
    def load_validation(self, validation_file: Optional[str] = None):
        """加载验证结果"""
        if validation_file is None:
            validation_file = os.path.join(self.project_path, "validation_report.json")
        
        if os.path.exists(validation_file):
            with open(validation_file, 'r', encoding='utf-8') as f:
                self.validation_data = json.load(f)
            return True
        return False
    
    def _get_type_cn(self, screen_type: str) -> str:
        """获取类型的中文名"""
        type_info = SCREEN_TYPES.get(screen_type, {})
        return type_info.get("cn", screen_type)
    
    def generate_terminal_report(self) -> str:
        """生成终端格式的报告"""
        if not self.analysis_data:
            return "Error: No analysis data"
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {self.project_name} AI Analysis Report")
        lines.append("=" * 70)
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        
        lines.append("")
        lines.append("Statistics")
        lines.append("-" * 70)
        lines.append(f"  Total: {total}")
        lines.append(f"  Analyzed: {analyzed}")
        lines.append(f"  Failed: {failed}")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("")
        lines.append("Type Distribution")
        lines.append("-" * 70)
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            bar = "#" * int(pct / 5)
            lines.append(f"  {cn_name:10s} ({screen_type:12s}): {bar:20s} {count:3d} ({pct:5.1f}%)")
        
        if self.validation_data:
            lines.append("")
            lines.append("Validation Results")
            lines.append("-" * 70)
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append(f"  PASS: {pass_count} ({pass_count/total*100:.1f}%)")
            lines.append(f"  REVIEW: {review_count} ({review_count/total*100:.1f}%)")
            lines.append(f"  FAIL: {fail_count} ({fail_count/total*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        if not self.analysis_data:
            return "# Error: No analysis data"
        
        lines = []
        lines.append(f"# {self.project_name} AI Analysis Report")
        lines.append("")
        lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        total_time = self.analysis_data.get("total_time", 0)
        
        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Screenshots | {total} |")
        lines.append(f"| Successfully Analyzed | {analyzed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Time | {total_time:.1f}s |")
        lines.append("")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("## Type Distribution")
        lines.append("")
        lines.append("| Type | Chinese | Count | Percentage |")
        lines.append("|------|---------|-------|------------|")
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            lines.append(f"| {screen_type} | {cn_name} | {count} | {pct:.1f}% |")
        lines.append("")
        
        if self.validation_data:
            lines.append("## Validation Results")
            lines.append("")
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append("| Status | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            lines.append(f"| PASS (High Confidence) | {pass_count} | {pass_count/total*100:.1f}% |")
            lines.append(f"| REVIEW (Medium) | {review_count} | {review_count/total*100:.1f}% |")
            lines.append(f"| FAIL (Low) | {fail_count} | {fail_count/total*100:.1f}% |")
            lines.append("")
        
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| # | Filename | Type | Description | Confidence |")
        lines.append("|---|----------|------|-------------|------------|")
        
        for i, (filename, result) in enumerate(sorted(results.items()), 1):
            screen_type = result.get("screen_type", "Unknown")
            desc_cn = result.get("description_cn", "")[:30]
            confidence = result.get("confidence", 0)
            lines.append(f"| {i} | {filename[:30]} | {screen_type} | {desc_cn} | {confidence:.0%} |")
        
        return "\n".join(lines)
    
    def generate_csv(self, output_file: str):
        """生成CSV格式的详细清单"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            headers = [
                "Index", "Filename", "Type", "Type_CN", "SubType",
                "Description_CN", "Description_EN", "Confidence"
            ]
            
            if self.validation_data:
                headers.extend(["ValidationStatus", "FinalConfidence", "SuggestedType"])
            
            writer.writerow(headers)
            
            val_results = self.validation_data.get("results", {}) if self.validation_data else {}
            
            for i, (filename, result) in enumerate(sorted(results.items()), 1):
                screen_type = result.get("screen_type", "Unknown")
                row = [
                    i,
                    filename,
                    screen_type,
                    self._get_type_cn(screen_type),
                    result.get("sub_type", ""),
                    result.get("description_cn", ""),
                    result.get("description_en", ""),
                    f"{result.get('confidence', 0):.0%}"
                ]
                
                if self.validation_data and filename in val_results:
                    val = val_results[filename]
                    row.extend([
                        val.get("validation_status", ""),
                        f"{val.get('final_confidence', 0):.0%}",
                        val.get("suggested_type", "")
                    ])
                
                writer.writerow(row)
        
        print(f"CSV saved: {output_file}")
    
    def generate_descriptions_json(self, output_file: str):
        """生成与现有系统兼容的 descriptions.json"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        descriptions = {}
        
        for filename, result in results.items():
            desc_cn = result.get("description_cn", "")
            descriptions[filename] = desc_cn
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        
        print(f"Descriptions saved: {output_file}")
    
    def save_all_reports(self):
        """保存所有格式的报告"""
        md_content = self.generate_markdown_report()
        md_file = os.path.join(self.project_path, f"{self.project_name}_AI_Report.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report: {md_file}")
        
        csv_file = os.path.join(self.project_path, f"{self.project_name}_AI_ScreenList.csv")
        self.generate_csv(csv_file)
        
        desc_file = os.path.join(self.project_path, "descriptions_ai.json")
        self.generate_descriptions_json(desc_file)
        
        print(self.generate_terminal_report())


def generate_report(project_path: str, project_name: Optional[str] = None):
    """为项目生成完整报告"""
    if project_name is None:
        project_name = os.path.basename(project_path)
    
    generator = ReportGenerator(project_name, project_path)
    
    if generator.load_analysis():
        generator.load_validation()
        generator.save_all_reports()
    else:
        print(f"No analysis found: {project_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Analysis Report Generator")
    parser.add_argument("project_path", type=str, help="Project path")
    parser.add_argument("--name", type=str, help="Project name")
    
    args = parser.parse_args()
    
    generate_report(args.project_path, args.name)




"""
报告生成器 - 生成可读的分析和验证报告
支持多种格式：终端输出、Markdown、JSON、CSV
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from validation_rules import SCREEN_TYPES


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self.analysis_data = None
        self.validation_data = None
    
    def load_analysis(self, analysis_file: Optional[str] = None):
        """加载分析结果"""
        if analysis_file is None:
            analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        return False
    
    def load_validation(self, validation_file: Optional[str] = None):
        """加载验证结果"""
        if validation_file is None:
            validation_file = os.path.join(self.project_path, "validation_report.json")
        
        if os.path.exists(validation_file):
            with open(validation_file, 'r', encoding='utf-8') as f:
                self.validation_data = json.load(f)
            return True
        return False
    
    def _get_type_cn(self, screen_type: str) -> str:
        """获取类型的中文名"""
        type_info = SCREEN_TYPES.get(screen_type, {})
        return type_info.get("cn", screen_type)
    
    def generate_terminal_report(self) -> str:
        """生成终端格式的报告"""
        if not self.analysis_data:
            return "Error: No analysis data"
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {self.project_name} AI Analysis Report")
        lines.append("=" * 70)
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        
        lines.append("")
        lines.append("Statistics")
        lines.append("-" * 70)
        lines.append(f"  Total: {total}")
        lines.append(f"  Analyzed: {analyzed}")
        lines.append(f"  Failed: {failed}")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("")
        lines.append("Type Distribution")
        lines.append("-" * 70)
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            bar = "#" * int(pct / 5)
            lines.append(f"  {cn_name:10s} ({screen_type:12s}): {bar:20s} {count:3d} ({pct:5.1f}%)")
        
        if self.validation_data:
            lines.append("")
            lines.append("Validation Results")
            lines.append("-" * 70)
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append(f"  PASS: {pass_count} ({pass_count/total*100:.1f}%)")
            lines.append(f"  REVIEW: {review_count} ({review_count/total*100:.1f}%)")
            lines.append(f"  FAIL: {fail_count} ({fail_count/total*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        if not self.analysis_data:
            return "# Error: No analysis data"
        
        lines = []
        lines.append(f"# {self.project_name} AI Analysis Report")
        lines.append("")
        lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        total_time = self.analysis_data.get("total_time", 0)
        
        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Screenshots | {total} |")
        lines.append(f"| Successfully Analyzed | {analyzed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Time | {total_time:.1f}s |")
        lines.append("")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("## Type Distribution")
        lines.append("")
        lines.append("| Type | Chinese | Count | Percentage |")
        lines.append("|------|---------|-------|------------|")
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            lines.append(f"| {screen_type} | {cn_name} | {count} | {pct:.1f}% |")
        lines.append("")
        
        if self.validation_data:
            lines.append("## Validation Results")
            lines.append("")
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append("| Status | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            lines.append(f"| PASS (High Confidence) | {pass_count} | {pass_count/total*100:.1f}% |")
            lines.append(f"| REVIEW (Medium) | {review_count} | {review_count/total*100:.1f}% |")
            lines.append(f"| FAIL (Low) | {fail_count} | {fail_count/total*100:.1f}% |")
            lines.append("")
        
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| # | Filename | Type | Description | Confidence |")
        lines.append("|---|----------|------|-------------|------------|")
        
        for i, (filename, result) in enumerate(sorted(results.items()), 1):
            screen_type = result.get("screen_type", "Unknown")
            desc_cn = result.get("description_cn", "")[:30]
            confidence = result.get("confidence", 0)
            lines.append(f"| {i} | {filename[:30]} | {screen_type} | {desc_cn} | {confidence:.0%} |")
        
        return "\n".join(lines)
    
    def generate_csv(self, output_file: str):
        """生成CSV格式的详细清单"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            headers = [
                "Index", "Filename", "Type", "Type_CN", "SubType",
                "Description_CN", "Description_EN", "Confidence"
            ]
            
            if self.validation_data:
                headers.extend(["ValidationStatus", "FinalConfidence", "SuggestedType"])
            
            writer.writerow(headers)
            
            val_results = self.validation_data.get("results", {}) if self.validation_data else {}
            
            for i, (filename, result) in enumerate(sorted(results.items()), 1):
                screen_type = result.get("screen_type", "Unknown")
                row = [
                    i,
                    filename,
                    screen_type,
                    self._get_type_cn(screen_type),
                    result.get("sub_type", ""),
                    result.get("description_cn", ""),
                    result.get("description_en", ""),
                    f"{result.get('confidence', 0):.0%}"
                ]
                
                if self.validation_data and filename in val_results:
                    val = val_results[filename]
                    row.extend([
                        val.get("validation_status", ""),
                        f"{val.get('final_confidence', 0):.0%}",
                        val.get("suggested_type", "")
                    ])
                
                writer.writerow(row)
        
        print(f"CSV saved: {output_file}")
    
    def generate_descriptions_json(self, output_file: str):
        """生成与现有系统兼容的 descriptions.json"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        descriptions = {}
        
        for filename, result in results.items():
            desc_cn = result.get("description_cn", "")
            descriptions[filename] = desc_cn
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        
        print(f"Descriptions saved: {output_file}")
    
    def save_all_reports(self):
        """保存所有格式的报告"""
        md_content = self.generate_markdown_report()
        md_file = os.path.join(self.project_path, f"{self.project_name}_AI_Report.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report: {md_file}")
        
        csv_file = os.path.join(self.project_path, f"{self.project_name}_AI_ScreenList.csv")
        self.generate_csv(csv_file)
        
        desc_file = os.path.join(self.project_path, "descriptions_ai.json")
        self.generate_descriptions_json(desc_file)
        
        print(self.generate_terminal_report())


def generate_report(project_path: str, project_name: Optional[str] = None):
    """为项目生成完整报告"""
    if project_name is None:
        project_name = os.path.basename(project_path)
    
    generator = ReportGenerator(project_name, project_path)
    
    if generator.load_analysis():
        generator.load_validation()
        generator.save_all_reports()
    else:
        print(f"No analysis found: {project_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Analysis Report Generator")
    parser.add_argument("project_path", type=str, help="Project path")
    parser.add_argument("--name", type=str, help="Project name")
    
    args = parser.parse_args()
    
    generate_report(args.project_path, args.name)





"""
报告生成器 - 生成可读的分析和验证报告
支持多种格式：终端输出、Markdown、JSON、CSV
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from validation_rules import SCREEN_TYPES


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self.analysis_data = None
        self.validation_data = None
    
    def load_analysis(self, analysis_file: Optional[str] = None):
        """加载分析结果"""
        if analysis_file is None:
            analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        return False
    
    def load_validation(self, validation_file: Optional[str] = None):
        """加载验证结果"""
        if validation_file is None:
            validation_file = os.path.join(self.project_path, "validation_report.json")
        
        if os.path.exists(validation_file):
            with open(validation_file, 'r', encoding='utf-8') as f:
                self.validation_data = json.load(f)
            return True
        return False
    
    def _get_type_cn(self, screen_type: str) -> str:
        """获取类型的中文名"""
        type_info = SCREEN_TYPES.get(screen_type, {})
        return type_info.get("cn", screen_type)
    
    def generate_terminal_report(self) -> str:
        """生成终端格式的报告"""
        if not self.analysis_data:
            return "Error: No analysis data"
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {self.project_name} AI Analysis Report")
        lines.append("=" * 70)
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        
        lines.append("")
        lines.append("Statistics")
        lines.append("-" * 70)
        lines.append(f"  Total: {total}")
        lines.append(f"  Analyzed: {analyzed}")
        lines.append(f"  Failed: {failed}")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("")
        lines.append("Type Distribution")
        lines.append("-" * 70)
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            bar = "#" * int(pct / 5)
            lines.append(f"  {cn_name:10s} ({screen_type:12s}): {bar:20s} {count:3d} ({pct:5.1f}%)")
        
        if self.validation_data:
            lines.append("")
            lines.append("Validation Results")
            lines.append("-" * 70)
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append(f"  PASS: {pass_count} ({pass_count/total*100:.1f}%)")
            lines.append(f"  REVIEW: {review_count} ({review_count/total*100:.1f}%)")
            lines.append(f"  FAIL: {fail_count} ({fail_count/total*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        if not self.analysis_data:
            return "# Error: No analysis data"
        
        lines = []
        lines.append(f"# {self.project_name} AI Analysis Report")
        lines.append("")
        lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        total_time = self.analysis_data.get("total_time", 0)
        
        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Screenshots | {total} |")
        lines.append(f"| Successfully Analyzed | {analyzed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Time | {total_time:.1f}s |")
        lines.append("")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("## Type Distribution")
        lines.append("")
        lines.append("| Type | Chinese | Count | Percentage |")
        lines.append("|------|---------|-------|------------|")
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            lines.append(f"| {screen_type} | {cn_name} | {count} | {pct:.1f}% |")
        lines.append("")
        
        if self.validation_data:
            lines.append("## Validation Results")
            lines.append("")
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append("| Status | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            lines.append(f"| PASS (High Confidence) | {pass_count} | {pass_count/total*100:.1f}% |")
            lines.append(f"| REVIEW (Medium) | {review_count} | {review_count/total*100:.1f}% |")
            lines.append(f"| FAIL (Low) | {fail_count} | {fail_count/total*100:.1f}% |")
            lines.append("")
        
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| # | Filename | Type | Description | Confidence |")
        lines.append("|---|----------|------|-------------|------------|")
        
        for i, (filename, result) in enumerate(sorted(results.items()), 1):
            screen_type = result.get("screen_type", "Unknown")
            desc_cn = result.get("description_cn", "")[:30]
            confidence = result.get("confidence", 0)
            lines.append(f"| {i} | {filename[:30]} | {screen_type} | {desc_cn} | {confidence:.0%} |")
        
        return "\n".join(lines)
    
    def generate_csv(self, output_file: str):
        """生成CSV格式的详细清单"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            headers = [
                "Index", "Filename", "Type", "Type_CN", "SubType",
                "Description_CN", "Description_EN", "Confidence"
            ]
            
            if self.validation_data:
                headers.extend(["ValidationStatus", "FinalConfidence", "SuggestedType"])
            
            writer.writerow(headers)
            
            val_results = self.validation_data.get("results", {}) if self.validation_data else {}
            
            for i, (filename, result) in enumerate(sorted(results.items()), 1):
                screen_type = result.get("screen_type", "Unknown")
                row = [
                    i,
                    filename,
                    screen_type,
                    self._get_type_cn(screen_type),
                    result.get("sub_type", ""),
                    result.get("description_cn", ""),
                    result.get("description_en", ""),
                    f"{result.get('confidence', 0):.0%}"
                ]
                
                if self.validation_data and filename in val_results:
                    val = val_results[filename]
                    row.extend([
                        val.get("validation_status", ""),
                        f"{val.get('final_confidence', 0):.0%}",
                        val.get("suggested_type", "")
                    ])
                
                writer.writerow(row)
        
        print(f"CSV saved: {output_file}")
    
    def generate_descriptions_json(self, output_file: str):
        """生成与现有系统兼容的 descriptions.json"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        descriptions = {}
        
        for filename, result in results.items():
            desc_cn = result.get("description_cn", "")
            descriptions[filename] = desc_cn
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        
        print(f"Descriptions saved: {output_file}")
    
    def save_all_reports(self):
        """保存所有格式的报告"""
        md_content = self.generate_markdown_report()
        md_file = os.path.join(self.project_path, f"{self.project_name}_AI_Report.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report: {md_file}")
        
        csv_file = os.path.join(self.project_path, f"{self.project_name}_AI_ScreenList.csv")
        self.generate_csv(csv_file)
        
        desc_file = os.path.join(self.project_path, "descriptions_ai.json")
        self.generate_descriptions_json(desc_file)
        
        print(self.generate_terminal_report())


def generate_report(project_path: str, project_name: Optional[str] = None):
    """为项目生成完整报告"""
    if project_name is None:
        project_name = os.path.basename(project_path)
    
    generator = ReportGenerator(project_name, project_path)
    
    if generator.load_analysis():
        generator.load_validation()
        generator.save_all_reports()
    else:
        print(f"No analysis found: {project_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Analysis Report Generator")
    parser.add_argument("project_path", type=str, help="Project path")
    parser.add_argument("--name", type=str, help="Project name")
    
    args = parser.parse_args()
    
    generate_report(args.project_path, args.name)




"""
报告生成器 - 生成可读的分析和验证报告
支持多种格式：终端输出、Markdown、JSON、CSV
"""

import os
import json
import csv
from typing import Dict, List, Optional
from datetime import datetime
from collections import Counter

from validation_rules import SCREEN_TYPES


class ReportGenerator:
    """分析报告生成器"""
    
    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self.analysis_data = None
        self.validation_data = None
    
    def load_analysis(self, analysis_file: Optional[str] = None):
        """加载分析结果"""
        if analysis_file is None:
            analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                self.analysis_data = json.load(f)
            return True
        return False
    
    def load_validation(self, validation_file: Optional[str] = None):
        """加载验证结果"""
        if validation_file is None:
            validation_file = os.path.join(self.project_path, "validation_report.json")
        
        if os.path.exists(validation_file):
            with open(validation_file, 'r', encoding='utf-8') as f:
                self.validation_data = json.load(f)
            return True
        return False
    
    def _get_type_cn(self, screen_type: str) -> str:
        """获取类型的中文名"""
        type_info = SCREEN_TYPES.get(screen_type, {})
        return type_info.get("cn", screen_type)
    
    def generate_terminal_report(self) -> str:
        """生成终端格式的报告"""
        if not self.analysis_data:
            return "Error: No analysis data"
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  {self.project_name} AI Analysis Report")
        lines.append("=" * 70)
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        
        lines.append("")
        lines.append("Statistics")
        lines.append("-" * 70)
        lines.append(f"  Total: {total}")
        lines.append(f"  Analyzed: {analyzed}")
        lines.append(f"  Failed: {failed}")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("")
        lines.append("Type Distribution")
        lines.append("-" * 70)
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            bar = "#" * int(pct / 5)
            lines.append(f"  {cn_name:10s} ({screen_type:12s}): {bar:20s} {count:3d} ({pct:5.1f}%)")
        
        if self.validation_data:
            lines.append("")
            lines.append("Validation Results")
            lines.append("-" * 70)
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append(f"  PASS: {pass_count} ({pass_count/total*100:.1f}%)")
            lines.append(f"  REVIEW: {review_count} ({review_count/total*100:.1f}%)")
            lines.append(f"  FAIL: {fail_count} ({fail_count/total*100:.1f}%)")
        
        lines.append("")
        lines.append("=" * 70)
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def generate_markdown_report(self) -> str:
        """生成Markdown格式的报告"""
        if not self.analysis_data:
            return "# Error: No analysis data"
        
        lines = []
        lines.append(f"# {self.project_name} AI Analysis Report")
        lines.append("")
        lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        total = self.analysis_data.get("total_screenshots", 0)
        analyzed = self.analysis_data.get("analyzed_count", 0)
        failed = self.analysis_data.get("failed_count", 0)
        total_time = self.analysis_data.get("total_time", 0)
        
        lines.append("## Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Screenshots | {total} |")
        lines.append(f"| Successfully Analyzed | {analyzed} |")
        lines.append(f"| Failed | {failed} |")
        lines.append(f"| Total Time | {total_time:.1f}s |")
        lines.append("")
        
        results = self.analysis_data.get("results", {})
        type_counts = Counter(r.get("screen_type", "Unknown") for r in results.values())
        
        lines.append("## Type Distribution")
        lines.append("")
        lines.append("| Type | Chinese | Count | Percentage |")
        lines.append("|------|---------|-------|------------|")
        
        for screen_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total > 0 else 0
            cn_name = self._get_type_cn(screen_type)
            lines.append(f"| {screen_type} | {cn_name} | {count} | {pct:.1f}% |")
        lines.append("")
        
        if self.validation_data:
            lines.append("## Validation Results")
            lines.append("")
            
            pass_count = self.validation_data.get("pass_count", 0)
            review_count = self.validation_data.get("review_count", 0)
            fail_count = self.validation_data.get("fail_count", 0)
            
            lines.append("| Status | Count | Percentage |")
            lines.append("|--------|-------|------------|")
            lines.append(f"| PASS (High Confidence) | {pass_count} | {pass_count/total*100:.1f}% |")
            lines.append(f"| REVIEW (Medium) | {review_count} | {review_count/total*100:.1f}% |")
            lines.append(f"| FAIL (Low) | {fail_count} | {fail_count/total*100:.1f}% |")
            lines.append("")
        
        lines.append("## Detailed Results")
        lines.append("")
        lines.append("| # | Filename | Type | Description | Confidence |")
        lines.append("|---|----------|------|-------------|------------|")
        
        for i, (filename, result) in enumerate(sorted(results.items()), 1):
            screen_type = result.get("screen_type", "Unknown")
            desc_cn = result.get("description_cn", "")[:30]
            confidence = result.get("confidence", 0)
            lines.append(f"| {i} | {filename[:30]} | {screen_type} | {desc_cn} | {confidence:.0%} |")
        
        return "\n".join(lines)
    
    def generate_csv(self, output_file: str):
        """生成CSV格式的详细清单"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            headers = [
                "Index", "Filename", "Type", "Type_CN", "SubType",
                "Description_CN", "Description_EN", "Confidence"
            ]
            
            if self.validation_data:
                headers.extend(["ValidationStatus", "FinalConfidence", "SuggestedType"])
            
            writer.writerow(headers)
            
            val_results = self.validation_data.get("results", {}) if self.validation_data else {}
            
            for i, (filename, result) in enumerate(sorted(results.items()), 1):
                screen_type = result.get("screen_type", "Unknown")
                row = [
                    i,
                    filename,
                    screen_type,
                    self._get_type_cn(screen_type),
                    result.get("sub_type", ""),
                    result.get("description_cn", ""),
                    result.get("description_en", ""),
                    f"{result.get('confidence', 0):.0%}"
                ]
                
                if self.validation_data and filename in val_results:
                    val = val_results[filename]
                    row.extend([
                        val.get("validation_status", ""),
                        f"{val.get('final_confidence', 0):.0%}",
                        val.get("suggested_type", "")
                    ])
                
                writer.writerow(row)
        
        print(f"CSV saved: {output_file}")
    
    def generate_descriptions_json(self, output_file: str):
        """生成与现有系统兼容的 descriptions.json"""
        if not self.analysis_data:
            return
        
        results = self.analysis_data.get("results", {})
        descriptions = {}
        
        for filename, result in results.items():
            desc_cn = result.get("description_cn", "")
            descriptions[filename] = desc_cn
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions, f, ensure_ascii=False, indent=2)
        
        print(f"Descriptions saved: {output_file}")
    
    def save_all_reports(self):
        """保存所有格式的报告"""
        md_content = self.generate_markdown_report()
        md_file = os.path.join(self.project_path, f"{self.project_name}_AI_Report.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        print(f"Markdown report: {md_file}")
        
        csv_file = os.path.join(self.project_path, f"{self.project_name}_AI_ScreenList.csv")
        self.generate_csv(csv_file)
        
        desc_file = os.path.join(self.project_path, "descriptions_ai.json")
        self.generate_descriptions_json(desc_file)
        
        print(self.generate_terminal_report())


def generate_report(project_path: str, project_name: Optional[str] = None):
    """为项目生成完整报告"""
    if project_name is None:
        project_name = os.path.basename(project_path)
    
    generator = ReportGenerator(project_name, project_path)
    
    if generator.load_analysis():
        generator.load_validation()
        generator.save_all_reports()
    else:
        print(f"No analysis found: {project_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Analysis Report Generator")
    parser.add_argument("project_path", type=str, help="Project path")
    parser.add_argument("--name", type=str, help="Project name")
    
    args = parser.parse_args()
    
    generate_report(args.project_path, args.name)




















