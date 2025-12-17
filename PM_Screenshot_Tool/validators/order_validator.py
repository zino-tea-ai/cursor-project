# -*- coding: utf-8 -*-
"""
顺序验证器
检查每个分组内的截图是否保持了原始相对顺序
"""

import os
import re
from typing import Dict, List, Tuple
try:
    from .hash_matcher import match_downloads_to_screens, get_original_order
except ImportError:
    from hash_matcher import match_downloads_to_screens, get_original_order


class OrderValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.downloads_path = os.path.join(project_path, "Downloads")
        self.screens_path = os.path.join(project_path, "Screens")
        
        # 建立映射关系
        self.mapping = {}  # Downloads -> Screens
        self.reverse_mapping = {}  # Screens -> Downloads
        self.original_order = []
        self.issues = []
    
    def validate(self) -> dict:
        """
        执行完整验证
        
        Returns:
            {
                "passed": bool,
                "issues": [
                    {"type": "wrong_order", "phase": "02_Welcome", "details": {...}},
                    ...
                ],
                "summary": str
            }
        """
        self.issues = []
        
        print("\n[VALIDATE] Starting order validation...")
        
        # 1. 建立映射
        print("[1/3] Building Downloads-Screens mapping...")
        self.mapping = match_downloads_to_screens(self.project_path)
        
        if not self.mapping:
            return {
                "passed": False,
                "issues": [{"type": "no_mapping", "message": "无法建立映射关系"}],
                "summary": "验证失败：无法匹配文件"
            }
        
        # 建立反向映射
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # 2. 获取原始顺序
        print("[2/3] Getting original order...")
        self.original_order = get_original_order(self.project_path)
        
        # 3. 检查每个分组的顺序
        print("[3/3] Checking order within each phase...")
        self._check_phase_orders()
        
        # 生成结果
        passed = len(self.issues) == 0
        
        result = {
            "passed": passed,
            "issues": self.issues,
            "summary": self._generate_summary()
        }
        
        print(f"\n[RESULT] {'PASSED' if passed else f'FAILED - {len(self.issues)} issues found'}")
        
        return result
    
    def _check_phase_orders(self):
        """检查每个阶段内的顺序"""
        
        # 按阶段分组Screens文件
        phases = {}
        for screen_file in os.listdir(self.screens_path):
            if not screen_file.endswith('.png'):
                continue
            
            # 解析阶段: 02_Welcome_01.png -> 02_Welcome
            parts = screen_file.split('_')
            if len(parts) >= 2:
                phase = f"{parts[0]}_{parts[1]}"
            else:
                phase = "Unknown"
            
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(screen_file)
        
        # 检查每个阶段
        for phase, screen_files in phases.items():
            self._check_single_phase(phase, screen_files)
    
    def _check_single_phase(self, phase: str, screen_files: List[str]):
        """检查单个阶段的顺序"""
        
        # 获取每个文件对应的原始序号
        file_to_original_index = {}
        
        for screen_file in screen_files:
            if screen_file in self.reverse_mapping:
                download_file = self.reverse_mapping[screen_file]
                # Screen_001.png -> 1
                match = re.search(r'Screen_(\d+)\.png', download_file)
                if match:
                    original_index = int(match.group(1))
                    file_to_original_index[screen_file] = original_index
        
        if len(file_to_original_index) < 2:
            return  # 少于2个文件，无需检查顺序
        
        # 按当前命名排序
        current_order = sorted(screen_files)
        
        # 获取对应的原始序号
        current_original_indices = [
            file_to_original_index.get(f, 999999) for f in current_order
        ]
        
        # 检查是否递增（允许有间隔，但必须递增）
        is_sorted = all(
            current_original_indices[i] < current_original_indices[i+1]
            for i in range(len(current_original_indices) - 1)
        )
        
        if not is_sorted:
            # 找出具体哪些顺序错了
            expected_order = sorted(
                screen_files,
                key=lambda f: file_to_original_index.get(f, 999999)
            )
            
            wrong_positions = []
            for i, (current, expected) in enumerate(zip(current_order, expected_order)):
                if current != expected:
                    wrong_positions.append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected,
                        "current_original_idx": file_to_original_index.get(current),
                        "expected_original_idx": file_to_original_index.get(expected)
                    })
            
            self.issues.append({
                "type": "wrong_order",
                "phase": phase,
                "current_order": current_order,
                "expected_order": expected_order,
                "wrong_positions": wrong_positions[:5],  # 只显示前5个
                "total_wrong": len(wrong_positions)
            })
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues:
            return "所有分组的顺序都正确"
        
        summary_lines = [f"发现 {len(self.issues)} 个分组存在顺序问题:"]
        
        for issue in self.issues:
            if issue["type"] == "wrong_order":
                summary_lines.append(
                    f"  - {issue['phase']}: {issue['total_wrong']}个文件顺序错误"
                )
            else:
                summary_lines.append(f"  - {issue.get('message', '未知问题')}")
        
        return "\n".join(summary_lines)
    
    def get_fix_plan(self) -> List[dict]:
        """
        生成修复计划
        
        Returns:
            [
                {"action": "rename", "from": "02_Welcome_03.png", "to": "02_Welcome_01.png"},
                ...
            ]
        """
        fix_plan = []
        
        for issue in self.issues:
            if issue["type"] != "wrong_order":
                continue
            
            phase = issue["phase"]
            expected_order = issue["expected_order"]
            
            # 为这个阶段的所有文件生成新名称
            for new_idx, filename in enumerate(expected_order, 1):
                # 解析原文件名
                parts = filename.split('_')
                if len(parts) >= 3:
                    # 02_Welcome_03.png -> 02_Welcome_01.png (新序号)
                    new_filename = f"{parts[0]}_{parts[1]}_{new_idx:02d}.png"
                    
                    if filename != new_filename:
                        fix_plan.append({
                            "action": "rename",
                            "phase": phase,
                            "from": filename,
                            "to": new_filename,
                            "original_download_idx": self.reverse_mapping.get(filename)
                        })
        
        return fix_plan


