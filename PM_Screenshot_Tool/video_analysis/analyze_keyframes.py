# -*- coding: utf-8 -*-
"""
视频关键帧提取与分析
从视频中提取关键帧，使用AI进行三层分类分析
"""

import os
import sys
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path

# 确保能找到项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("[WARN] OpenCV not available. Install with: pip install opencv-python")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("[WARN] Anthropic not available. Install with: pip install anthropic")

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

# 加载分类词表
def load_taxonomy():
    taxonomy_file = os.path.join(CONFIG_DIR, "taxonomy.json")
    if os.path.exists(taxonomy_file):
        with open(taxonomy_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

TAXONOMY = load_taxonomy()

# 三层分类提示词
ANALYSIS_PROMPT = """你是一个专业的产品分析师，专注于移动应用UI/UX分析。

请分析这个视频帧，按照以下三层分类体系进行分类：

## 分类框架

### Stage（阶段）
- **Onboarding**: 从启动到首次使用核心功能前的所有页面（包括欢迎、注册、权限、Paywall等）
- **Core**: 核心功能使用阶段（包括Dashboard、记录、进度、设置等）

### Module（模块）
Onboarding阶段：Welcome, Profile, Goal, Preference, Permission, Growth, Initialization, Paywall, Registration
Core阶段：Dashboard, Tracking, Progress, Content, Social, Profile, Settings

### Feature（功能点）
根据页面的具体功能判断，例如：
- Welcome: Splash, ValueProp, FeaturePreview
- Profile: GenderSelect, BirthdayInput, HeightInput, WeightInput
- Goal: DirectionSelect, TargetInput, PaceSelect
- Paywall: ValueReminder, PlanSelect, PriceDisplay, TrialOffer
- Tracking: FoodSearch, FoodDetail, PhotoScan, ManualInput

## 输出格式
请以JSON格式输出：
```json
{
  "stage": "Onboarding或Core",
  "module": "模块名称",
  "feature": "功能点名称",
  "page_role": "页面角色（Information/Collection/Action/Confirmation/Navigation）",
  "description_cn": "中文描述（20字以内）",
  "description_en": "English description (within 20 words)",
  "ui_elements": ["识别到的UI元素列表"],
  "is_modal": false,
  "transition_hint": "如果能看出是从哪里跳转来的或将跳转到哪里，描述一下",
  "confidence": 0.95
}
```

请只输出JSON，不要其他内容。"""


def extract_keyframes(video_path, output_dir, interval_seconds=1.0, similarity_threshold=0.85):
    """
    从视频提取关键帧
    
    Args:
        video_path: 视频文件路径
        output_dir: 输出目录
        interval_seconds: 提取间隔（秒）
        similarity_threshold: 相似度阈值，低于此值才保存新帧
    
    Returns:
        提取的帧信息列表
    """
    if not CV2_AVAILABLE:
        print("[ERROR] OpenCV not available")
        return []
    
    os.makedirs(output_dir, exist_ok=True)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return []
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"[VIDEO] FPS: {fps:.2f}, Total Frames: {total_frames}, Duration: {duration:.2f}s")
    
    frame_interval = int(fps * interval_seconds)
    frames_info = []
    last_frame_hash = None
    frame_count = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_interval == 0:
            # 计算帧的哈希值用于去重
            frame_small = cv2.resize(frame, (64, 64))
            frame_hash = hashlib.md5(frame_small.tobytes()).hexdigest()
            
            # 简单的相似度检查（基于哈希）
            if last_frame_hash != frame_hash:
                timestamp = frame_count / fps
                filename = f"frame_{saved_count:04d}_{timestamp:.2f}s.png"
                filepath = os.path.join(output_dir, filename)
                
                cv2.imwrite(filepath, frame)
                
                frames_info.append({
                    "index": saved_count,
                    "filename": filename,
                    "filepath": filepath,
                    "timestamp": timestamp,
                    "frame_number": frame_count
                })
                
                last_frame_hash = frame_hash
                saved_count += 1
                
                if saved_count % 10 == 0:
                    print(f"[EXTRACT] Saved {saved_count} frames...")
        
        frame_count += 1
    
    cap.release()
    print(f"[EXTRACT] Total extracted: {saved_count} keyframes")
    
    return frames_info


