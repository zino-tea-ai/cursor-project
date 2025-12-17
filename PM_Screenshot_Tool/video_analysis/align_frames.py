# -*- coding: utf-8 -*-
"""
视频帧与截图对齐
将视频关键帧分析结果与静态截图进行匹配对齐
"""

import os
import sys
import json
import base64
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from PIL import Image
import io

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")

# 加载API Key
API_KEYS_FILE = os.path.join(CONFIG_DIR, "api_keys.json")
if os.path.exists(API_KEYS_FILE):
    with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
        api_keys = json.load(f)
        for key, value in api_keys.items():
            if value and not os.environ.get(key):
                os.environ[key] = value


def compute_image_hash(image_path, hash_size=16):
    """
    计算图像的感知哈希
    """
    if not CV2_AVAILABLE:
        return None
    
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    
    # 缩放到统一大小
    resized = cv2.resize(img, (hash_size + 1, hash_size))
    
    # 计算差异哈希
    diff = resized[:, 1:] > resized[:, :-1]
    return diff.flatten()


def compute_similarity(hash1, hash2):
    """
    计算两个哈希的相似度
    """
    if hash1 is None or hash2 is None:
        return 0
    return 1 - (np.sum(hash1 != hash2) / len(hash1))


def align_by_visual_similarity(frames_dir, screens_dir, threshold=0.7):
    """
    基于视觉相似度对齐帧与截图
    
    Returns:
        对齐结果字典
    """
    alignments = {}
    
    # 获取所有帧和截图
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    screens = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')])
    
    print(f"[ALIGN] {len(frames)} frames vs {len(screens)} screenshots")
    
    # 计算所有截图的哈希
    screen_hashes = {}
    for screen in screens:
        screen_path = os.path.join(screens_dir, screen)
        screen_hashes[screen] = compute_image_hash(screen_path)
    
    # 对每个帧找最相似的截图
    for frame in frames:
        frame_path = os.path.join(frames_dir, frame)
        frame_hash = compute_image_hash(frame_path)
        
        best_match = None
        best_similarity = 0
        
        for screen, screen_hash in screen_hashes.items():
            similarity = compute_similarity(frame_hash, screen_hash)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = screen
        
        if best_similarity >= threshold:
            alignments[frame] = {
                "matched_screen": best_match,
                "similarity": round(best_similarity, 3),
                "method": "visual_hash"
            }
        else:
            alignments[frame] = {
                "matched_screen": None,
                "similarity": round(best_similarity, 3),
                "method": "visual_hash",
                "note": "No match above threshold"
            }
    
    return alignments


def align_with_ai(frames_dir, screens_dir, frame_analysis, client, sample_size=5):
    """
    使用AI进行更精确的对齐（抽样验证）
    """
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    screens = sorted([f for f in os.listdir(screens_dir) if f.endswith('.png')])
    
    # 随机抽取样本进行AI验证
    import random
    sample_frames = random.sample(frames, min(sample_size, len(frames)))
    
    ai_alignments = {}
    
    for frame in sample_frames:
        frame_path = os.path.join(frames_dir, frame)
        frame_info = frame_analysis.get(frame, {})
        
        # 构建提示词
        prompt = f"""我有一个视频帧需要与一组静态截图匹配。

视频帧信息：
- Stage: {frame_info.get('stage', 'Unknown')}
- Module: {frame_info.get('module', 'Unknown')}
- Feature: {frame_info.get('feature', 'Unknown')}
- 描述: {frame_info.get('description_cn', 'Unknown')}

静态截图列表（按顺序）：
{', '.join(screens[:30])}...（共{len(screens)}张）

请根据视频帧的内容，判断它最可能对应哪张静态截图。
只需回答截图文件名，例如：Screen_015.png"""

        try:
            with open(frame_path, "rb") as f:
                image_data = base64.standard_b64encode(f.read()).decode("utf-8")
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            result = response.content[0].text.strip()
            
            # 提取文件名
            for screen in screens:
                if screen in result:
                    ai_alignments[frame] = {
                        "matched_screen": screen,
                        "method": "ai_vision",
                        "raw_response": result
                    }
                    break
            
            if frame not in ai_alignments:
                ai_alignments[frame] = {
                    "matched_screen": None,
                    "method": "ai_vision",
                    "raw_response": result
                }
                
        except Exception as e:
            print(f"[ERROR] AI alignment failed for {frame}: {e}")
            ai_alignments[frame] = {"error": str(e)}
    
    return ai_alignments


