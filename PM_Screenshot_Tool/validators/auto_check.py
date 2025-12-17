# -*- coding: utf-8 -*-
"""
智能自检验系统 - 主控制器
自动验证、自动修复、循环直到通过
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_validator import OrderValidator
from fixers.order_fixer import OrderFixer


class AutoChecker:
    """
    自动检验器
    验证 -> 修复 -> 再验证 -> 循环直到通过或达到最大次数
    """
    
    def __init__(self, project_path: str, max_iterations: int = 3):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.max_iterations = max_iterations
        self.results_log = []
    
    def run(self, auto_fix: bool = True) -> dict:
        """
        运行自动检验
        
        Args:
            auto_fix: 是否自动修复发现的问题
        
        Returns:
            {
                "passed": bool,
                "iterations": int,
                "fixes_applied": int,
                "final_issues": [],
                "log": []
            }
        """
        print(f"\n{'='*60}")
        print(f"[AUTO-CHECK] Smart Validation System")
        print(f"   Project: {self.project_name}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Auto fix: {'Yes' if auto_fix else 'No'}")
        print('='*60)
        
        total_fixes = 0
        final_result = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Round {iteration}/{self.max_iterations}] Validating...")
            print('-'*40)
            
            # 验证
            validator = OrderValidator(self.project_path)
            result = validator.validate()
            
            self.results_log.append({
                "iteration": iteration,
                "time": datetime.now().isoformat(),
                "passed": result["passed"],
                "issues_count": len(result["issues"])
            })
            
            if result["passed"]:
                print(f"\n[PASSED] Validation passed!")
                final_result = result
                break
            
            # 有问题，尝试修复
            if auto_fix and result["issues"]:
                print(f"\n[FIX] Found {len(result['issues'])} issues, fixing...")
                
                fix_plan = validator.get_fix_plan()
                
                if fix_plan:
                    fixer = OrderFixer(self.project_path)
                    fix_result = fixer.fix(fix_plan, backup=(iteration == 1))
                    
                    total_fixes += fix_result["fixed_count"]
                    
                    if not fix_result["success"]:
                        print(f"\n[WARN] Errors during fix")
                        final_result = result
                        break
                else:
                    print(f"\n[WARN] Cannot generate fix plan")
                    final_result = result
                    break
            else:
                final_result = result
                break
        
        # 如果循环结束还没通过，做最后一次验证
        if final_result is None or not final_result["passed"]:
            print(f"\n[FINAL] Final validation...")
            validator = OrderValidator(self.project_path)
            final_result = validator.validate()
        
        # 生成报告
        report = {
            "passed": final_result["passed"],
            "iterations": len(self.results_log),
            "fixes_applied": total_fixes,
            "final_issues": final_result["issues"],
            "log": self.results_log
        }
        
        self._print_summary(report)
        self._save_report(report)
        
        return report
    
    def _print_summary(self, report: dict):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("[REPORT] Validation Report")
        print('='*60)
        
        status = "[OK] PASSED" if report["passed"] else "[FAIL] NOT PASSED"
        print(f"   Status: {status}")
        print(f"   Iterations: {report['iterations']}")
        print(f"   Files fixed: {report['fixes_applied']}")
        
        if report["final_issues"]:
            print(f"\n   Remaining issues:")
            for issue in report["final_issues"][:3]:
                print(f"     - {issue.get('phase', 'N/A')}: {issue.get('type', 'unknown')}")
        
        print('='*60)
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_path = os.path.join(self.project_path, "validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n[SAVED] Report saved: validation_report.json")


def check_project(project_name: str, auto_fix: bool = True) -> dict:
    """
    便捷函数：检验项目
    
    Args:
        project_name: 项目名称，如 "Calm_Analysis"
        auto_fix: 是否自动修复
    
    Returns:
        检验报告
    """
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    if not os.path.exists(project_path):
        print(f"[ERROR] Project not found: {project_name}")
        return {"passed": False, "error": "项目不存在"}
    
    checker = AutoChecker(project_path)
    return checker.run(auto_fix=auto_fix)


def check_all_projects(auto_fix: bool = True) -> dict:
    """检验所有项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_path = os.path.join(base_path, "projects")
    
    results = {}
    
    for name in os.listdir(projects_path):
        project_path = os.path.join(projects_path, name)
        screens_path = os.path.join(project_path, "Screens")
        
        if os.path.isdir(project_path) and os.path.exists(screens_path):
            print(f"\n\n{'#'*60}")
            print(f"# 检验项目: {name}")
            print('#'*60)
            
            checker = AutoChecker(project_path)
            results[name] = checker.run(auto_fix=auto_fix)
    
    # 汇总
    print(f"\n\n{'='*60}")
    print("[SUMMARY] All Projects Validation Summary")
    print('='*60)
    
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    
    print(f"   Passed: {passed_count}/{total_count}")
    
    for name, result in results.items():
        status = "[OK]" if result.get("passed") else "[FAIL]"
        print(f"   {status} {name}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能自检验系统")
    parser.add_argument("--project", "-p", help="项目名称，不指定则检验所有项目")
    parser.add_argument("--no-fix", action="store_true", help="只检验不修复")
    parser.add_argument("--all", "-a", action="store_true", help="检验所有项目")
    
    args = parser.parse_args()
    
    auto_fix = not args.no_fix
    
    if args.all or not args.project:
        check_all_projects(auto_fix=auto_fix)
    else:
        check_project(args.project, auto_fix=auto_fix)