def validate_project(project_name: str) -> dict:
    """便捷函数：验证项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    validator = OrderValidator(project_path)
    return validator.validate()


if __name__ == "__main__":
    import sys
    import json
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    print(f"\n{'='*60}")
    print(f"验证项目: {project}")
    print('='*60)
    
    result = validate_project(project)
    
    print(f"\n{'='*60}")
    print("验证结果")
    print('='*60)
    print(result["summary"])
    
    if not result["passed"]:
        print("\n详细问题:")
        for issue in result["issues"]:
            print(f"\n  阶段: {issue.get('phase', 'N/A')}")
            if "wrong_positions" in issue:
                for wp in issue["wrong_positions"][:3]:
                    print(f"    位置{wp['position']}: {wp['current']} 应为 {wp['expected']}")


顺序验证器
检查每个分组内的截图是否保持了原始相对顺序
"""

import os
import re
from typing import Dict, List, Tuple
try:
    from .hash_matcher import match_downloads_to_screens, get_original_order
except ImportError:
    from hash_matcher import match_downloads_to_screens, get_original_order


class OrderValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.downloads_path = os.path.join(project_path, "Downloads")
        self.screens_path = os.path.join(project_path, "Screens")
        
        # 建立映射关系
        self.mapping = {}  # Downloads -> Screens
        self.reverse_mapping = {}  # Screens -> Downloads
        self.original_order = []
        self.issues = []
    
    def validate(self) -> dict:
        """
        执行完整验证
        
        Returns:
            {
                "passed": bool,
                "issues": [
                    {"type": "wrong_order", "phase": "02_Welcome", "details": {...}},
                    ...
                ],
                "summary": str
            }
        """
        self.issues = []
        
        print("\n[VALIDATE] Starting order validation...")
        
        # 1. 建立映射
        print("[1/3] Building Downloads-Screens mapping...")
        self.mapping = match_downloads_to_screens(self.project_path)
        
        if not self.mapping:
            return {
                "passed": False,
                "issues": [{"type": "no_mapping", "message": "无法建立映射关系"}],
                "summary": "验证失败：无法匹配文件"
            }
        
        # 建立反向映射
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # 2. 获取原始顺序
        print("[2/3] Getting original order...")
        self.original_order = get_original_order(self.project_path)
        
        # 3. 检查每个分组的顺序
        print("[3/3] Checking order within each phase...")
        self._check_phase_orders()
        
        # 生成结果
        passed = len(self.issues) == 0
        
        result = {
            "passed": passed,
            "issues": self.issues,
            "summary": self._generate_summary()
        }
        
        print(f"\n[RESULT] {'PASSED' if passed else f'FAILED - {len(self.issues)} issues found'}")
        
        return result
    
    def _check_phase_orders(self):
        """检查每个阶段内的顺序"""
        
        # 按阶段分组Screens文件
        phases = {}
        for screen_file in os.listdir(self.screens_path):
            if not screen_file.endswith('.png'):
                continue
            
            # 解析阶段: 02_Welcome_01.png -> 02_Welcome
            parts = screen_file.split('_')
            if len(parts) >= 2:
                phase = f"{parts[0]}_{parts[1]}"
            else:
                phase = "Unknown"
            
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(screen_file)
        
        # 检查每个阶段
        for phase, screen_files in phases.items():
            self._check_single_phase(phase, screen_files)
    
    def _check_single_phase(self, phase: str, screen_files: List[str]):
        """检查单个阶段的顺序"""
        
        # 获取每个文件对应的原始序号
        file_to_original_index = {}
        
        for screen_file in screen_files:
            if screen_file in self.reverse_mapping:
                download_file = self.reverse_mapping[screen_file]
                # Screen_001.png -> 1
                match = re.search(r'Screen_(\d+)\.png', download_file)
                if match:
                    original_index = int(match.group(1))
                    file_to_original_index[screen_file] = original_index
        
        if len(file_to_original_index) < 2:
            return  # 少于2个文件，无需检查顺序
        
        # 按当前命名排序
        current_order = sorted(screen_files)
        
        # 获取对应的原始序号
        current_original_indices = [
            file_to_original_index.get(f, 999999) for f in current_order
        ]
        
        # 检查是否递增（允许有间隔，但必须递增）
        is_sorted = all(
            current_original_indices[i] < current_original_indices[i+1]
            for i in range(len(current_original_indices) - 1)
        )
        
        if not is_sorted:
            # 找出具体哪些顺序错了
            expected_order = sorted(
                screen_files,
                key=lambda f: file_to_original_index.get(f, 999999)
            )
            
            wrong_positions = []
            for i, (current, expected) in enumerate(zip(current_order, expected_order)):
                if current != expected:
                    wrong_positions.append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected,
                        "current_original_idx": file_to_original_index.get(current),
                        "expected_original_idx": file_to_original_index.get(expected)
                    })
            
            self.issues.append({
                "type": "wrong_order",
                "phase": phase,
                "current_order": current_order,
                "expected_order": expected_order,
                "wrong_positions": wrong_positions[:5],  # 只显示前5个
                "total_wrong": len(wrong_positions)
            })
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues:
            return "所有分组的顺序都正确"
        
        summary_lines = [f"发现 {len(self.issues)} 个分组存在顺序问题:"]
        
        for issue in self.issues:
            if issue["type"] == "wrong_order":
                summary_lines.append(
                    f"  - {issue['phase']}: {issue['total_wrong']}个文件顺序错误"
                )
            else:
                summary_lines.append(f"  - {issue.get('message', '未知问题')}")
        
        return "\n".join(summary_lines)
    
    def get_fix_plan(self) -> List[dict]:
        """
        生成修复计划
        
        Returns:
            [
                {"action": "rename", "from": "02_Welcome_03.png", "to": "02_Welcome_01.png"},
                ...
            ]
        """
        fix_plan = []
        
        for issue in self.issues:
            if issue["type"] != "wrong_order":
                continue
            
            phase = issue["phase"]
            expected_order = issue["expected_order"]
            
            # 为这个阶段的所有文件生成新名称
            for new_idx, filename in enumerate(expected_order, 1):
                # 解析原文件名
                parts = filename.split('_')
                if len(parts) >= 3:
                    # 02_Welcome_03.png -> 02_Welcome_01.png (新序号)
                    new_filename = f"{parts[0]}_{parts[1]}_{new_idx:02d}.png"
                    
                    if filename != new_filename:
                        fix_plan.append({
                            "action": "rename",
                            "phase": phase,
                            "from": filename,
                            "to": new_filename,
                            "original_download_idx": self.reverse_mapping.get(filename)
                        })
        
        return fix_plan