def dedupe_frames(frames_dir, threshold=0.9):
    """
    去除相似的帧
    
    Args:
        frames_dir: 帧目录
        threshold: 相似度阈值
    
    Returns:
        去重后的帧列表
    """
    if not CV2_AVAILABLE:
        return []
    
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    unique_frames = []
    last_hist = None
    
    for filename in frames:
        filepath = os.path.join(frames_dir, filename)
        img = cv2.imread(filepath)
        if img is None:
            continue
        
        # 计算颜色直方图
        hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        if last_hist is None:
            unique_frames.append(filename)
            last_hist = hist
        else:
            # 比较直方图相似度
            similarity = cv2.compareHist(hist, last_hist, cv2.HISTCMP_CORREL)
            if similarity < threshold:
                unique_frames.append(filename)
                last_hist = hist
            else:
                # 删除重复帧
                os.remove(filepath)
    
    print(f"[DEDUPE] Kept {len(unique_frames)} unique frames from {len(frames)}")
    return unique_frames


def analyze_frame_with_ai(image_path, client):
    """
    使用Claude分析单个帧
    """
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
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
                            "text": ANALYSIS_PROMPT
                        }
                    ]
                }
            ]
        )
        
        result_text = response.content[0].text.strip()
        
        # 提取JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        return json.loads(result_text)
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse error: {e}")
        return {"error": str(e), "raw": result_text if 'result_text' in locals() else ""}
    except Exception as e:
        print(f"[ERROR] API error: {e}")
        return {"error": str(e)}


def analyze_all_frames(frames_dir, output_file):
    """
    分析所有关键帧
    """
    if not ANTHROPIC_AVAILABLE:
        print("[ERROR] Anthropic not available")
        return {}
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set")
        return {}
    
    client = anthropic.Anthropic(api_key=api_key)
    
    frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    results = {}
    
    print(f"[ANALYZE] Starting analysis of {len(frames)} frames...")
    
    for i, filename in enumerate(frames):
        filepath = os.path.join(frames_dir, filename)
        print(f"[{i+1}/{len(frames)}] Analyzing {filename}...")
        
        result = analyze_frame_with_ai(filepath, client)
        result["filename"] = filename
        result["index"] = i
        
        # 从文件名提取时间戳
        try:
            timestamp_str = filename.split("_")[-1].replace("s.png", "")
            result["timestamp"] = float(timestamp_str)
        except:
            result["timestamp"] = i
        
        results[filename] = result
        
        # 每分析5个保存一次
        if (i + 1) % 5 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"[SAVE] Progress saved ({i+1}/{len(frames)})")
    
    # 最终保存
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"[DONE] Analysis complete. Results saved to {output_file}")
    return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="视频关键帧提取与分析")
    parser.add_argument("video_path", help="视频文件路径")
    parser.add_argument("--project", default="Cal_AI_-_Calorie_Tracker_Analysis", help="项目名称")
    parser.add_argument("--interval", type=float, default=1.0, help="提取间隔（秒）")
    parser.add_argument("--skip-extract", action="store_true", help="跳过提取，只分析")
    parser.add_argument("--skip-analyze", action="store_true", help="跳过分析，只提取")
    
    args = parser.parse_args()
    
    # 设置输出目录
    project_dir = os.path.join(PROJECTS_DIR, args.project)
    frames_dir = os.path.join(project_dir, "video_frames")
    output_file = os.path.join(project_dir, "keyframe_analysis.json")
    
    print("=" * 60)
    print("视频关键帧提取与分析")
    print("=" * 60)
    print(f"视频: {args.video_path}")
    print(f"项目: {args.project}")
    print(f"帧目录: {frames_dir}")
    print("=" * 60)
    
    # 步骤1：提取关键帧
    if not args.skip_extract:
        print("\n[Step 1] 提取关键帧...")
        frames_info = extract_keyframes(args.video_path, frames_dir, args.interval)
        
        # 去重
        print("\n[Step 1.5] 去除相似帧...")
        unique_frames = dedupe_frames(frames_dir)
        print(f"保留 {len(unique_frames)} 个独特帧")
    
    # 步骤2：AI分析
    if not args.skip_analyze:
        print("\n[Step 2] AI分析关键帧...")
        results = analyze_all_frames(frames_dir, output_file)
        print(f"分析完成，结果保存到: {output_file}")
    
    print("\n[DONE] 全部完成!")


if __name__ == "__main__":
    # 设置控制台编码
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    main()












