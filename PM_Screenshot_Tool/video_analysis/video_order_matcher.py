# -*- coding: utf-8 -*-
"""
视频顺序匹配器
用视频帧的时间顺序来匹配截图库，生成正确的排序
"""

import cv2
import os
import json
import numpy as np
from pathlib import Path

def compute_similarity(img1, img2):
    """计算两张图片的相似度（使用直方图对比）"""
    # 调整到相同大小
    img1 = cv2.resize(img1, (200, 400))
    img2 = cv2.resize(img2, (200, 400))
    
    # 转换为HSV并计算直方图
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)
    
    hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])
    
    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
    
    # 对比直方图
    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return score


def match_video_to_screenshots(video_path, screens_dir, output_path, interval_sec=2):
    """
    从视频中按时间顺序提取帧，匹配截图库
    
    Args:
        video_path: 视频文件路径
        screens_dir: 截图库目录
        output_path: 输出 JSON 路径
        interval_sec: 提取帧的间隔（秒）
    """
    print(f"Loading video: {video_path}")
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("ERROR: Cannot open video")
        return None
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    print(f"Video info: {fps:.1f} FPS, {total_frames} frames, {duration:.1f}s duration")
    
    # 加载所有截图
    print(f"\nLoading screenshots from: {screens_dir}")
    screenshots = {}
    for f in sorted(os.listdir(screens_dir)):
        if f.endswith('.png'):
            img = cv2.imread(os.path.join(screens_dir, f))
            if img is not None:
                screenshots[f] = img
    print(f"Loaded {len(screenshots)} screenshots")
    
    # 按时间顺序提取视频帧并匹配
    print(f"\nMatching video frames (every {interval_sec}s)...")
    interval_frames = int(fps * interval_sec)
    
    matches = []  # [(time_sec, best_match, score)]
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % interval_frames == 0:
            time_sec = frame_count / fps
            
            # 找最匹配的截图
            best_match = None
            best_score = 0
            
            for name, sc_img in screenshots.items():
                score = compute_similarity(frame, sc_img)
                if score > best_score:
                    best_score = score
                    best_match = name
            
            matches.append({
                "time_sec": round(time_sec, 1),
                "frame_idx": frame_count,
                "best_match": best_match,
                "score": round(best_score, 3)
            })
            
            if len(matches) % 20 == 0:
                print(f"  Processed {len(matches)} frames...")
        
        frame_count += 1
    
    cap.release()
    print(f"Total matches: {len(matches)}")
    
    # 去重：相邻相同的截图只保留第一个
    print("\nDeduplicating...")
    unique_order = []
    prev_match = None
    
    for m in matches:
        if m["best_match"] != prev_match:
            unique_order.append(m)
            prev_match = m["best_match"]
    
    print(f"Unique screens in order: {len(unique_order)}")
    
    # 生成排序映射
    order_mapping = []
    for i, m in enumerate(unique_order, 1):
        order_mapping.append({
            "new_index": i,
            "original_file": m["best_match"],
            "video_time": m["time_sec"],
            "match_score": m["score"]
        })
    
    # 保存结果
    result = {
        "video_path": video_path,
        "screens_dir": screens_dir,
        "total_video_duration": round(duration, 1),
        "interval_sec": interval_sec,
        "total_matches": len(matches),
        "unique_screens": len(unique_order),
        "order_mapping": order_mapping
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved to: {output_path}")
    
    # 显示前20个
    print("\n" + "="*60)
    print("正确排序（前20个）：")
    print("="*60)
    for m in order_mapping[:20]:
        print(f"  #{m['new_index']:3d} <- {m['original_file']} (t={m['video_time']:.0f}s, score={m['match_score']:.3f})")
    
    return result


if __name__ == "__main__":
    import sys
    
    # 默认路径
    video_path = "C:/Users/WIN/Desktop/calai.mp4"
    screens_dir = "projects/Cal_AI_-_Calorie_Tracker_Analysis/screens"
    output_path = "video_analysis/calai_video_order.json"
    
    # 运行匹配
    result = match_video_to_screenshots(video_path, screens_dir, output_path, interval_sec=2)
    
    if result:
        print(f"\n完成！共找到 {result['unique_screens']} 个唯一截图")
        print(f"结果保存在: {output_path}")