def validate_project(project_name: str) -> dict:
    """便捷函数：验证项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    validator = OrderValidator(project_path)
    return validator.validate()


if __name__ == "__main__":
    import sys
    import json
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    print(f"\n{'='*60}")
    print(f"验证项目: {project}")
    print('='*60)
    
    result = validate_project(project)
    
    print(f"\n{'='*60}")
    print("验证结果")
    print('='*60)
    print(result["summary"])
    
    if not result["passed"]:
        print("\n详细问题:")
        for issue in result["issues"]:
            print(f"\n  阶段: {issue.get('phase', 'N/A')}")
            if "wrong_positions" in issue:
                for wp in issue["wrong_positions"][:3]:
                    print(f"    位置{wp['position']}: {wp['current']} 应为 {wp['expected']}")


顺序验证器
检查每个分组内的截图是否保持了原始相对顺序
"""

import os
import re
from typing import Dict, List, Tuple
try:
    from .hash_matcher import match_downloads_to_screens, get_original_order
except ImportError:
    from hash_matcher import match_downloads_to_screens, get_original_order


class OrderValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.downloads_path = os.path.join(project_path, "Downloads")
        self.screens_path = os.path.join(project_path, "Screens")
        
        # 建立映射关系
        self.mapping = {}  # Downloads -> Screens
        self.reverse_mapping = {}  # Screens -> Downloads
        self.original_order = []
        self.issues = []
    
    def validate(self) -> dict:
        """
        执行完整验证
        
        Returns:
            {
                "passed": bool,
                "issues": [
                    {"type": "wrong_order", "phase": "02_Welcome", "details": {...}},
                    ...
                ],
                "summary": str
            }
        """
        self.issues = []
        
        print("\n[VALIDATE] Starting order validation...")
        
        # 1. 建立映射
        print("[1/3] Building Downloads-Screens mapping...")
        self.mapping = match_downloads_to_screens(self.project_path)
        
        if not self.mapping:
            return {
                "passed": False,
                "issues": [{"type": "no_mapping", "message": "无法建立映射关系"}],
                "summary": "验证失败：无法匹配文件"
            }
        
        # 建立反向映射
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # 2. 获取原始顺序
        print("[2/3] Getting original order...")
        self.original_order = get_original_order(self.project_path)
        
        # 3. 检查每个分组的顺序
        print("[3/3] Checking order within each phase...")
        self._check_phase_orders()
        
        # 生成结果
        passed = len(self.issues) == 0
        
        result = {
            "passed": passed,
            "issues": self.issues,
            "summary": self._generate_summary()
        }
        
        print(f"\n[RESULT] {'PASSED' if passed else f'FAILED - {len(self.issues)} issues found'}")
        
        return result
    
    def _check_phase_orders(self):
        """检查每个阶段内的顺序"""
        
        # 按阶段分组Screens文件
        phases = {}
        for screen_file in os.listdir(self.screens_path):
            if not screen_file.endswith('.png'):
                continue
            
            # 解析阶段: 02_Welcome_01.png -> 02_Welcome
            parts = screen_file.split('_')
            if len(parts) >= 2:
                phase = f"{parts[0]}_{parts[1]}"
            else:
                phase = "Unknown"
            
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(screen_file)
        
        # 检查每个阶段
        for phase, screen_files in phases.items():
            self._check_single_phase(phase, screen_files)
    
    def _check_single_phase(self, phase: str, screen_files: List[str]):
        """检查单个阶段的顺序"""
        
        # 获取每个文件对应的原始序号
        file_to_original_index = {}
        
        for screen_file in screen_files:
            if screen_file in self.reverse_mapping:
                download_file = self.reverse_mapping[screen_file]
                # Screen_001.png -> 1
                match = re.search(r'Screen_(\d+)\.png', download_file)
                if match:
                    original_index = int(match.group(1))
                    file_to_original_index[screen_file] = original_index
        
        if len(file_to_original_index) < 2:
            return  # 少于2个文件，无需检查顺序
        
        # 按当前命名排序
        current_order = sorted(screen_files)
        
        # 获取对应的原始序号
        current_original_indices = [
            file_to_original_index.get(f, 999999) for f in current_order
        ]
        
        # 检查是否递增（允许有间隔，但必须递增）
        is_sorted = all(
            current_original_indices[i] < current_original_indices[i+1]
            for i in range(len(current_original_indices) - 1)
        )
        
        if not is_sorted:
            # 找出具体哪些顺序错了
            expected_order = sorted(
                screen_files,
                key=lambda f: file_to_original_index.get(f, 999999)
            )
            
            wrong_positions = []
            for i, (current, expected) in enumerate(zip(current_order, expected_order)):
                if current != expected:
                    wrong_positions.append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected,
                        "current_original_idx": file_to_original_index.get(current),
                        "expected_original_idx": file_to_original_index.get(expected)
                    })
            
            self.issues.append({
                "type": "wrong_order",
                "phase": phase,
                "current_order": current_order,
                "expected_order": expected_order,
                "wrong_positions": wrong_positions[:5],  # 只显示前5个
                "total_wrong": len(wrong_positions)
            })
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues:
            return "所有分组的顺序都正确"
        
        summary_lines = [f"发现 {len(self.issues)} 个分组存在顺序问题:"]
        
        for issue in self.issues:
            if issue["type"] == "wrong_order":
                summary_lines.append(
                    f"  - {issue['phase']}: {issue['total_wrong']}个文件顺序错误"
                )
            else:
                summary_lines.append(f"  - {issue.get('message', '未知问题')}")
        
        return "\n".join(summary_lines)
    
    def get_fix_plan(self) -> List[dict]:
        """
        生成修复计划
        
        Returns:
            [
                {"action": "rename", "from": "02_Welcome_03.png", "to": "02_Welcome_01.png"},
                ...
            ]
        """
        fix_plan = []
        
        for issue in self.issues:
            if issue["type"] != "wrong_order":
                continue
            
            phase = issue["phase"]
            expected_order = issue["expected_order"]
            
            # 为这个阶段的所有文件生成新名称
            for new_idx, filename in enumerate(expected_order, 1):
                # 解析原文件名
                parts = filename.split('_')
                if len(parts) >= 3:
                    # 02_Welcome_03.png -> 02_Welcome_01.png (新序号)
                    new_filename = f"{parts[0]}_{parts[1]}_{new_idx:02d}.png"
                    
                    if filename != new_filename:
                        fix_plan.append({
                            "action": "rename",
                            "phase": phase,
                            "from": filename,
                            "to": new_filename,
                            "original_download_idx": self.reverse_mapping.get(filename)
                        })
        
        return fix_plan