智能自检验系统 - 主控制器
自动验证、自动修复、循环直到通过
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_validator import OrderValidator
from fixers.order_fixer import OrderFixer


class AutoChecker:
    """
    自动检验器
    验证 -> 修复 -> 再验证 -> 循环直到通过或达到最大次数
    """
    
    def __init__(self, project_path: str, max_iterations: int = 3):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.max_iterations = max_iterations
        self.results_log = []
    
    def run(self, auto_fix: bool = True) -> dict:
        """
        运行自动检验
        
        Args:
            auto_fix: 是否自动修复发现的问题
        
        Returns:
            {
                "passed": bool,
                "iterations": int,
                "fixes_applied": int,
                "final_issues": [],
                "log": []
            }
        """
        print(f"\n{'='*60}")
        print(f"[AUTO-CHECK] Smart Validation System")
        print(f"   Project: {self.project_name}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Auto fix: {'Yes' if auto_fix else 'No'}")
        print('='*60)
        
        total_fixes = 0
        final_result = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Round {iteration}/{self.max_iterations}] Validating...")
            print('-'*40)
            
            # 验证
            validator = OrderValidator(self.project_path)
            result = validator.validate()
            
            self.results_log.append({
                "iteration": iteration,
                "time": datetime.now().isoformat(),
                "passed": result["passed"],
                "issues_count": len(result["issues"])
            })
            
            if result["passed"]:
                print(f"\n[PASSED] Validation passed!")
                final_result = result
                break
            
            # 有问题，尝试修复
            if auto_fix and result["issues"]:
                print(f"\n[FIX] Found {len(result['issues'])} issues, fixing...")
                
                fix_plan = validator.get_fix_plan()
                
                if fix_plan:
                    fixer = OrderFixer(self.project_path)
                    fix_result = fixer.fix(fix_plan, backup=(iteration == 1))
                    
                    total_fixes += fix_result["fixed_count"]
                    
                    if not fix_result["success"]:
                        print(f"\n[WARN] Errors during fix")
                        final_result = result
                        break
                else:
                    print(f"\n[WARN] Cannot generate fix plan")
                    final_result = result
                    break
            else:
                final_result = result
                break
        
        # 如果循环结束还没通过，做最后一次验证
        if final_result is None or not final_result["passed"]:
            print(f"\n[FINAL] Final validation...")
            validator = OrderValidator(self.project_path)
            final_result = validator.validate()
        
        # 生成报告
        report = {
            "passed": final_result["passed"],
            "iterations": len(self.results_log),
            "fixes_applied": total_fixes,
            "final_issues": final_result["issues"],
            "log": self.results_log
        }
        
        self._print_summary(report)
        self._save_report(report)
        
        return report
    
    def _print_summary(self, report: dict):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("[REPORT] Validation Report")
        print('='*60)
        
        status = "[OK] PASSED" if report["passed"] else "[FAIL] NOT PASSED"
        print(f"   Status: {status}")
        print(f"   Iterations: {report['iterations']}")
        print(f"   Files fixed: {report['fixes_applied']}")
        
        if report["final_issues"]:
            print(f"\n   Remaining issues:")
            for issue in report["final_issues"][:3]:
                print(f"     - {issue.get('phase', 'N/A')}: {issue.get('type', 'unknown')}")
        
        print('='*60)
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_path = os.path.join(self.project_path, "validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n[SAVED] Report saved: validation_report.json")


