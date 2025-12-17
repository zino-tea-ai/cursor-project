# -*- coding: utf-8 -*-
"""
顺序修复器
根据验证结果自动修复文件顺序
"""

import os
import shutil
import json
from typing import List, Dict


class OrderFixer:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.screens_path = os.path.join(project_path, "Screens")
        self.backup_path = os.path.join(project_path, "_backup_screens")
        
    def fix(self, fix_plan: List[dict], backup: bool = True) -> dict:
        """
        执行修复计划
        
        Args:
            fix_plan: 来自OrderValidator.get_fix_plan()的修复计划
            backup: 是否备份原文件
        
        Returns:
            {
                "success": bool,
                "fixed_count": int,
                "errors": []
            }
        """
        if not fix_plan:
            return {"success": True, "fixed_count": 0, "errors": []}
        
        print(f"\n[FIX] Fixing {len(fix_plan)} files...")
        
        # 1. 备份
        if backup:
            self._create_backup()
        
        # 2. 使用临时文件名避免冲突
        temp_renames = []
        errors = []
        
        # 第一轮：重命名为临时文件名
        print("[FIX] Round 1: Rename to temp names...")
        for item in fix_plan:
            old_path = os.path.join(self.screens_path, item["from"])
            temp_name = f"_temp_{item['from']}"
            temp_path = os.path.join(self.screens_path, temp_name)
            
            try:
                if os.path.exists(old_path):
                    os.rename(old_path, temp_path)
                    temp_renames.append({
                        "temp_name": temp_name,
                        "final_name": item["to"]
                    })
            except Exception as e:
                errors.append(f"重命名失败 {item['from']}: {e}")
        
        # 第二轮：重命名为最终文件名
        print("[FIX] Round 2: Rename to final names...")
        fixed_count = 0
        
        for item in temp_renames:
            temp_path = os.path.join(self.screens_path, item["temp_name"])
            final_path = os.path.join(self.screens_path, item["final_name"])
            
            try:
                if os.path.exists(temp_path):
                    os.rename(temp_path, final_path)
                    fixed_count += 1
            except Exception as e:
                errors.append(f"最终重命名失败 {item['temp_name']}: {e}")
        
        # 3. 更新相关的JSON文件
        print("[FIX] Updating JSON files...")
        self._update_json_files(fix_plan)
        
        # 4. 更新缩略图文件夹
        print("[FIX] Updating thumbnails...")
        self._update_thumbnails(fix_plan)
        
        success = len(errors) == 0
        
        print(f"\n[FIX] {'Done' if success else 'Partial failure'}: Fixed {fixed_count} files")
        
        if errors:
            print(f"[FIX] Errors: {len(errors)}")
            for err in errors[:5]:
                print(f"       - {err}")
        
        return {
            "success": success,
            "fixed_count": fixed_count,
            "errors": errors
        }
    
    def _create_backup(self):
        """创建备份"""
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
        
        shutil.copytree(self.screens_path, self.backup_path)
        print(f"[FIX] Backup created: {self.backup_path}")
    
    def _update_json_files(self, fix_plan: List[dict]):
        """更新相关的JSON描述文件"""
        
        # 建立重命名映射
        rename_map = {item["from"]: item["to"] for item in fix_plan}
        
        json_files = [
            "descriptions.json",
            "descriptions_ai.json",
            "structured_descriptions.json",
            "ai_analysis.json"
        ]
        
        for json_file in json_files:
            json_path = os.path.join(self.project_path, json_file)
            
            if not os.path.exists(json_path):
                continue
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 如果是字典且键是文件名
                if isinstance(data, dict):
                    new_data = {}
                    updated = False
                    
                    for key, value in data.items():
                        if key in rename_map:
                            new_data[rename_map[key]] = value
                            updated = True
                        else:
                            new_data[key] = value
                    
                    if updated:
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(new_data, f, ensure_ascii=False, indent=2)
                        print(f"       Updated: {json_file}")
                        
            except Exception as e:
                print(f"       Skipped: {json_file} ({e})")
    
    def _update_thumbnails(self, fix_plan: List[dict]):
        """更新缩略图文件夹"""
        
        rename_map = {item["from"]: item["to"] for item in fix_plan}
        
        thumb_folders = [
            "Screens_thumbs",
            "Screens_thumbs_small",
            "Screens_thumbs_medium",
            "Screens_thumbs_large"
        ]
        
        for folder in thumb_folders:
            folder_path = os.path.join(self.project_path, folder)
            
            if not os.path.exists(folder_path):
                continue
            
            # 获取所有相关文件（包括.webp）
            for old_name, new_name in rename_map.items():
                # PNG
                old_png = os.path.join(folder_path, old_name)
                new_png = os.path.join(folder_path, new_name)
                
                # WebP
                old_webp = os.path.join(folder_path, old_name.replace('.png', '.webp'))
                new_webp = os.path.join(folder_path, new_name.replace('.png', '.webp'))
                
                # 使用临时名称避免冲突
                for old_path, new_path in [(old_png, new_png), (old_webp, new_webp)]:
                    if os.path.exists(old_path):
                        temp_path = old_path + ".temp"
                        try:
                            os.rename(old_path, temp_path)
                            os.rename(temp_path, new_path)
                        except:
                            pass
    
    def restore_backup(self):
        """恢复备份"""
        if os.path.exists(self.backup_path):
            if os.path.exists(self.screens_path):
                shutil.rmtree(self.screens_path)
            shutil.copytree(self.backup_path, self.screens_path)
            print("[FIX] Restored from backup")
            return True
        else:
            print("[FIX] No backup found")
            return False


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from order_validator import OrderValidator
    except ImportError:
        from validators.order_validator import OrderValidator
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试修复器: {project}")
    print('='*60)
    
    # 先验证
    validator = OrderValidator(project_path)
    result = validator.validate()
    
    if not result["passed"]:
        # 获取修复计划
        fix_plan = validator.get_fix_plan()
        print(f"\n修复计划: {len(fix_plan)} 个文件需要重命名")
        
        for item in fix_plan[:5]:
            print(f"  {item['from']} -> {item['to']}")
        
        if len(fix_plan) > 5:
            print(f"  ... 还有 {len(fix_plan) - 5} 个")
        
        # 询问是否执行
        confirm = input("\n是否执行修复? (y/n): ")
        if confirm.lower() == 'y':
            fixer = OrderFixer(project_path)
            fixer.fix(fix_plan)
    else:
        print("\n无需修复，顺序正确！")