def validate_project(project_name: str) -> dict:
    """便捷函数：验证项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    validator = OrderValidator(project_path)
    return validator.validate()


if __name__ == "__main__":
    import sys
    import json
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    print(f"\n{'='*60}")
    print(f"验证项目: {project}")
    print('='*60)
    
    result = validate_project(project)
    
    print(f"\n{'='*60}")
    print("验证结果")
    print('='*60)
    print(result["summary"])
    
    if not result["passed"]:
        print("\n详细问题:")
        for issue in result["issues"]:
            print(f"\n  阶段: {issue.get('phase', 'N/A')}")
            if "wrong_positions" in issue:
                for wp in issue["wrong_positions"][:3]:
                    print(f"    位置{wp['position']}: {wp['current']} 应为 {wp['expected']}")


顺序验证器
检查每个分组内的截图是否保持了原始相对顺序
"""

import os
import re
from typing import Dict, List, Tuple
try:
    from .hash_matcher import match_downloads_to_screens, get_original_order
except ImportError:
    from hash_matcher import match_downloads_to_screens, get_original_order


class OrderValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.downloads_path = os.path.join(project_path, "Downloads")
        self.screens_path = os.path.join(project_path, "Screens")
        
        # 建立映射关系
        self.mapping = {}  # Downloads -> Screens
        self.reverse_mapping = {}  # Screens -> Downloads
        self.original_order = []
        self.issues = []
    
    def validate(self) -> dict:
        """
        执行完整验证
        
        Returns:
            {
                "passed": bool,
                "issues": [
                    {"type": "wrong_order", "phase": "02_Welcome", "details": {...}},
                    ...
                ],
                "summary": str
            }
        """
        self.issues = []
        
        print("\n[VALIDATE] Starting order validation...")
        
        # 1. 建立映射
        print("[1/3] Building Downloads-Screens mapping...")
        self.mapping = match_downloads_to_screens(self.project_path)
        
        if not self.mapping:
            return {
                "passed": False,
                "issues": [{"type": "no_mapping", "message": "无法建立映射关系"}],
                "summary": "验证失败：无法匹配文件"
            }
        
        # 建立反向映射
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # 2. 获取原始顺序
        print("[2/3] Getting original order...")
        self.original_order = get_original_order(self.project_path)
        
        # 3. 检查每个分组的顺序
        print("[3/3] Checking order within each phase...")
        self._check_phase_orders()
        
        # 生成结果
        passed = len(self.issues) == 0
        
        result = {
            "passed": passed,
            "issues": self.issues,
            "summary": self._generate_summary()
        }
        
        print(f"\n[RESULT] {'PASSED' if passed else f'FAILED - {len(self.issues)} issues found'}")
        
        return result
    
    def _check_phase_orders(self):
        """检查每个阶段内的顺序"""
        
        # 按阶段分组Screens文件
        phases = {}
        for screen_file in os.listdir(self.screens_path):
            if not screen_file.endswith('.png'):
                continue
            
            # 解析阶段: 02_Welcome_01.png -> 02_Welcome
            parts = screen_file.split('_')
            if len(parts) >= 2:
                phase = f"{parts[0]}_{parts[1]}"
            else:
                phase = "Unknown"
            
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(screen_file)
        
        # 检查每个阶段
        for phase, screen_files in phases.items():
            self._check_single_phase(phase, screen_files)
    
    def _check_single_phase(self, phase: str, screen_files: List[str]):
        """检查单个阶段的顺序"""
        
        # 获取每个文件对应的原始序号
        file_to_original_index = {}
        
        for screen_file in screen_files:
            if screen_file in self.reverse_mapping:
                download_file = self.reverse_mapping[screen_file]
                # Screen_001.png -> 1
                match = re.search(r'Screen_(\d+)\.png', download_file)
                if match:
                    original_index = int(match.group(1))
                    file_to_original_index[screen_file] = original_index
        
        if len(file_to_original_index) < 2:
            return  # 少于2个文件，无需检查顺序
        
        # 按当前命名排序
        current_order = sorted(screen_files)
        
        # 获取对应的原始序号
        current_original_indices = [
            file_to_original_index.get(f, 999999) for f in current_order
        ]
        
        # 检查是否递增（允许有间隔，但必须递增）
        is_sorted = all(
            current_original_indices[i] < current_original_indices[i+1]
            for i in range(len(current_original_indices) - 1)
        )
        
        if not is_sorted:
            # 找出具体哪些顺序错了
            expected_order = sorted(
                screen_files,
                key=lambda f: file_to_original_index.get(f, 999999)
            )
            
            wrong_positions = []
            for i, (current, expected) in enumerate(zip(current_order, expected_order)):
                if current != expected:
                    wrong_positions.append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected,
                        "current_original_idx": file_to_original_index.get(current),
                        "expected_original_idx": file_to_original_index.get(expected)
                    })
            
            self.issues.append({
                "type": "wrong_order",
                "phase": phase,
                "current_order": current_order,
                "expected_order": expected_order,
                "wrong_positions": wrong_positions[:5],  # 只显示前5个
                "total_wrong": len(wrong_positions)
            })
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues:
            return "所有分组的顺序都正确"
        
        summary_lines = [f"发现 {len(self.issues)} 个分组存在顺序问题:"]
        
        for issue in self.issues:
            if issue["type"] == "wrong_order":
                summary_lines.append(
                    f"  - {issue['phase']}: {issue['total_wrong']}个文件顺序错误"
                )
            else:
                summary_lines.append(f"  - {issue.get('message', '未知问题')}")
        
        return "\n".join(summary_lines)
    
    def get_fix_plan(self) -> List[dict]:
        """
        生成修复计划
        
        Returns:
            [
                {"action": "rename", "from": "02_Welcome_03.png", "to": "02_Welcome_01.png"},
                ...
            ]
        """
        fix_plan = []
        
        for issue in self.issues:
            if issue["type"] != "wrong_order":
                continue
            
            phase = issue["phase"]
            expected_order = issue["expected_order"]
            
            # 为这个阶段的所有文件生成新名称
            for new_idx, filename in enumerate(expected_order, 1):
                # 解析原文件名
                parts = filename.split('_')
                if len(parts) >= 3:
                    # 02_Welcome_03.png -> 02_Welcome_01.png (新序号)
                    new_filename = f"{parts[0]}_{parts[1]}_{new_idx:02d}.png"
                    
                    if filename != new_filename:
                        fix_plan.append({
                            "action": "rename",
                            "phase": phase,
                            "from": filename,
                            "to": new_filename,
                            "original_download_idx": self.reverse_mapping.get(filename)
                        })
        
        return fix_plan