def check_project(project_name: str, auto_fix: bool = True) -> dict:
    """
    便捷函数：检验项目
    
    Args:
        project_name: 项目名称，如 "Calm_Analysis"
        auto_fix: 是否自动修复
    
    Returns:
        检验报告
    """
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    if not os.path.exists(project_path):
        print(f"[ERROR] Project not found: {project_name}")
        return {"passed": False, "error": "项目不存在"}
    
    checker = AutoChecker(project_path)
    return checker.run(auto_fix=auto_fix)


def check_all_projects(auto_fix: bool = True) -> dict:
    """检验所有项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_path = os.path.join(base_path, "projects")
    
    results = {}
    
    for name in os.listdir(projects_path):
        project_path = os.path.join(projects_path, name)
        screens_path = os.path.join(project_path, "Screens")
        
        if os.path.isdir(project_path) and os.path.exists(screens_path):
            print(f"\n\n{'#'*60}")
            print(f"# 检验项目: {name}")
            print('#'*60)
            
            checker = AutoChecker(project_path)
            results[name] = checker.run(auto_fix=auto_fix)
    
    # 汇总
    print(f"\n\n{'='*60}")
    print("[SUMMARY] All Projects Validation Summary")
    print('='*60)
    
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    
    print(f"   Passed: {passed_count}/{total_count}")
    
    for name, result in results.items():
        status = "[OK]" if result.get("passed") else "[FAIL]"
        print(f"   {status} {name}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能自检验系统")
    parser.add_argument("--project", "-p", help="项目名称，不指定则检验所有项目")
    parser.add_argument("--no-fix", action="store_true", help="只检验不修复")
    parser.add_argument("--all", "-a", action="store_true", help="检验所有项目")
    
    args = parser.parse_args()
    
    auto_fix = not args.no_fix
    
    if args.all or not args.project:
        check_all_projects(auto_fix=auto_fix)
    else:
        check_project(args.project, auto_fix=auto_fix)


智能自检验系统 - 主控制器
自动验证、自动修复、循环直到通过
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_validator import OrderValidator
from fixers.order_fixer import OrderFixer


class AutoChecker:
    """
    自动检验器
    验证 -> 修复 -> 再验证 -> 循环直到通过或达到最大次数
    """
    
    def __init__(self, project_path: str, max_iterations: int = 3):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.max_iterations = max_iterations
        self.results_log = []
    
    def run(self, auto_fix: bool = True) -> dict:
        """
        运行自动检验
        
        Args:
            auto_fix: 是否自动修复发现的问题
        
        Returns:
            {
                "passed": bool,
                "iterations": int,
                "fixes_applied": int,
                "final_issues": [],
                "log": []
            }
        """
        print(f"\n{'='*60}")
        print(f"[AUTO-CHECK] Smart Validation System")
        print(f"   Project: {self.project_name}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Auto fix: {'Yes' if auto_fix else 'No'}")
        print('='*60)
        
        total_fixes = 0
        final_result = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Round {iteration}/{self.max_iterations}] Validating...")
            print('-'*40)
            
            # 验证
            validator = OrderValidator(self.project_path)
            result = validator.validate()
            
            self.results_log.append({
                "iteration": iteration,
                "time": datetime.now().isoformat(),
                "passed": result["passed"],
                "issues_count": len(result["issues"])
            })
            
            if result["passed"]:
                print(f"\n[PASSED] Validation passed!")
                final_result = result
                break
            
            # 有问题，尝试修复
            if auto_fix and result["issues"]:
                print(f"\n[FIX] Found {len(result['issues'])} issues, fixing...")
                
                fix_plan = validator.get_fix_plan()
                
                if fix_plan:
                    fixer = OrderFixer(self.project_path)
                    fix_result = fixer.fix(fix_plan, backup=(iteration == 1))
                    
                    total_fixes += fix_result["fixed_count"]
                    
                    if not fix_result["success"]:
                        print(f"\n[WARN] Errors during fix")
                        final_result = result
                        break
                else:
                    print(f"\n[WARN] Cannot generate fix plan")
                    final_result = result
                    break
            else:
                final_result = result
                break
        
        # 如果循环结束还没通过，做最后一次验证
        if final_result is None or not final_result["passed"]:
            print(f"\n[FINAL] Final validation...")
            validator = OrderValidator(self.project_path)
            final_result = validator.validate()
        
        # 生成报告
        report = {
            "passed": final_result["passed"],
            "iterations": len(self.results_log),
            "fixes_applied": total_fixes,
            "final_issues": final_result["issues"],
            "log": self.results_log
        }
        
        self._print_summary(report)
        self._save_report(report)
        
        return report
    
    def _print_summary(self, report: dict):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("[REPORT] Validation Report")
        print('='*60)
        
        status = "[OK] PASSED" if report["passed"] else "[FAIL] NOT PASSED"
        print(f"   Status: {status}")
        print(f"   Iterations: {report['iterations']}")
        print(f"   Files fixed: {report['fixes_applied']}")
        
        if report["final_issues"]:
            print(f"\n   Remaining issues:")
            for issue in report["final_issues"][:3]:
                print(f"     - {issue.get('phase', 'N/A')}: {issue.get('type', 'unknown')}")
        
        print('='*60)
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_path = os.path.join(self.project_path, "validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n[SAVED] Report saved: validation_report.json")


def check_project(project_name: str, auto_fix: bool = True) -> dict:
    """
    便捷函数：检验项目
    
    Args:
        project_name: 项目名称，如 "Calm_Analysis"
        auto_fix: 是否自动修复
    
    Returns:
        检验报告
    """
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    if not os.path.exists(project_path):
        print(f"[ERROR] Project not found: {project_name}")
        return {"passed": False, "error": "项目不存在"}
    
    checker = AutoChecker(project_path)
    return checker.run(auto_fix=auto_fix)


def check_all_projects(auto_fix: bool = True) -> dict:
    """检验所有项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_path = os.path.join(base_path, "projects")
    
    results = {}
    
    for name in os.listdir(projects_path):
        project_path = os.path.join(projects_path, name)
        screens_path = os.path.join(project_path, "Screens")
        
        if os.path.isdir(project_path) and os.path.exists(screens_path):
            print(f"\n\n{'#'*60}")
            print(f"# 检验项目: {name}")
            print('#'*60)
            
            checker = AutoChecker(project_path)
            results[name] = checker.run(auto_fix=auto_fix)
    
    # 汇总
    print(f"\n\n{'='*60}")
    print("[SUMMARY] All Projects Validation Summary")
    print('='*60)
    
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    
    print(f"   Passed: {passed_count}/{total_count}")
    
    for name, result in results.items():
        status = "[OK]" if result.get("passed") else "[FAIL]"
        print(f"   {status} {name}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能自检验系统")
    parser.add_argument("--project", "-p", help="项目名称，不指定则检验所有项目")
    parser.add_argument("--no-fix", action="store_true", help="只检验不修复")
    parser.add_argument("--all", "-a", action="store_true", help="检验所有项目")
    
    args = parser.parse_args()
    
    auto_fix = not args.no_fix
    
    if args.all or not args.project:
        check_all_projects(auto_fix=auto_fix)
    else:
        check_project(args.project, auto_fix=auto_fix)


