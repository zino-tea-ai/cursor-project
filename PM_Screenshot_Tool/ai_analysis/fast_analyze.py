# -*- coding: utf-8 -*-
"""
高速AI分析脚本 v2.0 - 集成智能三层分析架构
支持传统模式和智能模式两种分析方式
"""

import os
import sys
import json
import time
import threading
import io
import base64
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from PIL import Image

# 设置API Key
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 配置
DEFAULT_CONCURRENT = 5      # 默认并发数
MAX_CONCURRENT = 10         # 最大并发数
AUTO_SAVE_INTERVAL = 10     # 每分析N张自动保存
RETRY_ON_RATE_LIMIT = True  # 遇到限流自动重试

# 自动重试配置
MAX_RETRIES = 3             # 单张图片最大重试次数
RETRY_DELAY = 2             # 重试间隔(秒)
RETRY_ON_PARSE_ERROR = True # JSON解析失败重试
RETRY_ON_API_ERROR = True   # API错误重试
FINAL_RETRY_ROUNDS = 2      # 最终批量重试轮数

# 唯一指定模型：Opus（质量最高）
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# 图片压缩配置
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB
COMPRESS_WIDTH = 800              # 压缩后宽度
COMPRESS_QUALITY = 85             # JPEG质量


def compress_image_for_api(image_path: str) -> Optional[str]:
    """
    如果图片太大，压缩成临时JPEG文件
    返回压缩后的临时文件路径，或None（无需压缩）
    """
    try:
        file_size = os.path.getsize(image_path)
        if file_size <= MAX_IMAGE_SIZE:
            return None
        
        # 打开并压缩
        img = Image.open(image_path)
        
        # 缩小
        ratio = COMPRESS_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((COMPRESS_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 转RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存临时文件
        temp_path = image_path + '.temp.jpg'
        img.save(temp_path, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)
        img.close()
        
        return temp_path
    except Exception:
        return None


class FastAnalyzer:
    """高速并行分析器（传统模式）"""
    
    def __init__(self, project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5):
        self.project_name = project_name
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        self.screens_folder = os.path.join(self.project_path, "Screens")
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
        # 已有结果（用于断点续传）
        self.existing_results = {}
        
        # 延迟导入分析器
        self.analyzer = None
    
    def _init_analyzer(self):
        """延迟初始化AI分析器"""
        if self.analyzer is None:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
            from ai_analyzer import AIScreenshotAnalyzer
            self.analyzer = AIScreenshotAnalyzer(model=self.model)
            if not self.analyzer.client:
                print("[ERROR] Failed to initialize API client!")
                return False
        return True
    
    def load_existing_results(self) -> Dict:
        """加载已有分析结果（断点续传）"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_results = data.get('results', {})
                    return self.existing_results
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")
        return {}
    
    def get_pending_screenshots(self) -> List[str]:
        """获取待分析的截图列表"""
        all_screenshots = sorted([
            f for f in os.listdir(self.screens_folder) 
            if f.lower().endswith('.png')
        ])
        
        # 排除已分析的
        pending = [f for f in all_screenshots if f not in self.existing_results]
        return pending
    
    def save_results(self, results: Dict, is_final: bool = False):
        """保存分析结果"""
        # 合并已有结果
        all_results = {**self.existing_results, **results}
        
        output = {
            'project_name': self.project_name,
            'total_screenshots': len(all_results),
            'analyzed_count': self.success_count + len(self.existing_results),
            'failed_count': self.fail_count,
            'results': all_results,
            'last_updated': datetime.now().isoformat(),
            'model': self.model
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        if is_final:
            print(f"\n[SAVED] {self.analysis_file}")
    
    def analyze_one(self, filename: str, retry_count: int = 0) -> Dict:
        """分析单张截图（线程安全，带自动重试和自动压缩）"""
        image_path = os.path.join(self.screens_folder, filename)
        compressed_path = None
        
        try:
            # 检查是否需要压缩
            compressed_path = compress_image_for_api(image_path)
            analyze_path = compressed_path if compressed_path else image_path
            
            result = self.analyzer.analyze_single(analyze_path)
            
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 检查是否需要重试
            error = result.get('error', '')
            should_retry = False
            
            if error:
                # JSON解析失败
                if RETRY_ON_PARSE_ERROR and 'parse' in error.lower():
                    should_retry = True
                # API错误（非404模型不存在）
                if RETRY_ON_API_ERROR and 'api error' in error.lower() and 'not_found' not in error.lower():
                    should_retry = True
            
            # 重试逻辑
            if should_retry and retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            
            return result
            
        except Exception as e:
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 异常重试
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                self.fail_count += 1
            
            return {
                'filename': filename,
                'screen_type': 'Unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def run(self) -> bool:
        """运行并行分析（传统模式）"""
        print("\n" + "=" * 70)
        print(f"  FAST ANALYZER (Legacy Mode) - {self.project_name}")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.screens_folder):
            print(f"[ERROR] Screens folder not found: {self.screens_folder}")
            return False
        
        # 加载已有结果
        self.load_existing_results()
        existing_count = len(self.existing_results)
        
        # 获取待分析列表
        pending = self.get_pending_screenshots()
        total_pending = len(pending)
        total_all = existing_count + total_pending
        
        print(f"\n  Total Screenshots: {total_all}")
        print(f"  Already Analyzed:  {existing_count} (will skip)")
        print(f"  Pending Analysis:  {total_pending}")
        print(f"  Concurrent:        {self.concurrent}")
        print(f"  Model:             {self.model}")
        
        if total_pending == 0:
            print("\n[DONE] All screenshots already analyzed!")
            return True
        
        # 预计时间（假设每张6秒，并行处理）
        estimated_time = (total_pending * 6) / self.concurrent
        print(f"  Estimated Time:    {int(estimated_time // 60)}m {int(estimated_time % 60)}s")
        print("=" * 70)
        
        # 初始化分析器
        if not self._init_analyzer():
            return False
        
        # 开始分析
        start_time = datetime.now()
        results = {}
        
        print(f"\n[START] {start_time.strftime('%H:%M:%S')}")
        print("-" * 70)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.analyze_one, f): f 
                for f in pending
            }
            
            completed = 0
            last_save = 0
            
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    # 进度显示
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    status = "OK" if not result.get('error') else "FAIL"
                    
                    # 计算时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total_pending - completed)
                    
                    # 进度条
                    pct = completed / total_pending
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total_pending} ({pct:.0%}) | {int(remaining)}s left | {filename[:20]}')
                    sys.stdout.flush()
                    
                    # 每10张详细输出
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total_pending}] {status} {filename[:30]:30s} -> {screen_type:12s} ({confidence:.0%})")
                    
                    # 自动保存
                    if completed - last_save >= AUTO_SAVE_INTERVAL:
                        self.save_results(results)
                        last_save = completed
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
        
        # 保存结果
        self.save_results(results)
        
        # 检查失败项，进行批量重试
        failed_items = [f for f, r in results.items() if r.get('error') or r.get('screen_type') == 'Unknown']
        
        if failed_items and FINAL_RETRY_ROUNDS > 0:
            print(f"\n\n[RETRY] {len(failed_items)} failed items, starting auto-retry...")
            results = self._retry_failed_items(results, failed_items)
        
        # 最终保存
        self.save_results(results, is_final=True)
        
        # 重新计算统计
        final_success = sum(1 for r in results.values() if not r.get('error') and r.get('screen_type') != 'Unknown')
        final_fail = len(results) - final_success
        
        # 统计
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "-" * 70)
        print(f"[DONE] Analysis complete!")
        print(f"  Success: {final_success}/{total_pending}")
        print(f"  Failed:  {final_fail}/{total_pending}")
        print(f"  Time:    {total_time:.1f}s ({total_time/max(1,total_pending):.2f}s per image)")
        print(f"  Speed:   {total_pending/max(1,total_time)*60:.1f} images/min")
        
        if final_fail > 0:
            print(f"\n[WARN] {final_fail} items still failed after retries")
        else:
            print(f"\n[OK] 100% success rate achieved!")
        
        return True
    
    def _retry_failed_items(self, results: Dict, failed_items: List[str]) -> Dict:
        """批量重试失败项（使用同一模型）"""
        
        for round_num in range(FINAL_RETRY_ROUNDS):
            if not failed_items:
                break
            
            print(f"\n[RETRY Round {round_num + 1}] Retrying {len(failed_items)} failed items...")
            
            retry_success = 0
            for filename in failed_items[:]:
                print(f"  Retrying: {filename}...", end=" ")
                
                old_fail = self.fail_count
                result = self.analyze_one(filename, retry_count=0)
                
                if not result.get('error') and result.get('screen_type') != 'Unknown':
                    results[filename] = result
                    failed_items.remove(filename)
                    retry_success += 1
                    self.fail_count = old_fail
                    self.success_count += 1
                    print("OK")
                else:
                    print("FAIL")
                
                time.sleep(1)
            
            print(f"  Round {round_num + 1}: {retry_success} recovered, {len(failed_items)} remaining")
            
            if not failed_items:
                print(f"\n[OK] All items recovered!")
                break
        
        return results
    
    def post_process(self):
        """后处理：生成structured_descriptions.json"""
        print("\n[POST] Generating structured_descriptions.json...")
        
        try:
            # 调用generate_structured.py
            import subprocess
            result = subprocess.run(
                ['python', 'generate_structured.py', self.project_name],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[OK] structured_descriptions.json generated")
            else:
                print(f"[WARN] {result.stderr}")
                
        except Exception as e:
            print(f"[WARN] Post-process error: {e}")


def run_smart_analysis(project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5) -> bool:
    """
    运行智能三层分析（新模式）
    
    Args:
        project_name: 项目名称
        model: AI模型
        concurrent: 并发数
    
    Returns:
        是否成功
    """
    try:
        from smart_analyzer import SmartAnalyzer
        
        analyzer = SmartAnalyzer(
            project_name=project_name,
            model=model,
            concurrent=concurrent,
            auto_fix=True,
            verbose=True
        )
        
        results = analyzer.run()
        
        if results:
            # 更新知识库
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from knowledge.learner import KnowledgeLearner
                
                learner = KnowledgeLearner()
                learner.learn_from_analysis(
                    project_name=project_name,
                    product_profile={
                        "app_category": analyzer.product_profile.app_category,
                        "sub_category": analyzer.product_profile.sub_category,
                        "target_users": analyzer.product_profile.target_users,
                        "core_value": analyzer.product_profile.core_value
                    },
                    flow_structure={
                        "stages": [s.name for s in analyzer.flow_structure.stages],
                        "paywall_position": analyzer.flow_structure.paywall_position,
                        "onboarding_length": analyzer.flow_structure.onboarding_length
                    },
                    results=results
                )
                print("\n[KNOWLEDGE] Updated knowledge base")
            except Exception as e:
                print(f"\n[WARN] Knowledge update skipped: {e}")
            
            return True
        
        return False
        
    except ImportError as e:
        print(f"[ERROR] Smart analyzer not available: {e}")
        print("[INFO] Falling back to legacy mode...")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fast AI Screenshot Analyzer")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--all", action="store_true", help="Analyze all pending projects")
    parser.add_argument("--legacy", action="store_true", help="Use legacy mode (no context)")
    parser.add_argument("--smart", action="store_true", help="Force smart mode (with context)")
    
    args = parser.parse_args()
    
    # 设置API Key
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not API_KEY:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_KEY = config.get("ANTHROPIC_API_KEY", "")
        
        if API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    if args.all:
        # 分析所有待处理项目
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects_dir = os.path.join(base_dir, "projects")
        
        for project_name in os.listdir(projects_dir):
            if project_name in ["null", "comparison_report.json", "comparison_report.md"]:
                continue
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                print(f"\n{'='*70}")
                print(f"Processing: {project_name}")
                print(f"{'='*70}")
                
                if args.legacy:
                    analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                    if analyzer.run():
                        analyzer.post_process()
                else:
                    if not run_smart_analysis(project_name, args.model, args.concurrent):
                        # 智能模式失败，回退到传统模式
                        analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                        if analyzer.run():
                            analyzer.post_process()
    else:
        # 分析单个项目
        if args.legacy:
            # 强制使用传统模式
            analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
            if analyzer.run():
                analyzer.post_process()
        elif args.smart:
            # 强制使用智能模式
            run_smart_analysis(args.project, args.model, args.concurrent)
        else:
            # 默认：尝试智能模式，失败则回退
            if not run_smart_analysis(args.project, args.model, args.concurrent):
                print("\n[INFO] Falling back to legacy mode...")
                analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
                if analyzer.run():
                    analyzer.post_process()
        


if __name__ == "__main__":
    main()

高速AI分析脚本 v2.0 - 集成智能三层分析架构
支持传统模式和智能模式两种分析方式
"""

import os
import sys
import json
import time
import threading
import io
import base64
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from PIL import Image

# 设置API Key
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 配置
DEFAULT_CONCURRENT = 5      # 默认并发数
MAX_CONCURRENT = 10         # 最大并发数
AUTO_SAVE_INTERVAL = 10     # 每分析N张自动保存
RETRY_ON_RATE_LIMIT = True  # 遇到限流自动重试

# 自动重试配置
MAX_RETRIES = 3             # 单张图片最大重试次数
RETRY_DELAY = 2             # 重试间隔(秒)
RETRY_ON_PARSE_ERROR = True # JSON解析失败重试
RETRY_ON_API_ERROR = True   # API错误重试
FINAL_RETRY_ROUNDS = 2      # 最终批量重试轮数

# 唯一指定模型：Opus（质量最高）
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# 图片压缩配置
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB
COMPRESS_WIDTH = 800              # 压缩后宽度
COMPRESS_QUALITY = 85             # JPEG质量


def compress_image_for_api(image_path: str) -> Optional[str]:
    """
    如果图片太大，压缩成临时JPEG文件
    返回压缩后的临时文件路径，或None（无需压缩）
    """
    try:
        file_size = os.path.getsize(image_path)
        if file_size <= MAX_IMAGE_SIZE:
            return None
        
        # 打开并压缩
        img = Image.open(image_path)
        
        # 缩小
        ratio = COMPRESS_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((COMPRESS_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 转RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存临时文件
        temp_path = image_path + '.temp.jpg'
        img.save(temp_path, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)
        img.close()
        
        return temp_path
    except Exception:
        return None


class FastAnalyzer:
    """高速并行分析器（传统模式）"""
    
    def __init__(self, project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5):
        self.project_name = project_name
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        self.screens_folder = os.path.join(self.project_path, "Screens")
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
        # 已有结果（用于断点续传）
        self.existing_results = {}
        
        # 延迟导入分析器
        self.analyzer = None
    
    def _init_analyzer(self):
        """延迟初始化AI分析器"""
        if self.analyzer is None:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
            from ai_analyzer import AIScreenshotAnalyzer
            self.analyzer = AIScreenshotAnalyzer(model=self.model)
            if not self.analyzer.client:
                print("[ERROR] Failed to initialize API client!")
                return False
        return True
    
    def load_existing_results(self) -> Dict:
        """加载已有分析结果（断点续传）"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_results = data.get('results', {})
                    return self.existing_results
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")
        return {}
    
    def get_pending_screenshots(self) -> List[str]:
        """获取待分析的截图列表"""
        all_screenshots = sorted([
            f for f in os.listdir(self.screens_folder) 
            if f.lower().endswith('.png')
        ])
        
        # 排除已分析的
        pending = [f for f in all_screenshots if f not in self.existing_results]
        return pending
    
    def save_results(self, results: Dict, is_final: bool = False):
        """保存分析结果"""
        # 合并已有结果
        all_results = {**self.existing_results, **results}
        
        output = {
            'project_name': self.project_name,
            'total_screenshots': len(all_results),
            'analyzed_count': self.success_count + len(self.existing_results),
            'failed_count': self.fail_count,
            'results': all_results,
            'last_updated': datetime.now().isoformat(),
            'model': self.model
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        if is_final:
            print(f"\n[SAVED] {self.analysis_file}")
    
    def analyze_one(self, filename: str, retry_count: int = 0) -> Dict:
        """分析单张截图（线程安全，带自动重试和自动压缩）"""
        image_path = os.path.join(self.screens_folder, filename)
        compressed_path = None
        
        try:
            # 检查是否需要压缩
            compressed_path = compress_image_for_api(image_path)
            analyze_path = compressed_path if compressed_path else image_path
            
            result = self.analyzer.analyze_single(analyze_path)
            
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 检查是否需要重试
            error = result.get('error', '')
            should_retry = False
            
            if error:
                # JSON解析失败
                if RETRY_ON_PARSE_ERROR and 'parse' in error.lower():
                    should_retry = True
                # API错误（非404模型不存在）
                if RETRY_ON_API_ERROR and 'api error' in error.lower() and 'not_found' not in error.lower():
                    should_retry = True
            
            # 重试逻辑
            if should_retry and retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            
            return result
            
        except Exception as e:
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 异常重试
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                self.fail_count += 1
            
            return {
                'filename': filename,
                'screen_type': 'Unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def run(self) -> bool:
        """运行并行分析（传统模式）"""
        print("\n" + "=" * 70)
        print(f"  FAST ANALYZER (Legacy Mode) - {self.project_name}")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.screens_folder):
            print(f"[ERROR] Screens folder not found: {self.screens_folder}")
            return False
        
        # 加载已有结果
        self.load_existing_results()
        existing_count = len(self.existing_results)
        
        # 获取待分析列表
        pending = self.get_pending_screenshots()
        total_pending = len(pending)
        total_all = existing_count + total_pending
        
        print(f"\n  Total Screenshots: {total_all}")
        print(f"  Already Analyzed:  {existing_count} (will skip)")
        print(f"  Pending Analysis:  {total_pending}")
        print(f"  Concurrent:        {self.concurrent}")
        print(f"  Model:             {self.model}")
        
        if total_pending == 0:
            print("\n[DONE] All screenshots already analyzed!")
            return True
        
        # 预计时间（假设每张6秒，并行处理）
        estimated_time = (total_pending * 6) / self.concurrent
        print(f"  Estimated Time:    {int(estimated_time // 60)}m {int(estimated_time % 60)}s")
        print("=" * 70)
        
        # 初始化分析器
        if not self._init_analyzer():
            return False
        
        # 开始分析
        start_time = datetime.now()
        results = {}
        
        print(f"\n[START] {start_time.strftime('%H:%M:%S')}")
        print("-" * 70)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.analyze_one, f): f 
                for f in pending
            }
            
            completed = 0
            last_save = 0
            
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    # 进度显示
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    status = "OK" if not result.get('error') else "FAIL"
                    
                    # 计算时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total_pending - completed)
                    
                    # 进度条
                    pct = completed / total_pending
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total_pending} ({pct:.0%}) | {int(remaining)}s left | {filename[:20]}')
                    sys.stdout.flush()
                    
                    # 每10张详细输出
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total_pending}] {status} {filename[:30]:30s} -> {screen_type:12s} ({confidence:.0%})")
                    
                    # 自动保存
                    if completed - last_save >= AUTO_SAVE_INTERVAL:
                        self.save_results(results)
                        last_save = completed
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
        
        # 保存结果
        self.save_results(results)
        
        # 检查失败项，进行批量重试
        failed_items = [f for f, r in results.items() if r.get('error') or r.get('screen_type') == 'Unknown']
        
        if failed_items and FINAL_RETRY_ROUNDS > 0:
            print(f"\n\n[RETRY] {len(failed_items)} failed items, starting auto-retry...")
            results = self._retry_failed_items(results, failed_items)
        
        # 最终保存
        self.save_results(results, is_final=True)
        
        # 重新计算统计
        final_success = sum(1 for r in results.values() if not r.get('error') and r.get('screen_type') != 'Unknown')
        final_fail = len(results) - final_success
        
        # 统计
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "-" * 70)
        print(f"[DONE] Analysis complete!")
        print(f"  Success: {final_success}/{total_pending}")
        print(f"  Failed:  {final_fail}/{total_pending}")
        print(f"  Time:    {total_time:.1f}s ({total_time/max(1,total_pending):.2f}s per image)")
        print(f"  Speed:   {total_pending/max(1,total_time)*60:.1f} images/min")
        
        if final_fail > 0:
            print(f"\n[WARN] {final_fail} items still failed after retries")
        else:
            print(f"\n[OK] 100% success rate achieved!")
        
        return True
    
    def _retry_failed_items(self, results: Dict, failed_items: List[str]) -> Dict:
        """批量重试失败项（使用同一模型）"""
        
        for round_num in range(FINAL_RETRY_ROUNDS):
            if not failed_items:
                break
            
            print(f"\n[RETRY Round {round_num + 1}] Retrying {len(failed_items)} failed items...")
            
            retry_success = 0
            for filename in failed_items[:]:
                print(f"  Retrying: {filename}...", end=" ")
                
                old_fail = self.fail_count
                result = self.analyze_one(filename, retry_count=0)
                
                if not result.get('error') and result.get('screen_type') != 'Unknown':
                    results[filename] = result
                    failed_items.remove(filename)
                    retry_success += 1
                    self.fail_count = old_fail
                    self.success_count += 1
                    print("OK")
                else:
                    print("FAIL")
                
                time.sleep(1)
            
            print(f"  Round {round_num + 1}: {retry_success} recovered, {len(failed_items)} remaining")
            
            if not failed_items:
                print(f"\n[OK] All items recovered!")
                break
        
        return results
    
    def post_process(self):
        """后处理：生成structured_descriptions.json"""
        print("\n[POST] Generating structured_descriptions.json...")
        
        try:
            # 调用generate_structured.py
            import subprocess
            result = subprocess.run(
                ['python', 'generate_structured.py', self.project_name],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[OK] structured_descriptions.json generated")
            else:
                print(f"[WARN] {result.stderr}")
                
        except Exception as e:
            print(f"[WARN] Post-process error: {e}")


def run_smart_analysis(project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5) -> bool:
    """
    运行智能三层分析（新模式）
    
    Args:
        project_name: 项目名称
        model: AI模型
        concurrent: 并发数
    
    Returns:
        是否成功
    """
    try:
        from smart_analyzer import SmartAnalyzer
        
        analyzer = SmartAnalyzer(
            project_name=project_name,
            model=model,
            concurrent=concurrent,
            auto_fix=True,
            verbose=True
        )
        
        results = analyzer.run()
        
        if results:
            # 更新知识库
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from knowledge.learner import KnowledgeLearner
                
                learner = KnowledgeLearner()
                learner.learn_from_analysis(
                    project_name=project_name,
                    product_profile={
                        "app_category": analyzer.product_profile.app_category,
                        "sub_category": analyzer.product_profile.sub_category,
                        "target_users": analyzer.product_profile.target_users,
                        "core_value": analyzer.product_profile.core_value
                    },
                    flow_structure={
                        "stages": [s.name for s in analyzer.flow_structure.stages],
                        "paywall_position": analyzer.flow_structure.paywall_position,
                        "onboarding_length": analyzer.flow_structure.onboarding_length
                    },
                    results=results
                )
                print("\n[KNOWLEDGE] Updated knowledge base")
            except Exception as e:
                print(f"\n[WARN] Knowledge update skipped: {e}")
            
            return True
        
        return False
        
    except ImportError as e:
        print(f"[ERROR] Smart analyzer not available: {e}")
        print("[INFO] Falling back to legacy mode...")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fast AI Screenshot Analyzer")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--all", action="store_true", help="Analyze all pending projects")
    parser.add_argument("--legacy", action="store_true", help="Use legacy mode (no context)")
    parser.add_argument("--smart", action="store_true", help="Force smart mode (with context)")
    
    args = parser.parse_args()
    
    # 设置API Key
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not API_KEY:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_KEY = config.get("ANTHROPIC_API_KEY", "")
        
        if API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    if args.all:
        # 分析所有待处理项目
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects_dir = os.path.join(base_dir, "projects")
        
        for project_name in os.listdir(projects_dir):
            if project_name in ["null", "comparison_report.json", "comparison_report.md"]:
                continue
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                print(f"\n{'='*70}")
                print(f"Processing: {project_name}")
                print(f"{'='*70}")
                
                if args.legacy:
                    analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                    if analyzer.run():
                        analyzer.post_process()
                else:
                    if not run_smart_analysis(project_name, args.model, args.concurrent):
                        # 智能模式失败，回退到传统模式
                        analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                        if analyzer.run():
                            analyzer.post_process()
    else:
        # 分析单个项目
        if args.legacy:
            # 强制使用传统模式
            analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
            if analyzer.run():
                analyzer.post_process()
        elif args.smart:
            # 强制使用智能模式
            run_smart_analysis(args.project, args.model, args.concurrent)
        else:
            # 默认：尝试智能模式，失败则回退
            if not run_smart_analysis(args.project, args.model, args.concurrent):
                print("\n[INFO] Falling back to legacy mode...")
                analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
                if analyzer.run():
                    analyzer.post_process()
        


if __name__ == "__main__":
    main()

高速AI分析脚本 v2.0 - 集成智能三层分析架构
支持传统模式和智能模式两种分析方式
"""

import os
import sys
import json
import time
import threading
import io
import base64
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from PIL import Image

# 设置API Key
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 配置
DEFAULT_CONCURRENT = 5      # 默认并发数
MAX_CONCURRENT = 10         # 最大并发数
AUTO_SAVE_INTERVAL = 10     # 每分析N张自动保存
RETRY_ON_RATE_LIMIT = True  # 遇到限流自动重试

# 自动重试配置
MAX_RETRIES = 3             # 单张图片最大重试次数
RETRY_DELAY = 2             # 重试间隔(秒)
RETRY_ON_PARSE_ERROR = True # JSON解析失败重试
RETRY_ON_API_ERROR = True   # API错误重试
FINAL_RETRY_ROUNDS = 2      # 最终批量重试轮数

# 唯一指定模型：Opus（质量最高）
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# 图片压缩配置
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB
COMPRESS_WIDTH = 800              # 压缩后宽度
COMPRESS_QUALITY = 85             # JPEG质量


def compress_image_for_api(image_path: str) -> Optional[str]:
    """
    如果图片太大，压缩成临时JPEG文件
    返回压缩后的临时文件路径，或None（无需压缩）
    """
    try:
        file_size = os.path.getsize(image_path)
        if file_size <= MAX_IMAGE_SIZE:
            return None
        
        # 打开并压缩
        img = Image.open(image_path)
        
        # 缩小
        ratio = COMPRESS_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((COMPRESS_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 转RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存临时文件
        temp_path = image_path + '.temp.jpg'
        img.save(temp_path, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)
        img.close()
        
        return temp_path
    except Exception:
        return None


class FastAnalyzer:
    """高速并行分析器（传统模式）"""
    
    def __init__(self, project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5):
        self.project_name = project_name
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        self.screens_folder = os.path.join(self.project_path, "Screens")
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
        # 已有结果（用于断点续传）
        self.existing_results = {}
        
        # 延迟导入分析器
        self.analyzer = None
    
    def _init_analyzer(self):
        """延迟初始化AI分析器"""
        if self.analyzer is None:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
            from ai_analyzer import AIScreenshotAnalyzer
            self.analyzer = AIScreenshotAnalyzer(model=self.model)
            if not self.analyzer.client:
                print("[ERROR] Failed to initialize API client!")
                return False
        return True
    
    def load_existing_results(self) -> Dict:
        """加载已有分析结果（断点续传）"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_results = data.get('results', {})
                    return self.existing_results
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")
        return {}
    
    def get_pending_screenshots(self) -> List[str]:
        """获取待分析的截图列表"""
        all_screenshots = sorted([
            f for f in os.listdir(self.screens_folder) 
            if f.lower().endswith('.png')
        ])
        
        # 排除已分析的
        pending = [f for f in all_screenshots if f not in self.existing_results]
        return pending
    
    def save_results(self, results: Dict, is_final: bool = False):
        """保存分析结果"""
        # 合并已有结果
        all_results = {**self.existing_results, **results}
        
        output = {
            'project_name': self.project_name,
            'total_screenshots': len(all_results),
            'analyzed_count': self.success_count + len(self.existing_results),
            'failed_count': self.fail_count,
            'results': all_results,
            'last_updated': datetime.now().isoformat(),
            'model': self.model
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        if is_final:
            print(f"\n[SAVED] {self.analysis_file}")
    
    def analyze_one(self, filename: str, retry_count: int = 0) -> Dict:
        """分析单张截图（线程安全，带自动重试和自动压缩）"""
        image_path = os.path.join(self.screens_folder, filename)
        compressed_path = None
        
        try:
            # 检查是否需要压缩
            compressed_path = compress_image_for_api(image_path)
            analyze_path = compressed_path if compressed_path else image_path
            
            result = self.analyzer.analyze_single(analyze_path)
            
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 检查是否需要重试
            error = result.get('error', '')
            should_retry = False
            
            if error:
                # JSON解析失败
                if RETRY_ON_PARSE_ERROR and 'parse' in error.lower():
                    should_retry = True
                # API错误（非404模型不存在）
                if RETRY_ON_API_ERROR and 'api error' in error.lower() and 'not_found' not in error.lower():
                    should_retry = True
            
            # 重试逻辑
            if should_retry and retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            
            return result
            
        except Exception as e:
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 异常重试
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                self.fail_count += 1
            
            return {
                'filename': filename,
                'screen_type': 'Unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def run(self) -> bool:
        """运行并行分析（传统模式）"""
        print("\n" + "=" * 70)
        print(f"  FAST ANALYZER (Legacy Mode) - {self.project_name}")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.screens_folder):
            print(f"[ERROR] Screens folder not found: {self.screens_folder}")
            return False
        
        # 加载已有结果
        self.load_existing_results()
        existing_count = len(self.existing_results)
        
        # 获取待分析列表
        pending = self.get_pending_screenshots()
        total_pending = len(pending)
        total_all = existing_count + total_pending
        
        print(f"\n  Total Screenshots: {total_all}")
        print(f"  Already Analyzed:  {existing_count} (will skip)")
        print(f"  Pending Analysis:  {total_pending}")
        print(f"  Concurrent:        {self.concurrent}")
        print(f"  Model:             {self.model}")
        
        if total_pending == 0:
            print("\n[DONE] All screenshots already analyzed!")
            return True
        
        # 预计时间（假设每张6秒，并行处理）
        estimated_time = (total_pending * 6) / self.concurrent
        print(f"  Estimated Time:    {int(estimated_time // 60)}m {int(estimated_time % 60)}s")
        print("=" * 70)
        
        # 初始化分析器
        if not self._init_analyzer():
            return False
        
        # 开始分析
        start_time = datetime.now()
        results = {}
        
        print(f"\n[START] {start_time.strftime('%H:%M:%S')}")
        print("-" * 70)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.analyze_one, f): f 
                for f in pending
            }
            
            completed = 0
            last_save = 0
            
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    # 进度显示
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    status = "OK" if not result.get('error') else "FAIL"
                    
                    # 计算时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total_pending - completed)
                    
                    # 进度条
                    pct = completed / total_pending
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total_pending} ({pct:.0%}) | {int(remaining)}s left | {filename[:20]}')
                    sys.stdout.flush()
                    
                    # 每10张详细输出
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total_pending}] {status} {filename[:30]:30s} -> {screen_type:12s} ({confidence:.0%})")
                    
                    # 自动保存
                    if completed - last_save >= AUTO_SAVE_INTERVAL:
                        self.save_results(results)
                        last_save = completed
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
        
        # 保存结果
        self.save_results(results)
        
        # 检查失败项，进行批量重试
        failed_items = [f for f, r in results.items() if r.get('error') or r.get('screen_type') == 'Unknown']
        
        if failed_items and FINAL_RETRY_ROUNDS > 0:
            print(f"\n\n[RETRY] {len(failed_items)} failed items, starting auto-retry...")
            results = self._retry_failed_items(results, failed_items)
        
        # 最终保存
        self.save_results(results, is_final=True)
        
        # 重新计算统计
        final_success = sum(1 for r in results.values() if not r.get('error') and r.get('screen_type') != 'Unknown')
        final_fail = len(results) - final_success
        
        # 统计
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "-" * 70)
        print(f"[DONE] Analysis complete!")
        print(f"  Success: {final_success}/{total_pending}")
        print(f"  Failed:  {final_fail}/{total_pending}")
        print(f"  Time:    {total_time:.1f}s ({total_time/max(1,total_pending):.2f}s per image)")
        print(f"  Speed:   {total_pending/max(1,total_time)*60:.1f} images/min")
        
        if final_fail > 0:
            print(f"\n[WARN] {final_fail} items still failed after retries")
        else:
            print(f"\n[OK] 100% success rate achieved!")
        
        return True
    
    def _retry_failed_items(self, results: Dict, failed_items: List[str]) -> Dict:
        """批量重试失败项（使用同一模型）"""
        
        for round_num in range(FINAL_RETRY_ROUNDS):
            if not failed_items:
                break
            
            print(f"\n[RETRY Round {round_num + 1}] Retrying {len(failed_items)} failed items...")
            
            retry_success = 0
            for filename in failed_items[:]:
                print(f"  Retrying: {filename}...", end=" ")
                
                old_fail = self.fail_count
                result = self.analyze_one(filename, retry_count=0)
                
                if not result.get('error') and result.get('screen_type') != 'Unknown':
                    results[filename] = result
                    failed_items.remove(filename)
                    retry_success += 1
                    self.fail_count = old_fail
                    self.success_count += 1
                    print("OK")
                else:
                    print("FAIL")
                
                time.sleep(1)
            
            print(f"  Round {round_num + 1}: {retry_success} recovered, {len(failed_items)} remaining")
            
            if not failed_items:
                print(f"\n[OK] All items recovered!")
                break
        
        return results
    
    def post_process(self):
        """后处理：生成structured_descriptions.json"""
        print("\n[POST] Generating structured_descriptions.json...")
        
        try:
            # 调用generate_structured.py
            import subprocess
            result = subprocess.run(
                ['python', 'generate_structured.py', self.project_name],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[OK] structured_descriptions.json generated")
            else:
                print(f"[WARN] {result.stderr}")
                
        except Exception as e:
            print(f"[WARN] Post-process error: {e}")


def run_smart_analysis(project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5) -> bool:
    """
    运行智能三层分析（新模式）
    
    Args:
        project_name: 项目名称
        model: AI模型
        concurrent: 并发数
    
    Returns:
        是否成功
    """
    try:
        from smart_analyzer import SmartAnalyzer
        
        analyzer = SmartAnalyzer(
            project_name=project_name,
            model=model,
            concurrent=concurrent,
            auto_fix=True,
            verbose=True
        )
        
        results = analyzer.run()
        
        if results:
            # 更新知识库
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from knowledge.learner import KnowledgeLearner
                
                learner = KnowledgeLearner()
                learner.learn_from_analysis(
                    project_name=project_name,
                    product_profile={
                        "app_category": analyzer.product_profile.app_category,
                        "sub_category": analyzer.product_profile.sub_category,
                        "target_users": analyzer.product_profile.target_users,
                        "core_value": analyzer.product_profile.core_value
                    },
                    flow_structure={
                        "stages": [s.name for s in analyzer.flow_structure.stages],
                        "paywall_position": analyzer.flow_structure.paywall_position,
                        "onboarding_length": analyzer.flow_structure.onboarding_length
                    },
                    results=results
                )
                print("\n[KNOWLEDGE] Updated knowledge base")
            except Exception as e:
                print(f"\n[WARN] Knowledge update skipped: {e}")
            
            return True
        
        return False
        
    except ImportError as e:
        print(f"[ERROR] Smart analyzer not available: {e}")
        print("[INFO] Falling back to legacy mode...")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fast AI Screenshot Analyzer")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--all", action="store_true", help="Analyze all pending projects")
    parser.add_argument("--legacy", action="store_true", help="Use legacy mode (no context)")
    parser.add_argument("--smart", action="store_true", help="Force smart mode (with context)")
    
    args = parser.parse_args()
    
    # 设置API Key
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not API_KEY:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_KEY = config.get("ANTHROPIC_API_KEY", "")
        
        if API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    if args.all:
        # 分析所有待处理项目
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects_dir = os.path.join(base_dir, "projects")
        
        for project_name in os.listdir(projects_dir):
            if project_name in ["null", "comparison_report.json", "comparison_report.md"]:
                continue
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                print(f"\n{'='*70}")
                print(f"Processing: {project_name}")
                print(f"{'='*70}")
                
                if args.legacy:
                    analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                    if analyzer.run():
                        analyzer.post_process()
                else:
                    if not run_smart_analysis(project_name, args.model, args.concurrent):
                        # 智能模式失败，回退到传统模式
                        analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                        if analyzer.run():
                            analyzer.post_process()
    else:
        # 分析单个项目
        if args.legacy:
            # 强制使用传统模式
            analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
            if analyzer.run():
                analyzer.post_process()
        elif args.smart:
            # 强制使用智能模式
            run_smart_analysis(args.project, args.model, args.concurrent)
        else:
            # 默认：尝试智能模式，失败则回退
            if not run_smart_analysis(args.project, args.model, args.concurrent):
                print("\n[INFO] Falling back to legacy mode...")
                analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
                if analyzer.run():
                    analyzer.post_process()
        


if __name__ == "__main__":
    main()

高速AI分析脚本 v2.0 - 集成智能三层分析架构
支持传统模式和智能模式两种分析方式
"""

import os
import sys
import json
import time
import threading
import io
import base64
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from PIL import Image

# 设置API Key
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 配置
DEFAULT_CONCURRENT = 5      # 默认并发数
MAX_CONCURRENT = 10         # 最大并发数
AUTO_SAVE_INTERVAL = 10     # 每分析N张自动保存
RETRY_ON_RATE_LIMIT = True  # 遇到限流自动重试

# 自动重试配置
MAX_RETRIES = 3             # 单张图片最大重试次数
RETRY_DELAY = 2             # 重试间隔(秒)
RETRY_ON_PARSE_ERROR = True # JSON解析失败重试
RETRY_ON_API_ERROR = True   # API错误重试
FINAL_RETRY_ROUNDS = 2      # 最终批量重试轮数

# 唯一指定模型：Opus（质量最高）
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# 图片压缩配置
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB
COMPRESS_WIDTH = 800              # 压缩后宽度
COMPRESS_QUALITY = 85             # JPEG质量


def compress_image_for_api(image_path: str) -> Optional[str]:
    """
    如果图片太大，压缩成临时JPEG文件
    返回压缩后的临时文件路径，或None（无需压缩）
    """
    try:
        file_size = os.path.getsize(image_path)
        if file_size <= MAX_IMAGE_SIZE:
            return None
        
        # 打开并压缩
        img = Image.open(image_path)
        
        # 缩小
        ratio = COMPRESS_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((COMPRESS_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 转RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存临时文件
        temp_path = image_path + '.temp.jpg'
        img.save(temp_path, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)
        img.close()
        
        return temp_path
    except Exception:
        return None


class FastAnalyzer:
    """高速并行分析器（传统模式）"""
    
    def __init__(self, project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5):
        self.project_name = project_name
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        self.screens_folder = os.path.join(self.project_path, "Screens")
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
        # 已有结果（用于断点续传）
        self.existing_results = {}
        
        # 延迟导入分析器
        self.analyzer = None
    
    def _init_analyzer(self):
        """延迟初始化AI分析器"""
        if self.analyzer is None:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
            from ai_analyzer import AIScreenshotAnalyzer
            self.analyzer = AIScreenshotAnalyzer(model=self.model)
            if not self.analyzer.client:
                print("[ERROR] Failed to initialize API client!")
                return False
        return True
    
    def load_existing_results(self) -> Dict:
        """加载已有分析结果（断点续传）"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_results = data.get('results', {})
                    return self.existing_results
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")
        return {}
    
    def get_pending_screenshots(self) -> List[str]:
        """获取待分析的截图列表"""
        all_screenshots = sorted([
            f for f in os.listdir(self.screens_folder) 
            if f.lower().endswith('.png')
        ])
        
        # 排除已分析的
        pending = [f for f in all_screenshots if f not in self.existing_results]
        return pending
    
    def save_results(self, results: Dict, is_final: bool = False):
        """保存分析结果"""
        # 合并已有结果
        all_results = {**self.existing_results, **results}
        
        output = {
            'project_name': self.project_name,
            'total_screenshots': len(all_results),
            'analyzed_count': self.success_count + len(self.existing_results),
            'failed_count': self.fail_count,
            'results': all_results,
            'last_updated': datetime.now().isoformat(),
            'model': self.model
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        if is_final:
            print(f"\n[SAVED] {self.analysis_file}")
    
    def analyze_one(self, filename: str, retry_count: int = 0) -> Dict:
        """分析单张截图（线程安全，带自动重试和自动压缩）"""
        image_path = os.path.join(self.screens_folder, filename)
        compressed_path = None
        
        try:
            # 检查是否需要压缩
            compressed_path = compress_image_for_api(image_path)
            analyze_path = compressed_path if compressed_path else image_path
            
            result = self.analyzer.analyze_single(analyze_path)
            
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 检查是否需要重试
            error = result.get('error', '')
            should_retry = False
            
            if error:
                # JSON解析失败
                if RETRY_ON_PARSE_ERROR and 'parse' in error.lower():
                    should_retry = True
                # API错误（非404模型不存在）
                if RETRY_ON_API_ERROR and 'api error' in error.lower() and 'not_found' not in error.lower():
                    should_retry = True
            
            # 重试逻辑
            if should_retry and retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            
            return result
            
        except Exception as e:
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 异常重试
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                self.fail_count += 1
            
            return {
                'filename': filename,
                'screen_type': 'Unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def run(self) -> bool:
        """运行并行分析（传统模式）"""
        print("\n" + "=" * 70)
        print(f"  FAST ANALYZER (Legacy Mode) - {self.project_name}")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.screens_folder):
            print(f"[ERROR] Screens folder not found: {self.screens_folder}")
            return False
        
        # 加载已有结果
        self.load_existing_results()
        existing_count = len(self.existing_results)
        
        # 获取待分析列表
        pending = self.get_pending_screenshots()
        total_pending = len(pending)
        total_all = existing_count + total_pending
        
        print(f"\n  Total Screenshots: {total_all}")
        print(f"  Already Analyzed:  {existing_count} (will skip)")
        print(f"  Pending Analysis:  {total_pending}")
        print(f"  Concurrent:        {self.concurrent}")
        print(f"  Model:             {self.model}")
        
        if total_pending == 0:
            print("\n[DONE] All screenshots already analyzed!")
            return True
        
        # 预计时间（假设每张6秒，并行处理）
        estimated_time = (total_pending * 6) / self.concurrent
        print(f"  Estimated Time:    {int(estimated_time // 60)}m {int(estimated_time % 60)}s")
        print("=" * 70)
        
        # 初始化分析器
        if not self._init_analyzer():
            return False
        
        # 开始分析
        start_time = datetime.now()
        results = {}
        
        print(f"\n[START] {start_time.strftime('%H:%M:%S')}")
        print("-" * 70)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.analyze_one, f): f 
                for f in pending
            }
            
            completed = 0
            last_save = 0
            
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    # 进度显示
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    status = "OK" if not result.get('error') else "FAIL"
                    
                    # 计算时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total_pending - completed)
                    
                    # 进度条
                    pct = completed / total_pending
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total_pending} ({pct:.0%}) | {int(remaining)}s left | {filename[:20]}')
                    sys.stdout.flush()
                    
                    # 每10张详细输出
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total_pending}] {status} {filename[:30]:30s} -> {screen_type:12s} ({confidence:.0%})")
                    
                    # 自动保存
                    if completed - last_save >= AUTO_SAVE_INTERVAL:
                        self.save_results(results)
                        last_save = completed
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
        
        # 保存结果
        self.save_results(results)
        
        # 检查失败项，进行批量重试
        failed_items = [f for f, r in results.items() if r.get('error') or r.get('screen_type') == 'Unknown']
        
        if failed_items and FINAL_RETRY_ROUNDS > 0:
            print(f"\n\n[RETRY] {len(failed_items)} failed items, starting auto-retry...")
            results = self._retry_failed_items(results, failed_items)
        
        # 最终保存
        self.save_results(results, is_final=True)
        
        # 重新计算统计
        final_success = sum(1 for r in results.values() if not r.get('error') and r.get('screen_type') != 'Unknown')
        final_fail = len(results) - final_success
        
        # 统计
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "-" * 70)
        print(f"[DONE] Analysis complete!")
        print(f"  Success: {final_success}/{total_pending}")
        print(f"  Failed:  {final_fail}/{total_pending}")
        print(f"  Time:    {total_time:.1f}s ({total_time/max(1,total_pending):.2f}s per image)")
        print(f"  Speed:   {total_pending/max(1,total_time)*60:.1f} images/min")
        
        if final_fail > 0:
            print(f"\n[WARN] {final_fail} items still failed after retries")
        else:
            print(f"\n[OK] 100% success rate achieved!")
        
        return True
    
    def _retry_failed_items(self, results: Dict, failed_items: List[str]) -> Dict:
        """批量重试失败项（使用同一模型）"""
        
        for round_num in range(FINAL_RETRY_ROUNDS):
            if not failed_items:
                break
            
            print(f"\n[RETRY Round {round_num + 1}] Retrying {len(failed_items)} failed items...")
            
            retry_success = 0
            for filename in failed_items[:]:
                print(f"  Retrying: {filename}...", end=" ")
                
                old_fail = self.fail_count
                result = self.analyze_one(filename, retry_count=0)
                
                if not result.get('error') and result.get('screen_type') != 'Unknown':
                    results[filename] = result
                    failed_items.remove(filename)
                    retry_success += 1
                    self.fail_count = old_fail
                    self.success_count += 1
                    print("OK")
                else:
                    print("FAIL")
                
                time.sleep(1)
            
            print(f"  Round {round_num + 1}: {retry_success} recovered, {len(failed_items)} remaining")
            
            if not failed_items:
                print(f"\n[OK] All items recovered!")
                break
        
        return results
    
    def post_process(self):
        """后处理：生成structured_descriptions.json"""
        print("\n[POST] Generating structured_descriptions.json...")
        
        try:
            # 调用generate_structured.py
            import subprocess
            result = subprocess.run(
                ['python', 'generate_structured.py', self.project_name],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[OK] structured_descriptions.json generated")
            else:
                print(f"[WARN] {result.stderr}")
                
        except Exception as e:
            print(f"[WARN] Post-process error: {e}")


def run_smart_analysis(project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5) -> bool:
    """
    运行智能三层分析（新模式）
    
    Args:
        project_name: 项目名称
        model: AI模型
        concurrent: 并发数
    
    Returns:
        是否成功
    """
    try:
        from smart_analyzer import SmartAnalyzer
        
        analyzer = SmartAnalyzer(
            project_name=project_name,
            model=model,
            concurrent=concurrent,
            auto_fix=True,
            verbose=True
        )
        
        results = analyzer.run()
        
        if results:
            # 更新知识库
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from knowledge.learner import KnowledgeLearner
                
                learner = KnowledgeLearner()
                learner.learn_from_analysis(
                    project_name=project_name,
                    product_profile={
                        "app_category": analyzer.product_profile.app_category,
                        "sub_category": analyzer.product_profile.sub_category,
                        "target_users": analyzer.product_profile.target_users,
                        "core_value": analyzer.product_profile.core_value
                    },
                    flow_structure={
                        "stages": [s.name for s in analyzer.flow_structure.stages],
                        "paywall_position": analyzer.flow_structure.paywall_position,
                        "onboarding_length": analyzer.flow_structure.onboarding_length
                    },
                    results=results
                )
                print("\n[KNOWLEDGE] Updated knowledge base")
            except Exception as e:
                print(f"\n[WARN] Knowledge update skipped: {e}")
            
            return True
        
        return False
        
    except ImportError as e:
        print(f"[ERROR] Smart analyzer not available: {e}")
        print("[INFO] Falling back to legacy mode...")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fast AI Screenshot Analyzer")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--all", action="store_true", help="Analyze all pending projects")
    parser.add_argument("--legacy", action="store_true", help="Use legacy mode (no context)")
    parser.add_argument("--smart", action="store_true", help="Force smart mode (with context)")
    
    args = parser.parse_args()
    
    # 设置API Key
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not API_KEY:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_KEY = config.get("ANTHROPIC_API_KEY", "")
        
        if API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    if args.all:
        # 分析所有待处理项目
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects_dir = os.path.join(base_dir, "projects")
        
        for project_name in os.listdir(projects_dir):
            if project_name in ["null", "comparison_report.json", "comparison_report.md"]:
                continue
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                print(f"\n{'='*70}")
                print(f"Processing: {project_name}")
                print(f"{'='*70}")
                
                if args.legacy:
                    analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                    if analyzer.run():
                        analyzer.post_process()
                else:
                    if not run_smart_analysis(project_name, args.model, args.concurrent):
                        # 智能模式失败，回退到传统模式
                        analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                        if analyzer.run():
                            analyzer.post_process()
    else:
        # 分析单个项目
        if args.legacy:
            # 强制使用传统模式
            analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
            if analyzer.run():
                analyzer.post_process()
        elif args.smart:
            # 强制使用智能模式
            run_smart_analysis(args.project, args.model, args.concurrent)
        else:
            # 默认：尝试智能模式，失败则回退
            if not run_smart_analysis(args.project, args.model, args.concurrent):
                print("\n[INFO] Falling back to legacy mode...")
                analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
                if analyzer.run():
                    analyzer.post_process()
        


if __name__ == "__main__":
    main()

高速AI分析脚本 v2.0 - 集成智能三层分析架构
支持传统模式和智能模式两种分析方式
"""

import os
import sys
import json
import time
import threading
import io
import base64
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from PIL import Image

# 设置API Key
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 配置
DEFAULT_CONCURRENT = 5      # 默认并发数
MAX_CONCURRENT = 10         # 最大并发数
AUTO_SAVE_INTERVAL = 10     # 每分析N张自动保存
RETRY_ON_RATE_LIMIT = True  # 遇到限流自动重试

# 自动重试配置
MAX_RETRIES = 3             # 单张图片最大重试次数
RETRY_DELAY = 2             # 重试间隔(秒)
RETRY_ON_PARSE_ERROR = True # JSON解析失败重试
RETRY_ON_API_ERROR = True   # API错误重试
FINAL_RETRY_ROUNDS = 2      # 最终批量重试轮数

# 唯一指定模型：Opus（质量最高）
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# 图片压缩配置
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB
COMPRESS_WIDTH = 800              # 压缩后宽度
COMPRESS_QUALITY = 85             # JPEG质量


def compress_image_for_api(image_path: str) -> Optional[str]:
    """
    如果图片太大，压缩成临时JPEG文件
    返回压缩后的临时文件路径，或None（无需压缩）
    """
    try:
        file_size = os.path.getsize(image_path)
        if file_size <= MAX_IMAGE_SIZE:
            return None
        
        # 打开并压缩
        img = Image.open(image_path)
        
        # 缩小
        ratio = COMPRESS_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((COMPRESS_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 转RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存临时文件
        temp_path = image_path + '.temp.jpg'
        img.save(temp_path, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)
        img.close()
        
        return temp_path
    except Exception:
        return None


class FastAnalyzer:
    """高速并行分析器（传统模式）"""
    
    def __init__(self, project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5):
        self.project_name = project_name
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        self.screens_folder = os.path.join(self.project_path, "Screens")
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
        # 已有结果（用于断点续传）
        self.existing_results = {}
        
        # 延迟导入分析器
        self.analyzer = None
    
    def _init_analyzer(self):
        """延迟初始化AI分析器"""
        if self.analyzer is None:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
            from ai_analyzer import AIScreenshotAnalyzer
            self.analyzer = AIScreenshotAnalyzer(model=self.model)
            if not self.analyzer.client:
                print("[ERROR] Failed to initialize API client!")
                return False
        return True
    
    def load_existing_results(self) -> Dict:
        """加载已有分析结果（断点续传）"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_results = data.get('results', {})
                    return self.existing_results
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")
        return {}
    
    def get_pending_screenshots(self) -> List[str]:
        """获取待分析的截图列表"""
        all_screenshots = sorted([
            f for f in os.listdir(self.screens_folder) 
            if f.lower().endswith('.png')
        ])
        
        # 排除已分析的
        pending = [f for f in all_screenshots if f not in self.existing_results]
        return pending
    
    def save_results(self, results: Dict, is_final: bool = False):
        """保存分析结果"""
        # 合并已有结果
        all_results = {**self.existing_results, **results}
        
        output = {
            'project_name': self.project_name,
            'total_screenshots': len(all_results),
            'analyzed_count': self.success_count + len(self.existing_results),
            'failed_count': self.fail_count,
            'results': all_results,
            'last_updated': datetime.now().isoformat(),
            'model': self.model
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        if is_final:
            print(f"\n[SAVED] {self.analysis_file}")
    
    def analyze_one(self, filename: str, retry_count: int = 0) -> Dict:
        """分析单张截图（线程安全，带自动重试和自动压缩）"""
        image_path = os.path.join(self.screens_folder, filename)
        compressed_path = None
        
        try:
            # 检查是否需要压缩
            compressed_path = compress_image_for_api(image_path)
            analyze_path = compressed_path if compressed_path else image_path
            
            result = self.analyzer.analyze_single(analyze_path)
            
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 检查是否需要重试
            error = result.get('error', '')
            should_retry = False
            
            if error:
                # JSON解析失败
                if RETRY_ON_PARSE_ERROR and 'parse' in error.lower():
                    should_retry = True
                # API错误（非404模型不存在）
                if RETRY_ON_API_ERROR and 'api error' in error.lower() and 'not_found' not in error.lower():
                    should_retry = True
            
            # 重试逻辑
            if should_retry and retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            
            return result
            
        except Exception as e:
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 异常重试
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                self.fail_count += 1
            
            return {
                'filename': filename,
                'screen_type': 'Unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def run(self) -> bool:
        """运行并行分析（传统模式）"""
        print("\n" + "=" * 70)
        print(f"  FAST ANALYZER (Legacy Mode) - {self.project_name}")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.screens_folder):
            print(f"[ERROR] Screens folder not found: {self.screens_folder}")
            return False
        
        # 加载已有结果
        self.load_existing_results()
        existing_count = len(self.existing_results)
        
        # 获取待分析列表
        pending = self.get_pending_screenshots()
        total_pending = len(pending)
        total_all = existing_count + total_pending
        
        print(f"\n  Total Screenshots: {total_all}")
        print(f"  Already Analyzed:  {existing_count} (will skip)")
        print(f"  Pending Analysis:  {total_pending}")
        print(f"  Concurrent:        {self.concurrent}")
        print(f"  Model:             {self.model}")
        
        if total_pending == 0:
            print("\n[DONE] All screenshots already analyzed!")
            return True
        
        # 预计时间（假设每张6秒，并行处理）
        estimated_time = (total_pending * 6) / self.concurrent
        print(f"  Estimated Time:    {int(estimated_time // 60)}m {int(estimated_time % 60)}s")
        print("=" * 70)
        
        # 初始化分析器
        if not self._init_analyzer():
            return False
        
        # 开始分析
        start_time = datetime.now()
        results = {}
        
        print(f"\n[START] {start_time.strftime('%H:%M:%S')}")
        print("-" * 70)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.analyze_one, f): f 
                for f in pending
            }
            
            completed = 0
            last_save = 0
            
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    # 进度显示
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    status = "OK" if not result.get('error') else "FAIL"
                    
                    # 计算时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total_pending - completed)
                    
                    # 进度条
                    pct = completed / total_pending
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total_pending} ({pct:.0%}) | {int(remaining)}s left | {filename[:20]}')
                    sys.stdout.flush()
                    
                    # 每10张详细输出
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total_pending}] {status} {filename[:30]:30s} -> {screen_type:12s} ({confidence:.0%})")
                    
                    # 自动保存
                    if completed - last_save >= AUTO_SAVE_INTERVAL:
                        self.save_results(results)
                        last_save = completed
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
        
        # 保存结果
        self.save_results(results)
        
        # 检查失败项，进行批量重试
        failed_items = [f for f, r in results.items() if r.get('error') or r.get('screen_type') == 'Unknown']
        
        if failed_items and FINAL_RETRY_ROUNDS > 0:
            print(f"\n\n[RETRY] {len(failed_items)} failed items, starting auto-retry...")
            results = self._retry_failed_items(results, failed_items)
        
        # 最终保存
        self.save_results(results, is_final=True)
        
        # 重新计算统计
        final_success = sum(1 for r in results.values() if not r.get('error') and r.get('screen_type') != 'Unknown')
        final_fail = len(results) - final_success
        
        # 统计
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "-" * 70)
        print(f"[DONE] Analysis complete!")
        print(f"  Success: {final_success}/{total_pending}")
        print(f"  Failed:  {final_fail}/{total_pending}")
        print(f"  Time:    {total_time:.1f}s ({total_time/max(1,total_pending):.2f}s per image)")
        print(f"  Speed:   {total_pending/max(1,total_time)*60:.1f} images/min")
        
        if final_fail > 0:
            print(f"\n[WARN] {final_fail} items still failed after retries")
        else:
            print(f"\n[OK] 100% success rate achieved!")
        
        return True
    
    def _retry_failed_items(self, results: Dict, failed_items: List[str]) -> Dict:
        """批量重试失败项（使用同一模型）"""
        
        for round_num in range(FINAL_RETRY_ROUNDS):
            if not failed_items:
                break
            
            print(f"\n[RETRY Round {round_num + 1}] Retrying {len(failed_items)} failed items...")
            
            retry_success = 0
            for filename in failed_items[:]:
                print(f"  Retrying: {filename}...", end=" ")
                
                old_fail = self.fail_count
                result = self.analyze_one(filename, retry_count=0)
                
                if not result.get('error') and result.get('screen_type') != 'Unknown':
                    results[filename] = result
                    failed_items.remove(filename)
                    retry_success += 1
                    self.fail_count = old_fail
                    self.success_count += 1
                    print("OK")
                else:
                    print("FAIL")
                
                time.sleep(1)
            
            print(f"  Round {round_num + 1}: {retry_success} recovered, {len(failed_items)} remaining")
            
            if not failed_items:
                print(f"\n[OK] All items recovered!")
                break
        
        return results
    
    def post_process(self):
        """后处理：生成structured_descriptions.json"""
        print("\n[POST] Generating structured_descriptions.json...")
        
        try:
            # 调用generate_structured.py
            import subprocess
            result = subprocess.run(
                ['python', 'generate_structured.py', self.project_name],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[OK] structured_descriptions.json generated")
            else:
                print(f"[WARN] {result.stderr}")
                
        except Exception as e:
            print(f"[WARN] Post-process error: {e}")


def run_smart_analysis(project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5) -> bool:
    """
    运行智能三层分析（新模式）
    
    Args:
        project_name: 项目名称
        model: AI模型
        concurrent: 并发数
    
    Returns:
        是否成功
    """
    try:
        from smart_analyzer import SmartAnalyzer
        
        analyzer = SmartAnalyzer(
            project_name=project_name,
            model=model,
            concurrent=concurrent,
            auto_fix=True,
            verbose=True
        )
        
        results = analyzer.run()
        
        if results:
            # 更新知识库
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from knowledge.learner import KnowledgeLearner
                
                learner = KnowledgeLearner()
                learner.learn_from_analysis(
                    project_name=project_name,
                    product_profile={
                        "app_category": analyzer.product_profile.app_category,
                        "sub_category": analyzer.product_profile.sub_category,
                        "target_users": analyzer.product_profile.target_users,
                        "core_value": analyzer.product_profile.core_value
                    },
                    flow_structure={
                        "stages": [s.name for s in analyzer.flow_structure.stages],
                        "paywall_position": analyzer.flow_structure.paywall_position,
                        "onboarding_length": analyzer.flow_structure.onboarding_length
                    },
                    results=results
                )
                print("\n[KNOWLEDGE] Updated knowledge base")
            except Exception as e:
                print(f"\n[WARN] Knowledge update skipped: {e}")
            
            return True
        
        return False
        
    except ImportError as e:
        print(f"[ERROR] Smart analyzer not available: {e}")
        print("[INFO] Falling back to legacy mode...")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fast AI Screenshot Analyzer")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--all", action="store_true", help="Analyze all pending projects")
    parser.add_argument("--legacy", action="store_true", help="Use legacy mode (no context)")
    parser.add_argument("--smart", action="store_true", help="Force smart mode (with context)")
    
    args = parser.parse_args()
    
    # 设置API Key
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not API_KEY:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_KEY = config.get("ANTHROPIC_API_KEY", "")
        
        if API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    if args.all:
        # 分析所有待处理项目
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects_dir = os.path.join(base_dir, "projects")
        
        for project_name in os.listdir(projects_dir):
            if project_name in ["null", "comparison_report.json", "comparison_report.md"]:
                continue
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                print(f"\n{'='*70}")
                print(f"Processing: {project_name}")
                print(f"{'='*70}")
                
                if args.legacy:
                    analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                    if analyzer.run():
                        analyzer.post_process()
                else:
                    if not run_smart_analysis(project_name, args.model, args.concurrent):
                        # 智能模式失败，回退到传统模式
                        analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                        if analyzer.run():
                            analyzer.post_process()
    else:
        # 分析单个项目
        if args.legacy:
            # 强制使用传统模式
            analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
            if analyzer.run():
                analyzer.post_process()
        elif args.smart:
            # 强制使用智能模式
            run_smart_analysis(args.project, args.model, args.concurrent)
        else:
            # 默认：尝试智能模式，失败则回退
            if not run_smart_analysis(args.project, args.model, args.concurrent):
                print("\n[INFO] Falling back to legacy mode...")
                analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
                if analyzer.run():
                    analyzer.post_process()
        


if __name__ == "__main__":
    main()

高速AI分析脚本 v2.0 - 集成智能三层分析架构
支持传统模式和智能模式两种分析方式
"""

import os
import sys
import json
import time
import threading
import io
import base64
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from PIL import Image

# 设置API Key
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# 配置
DEFAULT_CONCURRENT = 5      # 默认并发数
MAX_CONCURRENT = 10         # 最大并发数
AUTO_SAVE_INTERVAL = 10     # 每分析N张自动保存
RETRY_ON_RATE_LIMIT = True  # 遇到限流自动重试

# 自动重试配置
MAX_RETRIES = 3             # 单张图片最大重试次数
RETRY_DELAY = 2             # 重试间隔(秒)
RETRY_ON_PARSE_ERROR = True # JSON解析失败重试
RETRY_ON_API_ERROR = True   # API错误重试
FINAL_RETRY_ROUNDS = 2      # 最终批量重试轮数

# 唯一指定模型：Opus（质量最高）
DEFAULT_MODEL = "claude-opus-4-5-20251101"

# 图片压缩配置
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB
COMPRESS_WIDTH = 800              # 压缩后宽度
COMPRESS_QUALITY = 85             # JPEG质量


def compress_image_for_api(image_path: str) -> Optional[str]:
    """
    如果图片太大，压缩成临时JPEG文件
    返回压缩后的临时文件路径，或None（无需压缩）
    """
    try:
        file_size = os.path.getsize(image_path)
        if file_size <= MAX_IMAGE_SIZE:
            return None
        
        # 打开并压缩
        img = Image.open(image_path)
        
        # 缩小
        ratio = COMPRESS_WIDTH / img.width
        new_height = int(img.height * ratio)
        img = img.resize((COMPRESS_WIDTH, new_height), Image.Resampling.LANCZOS)
        
        # 转RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 保存临时文件
        temp_path = image_path + '.temp.jpg'
        img.save(temp_path, 'JPEG', quality=COMPRESS_QUALITY, optimize=True)
        img.close()
        
        return temp_path
    except Exception:
        return None


class FastAnalyzer:
    """高速并行分析器（传统模式）"""
    
    def __init__(self, project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5):
        self.project_name = project_name
        self.model = model
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 路径设置
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.project_path = os.path.join(self.base_dir, "projects", project_name)
        self.screens_folder = os.path.join(self.project_path, "Screens")
        self.analysis_file = os.path.join(self.project_path, "ai_analysis.json")
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
        
        # 已有结果（用于断点续传）
        self.existing_results = {}
        
        # 延迟导入分析器
        self.analyzer = None
    
    def _init_analyzer(self):
        """延迟初始化AI分析器"""
        if self.analyzer is None:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
            from ai_analyzer import AIScreenshotAnalyzer
            self.analyzer = AIScreenshotAnalyzer(model=self.model)
            if not self.analyzer.client:
                print("[ERROR] Failed to initialize API client!")
                return False
        return True
    
    def load_existing_results(self) -> Dict:
        """加载已有分析结果（断点续传）"""
        if os.path.exists(self.analysis_file):
            try:
                with open(self.analysis_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.existing_results = data.get('results', {})
                    return self.existing_results
            except Exception as e:
                print(f"[WARN] Failed to load existing results: {e}")
        return {}
    
    def get_pending_screenshots(self) -> List[str]:
        """获取待分析的截图列表"""
        all_screenshots = sorted([
            f for f in os.listdir(self.screens_folder) 
            if f.lower().endswith('.png')
        ])
        
        # 排除已分析的
        pending = [f for f in all_screenshots if f not in self.existing_results]
        return pending
    
    def save_results(self, results: Dict, is_final: bool = False):
        """保存分析结果"""
        # 合并已有结果
        all_results = {**self.existing_results, **results}
        
        output = {
            'project_name': self.project_name,
            'total_screenshots': len(all_results),
            'analyzed_count': self.success_count + len(self.existing_results),
            'failed_count': self.fail_count,
            'results': all_results,
            'last_updated': datetime.now().isoformat(),
            'model': self.model
        }
        
        with open(self.analysis_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        if is_final:
            print(f"\n[SAVED] {self.analysis_file}")
    
    def analyze_one(self, filename: str, retry_count: int = 0) -> Dict:
        """分析单张截图（线程安全，带自动重试和自动压缩）"""
        image_path = os.path.join(self.screens_folder, filename)
        compressed_path = None
        
        try:
            # 检查是否需要压缩
            compressed_path = compress_image_for_api(image_path)
            analyze_path = compressed_path if compressed_path else image_path
            
            result = self.analyzer.analyze_single(analyze_path)
            
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 检查是否需要重试
            error = result.get('error', '')
            should_retry = False
            
            if error:
                # JSON解析失败
                if RETRY_ON_PARSE_ERROR and 'parse' in error.lower():
                    should_retry = True
                # API错误（非404模型不存在）
                if RETRY_ON_API_ERROR and 'api error' in error.lower() and 'not_found' not in error.lower():
                    should_retry = True
            
            # 重试逻辑
            if should_retry and retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            
            return result
            
        except Exception as e:
            # 清理压缩文件
            if compressed_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except:
                    pass
            
            # 异常重试
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return self.analyze_one(filename, retry_count + 1)
            
            with self.lock:
                self.fail_count += 1
            
            return {
                'filename': filename,
                'screen_type': 'Unknown',
                'error': str(e),
                'confidence': 0.0
            }
    
    def run(self) -> bool:
        """运行并行分析（传统模式）"""
        print("\n" + "=" * 70)
        print(f"  FAST ANALYZER (Legacy Mode) - {self.project_name}")
        print("=" * 70)
        
        # 检查项目
        if not os.path.exists(self.screens_folder):
            print(f"[ERROR] Screens folder not found: {self.screens_folder}")
            return False
        
        # 加载已有结果
        self.load_existing_results()
        existing_count = len(self.existing_results)
        
        # 获取待分析列表
        pending = self.get_pending_screenshots()
        total_pending = len(pending)
        total_all = existing_count + total_pending
        
        print(f"\n  Total Screenshots: {total_all}")
        print(f"  Already Analyzed:  {existing_count} (will skip)")
        print(f"  Pending Analysis:  {total_pending}")
        print(f"  Concurrent:        {self.concurrent}")
        print(f"  Model:             {self.model}")
        
        if total_pending == 0:
            print("\n[DONE] All screenshots already analyzed!")
            return True
        
        # 预计时间（假设每张6秒，并行处理）
        estimated_time = (total_pending * 6) / self.concurrent
        print(f"  Estimated Time:    {int(estimated_time // 60)}m {int(estimated_time % 60)}s")
        print("=" * 70)
        
        # 初始化分析器
        if not self._init_analyzer():
            return False
        
        # 开始分析
        start_time = datetime.now()
        results = {}
        
        print(f"\n[START] {start_time.strftime('%H:%M:%S')}")
        print("-" * 70)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(self.analyze_one, f): f 
                for f in pending
            }
            
            completed = 0
            last_save = 0
            
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    # 进度显示
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    status = "OK" if not result.get('error') else "FAIL"
                    
                    # 计算时间
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / completed
                    remaining = avg_time * (total_pending - completed)
                    
                    # 进度条
                    pct = completed / total_pending
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total_pending} ({pct:.0%}) | {int(remaining)}s left | {filename[:20]}')
                    sys.stdout.flush()
                    
                    # 每10张详细输出
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total_pending}] {status} {filename[:30]:30s} -> {screen_type:12s} ({confidence:.0%})")
                    
                    # 自动保存
                    if completed - last_save >= AUTO_SAVE_INTERVAL:
                        self.save_results(results)
                        last_save = completed
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
        
        # 保存结果
        self.save_results(results)
        
        # 检查失败项，进行批量重试
        failed_items = [f for f, r in results.items() if r.get('error') or r.get('screen_type') == 'Unknown']
        
        if failed_items and FINAL_RETRY_ROUNDS > 0:
            print(f"\n\n[RETRY] {len(failed_items)} failed items, starting auto-retry...")
            results = self._retry_failed_items(results, failed_items)
        
        # 最终保存
        self.save_results(results, is_final=True)
        
        # 重新计算统计
        final_success = sum(1 for r in results.values() if not r.get('error') and r.get('screen_type') != 'Unknown')
        final_fail = len(results) - final_success
        
        # 统计
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        print("\n" + "-" * 70)
        print(f"[DONE] Analysis complete!")
        print(f"  Success: {final_success}/{total_pending}")
        print(f"  Failed:  {final_fail}/{total_pending}")
        print(f"  Time:    {total_time:.1f}s ({total_time/max(1,total_pending):.2f}s per image)")
        print(f"  Speed:   {total_pending/max(1,total_time)*60:.1f} images/min")
        
        if final_fail > 0:
            print(f"\n[WARN] {final_fail} items still failed after retries")
        else:
            print(f"\n[OK] 100% success rate achieved!")
        
        return True
    
    def _retry_failed_items(self, results: Dict, failed_items: List[str]) -> Dict:
        """批量重试失败项（使用同一模型）"""
        
        for round_num in range(FINAL_RETRY_ROUNDS):
            if not failed_items:
                break
            
            print(f"\n[RETRY Round {round_num + 1}] Retrying {len(failed_items)} failed items...")
            
            retry_success = 0
            for filename in failed_items[:]:
                print(f"  Retrying: {filename}...", end=" ")
                
                old_fail = self.fail_count
                result = self.analyze_one(filename, retry_count=0)
                
                if not result.get('error') and result.get('screen_type') != 'Unknown':
                    results[filename] = result
                    failed_items.remove(filename)
                    retry_success += 1
                    self.fail_count = old_fail
                    self.success_count += 1
                    print("OK")
                else:
                    print("FAIL")
                
                time.sleep(1)
            
            print(f"  Round {round_num + 1}: {retry_success} recovered, {len(failed_items)} remaining")
            
            if not failed_items:
                print(f"\n[OK] All items recovered!")
                break
        
        return results
    
    def post_process(self):
        """后处理：生成structured_descriptions.json"""
        print("\n[POST] Generating structured_descriptions.json...")
        
        try:
            # 调用generate_structured.py
            import subprocess
            result = subprocess.run(
                ['python', 'generate_structured.py', self.project_name],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("[OK] structured_descriptions.json generated")
            else:
                print(f"[WARN] {result.stderr}")
                
        except Exception as e:
            print(f"[WARN] Post-process error: {e}")


def run_smart_analysis(project_name: str, model: str = DEFAULT_MODEL, concurrent: int = 5) -> bool:
    """
    运行智能三层分析（新模式）
    
    Args:
        project_name: 项目名称
        model: AI模型
        concurrent: 并发数
    
    Returns:
        是否成功
    """
    try:
        from smart_analyzer import SmartAnalyzer
        
        analyzer = SmartAnalyzer(
            project_name=project_name,
            model=model,
            concurrent=concurrent,
            auto_fix=True,
            verbose=True
        )
        
        results = analyzer.run()
        
        if results:
            # 更新知识库
            try:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from knowledge.learner import KnowledgeLearner
                
                learner = KnowledgeLearner()
                learner.learn_from_analysis(
                    project_name=project_name,
                    product_profile={
                        "app_category": analyzer.product_profile.app_category,
                        "sub_category": analyzer.product_profile.sub_category,
                        "target_users": analyzer.product_profile.target_users,
                        "core_value": analyzer.product_profile.core_value
                    },
                    flow_structure={
                        "stages": [s.name for s in analyzer.flow_structure.stages],
                        "paywall_position": analyzer.flow_structure.paywall_position,
                        "onboarding_length": analyzer.flow_structure.onboarding_length
                    },
                    results=results
                )
                print("\n[KNOWLEDGE] Updated knowledge base")
            except Exception as e:
                print(f"\n[WARN] Knowledge update skipped: {e}")
            
            return True
        
        return False
        
    except ImportError as e:
        print(f"[ERROR] Smart analyzer not available: {e}")
        print("[INFO] Falling back to legacy mode...")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fast AI Screenshot Analyzer")
    parser.add_argument("--project", type=str, required=True, help="Project name")
    parser.add_argument("--concurrent", "-c", type=int, default=5, help="Concurrent requests (1-10)")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Model name")
    parser.add_argument("--all", action="store_true", help="Analyze all pending projects")
    parser.add_argument("--legacy", action="store_true", help="Use legacy mode (no context)")
    parser.add_argument("--smart", action="store_true", help="Force smart mode (with context)")
    
    args = parser.parse_args()
    
    # 设置API Key
    global API_KEY
    API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    if not API_KEY:
        # 尝试从配置文件加载
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "api_keys.json"
        )
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                API_KEY = config.get("ANTHROPIC_API_KEY", "")
        
        if API_KEY:
            os.environ["ANTHROPIC_API_KEY"] = API_KEY
        else:
            print("[ERROR] Please set ANTHROPIC_API_KEY environment variable")
            return
    
    if args.all:
        # 分析所有待处理项目
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        projects_dir = os.path.join(base_dir, "projects")
        
        for project_name in os.listdir(projects_dir):
            if project_name in ["null", "comparison_report.json", "comparison_report.md"]:
                continue
            project_path = os.path.join(projects_dir, project_name)
            if os.path.isdir(project_path):
                print(f"\n{'='*70}")
                print(f"Processing: {project_name}")
                print(f"{'='*70}")
                
                if args.legacy:
                    analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                    if analyzer.run():
                        analyzer.post_process()
                else:
                    if not run_smart_analysis(project_name, args.model, args.concurrent):
                        # 智能模式失败，回退到传统模式
                        analyzer = FastAnalyzer(project_name, args.model, args.concurrent)
                        if analyzer.run():
                            analyzer.post_process()
    else:
        # 分析单个项目
        if args.legacy:
            # 强制使用传统模式
            analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
            if analyzer.run():
                analyzer.post_process()
        elif args.smart:
            # 强制使用智能模式
            run_smart_analysis(args.project, args.model, args.concurrent)
        else:
            # 默认：尝试智能模式，失败则回退
            if not run_smart_analysis(args.project, args.model, args.concurrent):
                print("\n[INFO] Falling back to legacy mode...")
                analyzer = FastAnalyzer(args.project, args.model, args.concurrent)
                if analyzer.run():
                    analyzer.post_process()
        


if __name__ == "__main__":
    main()
