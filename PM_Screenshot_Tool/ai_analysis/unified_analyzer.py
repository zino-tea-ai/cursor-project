# -*- coding: utf-8 -*-
"""
统一分析器 - 支持多模型切换
自动选择最优模型，支持 Claude 和 OpenAI
"""

import os
import json
import time
import sys
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Literal

# 配置
DEFAULT_CONCURRENT = 5
MAX_CONCURRENT = 10
AUTO_SAVE_INTERVAL = 10


# ============================================================
# 模型配置
# ============================================================

PROVIDER_MODELS = {
    'claude': {
        'fast': 'claude-3-5-haiku-latest',      # 批量初筛 - 最便宜
        'standard': 'claude-sonnet-4-20250514',  # 常规分析 - 平衡
        'deep': 'claude-opus-4-5-20251101',      # 深度分析 - 最强推理
    },
    'openai': {
        'fast': 'gpt-4o-mini',       # 批量初筛
        'standard': 'gpt-4o',        # 常规分析
        'deep': 'gpt-4o',            # 深度分析（GPT-5.2可用时更新）
    }
}

# 任务类型推荐的模型配置
TASK_RECOMMENDATIONS = {
    'batch_classify': {'provider': 'claude', 'tier': 'fast'},      # 批量分类 - 用Haiku最省钱
    'deep_analysis': {'provider': 'claude', 'tier': 'standard'},   # 深度分析 - 用Sonnet
    'verification': {'provider': 'claude', 'tier': 'deep'},        # 关键验证 - 用Opus
    'report_summary': {'provider': 'openai', 'tier': 'deep'},      # 报告汇总 - 用GPT(大上下文)
    'design_generation': {'provider': 'openai', 'tier': 'deep'},   # 设计生成 - 用GPT
}