智能自检验系统 - 主控制器
自动验证、自动修复、循环直到通过
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_validator import OrderValidator
from fixers.order_fixer import OrderFixer


class AutoChecker:
    """
    自动检验器
    验证 -> 修复 -> 再验证 -> 循环直到通过或达到最大次数
    """
    
    def __init__(self, project_path: str, max_iterations: int = 3):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.max_iterations = max_iterations
        self.results_log = []
    
    def run(self, auto_fix: bool = True) -> dict:
        """
        运行自动检验
        
        Args:
            auto_fix: 是否自动修复发现的问题
        
        Returns:
            {
                "passed": bool,
                "iterations": int,
                "fixes_applied": int,
                "final_issues": [],
                "log": []
            }
        """
        print(f"\n{'='*60}")
        print(f"[AUTO-CHECK] Smart Validation System")
        print(f"   Project: {self.project_name}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Auto fix: {'Yes' if auto_fix else 'No'}")
        print('='*60)
        
        total_fixes = 0
        final_result = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Round {iteration}/{self.max_iterations}] Validating...")
            print('-'*40)
            
            # 验证
            validator = OrderValidator(self.project_path)
            result = validator.validate()
            
            self.results_log.append({
                "iteration": iteration,
                "time": datetime.now().isoformat(),
                "passed": result["passed"],
                "issues_count": len(result["issues"])
            })
            
            if result["passed"]:
                print(f"\n[PASSED] Validation passed!")
                final_result = result
                break
            
            # 有问题，尝试修复
            if auto_fix and result["issues"]:
                print(f"\n[FIX] Found {len(result['issues'])} issues, fixing...")
                
                fix_plan = validator.get_fix_plan()
                
                if fix_plan:
                    fixer = OrderFixer(self.project_path)
                    fix_result = fixer.fix(fix_plan, backup=(iteration == 1))
                    
                    total_fixes += fix_result["fixed_count"]
                    
                    if not fix_result["success"]:
                        print(f"\n[WARN] Errors during fix")
                        final_result = result
                        break
                else:
                    print(f"\n[WARN] Cannot generate fix plan")
                    final_result = result
                    break
            else:
                final_result = result
                break
        
        # 如果循环结束还没通过，做最后一次验证
        if final_result is None or not final_result["passed"]:
            print(f"\n[FINAL] Final validation...")
            validator = OrderValidator(self.project_path)
            final_result = validator.validate()
        
        # 生成报告
        report = {
            "passed": final_result["passed"],
            "iterations": len(self.results_log),
            "fixes_applied": total_fixes,
            "final_issues": final_result["issues"],
            "log": self.results_log
        }
        
        self._print_summary(report)
        self._save_report(report)
        
        return report
    
    def _print_summary(self, report: dict):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("[REPORT] Validation Report")
        print('='*60)
        
        status = "[OK] PASSED" if report["passed"] else "[FAIL] NOT PASSED"
        print(f"   Status: {status}")
        print(f"   Iterations: {report['iterations']}")
        print(f"   Files fixed: {report['fixes_applied']}")
        
        if report["final_issues"]:
            print(f"\n   Remaining issues:")
            for issue in report["final_issues"][:3]:
                print(f"     - {issue.get('phase', 'N/A')}: {issue.get('type', 'unknown')}")
        
        print('='*60)
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_path = os.path.join(self.project_path, "validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n[SAVED] Report saved: validation_report.json")