顺序修复器
根据验证结果自动修复文件顺序
"""

import os
import shutil
import json
from typing import List, Dict


class OrderFixer:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.screens_path = os.path.join(project_path, "Screens")
        self.backup_path = os.path.join(project_path, "_backup_screens")
        
    def fix(self, fix_plan: List[dict], backup: bool = True) -> dict:
        """
        执行修复计划
        
        Args:
            fix_plan: 来自OrderValidator.get_fix_plan()的修复计划
            backup: 是否备份原文件
        
        Returns:
            {
                "success": bool,
                "fixed_count": int,
                "errors": []
            }
        """
        if not fix_plan:
            return {"success": True, "fixed_count": 0, "errors": []}
        
        print(f"\n[FIX] Fixing {len(fix_plan)} files...")
        
        # 1. 备份
        if backup:
            self._create_backup()
        
        # 2. 使用临时文件名避免冲突
        temp_renames = []
        errors = []
        
        # 第一轮：重命名为临时文件名
        print("[FIX] Round 1: Rename to temp names...")
        for item in fix_plan:
            old_path = os.path.join(self.screens_path, item["from"])
            temp_name = f"_temp_{item['from']}"
            temp_path = os.path.join(self.screens_path, temp_name)
            
            try:
                if os.path.exists(old_path):
                    os.rename(old_path, temp_path)
                    temp_renames.append({
                        "temp_name": temp_name,
                        "final_name": item["to"]
                    })
            except Exception as e:
                errors.append(f"重命名失败 {item['from']}: {e}")
        
        # 第二轮：重命名为最终文件名
        print("[FIX] Round 2: Rename to final names...")
        fixed_count = 0
        
        for item in temp_renames:
            temp_path = os.path.join(self.screens_path, item["temp_name"])
            final_path = os.path.join(self.screens_path, item["final_name"])
            
            try:
                if os.path.exists(temp_path):
                    os.rename(temp_path, final_path)
                    fixed_count += 1
            except Exception as e:
                errors.append(f"最终重命名失败 {item['temp_name']}: {e}")
        
        # 3. 更新相关的JSON文件
        print("[FIX] Updating JSON files...")
        self._update_json_files(fix_plan)
        
        # 4. 更新缩略图文件夹
        print("[FIX] Updating thumbnails...")
        self._update_thumbnails(fix_plan)
        
        success = len(errors) == 0
        
        print(f"\n[FIX] {'Done' if success else 'Partial failure'}: Fixed {fixed_count} files")
        
        if errors:
            print(f"[FIX] Errors: {len(errors)}")
            for err in errors[:5]:
                print(f"       - {err}")
        
        return {
            "success": success,
            "fixed_count": fixed_count,
            "errors": errors
        }
    
    def _create_backup(self):
        """创建备份"""
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
        
        shutil.copytree(self.screens_path, self.backup_path)
        print(f"[FIX] Backup created: {self.backup_path}")
    
    def _update_json_files(self, fix_plan: List[dict]):
        """更新相关的JSON描述文件"""
        
        # 建立重命名映射
        rename_map = {item["from"]: item["to"] for item in fix_plan}
        
        json_files = [
            "descriptions.json",
            "descriptions_ai.json",
            "structured_descriptions.json",
            "ai_analysis.json"
        ]
        
        for json_file in json_files:
            json_path = os.path.join(self.project_path, json_file)
            
            if not os.path.exists(json_path):
                continue
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 如果是字典且键是文件名
                if isinstance(data, dict):
                    new_data = {}
                    updated = False
                    
                    for key, value in data.items():
                        if key in rename_map:
                            new_data[rename_map[key]] = value
                            updated = True
                        else:
                            new_data[key] = value
                    
                    if updated:
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(new_data, f, ensure_ascii=False, indent=2)
                        print(f"       Updated: {json_file}")
                        
            except Exception as e:
                print(f"       Skipped: {json_file} ({e})")
    
    def _update_thumbnails(self, fix_plan: List[dict]):
        """更新缩略图文件夹"""
        
        rename_map = {item["from"]: item["to"] for item in fix_plan}
        
        thumb_folders = [
            "Screens_thumbs",
            "Screens_thumbs_small",
            "Screens_thumbs_medium",
            "Screens_thumbs_large"
        ]
        
        for folder in thumb_folders:
            folder_path = os.path.join(self.project_path, folder)
            
            if not os.path.exists(folder_path):
                continue
            
            # 获取所有相关文件（包括.webp）
            for old_name, new_name in rename_map.items():
                # PNG
                old_png = os.path.join(folder_path, old_name)
                new_png = os.path.join(folder_path, new_name)
                
                # WebP
                old_webp = os.path.join(folder_path, old_name.replace('.png', '.webp'))
                new_webp = os.path.join(folder_path, new_name.replace('.png', '.webp'))
                
                # 使用临时名称避免冲突
                for old_path, new_path in [(old_png, new_png), (old_webp, new_webp)]:
                    if os.path.exists(old_path):
                        temp_path = old_path + ".temp"
                        try:
                            os.rename(old_path, temp_path)
                            os.rename(temp_path, new_path)
                        except:
                            pass
    
    def restore_backup(self):
        """恢复备份"""
        if os.path.exists(self.backup_path):
            if os.path.exists(self.screens_path):
                shutil.rmtree(self.screens_path)
            shutil.copytree(self.backup_path, self.screens_path)
            print("[FIX] Restored from backup")
            return True
        else:
            print("[FIX] No backup found")
            return False


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from order_validator import OrderValidator
    except ImportError:
        from validators.order_validator import OrderValidator
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试修复器: {project}")
    print('='*60)
    
    # 先验证
    validator = OrderValidator(project_path)
    result = validator.validate()
    
    if not result["passed"]:
        # 获取修复计划
        fix_plan = validator.get_fix_plan()
        print(f"\n修复计划: {len(fix_plan)} 个文件需要重命名")
        
        for item in fix_plan[:5]:
            print(f"  {item['from']} -> {item['to']}")
        
        if len(fix_plan) > 5:
            print(f"  ... 还有 {len(fix_plan) - 5} 个")
        
        # 询问是否执行
        confirm = input("\n是否执行修复? (y/n): ")
        if confirm.lower() == 'y':
            fixer = OrderFixer(project_path)
            fixer.fix(fix_plan)
    else:
        print("\n无需修复，顺序正确！")


顺序修复器
根据验证结果自动修复文件顺序
"""