class UnifiedAnalyzer:
    """
    统一分析器 - 支持 Claude 和 OpenAI 双引擎
    
    使用示例:
        # 自动选择模型
        analyzer = UnifiedAnalyzer(task='batch_classify')
        
        # 指定模型
        analyzer = UnifiedAnalyzer(provider='openai', tier='standard')
        
        # 分析截图
        result = analyzer.analyze_single('screenshot.png')
    """
    
    def __init__(
        self,
        provider: Literal['claude', 'openai', 'auto'] = 'auto',
        tier: Literal['fast', 'standard', 'deep'] = 'standard',
        task: Optional[str] = None,
        model: Optional[str] = None,
        concurrent: int = 5
    ):
        """
        初始化统一分析器
        
        Args:
            provider: 提供商 - claude/openai/auto
            tier: 模型层级 - fast/standard/deep
            task: 任务类型 - 自动选择最优配置
            model: 直接指定模型名称（覆盖其他设置）
            concurrent: 并发数
        """
        # 如果指定了任务类型，使用推荐配置
        if task and task in TASK_RECOMMENDATIONS:
            rec = TASK_RECOMMENDATIONS[task]
            provider = rec['provider']
            tier = rec['tier']
            print(f"[AUTO] Task '{task}' -> {provider}/{tier}")
        
        # auto模式默认用claude
        if provider == 'auto':
            provider = 'claude'
        
        self.provider = provider
        self.tier = tier
        self.model = model or PROVIDER_MODELS[provider][tier]
        self.concurrent = min(concurrent, MAX_CONCURRENT)
        
        # 底层分析器
        self._analyzer = None
        self._init_analyzer()
        
        # 统计
        self.success_count = 0
        self.fail_count = 0
        self.lock = threading.Lock()
    
    def _init_analyzer(self):
        """初始化底层分析器"""
        if self.provider == 'claude':
            try:
                from ai_analyzer import AIScreenshotAnalyzer
                self._analyzer = AIScreenshotAnalyzer(model=self.model)
                print(f"[OK] Unified Analyzer (Claude: {self.model})")
            except Exception as e:
                print(f"[ERROR] Failed to init Claude analyzer: {e}")
        
        elif self.provider == 'openai':
            try:
                from openai_analyzer import OpenAIScreenshotAnalyzer
                self._analyzer = OpenAIScreenshotAnalyzer(model=self.model, tier=self.tier)
                print(f"[OK] Unified Analyzer (OpenAI: {self.model})")
            except Exception as e:
                print(f"[ERROR] Failed to init OpenAI analyzer: {e}")
    
    @property
    def is_ready(self) -> bool:
        """检查分析器是否就绪"""
        if self._analyzer is None:
            return False
        if self.provider == 'claude':
            return self._analyzer.client is not None
        elif self.provider == 'openai':
            return self._analyzer.client is not None
        return False
    
    def analyze_single(self, image_path: str) -> Dict:
        """
        分析单张截图
        
        Args:
            image_path: 图片路径
        
        Returns:
            分析结果字典
        """
        if not self.is_ready:
            return {
                "filename": os.path.basename(image_path),
                "error": "Analyzer not ready",
                "provider": self.provider,
                "model": self.model
            }
        
        result = self._analyzer.analyze_single(image_path)
        
        # 添加统一字段
        result['provider'] = self.provider
        result['model'] = self.model
        result['tier'] = self.tier
        
        return result
    
    def analyze_batch(
        self,
        image_folder: str,
        output_file: Optional[str] = None,
        delay: float = 0.3,
        use_parallel: bool = True
    ) -> Dict:
        """
        批量分析截图
        
        Args:
            image_folder: 图片文件夹
            output_file: 输出文件路径
            delay: API调用间隔
            use_parallel: 是否并行处理
        
        Returns:
            批量分析结果
        """
        if use_parallel:
            return self._analyze_batch_parallel(image_folder, output_file)
        else:
            return self._analyzer.analyze_batch(image_folder, output_file, delay)
    
    def _analyze_batch_parallel(
        self,
        image_folder: str,
        output_file: Optional[str] = None
    ) -> Dict:
        """并行批量分析"""
        start_time = datetime.now()
        
        # 获取图片列表
        image_files = sorted([
            f for f in os.listdir(image_folder)
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ])
        
        total = len(image_files)
        results = {}
        
        print(f"\n{'=' * 70}")
        print(f"  UNIFIED ANALYZER - Parallel Mode")
        print(f"{'=' * 70}")
        print(f"  Provider:    {self.provider}")
        print(f"  Model:       {self.model}")
        print(f"  Tier:        {self.tier}")
        print(f"  Concurrent:  {self.concurrent}")
        print(f"  Total:       {total} screenshots")
        print(f"{'=' * 70}\n")
        
        if not self.is_ready:
            print("[ERROR] Analyzer not ready!")
            return {"error": "Analyzer not ready"}
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            future_to_file = {
                executor.submit(self._analyze_one, os.path.join(image_folder, f)): f
                for f in image_files
            }
            
            completed = 0
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed += 1
                
                try:
                    result = future.result()
                    results[filename] = result
                    
                    status = "OK" if not result.get('error') else "FAIL"
                    screen_type = result.get('screen_type', 'Unknown')
                    confidence = result.get('confidence', 0)
                    
                    # 进度显示
                    pct = completed / total
                    bar_len = 40
                    filled = int(bar_len * pct)
                    bar = '=' * filled + '-' * (bar_len - filled)
                    
                    sys.stdout.write(f'\r[{bar}] {completed}/{total} ({pct:.0%})')
                    sys.stdout.flush()
                    
                    if completed % 10 == 0:
                        print(f"\n  [{completed:3d}/{total}] {status} {filename[:30]:30s} -> {screen_type}")
                        
                except Exception as e:
                    print(f"\n[ERROR] {filename}: {e}")
                    results[filename] = {"error": str(e), "filename": filename}
        
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # 统计
        success = sum(1 for r in results.values() if not r.get('error'))
        failed = total - success
        
        batch_result = {
            "project_name": os.path.basename(image_folder),
            "total_screenshots": total,
            "analyzed_count": success,
            "failed_count": failed,
            "results": results,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "total_time": total_time,
            "provider": self.provider,
            "model": self.model,
            "tier": self.tier
        }
        
        # 保存结果
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(batch_result, f, ensure_ascii=False, indent=2)
            print(f"\n\n[SAVED] {output_file}")
        
        print(f"\n{'=' * 70}")
        print(f"[DONE] {success}/{total} success | {total_time:.1f}s | {total/max(1,total_time)*60:.1f} img/min")
        print(f"{'=' * 70}")
        
        return batch_result
    
    def _analyze_one(self, image_path: str) -> Dict:
        """分析单张（用于并行）"""
        try:
            result = self.analyze_single(image_path)
            with self.lock:
                if result.get('error'):
                    self.fail_count += 1
                else:
                    self.success_count += 1
            return result
        except Exception as e:
            with self.lock:
                self.fail_count += 1
            return {
                "filename": os.path.basename(image_path),
                "error": str(e),
                "provider": self.provider
            }
    
    @staticmethod
    def compare_providers(image_path: str) -> Dict:
        """
        对比两个提供商的分析结果
        
        Args:
            image_path: 图片路径
        
        Returns:
            对比结果
        """
        results = {}
        
        print(f"\n[COMPARE] Analyzing with both providers...")
        print(f"  Image: {os.path.basename(image_path)}\n")
        
        for provider in ['claude', 'openai']:
            print(f"  [{provider.upper()}] Analyzing...")
            try:
                analyzer = UnifiedAnalyzer(provider=provider, tier='standard')
                result = analyzer.analyze_single(image_path)
                results[provider] = result
                print(f"  [{provider.upper()}] -> {result.get('screen_type', 'Unknown')} ({result.get('confidence', 0):.0%})")
            except Exception as e:
                results[provider] = {"error": str(e)}
                print(f"  [{provider.upper()}] Error: {e}")
        
        # 对比
        print(f"\n{'=' * 50}")
        print("  COMPARISON")
        print(f"{'=' * 50}")
        
        claude_result = results.get('claude', {})
        openai_result = results.get('openai', {})
        
        print(f"  Screen Type:")
        print(f"    Claude: {claude_result.get('screen_type', 'N/A')}")
        print(f"    OpenAI: {openai_result.get('screen_type', 'N/A')}")
        
        print(f"\n  Confidence:")
        print(f"    Claude: {claude_result.get('confidence', 0):.0%}")
        print(f"    OpenAI: {openai_result.get('confidence', 0):.0%}")
        
        print(f"\n  Analysis Time:")
        print(f"    Claude: {claude_result.get('analysis_time', 0):.2f}s")
        print(f"    OpenAI: {openai_result.get('analysis_time', 0):.2f}s")
        
        # 判断一致性
        same_type = claude_result.get('screen_type') == openai_result.get('screen_type')
        print(f"\n  Agreement: {'[OK] Same' if same_type else '[DIFF] Different'}")
        
        return {
            "image": image_path,
            "results": results,
            "agreement": same_type
        }