def check_project(project_name: str, auto_fix: bool = True) -> dict:
    """
    便捷函数：检验项目
    
    Args:
        project_name: 项目名称，如 "Calm_Analysis"
        auto_fix: 是否自动修复
    
    Returns:
        检验报告
    """
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    if not os.path.exists(project_path):
        print(f"[ERROR] Project not found: {project_name}")
        return {"passed": False, "error": "项目不存在"}
    
    checker = AutoChecker(project_path)
    return checker.run(auto_fix=auto_fix)


def check_all_projects(auto_fix: bool = True) -> dict:
    """检验所有项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_path = os.path.join(base_path, "projects")
    
    results = {}
    
    for name in os.listdir(projects_path):
        project_path = os.path.join(projects_path, name)
        screens_path = os.path.join(project_path, "Screens")
        
        if os.path.isdir(project_path) and os.path.exists(screens_path):
            print(f"\n\n{'#'*60}")
            print(f"# 检验项目: {name}")
            print('#'*60)
            
            checker = AutoChecker(project_path)
            results[name] = checker.run(auto_fix=auto_fix)
    
    # 汇总
    print(f"\n\n{'='*60}")
    print("[SUMMARY] All Projects Validation Summary")
    print('='*60)
    
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    
    print(f"   Passed: {passed_count}/{total_count}")
    
    for name, result in results.items():
        status = "[OK]" if result.get("passed") else "[FAIL]"
        print(f"   {status} {name}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能自检验系统")
    parser.add_argument("--project", "-p", help="项目名称，不指定则检验所有项目")
    parser.add_argument("--no-fix", action="store_true", help="只检验不修复")
    parser.add_argument("--all", "-a", action="store_true", help="检验所有项目")
    
    args = parser.parse_args()
    
    auto_fix = not args.no_fix
    
    if args.all or not args.project:
        check_all_projects(auto_fix=auto_fix)
    else:
        check_project(args.project, auto_fix=auto_fix)


智能自检验系统 - 主控制器
自动验证、自动修复、循环直到通过
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_validator import OrderValidator
from fixers.order_fixer import OrderFixer


class AutoChecker:
    """
    自动检验器
    验证 -> 修复 -> 再验证 -> 循环直到通过或达到最大次数
    """
    
    def __init__(self, project_path: str, max_iterations: int = 3):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.max_iterations = max_iterations
        self.results_log = []
    
    def run(self, auto_fix: bool = True) -> dict:
        """
        运行自动检验
        
        Args:
            auto_fix: 是否自动修复发现的问题
        
        Returns:
            {
                "passed": bool,
                "iterations": int,
                "fixes_applied": int,
                "final_issues": [],
                "log": []
            }
        """
        print(f"\n{'='*60}")
        print(f"[AUTO-CHECK] Smart Validation System")
        print(f"   Project: {self.project_name}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Auto fix: {'Yes' if auto_fix else 'No'}")
        print('='*60)
        
        total_fixes = 0
        final_result = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Round {iteration}/{self.max_iterations}] Validating...")
            print('-'*40)
            
            # 验证
            validator = OrderValidator(self.project_path)
            result = validator.validate()
            
            self.results_log.append({
                "iteration": iteration,
                "time": datetime.now().isoformat(),
                "passed": result["passed"],
                "issues_count": len(result["issues"])
            })
            
            if result["passed"]:
                print(f"\n[PASSED] Validation passed!")
                final_result = result
                break
            
            # 有问题，尝试修复
            if auto_fix and result["issues"]:
                print(f"\n[FIX] Found {len(result['issues'])} issues, fixing...")
                
                fix_plan = validator.get_fix_plan()
                
                if fix_plan:
                    fixer = OrderFixer(self.project_path)
                    fix_result = fixer.fix(fix_plan, backup=(iteration == 1))
                    
                    total_fixes += fix_result["fixed_count"]
                    
                    if not fix_result["success"]:
                        print(f"\n[WARN] Errors during fix")
                        final_result = result
                        break
                else:
                    print(f"\n[WARN] Cannot generate fix plan")
                    final_result = result
                    break
            else:
                final_result = result
                break
        
        # 如果循环结束还没通过，做最后一次验证
        if final_result is None or not final_result["passed"]:
            print(f"\n[FINAL] Final validation...")
            validator = OrderValidator(self.project_path)
            final_result = validator.validate()
        
        # 生成报告
        report = {
            "passed": final_result["passed"],
            "iterations": len(self.results_log),
            "fixes_applied": total_fixes,
            "final_issues": final_result["issues"],
            "log": self.results_log
        }
        
        self._print_summary(report)
        self._save_report(report)
        
        return report
    
    def _print_summary(self, report: dict):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("[REPORT] Validation Report")
        print('='*60)
        
        status = "[OK] PASSED" if report["passed"] else "[FAIL] NOT PASSED"
        print(f"   Status: {status}")
        print(f"   Iterations: {report['iterations']}")
        print(f"   Files fixed: {report['fixes_applied']}")
        
        if report["final_issues"]:
            print(f"\n   Remaining issues:")
            for issue in report["final_issues"][:3]:
                print(f"     - {issue.get('phase', 'N/A')}: {issue.get('type', 'unknown')}")
        
        print('='*60)
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_path = os.path.join(self.project_path, "validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n[SAVED] Report saved: validation_report.json")


def check_project(project_name: str, auto_fix: bool = True) -> dict:
    """
    便捷函数：检验项目
    
    Args:
        project_name: 项目名称，如 "Calm_Analysis"
        auto_fix: 是否自动修复
    
    Returns:
        检验报告
    """
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    if not os.path.exists(project_path):
        print(f"[ERROR] Project not found: {project_name}")
        return {"passed": False, "error": "项目不存在"}
    
    checker = AutoChecker(project_path)
    return checker.run(auto_fix=auto_fix)


def check_all_projects(auto_fix: bool = True) -> dict:
    """检验所有项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_path = os.path.join(base_path, "projects")
    
    results = {}
    
    for name in os.listdir(projects_path):
        project_path = os.path.join(projects_path, name)
        screens_path = os.path.join(project_path, "Screens")
        
        if os.path.isdir(project_path) and os.path.exists(screens_path):
            print(f"\n\n{'#'*60}")
            print(f"# 检验项目: {name}")
            print('#'*60)
            
            checker = AutoChecker(project_path)
            results[name] = checker.run(auto_fix=auto_fix)
    
    # 汇总
    print(f"\n\n{'='*60}")
    print("[SUMMARY] All Projects Validation Summary")
    print('='*60)
    
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    
    print(f"   Passed: {passed_count}/{total_count}")
    
    for name, result in results.items():
        status = "[OK]" if result.get("passed") else "[FAIL]"
        print(f"   {status} {name}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能自检验系统")
    parser.add_argument("--project", "-p", help="项目名称，不指定则检验所有项目")
    parser.add_argument("--no-fix", action="store_true", help="只检验不修复")
    parser.add_argument("--all", "-a", action="store_true", help="检验所有项目")
    
    args = parser.parse_args()
    
    auto_fix = not args.no_fix
    
    if args.all or not args.project:
        check_all_projects(auto_fix=auto_fix)
    else:
        check_project(args.project, auto_fix=auto_fix)