import os
import shutil
import json
from typing import List, Dict


class OrderFixer:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.screens_path = os.path.join(project_path, "Screens")
        self.backup_path = os.path.join(project_path, "_backup_screens")
        
    def fix(self, fix_plan: List[dict], backup: bool = True) -> dict:
        """
        执行修复计划
        
        Args:
            fix_plan: 来自OrderValidator.get_fix_plan()的修复计划
            backup: 是否备份原文件
        
        Returns:
            {
                "success": bool,
                "fixed_count": int,
                "errors": []
            }
        """
        if not fix_plan:
            return {"success": True, "fixed_count": 0, "errors": []}
        
        print(f"\n[FIX] Fixing {len(fix_plan)} files...")
        
        # 1. 备份
        if backup:
            self._create_backup()
        
        # 2. 使用临时文件名避免冲突
        temp_renames = []
        errors = []
        
        # 第一轮：重命名为临时文件名
        print("[FIX] Round 1: Rename to temp names...")
        for item in fix_plan:
            old_path = os.path.join(self.screens_path, item["from"])
            temp_name = f"_temp_{item['from']}"
            temp_path = os.path.join(self.screens_path, temp_name)
            
            try:
                if os.path.exists(old_path):
                    os.rename(old_path, temp_path)
                    temp_renames.append({
                        "temp_name": temp_name,
                        "final_name": item["to"]
                    })
            except Exception as e:
                errors.append(f"重命名失败 {item['from']}: {e}")
        
        # 第二轮：重命名为最终文件名
        print("[FIX] Round 2: Rename to final names...")
        fixed_count = 0
        
        for item in temp_renames:
            temp_path = os.path.join(self.screens_path, item["temp_name"])
            final_path = os.path.join(self.screens_path, item["final_name"])
            
            try:
                if os.path.exists(temp_path):
                    os.rename(temp_path, final_path)
                    fixed_count += 1
            except Exception as e:
                errors.append(f"最终重命名失败 {item['temp_name']}: {e}")
        
        # 3. 更新相关的JSON文件
        print("[FIX] Updating JSON files...")
        self._update_json_files(fix_plan)
        
        # 4. 更新缩略图文件夹
        print("[FIX] Updating thumbnails...")
        self._update_thumbnails(fix_plan)
        
        success = len(errors) == 0
        
        print(f"\n[FIX] {'Done' if success else 'Partial failure'}: Fixed {fixed_count} files")
        
        if errors:
            print(f"[FIX] Errors: {len(errors)}")
            for err in errors[:5]:
                print(f"       - {err}")
        
        return {
            "success": success,
            "fixed_count": fixed_count,
            "errors": errors
        }
    
    def _create_backup(self):
        """创建备份"""
        if os.path.exists(self.backup_path):
            shutil.rmtree(self.backup_path)
        
        shutil.copytree(self.screens_path, self.backup_path)
        print(f"[FIX] Backup created: {self.backup_path}")
    
    def _update_json_files(self, fix_plan: List[dict]):
        """更新相关的JSON描述文件"""
        
        # 建立重命名映射
        rename_map = {item["from"]: item["to"] for item in fix_plan}
        
        json_files = [
            "descriptions.json",
            "descriptions_ai.json",
            "structured_descriptions.json",
            "ai_analysis.json"
        ]
        
        for json_file in json_files:
            json_path = os.path.join(self.project_path, json_file)
            
            if not os.path.exists(json_path):
                continue
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 如果是字典且键是文件名
                if isinstance(data, dict):
                    new_data = {}
                    updated = False
                    
                    for key, value in data.items():
                        if key in rename_map:
                            new_data[rename_map[key]] = value
                            updated = True
                        else:
                            new_data[key] = value
                    
                    if updated:
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(new_data, f, ensure_ascii=False, indent=2)
                        print(f"       Updated: {json_file}")
                        
            except Exception as e:
                print(f"       Skipped: {json_file} ({e})")
    
    def _update_thumbnails(self, fix_plan: List[dict]):
        """更新缩略图文件夹"""
        
        rename_map = {item["from"]: item["to"] for item in fix_plan}
        
        thumb_folders = [
            "Screens_thumbs",
            "Screens_thumbs_small",
            "Screens_thumbs_medium",
            "Screens_thumbs_large"
        ]
        
        for folder in thumb_folders:
            folder_path = os.path.join(self.project_path, folder)
            
            if not os.path.exists(folder_path):
                continue
            
            # 获取所有相关文件（包括.webp）
            for old_name, new_name in rename_map.items():
                # PNG
                old_png = os.path.join(folder_path, old_name)
                new_png = os.path.join(folder_path, new_name)
                
                # WebP
                old_webp = os.path.join(folder_path, old_name.replace('.png', '.webp'))
                new_webp = os.path.join(folder_path, new_name.replace('.png', '.webp'))
                
                # 使用临时名称避免冲突
                for old_path, new_path in [(old_png, new_png), (old_webp, new_webp)]:
                    if os.path.exists(old_path):
                        temp_path = old_path + ".temp"
                        try:
                            os.rename(old_path, temp_path)
                            os.rename(temp_path, new_path)
                        except:
                            pass
    
    def restore_backup(self):
        """恢复备份"""
        if os.path.exists(self.backup_path):
            if os.path.exists(self.screens_path):
                shutil.rmtree(self.screens_path)
            shutil.copytree(self.backup_path, self.screens_path)
            print("[FIX] Restored from backup")
            return True
        else:
            print("[FIX] No backup found")
            return False


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from order_validator import OrderValidator
    except ImportError:
        from validators.order_validator import OrderValidator
    
    project = sys.argv[1] if len(sys.argv) > 1 else "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试修复器: {project}")
    print('='*60)
    
    # 先验证
    validator = OrderValidator(project_path)
    result = validator.validate()
    
    if not result["passed"]:
        # 获取修复计划
        fix_plan = validator.get_fix_plan()
        print(f"\n修复计划: {len(fix_plan)} 个文件需要重命名")
        
        for item in fix_plan[:5]:
            print(f"  {item['from']} -> {item['to']}")
        
        if len(fix_plan) > 5:
            print(f"  ... 还有 {len(fix_plan) - 5} 个")
        
        # 询问是否执行
        confirm = input("\n是否执行修复? (y/n): ")
        if confirm.lower() == 'y':
            fixer = OrderFixer(project_path)
            fixer.fix(fix_plan)
    else:
        print("\n无需修复，顺序正确！")