def validate_project(project_name: str) -> dict:
    """便捷函数：验证项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    validator = OrderValidator(project_path)
    return validator.validate()


if __name__ == "__main__":
    import sys
    import json
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    print(f"\n{'='*60}")
    print(f"验证项目: {project}")
    print('='*60)
    
    result = validate_project(project)
    
    print(f"\n{'='*60}")
    print("验证结果")
    print('='*60)
    print(result["summary"])
    
    if not result["passed"]:
        print("\n详细问题:")
        for issue in result["issues"]:
            print(f"\n  阶段: {issue.get('phase', 'N/A')}")
            if "wrong_positions" in issue:
                for wp in issue["wrong_positions"][:3]:
                    print(f"    位置{wp['position']}: {wp['current']} 应为 {wp['expected']}")


顺序验证器
检查每个分组内的截图是否保持了原始相对顺序
"""

import os
import re
from typing import Dict, List, Tuple
try:
    from .hash_matcher import match_downloads_to_screens, get_original_order
except ImportError:
    from hash_matcher import match_downloads_to_screens, get_original_order


class OrderValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.downloads_path = os.path.join(project_path, "Downloads")
        self.screens_path = os.path.join(project_path, "Screens")
        
        # 建立映射关系
        self.mapping = {}  # Downloads -> Screens
        self.reverse_mapping = {}  # Screens -> Downloads
        self.original_order = []
        self.issues = []
    
    def validate(self) -> dict:
        """
        执行完整验证
        
        Returns:
            {
                "passed": bool,
                "issues": [
                    {"type": "wrong_order", "phase": "02_Welcome", "details": {...}},
                    ...
                ],
                "summary": str
            }
        """
        self.issues = []
        
        print("\n[VALIDATE] Starting order validation...")
        
        # 1. 建立映射
        print("[1/3] Building Downloads-Screens mapping...")
        self.mapping = match_downloads_to_screens(self.project_path)
        
        if not self.mapping:
            return {
                "passed": False,
                "issues": [{"type": "no_mapping", "message": "无法建立映射关系"}],
                "summary": "验证失败：无法匹配文件"
            }
        
        # 建立反向映射
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # 2. 获取原始顺序
        print("[2/3] Getting original order...")
        self.original_order = get_original_order(self.project_path)
        
        # 3. 检查每个分组的顺序
        print("[3/3] Checking order within each phase...")
        self._check_phase_orders()
        
        # 生成结果
        passed = len(self.issues) == 0
        
        result = {
            "passed": passed,
            "issues": self.issues,
            "summary": self._generate_summary()
        }
        
        print(f"\n[RESULT] {'PASSED' if passed else f'FAILED - {len(self.issues)} issues found'}")
        
        return result
    
    def _check_phase_orders(self):
        """检查每个阶段内的顺序"""
        
        # 按阶段分组Screens文件
        phases = {}
        for screen_file in os.listdir(self.screens_path):
            if not screen_file.endswith('.png'):
                continue
            
            # 解析阶段: 02_Welcome_01.png -> 02_Welcome
            parts = screen_file.split('_')
            if len(parts) >= 2:
                phase = f"{parts[0]}_{parts[1]}"
            else:
                phase = "Unknown"
            
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(screen_file)
        
        # 检查每个阶段
        for phase, screen_files in phases.items():
            self._check_single_phase(phase, screen_files)
    
    def _check_single_phase(self, phase: str, screen_files: List[str]):
        """检查单个阶段的顺序"""
        
        # 获取每个文件对应的原始序号
        file_to_original_index = {}
        
        for screen_file in screen_files:
            if screen_file in self.reverse_mapping:
                download_file = self.reverse_mapping[screen_file]
                # Screen_001.png -> 1
                match = re.search(r'Screen_(\d+)\.png', download_file)
                if match:
                    original_index = int(match.group(1))
                    file_to_original_index[screen_file] = original_index
        
        if len(file_to_original_index) < 2:
            return  # 少于2个文件，无需检查顺序
        
        # 按当前命名排序
        current_order = sorted(screen_files)
        
        # 获取对应的原始序号
        current_original_indices = [
            file_to_original_index.get(f, 999999) for f in current_order
        ]
        
        # 检查是否递增（允许有间隔，但必须递增）
        is_sorted = all(
            current_original_indices[i] < current_original_indices[i+1]
            for i in range(len(current_original_indices) - 1)
        )
        
        if not is_sorted:
            # 找出具体哪些顺序错了
            expected_order = sorted(
                screen_files,
                key=lambda f: file_to_original_index.get(f, 999999)
            )
            
            wrong_positions = []
            for i, (current, expected) in enumerate(zip(current_order, expected_order)):
                if current != expected:
                    wrong_positions.append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected,
                        "current_original_idx": file_to_original_index.get(current),
                        "expected_original_idx": file_to_original_index.get(expected)
                    })
            
            self.issues.append({
                "type": "wrong_order",
                "phase": phase,
                "current_order": current_order,
                "expected_order": expected_order,
                "wrong_positions": wrong_positions[:5],  # 只显示前5个
                "total_wrong": len(wrong_positions)
            })
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues:
            return "所有分组的顺序都正确"
        
        summary_lines = [f"发现 {len(self.issues)} 个分组存在顺序问题:"]
        
        for issue in self.issues:
            if issue["type"] == "wrong_order":
                summary_lines.append(
                    f"  - {issue['phase']}: {issue['total_wrong']}个文件顺序错误"
                )
            else:
                summary_lines.append(f"  - {issue.get('message', '未知问题')}")
        
        return "\n".join(summary_lines)
    
    def get_fix_plan(self) -> List[dict]:
        """
        生成修复计划
        
        Returns:
            [
                {"action": "rename", "from": "02_Welcome_03.png", "to": "02_Welcome_01.png"},
                ...
            ]
        """
        fix_plan = []
        
        for issue in self.issues:
            if issue["type"] != "wrong_order":
                continue
            
            phase = issue["phase"]
            expected_order = issue["expected_order"]
            
            # 为这个阶段的所有文件生成新名称
            for new_idx, filename in enumerate(expected_order, 1):
                # 解析原文件名
                parts = filename.split('_')
                if len(parts) >= 3:
                    # 02_Welcome_03.png -> 02_Welcome_01.png (新序号)
                    new_filename = f"{parts[0]}_{parts[1]}_{new_idx:02d}.png"
                    
                    if filename != new_filename:
                        fix_plan.append({
                            "action": "rename",
                            "phase": phase,
                            "from": filename,
                            "to": new_filename,
                            "original_download_idx": self.reverse_mapping.get(filename)
                        })
        
        return fix_plan