# ============================================================
# 快捷函数
# ============================================================

def quick_analyze(image_path: str, task: str = None) -> Dict:
    """
    快速分析截图
    
    Args:
        image_path: 图片路径
        task: 任务类型（可选）
    """
    analyzer = UnifiedAnalyzer(task=task)
    return analyzer.analyze_single(image_path)


def batch_analyze(
    project_name: str,
    provider: str = 'claude',
    tier: str = 'standard',
    concurrent: int = 5
) -> Dict:
    """
    批量分析项目
    
    Args:
        project_name: 项目名称
        provider: 提供商
        tier: 模型层级
        concurrent: 并发数
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_dir, "projects", project_name)
    screens_folder = os.path.join(project_path, "Screens")
    output_file = os.path.join(project_path, f"analysis_{provider}.json")
    
    analyzer = UnifiedAnalyzer(provider=provider, tier=tier, concurrent=concurrent)
    return analyzer.analyze_batch(screens_folder, output_file)


# ============================================================
# 命令行入口
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="统一分析器 - 支持多模型切换")
    parser.add_argument("--image", type=str, help="单张图片路径")
    parser.add_argument("--project", type=str, help="项目名称")
    parser.add_argument("--folder", type=str, help="图片文件夹路径")
    parser.add_argument("--provider", "-p", type=str, default="claude",
                        choices=['claude', 'openai', 'auto'],
                        help="AI提供商")
    parser.add_argument("--tier", "-t", type=str, default="standard",
                        choices=['fast', 'standard', 'deep'],
                        help="模型层级")
    parser.add_argument("--task", type=str,
                        choices=['batch_classify', 'deep_analysis', 'verification', 
                                'report_summary', 'design_generation'],
                        help="任务类型（自动选择最优模型）")
    parser.add_argument("--concurrent", "-c", type=int, default=5,
                        help="并发数")
    parser.add_argument("--compare", action="store_true",
                        help="对比两个提供商的结果")
    parser.add_argument("--output", "-o", type=str, help="输出文件路径")
    
    args = parser.parse_args()
    
    if args.compare and args.image:
        # 对比模式
        UnifiedAnalyzer.compare_providers(args.image)
    
    elif args.image:
        # 单图分析
        analyzer = UnifiedAnalyzer(
            provider=args.provider,
            tier=args.tier,
            task=args.task
        )
        result = analyzer.analyze_single(args.image)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.project:
        # 项目分析
        result = batch_analyze(
            args.project,
            provider=args.provider,
            tier=args.tier,
            concurrent=args.concurrent
        )
    
    elif args.folder:
        # 文件夹分析
        analyzer = UnifiedAnalyzer(
            provider=args.provider,
            tier=args.tier,
            task=args.task,
            concurrent=args.concurrent
        )
        output = args.output or os.path.join(args.folder, f"analysis_{args.provider}.json")
        analyzer.analyze_batch(args.folder, output)
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  # 单图分析（使用Claude）")
        print("  python unified_analyzer.py --image screenshot.png")
        print("")
        print("  # 单图分析（使用OpenAI）")
        print("  python unified_analyzer.py --image screenshot.png -p openai")
        print("")
        print("  # 对比两个提供商")
        print("  python unified_analyzer.py --image screenshot.png --compare")
        print("")
        print("  # 批量分析项目")
        print("  python unified_analyzer.py --project Calm -p claude -t fast -c 5")
        print("")
        print("  # 使用任务类型自动选择模型")
        print("  python unified_analyzer.py --project Calm --task batch_classify")

















