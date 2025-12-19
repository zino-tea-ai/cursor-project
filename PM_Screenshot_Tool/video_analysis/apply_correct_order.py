# -*- coding: utf-8 -*-
"""
应用正确的视频顺序到截图和分析数据
"""

import os
import json
import shutil
from pathlib import Path

def apply_correct_order(project_name="Cal_AI_-_Calorie_Tracker_Analysis"):
    """应用正确的视频顺序"""
    
    base_dir = Path(__file__).parent.parent
    project_dir = base_dir / "projects" / project_name
    screens_dir = project_dir / "screens"
    
    # 读取正确顺序
    order_file = base_dir / "video_analysis" / "calai_correct_order.json"
    with open(order_file, 'r', encoding='utf-8') as f:
        order_data = json.load(f)
    
    correct_order = order_data['correct_order']
    print(f"正确顺序包含 {len(correct_order)} 个截图")
    
    # 创建从原始文件名到新索引的映射
    # 新索引就是视频中出现的顺序
    old_to_new = {}
    for item in correct_order:
        old_name = item['original_file']
        new_idx = item['new_index']
        old_to_new[old_name] = new_idx
    
    # 找出未匹配的截图
    all_screens = set(f for f in os.listdir(screens_dir) if f.endswith('.png'))
    matched = set(old_to_new.keys())
    unmatched = all_screens - matched
    
    # 把未匹配的截图加到末尾
    next_idx = len(correct_order) + 1
    for s in sorted(unmatched):
        old_to_new[s] = next_idx
        next_idx += 1
    
    print(f"总映射: {len(old_to_new)} 个截图")
    
    # 创建临时目录
    temp_dir = project_dir / "screens_temp"
    temp_dir.mkdir(exist_ok=True)
    
    # 复制并重命名截图
    print("\n重命名截图...")
    for old_name, new_idx in old_to_new.items():
        old_path = screens_dir / old_name
        new_name = f"Screen_{new_idx:03d}.png"
        new_path = temp_dir / new_name
        
        if old_path.exists():
            shutil.copy(old_path, new_path)
            print(f"  {old_name} -> {new_name}")
    
    # 备份原始目录
    backup_dir = project_dir / "screens_backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.move(screens_dir, backup_dir)
    
    # 将临时目录改名为正式目录
    shutil.move(temp_dir, screens_dir)
    
    print(f"\n完成！原始截图已备份到: {backup_dir}")
    
    # 更新 AI 分析结果
    ai_analysis_file = project_dir / "ai_analysis.json"
    if ai_analysis_file.exists():
        print("\n更新 AI 分析结果...")
        with open(ai_analysis_file, 'r', encoding='utf-8') as f:
            ai_data = json.load(f)
        
        # 创建新的 results
        old_results = ai_data.get('results', {})
        new_results = {}
        
        for old_name, new_idx in old_to_new.items():
            new_name = f"Screen_{new_idx:03d}.png"
            if old_name in old_results:
                new_results[new_name] = old_results[old_name]
        
        ai_data['results'] = new_results
        ai_data['order_corrected'] = True
        ai_data['order_source'] = 'video_timeline'
        
        with open(ai_analysis_file, 'w', encoding='utf-8') as f:
            json.dump(ai_data, f, ensure_ascii=False, indent=2)
        
        print(f"  更新了 {len(new_results)} 个分析结果")
    
    # 更新 manifest
    manifest_file = project_dir / "manifest.json"
    if manifest_file.exists():
        print("\n更新 manifest...")
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        # 重建 screenshots 列表
        new_screenshots = []
        for new_idx in range(1, len(old_to_new) + 1):
            new_name = f"Screen_{new_idx:03d}.png"
            new_screenshots.append({
                "index": new_idx,
                "filename": new_name,
                "order_source": "video_timeline"
            })
        
        manifest['screenshots'] = new_screenshots
        manifest['order_corrected'] = True
        manifest['total'] = len(new_screenshots)
        
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        
        print(f"  更新了 manifest")
    
    print("\n✅ 顺序修正完成！")
    return True


if __name__ == "__main__":
    apply_correct_order()




