def validate_project(project_name: str) -> dict:
    """便捷函数：验证项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    validator = OrderValidator(project_path)
    return validator.validate()


if __name__ == "__main__":
    import sys
    import json
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    print(f"\n{'='*60}")
    print(f"验证项目: {project}")
    print('='*60)
    
    result = validate_project(project)
    
    print(f"\n{'='*60}")
    print("验证结果")
    print('='*60)
    print(result["summary"])
    
    if not result["passed"]:
        print("\n详细问题:")
        for issue in result["issues"]:
            print(f"\n  阶段: {issue.get('phase', 'N/A')}")
            if "wrong_positions" in issue:
                for wp in issue["wrong_positions"][:3]:
                    print(f"    位置{wp['position']}: {wp['current']} 应为 {wp['expected']}")


顺序验证器
检查每个分组内的截图是否保持了原始相对顺序
"""

import os
import re
from typing import Dict, List, Tuple
try:
    from .hash_matcher import match_downloads_to_screens, get_original_order
except ImportError:
    from hash_matcher import match_downloads_to_screens, get_original_order


class OrderValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.downloads_path = os.path.join(project_path, "Downloads")
        self.screens_path = os.path.join(project_path, "Screens")
        
        # 建立映射关系
        self.mapping = {}  # Downloads -> Screens
        self.reverse_mapping = {}  # Screens -> Downloads
        self.original_order = []
        self.issues = []
    
    def validate(self) -> dict:
        """
        执行完整验证
        
        Returns:
            {
                "passed": bool,
                "issues": [
                    {"type": "wrong_order", "phase": "02_Welcome", "details": {...}},
                    ...
                ],
                "summary": str
            }
        """
        self.issues = []
        
        print("\n[VALIDATE] Starting order validation...")
        
        # 1. 建立映射
        print("[1/3] Building Downloads-Screens mapping...")
        self.mapping = match_downloads_to_screens(self.project_path)
        
        if not self.mapping:
            return {
                "passed": False,
                "issues": [{"type": "no_mapping", "message": "无法建立映射关系"}],
                "summary": "验证失败：无法匹配文件"
            }
        
        # 建立反向映射
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        
        # 2. 获取原始顺序
        print("[2/3] Getting original order...")
        self.original_order = get_original_order(self.project_path)
        
        # 3. 检查每个分组的顺序
        print("[3/3] Checking order within each phase...")
        self._check_phase_orders()
        
        # 生成结果
        passed = len(self.issues) == 0
        
        result = {
            "passed": passed,
            "issues": self.issues,
            "summary": self._generate_summary()
        }
        
        print(f"\n[RESULT] {'PASSED' if passed else f'FAILED - {len(self.issues)} issues found'}")
        
        return result
    
    def _check_phase_orders(self):
        """检查每个阶段内的顺序"""
        
        # 按阶段分组Screens文件
        phases = {}
        for screen_file in os.listdir(self.screens_path):
            if not screen_file.endswith('.png'):
                continue
            
            # 解析阶段: 02_Welcome_01.png -> 02_Welcome
            parts = screen_file.split('_')
            if len(parts) >= 2:
                phase = f"{parts[0]}_{parts[1]}"
            else:
                phase = "Unknown"
            
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(screen_file)
        
        # 检查每个阶段
        for phase, screen_files in phases.items():
            self._check_single_phase(phase, screen_files)
    
    def _check_single_phase(self, phase: str, screen_files: List[str]):
        """检查单个阶段的顺序"""
        
        # 获取每个文件对应的原始序号
        file_to_original_index = {}
        
        for screen_file in screen_files:
            if screen_file in self.reverse_mapping:
                download_file = self.reverse_mapping[screen_file]
                # Screen_001.png -> 1
                match = re.search(r'Screen_(\d+)\.png', download_file)
                if match:
                    original_index = int(match.group(1))
                    file_to_original_index[screen_file] = original_index
        
        if len(file_to_original_index) < 2:
            return  # 少于2个文件，无需检查顺序
        
        # 按当前命名排序
        current_order = sorted(screen_files)
        
        # 获取对应的原始序号
        current_original_indices = [
            file_to_original_index.get(f, 999999) for f in current_order
        ]
        
        # 检查是否递增（允许有间隔，但必须递增）
        is_sorted = all(
            current_original_indices[i] < current_original_indices[i+1]
            for i in range(len(current_original_indices) - 1)
        )
        
        if not is_sorted:
            # 找出具体哪些顺序错了
            expected_order = sorted(
                screen_files,
                key=lambda f: file_to_original_index.get(f, 999999)
            )
            
            wrong_positions = []
            for i, (current, expected) in enumerate(zip(current_order, expected_order)):
                if current != expected:
                    wrong_positions.append({
                        "position": i + 1,
                        "current": current,
                        "expected": expected,
                        "current_original_idx": file_to_original_index.get(current),
                        "expected_original_idx": file_to_original_index.get(expected)
                    })
            
            self.issues.append({
                "type": "wrong_order",
                "phase": phase,
                "current_order": current_order,
                "expected_order": expected_order,
                "wrong_positions": wrong_positions[:5],  # 只显示前5个
                "total_wrong": len(wrong_positions)
            })
    
    def _generate_summary(self) -> str:
        """生成摘要"""
        if not self.issues:
            return "所有分组的顺序都正确"
        
        summary_lines = [f"发现 {len(self.issues)} 个分组存在顺序问题:"]
        
        for issue in self.issues:
            if issue["type"] == "wrong_order":
                summary_lines.append(
                    f"  - {issue['phase']}: {issue['total_wrong']}个文件顺序错误"
                )
            else:
                summary_lines.append(f"  - {issue.get('message', '未知问题')}")
        
        return "\n".join(summary_lines)
    
    def get_fix_plan(self) -> List[dict]:
        """
        生成修复计划
        
        Returns:
            [
                {"action": "rename", "from": "02_Welcome_03.png", "to": "02_Welcome_01.png"},
                ...
            ]
        """
        fix_plan = []
        
        for issue in self.issues:
            if issue["type"] != "wrong_order":
                continue
            
            phase = issue["phase"]
            expected_order = issue["expected_order"]
            
            # 为这个阶段的所有文件生成新名称
            for new_idx, filename in enumerate(expected_order, 1):
                # 解析原文件名
                parts = filename.split('_')
                if len(parts) >= 3:
                    # 02_Welcome_03.png -> 02_Welcome_01.png (新序号)
                    new_filename = f"{parts[0]}_{parts[1]}_{new_idx:02d}.png"
                    
                    if filename != new_filename:
                        fix_plan.append({
                            "action": "rename",
                            "phase": phase,
                            "from": filename,
                            "to": new_filename,
                            "original_download_idx": self.reverse_mapping.get(filename)
                        })
        
        return fix_plan


def validate_project(project_name: str) -> dict:
    """便捷函数：验证项目"""
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project_name)
    
    validator = OrderValidator(project_path)
    return validator.validate()


if __name__ == "__main__":
    import sys
    import json
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    print(f"\n{'='*60}")
    print(f"验证项目: {project}")
    print('='*60)
    
    result = validate_project(project)
    
    print(f"\n{'='*60}")
    print("验证结果")
    print('='*60)
    print(result["summary"])
    
    if not result["passed"]:
        print("\n详细问题:")
        for issue in result["issues"]:
            print(f"\n  阶段: {issue.get('phase', 'N/A')}")
            if "wrong_positions" in issue:
                for wp in issue["wrong_positions"][:3]:
                    print(f"    位置{wp['position']}: {wp['current']} 应为 {wp['expected']}")