智能自检验系统 - 主控制器
自动验证、自动修复、循环直到通过
"""

import os
import sys
import json
import time
from datetime import datetime

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from order_validator import OrderValidator
from fixers.order_fixer import OrderFixer


class AutoChecker:
    """
    自动检验器
    验证 -> 修复 -> 再验证 -> 循环直到通过或达到最大次数
    """
    
    def __init__(self, project_path: str, max_iterations: int = 3):
        self.project_path = project_path
        self.project_name = os.path.basename(project_path)
        self.max_iterations = max_iterations
        self.results_log = []
    
    def run(self, auto_fix: bool = True) -> dict:
        """
        运行自动检验
        
        Args:
            auto_fix: 是否自动修复发现的问题
        
        Returns:
            {
                "passed": bool,
                "iterations": int,
                "fixes_applied": int,
                "final_issues": [],
                "log": []
            }
        """
        print(f"\n{'='*60}")
        print(f"[AUTO-CHECK] Smart Validation System")
        print(f"   Project: {self.project_name}")
        print(f"   Max iterations: {self.max_iterations}")
        print(f"   Auto fix: {'Yes' if auto_fix else 'No'}")
        print('='*60)
        
        total_fixes = 0
        final_result = None
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[Round {iteration}/{self.max_iterations}] Validating...")
            print('-'*40)
            
            # 验证
            validator = OrderValidator(self.project_path)
            result = validator.validate()
            
            self.results_log.append({
                "iteration": iteration,
                "time": datetime.now().isoformat(),
                "passed": result["passed"],
                "issues_count": len(result["issues"])
            })
            
            if result["passed"]:
                print(f"\n[PASSED] Validation passed!")
                final_result = result
                break
            
            # 有问题，尝试修复
            if auto_fix and result["issues"]:
                print(f"\n[FIX] Found {len(result['issues'])} issues, fixing...")
                
                fix_plan = validator.get_fix_plan()
                
                if fix_plan:
                    fixer = OrderFixer(self.project_path)
                    fix_result = fixer.fix(fix_plan, backup=(iteration == 1))
                    
                    total_fixes += fix_result["fixed_count"]
                    
                    if not fix_result["success"]:
                        print(f"\n[WARN] Errors during fix")
                        final_result = result
                        break
                else:
                    print(f"\n[WARN] Cannot generate fix plan")
                    final_result = result
                    break
            else:
                final_result = result
                break
        
        # 如果循环结束还没通过，做最后一次验证
        if final_result is None or not final_result["passed"]:
            print(f"\n[FINAL] Final validation...")
            validator = OrderValidator(self.project_path)
            final_result = validator.validate()
        
        # 生成报告
        report = {
            "passed": final_result["passed"],
            "iterations": len(self.results_log),
            "fixes_applied": total_fixes,
            "final_issues": final_result["issues"],
            "log": self.results_log
        }
        
        self._print_summary(report)
        self._save_report(report)
        
        return report
    
    def _print_summary(self, report: dict):
        """打印摘要"""
        print(f"\n{'='*60}")
        print("[REPORT] Validation Report")
        print('='*60)
        
        status = "[OK] PASSED" if report["passed"] else "[FAIL] NOT PASSED"
        print(f"   Status: {status}")
        print(f"   Iterations: {report['iterations']}")
        print(f"   Files fixed: {report['fixes_applied']}")
        
        if report["final_issues"]:
            print(f"\n   Remaining issues:")
            for issue in report["final_issues"][:3]:
                print(f"     - {issue.get('phase', 'N/A')}: {issue.get('type', 'unknown')}")
        
        print('='*60)
    
    def _save_report(self, report: dict):
        """保存报告到文件"""
        report_path = os.path.join(self.project_path, "validation_report.json")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n[SAVED] Report saved: validation_report.json")


def check_project(project_name: str, auto_fix: bool = True) -> dict:
    """
    便捷函数：检验项目
    
    Args:
        project_name: 项目名称，如 "Calm_Analysis"
        auto_fix: 是否自动修复
    
    Returns:
        检验报告
    """
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    if not os.path.exists(project_path):
        print(f"[ERROR] Project not found: {project_name}")
        return {"passed": False, "error": "项目不存在"}
    
    checker = AutoChecker(project_path)
    return checker.run(auto_fix=auto_fix)


def check_all_projects(auto_fix: bool = True) -> dict:
    """检验所有项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    projects_path = os.path.join(base_path, "projects")
    
    results = {}
    
    for name in os.listdir(projects_path):
        project_path = os.path.join(projects_path, name)
        screens_path = os.path.join(project_path, "Screens")
        
        if os.path.isdir(project_path) and os.path.exists(screens_path):
            print(f"\n\n{'#'*60}")
            print(f"# 检验项目: {name}")
            print('#'*60)
            
            checker = AutoChecker(project_path)
            results[name] = checker.run(auto_fix=auto_fix)
    
    # 汇总
    print(f"\n\n{'='*60}")
    print("[SUMMARY] All Projects Validation Summary")
    print('='*60)
    
    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    
    print(f"   Passed: {passed_count}/{total_count}")
    
    for name, result in results.items():
        status = "[OK]" if result.get("passed") else "[FAIL]"
        print(f"   {status} {name}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="智能自检验系统")
    parser.add_argument("--project", "-p", help="项目名称，不指定则检验所有项目")
    parser.add_argument("--no-fix", action="store_true", help="只检验不修复")
    parser.add_argument("--all", "-a", action="store_true", help="检验所有项目")
    
    args = parser.parse_args()
    
    auto_fix = not args.no_fix
    
    if args.all or not args.project:
        check_all_projects(auto_fix=auto_fix)
    else:
        check_project(args.project, auto_fix=auto_fix)