def merge_analysis_to_screenshots(project_dir, alignments, frame_analysis):
    """
    将视频帧分析结果合并到截图数据中
    """
    ai_file = os.path.join(project_dir, "ai_analysis.json")
    
    if not os.path.exists(ai_file):
        print(f"[WARN] ai_analysis.json not found")
        return
    
    with open(ai_file, 'r', encoding='utf-8') as f:
        ai_data = json.load(f)
    
    results = ai_data.get("results", {})
    updated_count = 0
    
    for frame, alignment in alignments.items():
        matched_screen = alignment.get("matched_screen")
        if not matched_screen or matched_screen not in results:
            continue
        
        frame_info = frame_analysis.get(frame, {})
        
        # 补充视频帧信息
        results[matched_screen]["video_frame"] = frame
        results[matched_screen]["video_timestamp"] = frame_info.get("timestamp")
        
        # 如果视频分析有更高置信度，更新分类
        if frame_info.get("confidence", 0) > results[matched_screen].get("confidence", 0):
            if frame_info.get("stage"):
                results[matched_screen]["stage"] = frame_info["stage"]
            if frame_info.get("module"):
                results[matched_screen]["module"] = frame_info["module"]
            if frame_info.get("feature"):
                results[matched_screen]["feature"] = frame_info["feature"]
            results[matched_screen]["video_enhanced"] = True
        
        updated_count += 1
    
    ai_data["results"] = results
    ai_data["video_alignment_at"] = datetime.now().isoformat() if 'datetime' in dir() else "updated"
    
    with open(ai_file, 'w', encoding='utf-8') as f:
        json.dump(ai_data, f, ensure_ascii=False, indent=2)
    
    print(f"[MERGE] Updated {updated_count} screenshots with video data")


def main():
    """主函数"""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="视频帧与截图对齐")
    parser.add_argument("--project", default="Cal_AI_-_Calorie_Tracker_Analysis", help="项目名称")
    parser.add_argument("--threshold", type=float, default=0.7, help="相似度阈值")
    parser.add_argument("--use-ai", action="store_true", help="使用AI辅助对齐")
    
    args = parser.parse_args()
    
    # 设置路径
    project_dir = os.path.join(PROJECTS_DIR, args.project)
    frames_dir = os.path.join(project_dir, "video_frames")
    screens_dir = os.path.join(project_dir, "Screens")
    frame_analysis_file = os.path.join(project_dir, "keyframe_analysis.json")
    output_file = os.path.join(project_dir, "video_alignment.json")
    
    print("=" * 60)
    print("视频帧与截图对齐")
    print("=" * 60)
    print(f"项目: {args.project}")
    print(f"帧目录: {frames_dir}")
    print(f"截图目录: {screens_dir}")
    print("=" * 60)
    
    # 检查目录
    if not os.path.exists(frames_dir):
        print(f"[ERROR] Frames directory not found: {frames_dir}")
        print("请先运行 analyze_keyframes.py 提取关键帧")
        return
    
    if not os.path.exists(screens_dir):
        print(f"[ERROR] Screens directory not found: {screens_dir}")
        return
    
    # 加载帧分析结果
    frame_analysis = {}
    if os.path.exists(frame_analysis_file):
        with open(frame_analysis_file, 'r', encoding='utf-8') as f:
            frame_analysis = json.load(f)
        print(f"[LOAD] Loaded {len(frame_analysis)} frame analysis results")
    
    # 步骤1：视觉相似度对齐
    print("\n[Step 1] 基于视觉相似度对齐...")
    alignments = align_by_visual_similarity(frames_dir, screens_dir, args.threshold)
    
    matched = sum(1 for a in alignments.values() if a.get("matched_screen"))
    print(f"[RESULT] 匹配成功: {matched}/{len(alignments)}")
    
    # 步骤2：AI辅助对齐（可选）
    if args.use_ai and ANTHROPIC_AVAILABLE:
        print("\n[Step 2] AI辅助对齐验证...")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)
            ai_alignments = align_with_ai(frames_dir, screens_dir, frame_analysis, client)
            
            # 合并AI结果
            for frame, ai_result in ai_alignments.items():
                if frame in alignments and ai_result.get("matched_screen"):
                    alignments[frame]["ai_verified"] = ai_result
    
    # 保存对齐结果
    alignment_result = {
        "project": args.project,
        "created_at": datetime.now().isoformat(),
        "threshold": args.threshold,
        "total_frames": len(alignments),
        "matched_count": matched,
        "alignments": alignments
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(alignment_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n[SAVE] 对齐结果保存到: {output_file}")
    
    # 步骤3：合并到截图数据
    print("\n[Step 3] 合并视频数据到截图分析...")
    merge_analysis_to_screenshots(project_dir, alignments, frame_analysis)
    
    print("\n[DONE] 对齐完成!")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    main()












