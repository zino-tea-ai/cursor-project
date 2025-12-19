# -*- coding: utf-8 -*-
"""
第一批：重分析旧产品 + 下载P0新产品
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# 配置
OLD_PRODUCTS = [
    'MyFitnessPal_Analysis',
    'Runna_Analysis', 
    'Strava_Analysis',
    'Flo_Analysis',
    'Cal_AI_-_Calorie_Tracker_Analysis'
]

NEW_P0_PRODUCTS = [
    'Peloton: Fitness & Workouts',
    'LADDER Strength Training Plans',
    'Fitbit: Health & Fitness',
    'Headspace: Meditation & Sleep',
    'Zwift: Indoor Cycling Fitness',
    'WeightWatchers Program',
    'Carbon - Macro Coach & Tracker'
]

def load_api_key():
    config_path = 'config/api_keys.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')
        return True
    return False

def reanalyze_old_products():
    """重新分析旧产品"""
    print("\n" + "=" * 70)
    print("  STEP 1: 重新分析旧产品（使用新系统）")
    print("=" * 70)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_analysis'))
    from smart_analyzer import SmartAnalyzer
    
    results = []
    for i, project in enumerate(OLD_PRODUCTS, 1):
        print(f"\n[{i}/{len(OLD_PRODUCTS)}] {project}")
        print("-" * 50)
        
        try:
            analyzer = SmartAnalyzer(project, concurrent=5)
            analyzer.run()
            results.append({'project': project, 'status': 'success'})
            print(f"[OK] {project} 分析完成")
        except Exception as e:
            results.append({'project': project, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {project}: {e}")
    
    return results

def download_new_products():
    """下载P0新产品"""
    print("\n" + "=" * 70)
    print("  STEP 2: 下载P0新产品")
    print("=" * 70)
    
    from smart_batch_download import SmartBatchDownloader
    
    downloader = SmartBatchDownloader()
    
    results = []
    for i, app_name in enumerate(NEW_P0_PRODUCTS, 1):
        print(f"\n[{i}/{len(NEW_P0_PRODUCTS)}] {app_name}")
        print("-" * 50)
        
        try:
            success = downloader.process_product(app_name)
            results.append({'app': app_name, 'status': 'success' if success else 'failed'})
        except Exception as e:
            results.append({'app': app_name, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {app_name}: {e}")
    
    return results

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("  批量处理 - 第一批")
    print("=" * 70)
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  旧产品重分析: {len(OLD_PRODUCTS)} 个")
    print(f"  新产品下载: {len(NEW_P0_PRODUCTS)} 个")
    print("=" * 70)
    
    # 加载API Key
    if not load_api_key():
        print("[ERROR] 无法加载API Key")
        return
    
    # Step 1: 重分析旧产品
    old_results = reanalyze_old_products()
    
    # Step 2: 下载新产品
    print("\n" + "!" * 70)
    print("  请确保Chrome已打开并登录screensdesign.com")
    print("!" * 70)
    input("  按回车键继续下载新产品...")
    
    new_results = download_new_products()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("  处理完成")
    print("=" * 70)
    print(f"  总耗时: {duration:.1f} 分钟")
    print()
    print("  旧产品重分析:")
    for r in old_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['project']}")
    print()
    print("  新产品下载:")
    for r in new_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['app']}")
    print("=" * 70)

if __name__ == "__main__":
    main()


"""
第一批：重分析旧产品 + 下载P0新产品
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# 配置
OLD_PRODUCTS = [
    'MyFitnessPal_Analysis',
    'Runna_Analysis', 
    'Strava_Analysis',
    'Flo_Analysis',
    'Cal_AI_-_Calorie_Tracker_Analysis'
]

NEW_P0_PRODUCTS = [
    'Peloton: Fitness & Workouts',
    'LADDER Strength Training Plans',
    'Fitbit: Health & Fitness',
    'Headspace: Meditation & Sleep',
    'Zwift: Indoor Cycling Fitness',
    'WeightWatchers Program',
    'Carbon - Macro Coach & Tracker'
]

def load_api_key():
    config_path = 'config/api_keys.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')
        return True
    return False

def reanalyze_old_products():
    """重新分析旧产品"""
    print("\n" + "=" * 70)
    print("  STEP 1: 重新分析旧产品（使用新系统）")
    print("=" * 70)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_analysis'))
    from smart_analyzer import SmartAnalyzer
    
    results = []
    for i, project in enumerate(OLD_PRODUCTS, 1):
        print(f"\n[{i}/{len(OLD_PRODUCTS)}] {project}")
        print("-" * 50)
        
        try:
            analyzer = SmartAnalyzer(project, concurrent=5)
            analyzer.run()
            results.append({'project': project, 'status': 'success'})
            print(f"[OK] {project} 分析完成")
        except Exception as e:
            results.append({'project': project, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {project}: {e}")
    
    return results

def download_new_products():
    """下载P0新产品"""
    print("\n" + "=" * 70)
    print("  STEP 2: 下载P0新产品")
    print("=" * 70)
    
    from smart_batch_download import SmartBatchDownloader
    
    downloader = SmartBatchDownloader()
    
    results = []
    for i, app_name in enumerate(NEW_P0_PRODUCTS, 1):
        print(f"\n[{i}/{len(NEW_P0_PRODUCTS)}] {app_name}")
        print("-" * 50)
        
        try:
            success = downloader.process_product(app_name)
            results.append({'app': app_name, 'status': 'success' if success else 'failed'})
        except Exception as e:
            results.append({'app': app_name, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {app_name}: {e}")
    
    return results

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("  批量处理 - 第一批")
    print("=" * 70)
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  旧产品重分析: {len(OLD_PRODUCTS)} 个")
    print(f"  新产品下载: {len(NEW_P0_PRODUCTS)} 个")
    print("=" * 70)
    
    # 加载API Key
    if not load_api_key():
        print("[ERROR] 无法加载API Key")
        return
    
    # Step 1: 重分析旧产品
    old_results = reanalyze_old_products()
    
    # Step 2: 下载新产品
    print("\n" + "!" * 70)
    print("  请确保Chrome已打开并登录screensdesign.com")
    print("!" * 70)
    input("  按回车键继续下载新产品...")
    
    new_results = download_new_products()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("  处理完成")
    print("=" * 70)
    print(f"  总耗时: {duration:.1f} 分钟")
    print()
    print("  旧产品重分析:")
    for r in old_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['project']}")
    print()
    print("  新产品下载:")
    for r in new_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['app']}")
    print("=" * 70)

if __name__ == "__main__":
    main()


"""
第一批：重分析旧产品 + 下载P0新产品
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# 配置
OLD_PRODUCTS = [
    'MyFitnessPal_Analysis',
    'Runna_Analysis', 
    'Strava_Analysis',
    'Flo_Analysis',
    'Cal_AI_-_Calorie_Tracker_Analysis'
]

NEW_P0_PRODUCTS = [
    'Peloton: Fitness & Workouts',
    'LADDER Strength Training Plans',
    'Fitbit: Health & Fitness',
    'Headspace: Meditation & Sleep',
    'Zwift: Indoor Cycling Fitness',
    'WeightWatchers Program',
    'Carbon - Macro Coach & Tracker'
]

def load_api_key():
    config_path = 'config/api_keys.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')
        return True
    return False

def reanalyze_old_products():
    """重新分析旧产品"""
    print("\n" + "=" * 70)
    print("  STEP 1: 重新分析旧产品（使用新系统）")
    print("=" * 70)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_analysis'))
    from smart_analyzer import SmartAnalyzer
    
    results = []
    for i, project in enumerate(OLD_PRODUCTS, 1):
        print(f"\n[{i}/{len(OLD_PRODUCTS)}] {project}")
        print("-" * 50)
        
        try:
            analyzer = SmartAnalyzer(project, concurrent=5)
            analyzer.run()
            results.append({'project': project, 'status': 'success'})
            print(f"[OK] {project} 分析完成")
        except Exception as e:
            results.append({'project': project, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {project}: {e}")
    
    return results

def download_new_products():
    """下载P0新产品"""
    print("\n" + "=" * 70)
    print("  STEP 2: 下载P0新产品")
    print("=" * 70)
    
    from smart_batch_download import SmartBatchDownloader
    
    downloader = SmartBatchDownloader()
    
    results = []
    for i, app_name in enumerate(NEW_P0_PRODUCTS, 1):
        print(f"\n[{i}/{len(NEW_P0_PRODUCTS)}] {app_name}")
        print("-" * 50)
        
        try:
            success = downloader.process_product(app_name)
            results.append({'app': app_name, 'status': 'success' if success else 'failed'})
        except Exception as e:
            results.append({'app': app_name, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {app_name}: {e}")
    
    return results

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("  批量处理 - 第一批")
    print("=" * 70)
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  旧产品重分析: {len(OLD_PRODUCTS)} 个")
    print(f"  新产品下载: {len(NEW_P0_PRODUCTS)} 个")
    print("=" * 70)
    
    # 加载API Key
    if not load_api_key():
        print("[ERROR] 无法加载API Key")
        return
    
    # Step 1: 重分析旧产品
    old_results = reanalyze_old_products()
    
    # Step 2: 下载新产品
    print("\n" + "!" * 70)
    print("  请确保Chrome已打开并登录screensdesign.com")
    print("!" * 70)
    input("  按回车键继续下载新产品...")
    
    new_results = download_new_products()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("  处理完成")
    print("=" * 70)
    print(f"  总耗时: {duration:.1f} 分钟")
    print()
    print("  旧产品重分析:")
    for r in old_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['project']}")
    print()
    print("  新产品下载:")
    for r in new_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['app']}")
    print("=" * 70)

if __name__ == "__main__":
    main()


"""
第一批：重分析旧产品 + 下载P0新产品
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# 配置
OLD_PRODUCTS = [
    'MyFitnessPal_Analysis',
    'Runna_Analysis', 
    'Strava_Analysis',
    'Flo_Analysis',
    'Cal_AI_-_Calorie_Tracker_Analysis'
]

NEW_P0_PRODUCTS = [
    'Peloton: Fitness & Workouts',
    'LADDER Strength Training Plans',
    'Fitbit: Health & Fitness',
    'Headspace: Meditation & Sleep',
    'Zwift: Indoor Cycling Fitness',
    'WeightWatchers Program',
    'Carbon - Macro Coach & Tracker'
]

def load_api_key():
    config_path = 'config/api_keys.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')
        return True
    return False

def reanalyze_old_products():
    """重新分析旧产品"""
    print("\n" + "=" * 70)
    print("  STEP 1: 重新分析旧产品（使用新系统）")
    print("=" * 70)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_analysis'))
    from smart_analyzer import SmartAnalyzer
    
    results = []
    for i, project in enumerate(OLD_PRODUCTS, 1):
        print(f"\n[{i}/{len(OLD_PRODUCTS)}] {project}")
        print("-" * 50)
        
        try:
            analyzer = SmartAnalyzer(project, concurrent=5)
            analyzer.run()
            results.append({'project': project, 'status': 'success'})
            print(f"[OK] {project} 分析完成")
        except Exception as e:
            results.append({'project': project, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {project}: {e}")
    
    return results

def download_new_products():
    """下载P0新产品"""
    print("\n" + "=" * 70)
    print("  STEP 2: 下载P0新产品")
    print("=" * 70)
    
    from smart_batch_download import SmartBatchDownloader
    
    downloader = SmartBatchDownloader()
    
    results = []
    for i, app_name in enumerate(NEW_P0_PRODUCTS, 1):
        print(f"\n[{i}/{len(NEW_P0_PRODUCTS)}] {app_name}")
        print("-" * 50)
        
        try:
            success = downloader.process_product(app_name)
            results.append({'app': app_name, 'status': 'success' if success else 'failed'})
        except Exception as e:
            results.append({'app': app_name, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {app_name}: {e}")
    
    return results

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("  批量处理 - 第一批")
    print("=" * 70)
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  旧产品重分析: {len(OLD_PRODUCTS)} 个")
    print(f"  新产品下载: {len(NEW_P0_PRODUCTS)} 个")
    print("=" * 70)
    
    # 加载API Key
    if not load_api_key():
        print("[ERROR] 无法加载API Key")
        return
    
    # Step 1: 重分析旧产品
    old_results = reanalyze_old_products()
    
    # Step 2: 下载新产品
    print("\n" + "!" * 70)
    print("  请确保Chrome已打开并登录screensdesign.com")
    print("!" * 70)
    input("  按回车键继续下载新产品...")
    
    new_results = download_new_products()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("  处理完成")
    print("=" * 70)
    print(f"  总耗时: {duration:.1f} 分钟")
    print()
    print("  旧产品重分析:")
    for r in old_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['project']}")
    print()
    print("  新产品下载:")
    for r in new_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['app']}")
    print("=" * 70)

if __name__ == "__main__":
    main()



"""
第一批：重分析旧产品 + 下载P0新产品
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# 配置
OLD_PRODUCTS = [
    'MyFitnessPal_Analysis',
    'Runna_Analysis', 
    'Strava_Analysis',
    'Flo_Analysis',
    'Cal_AI_-_Calorie_Tracker_Analysis'
]

NEW_P0_PRODUCTS = [
    'Peloton: Fitness & Workouts',
    'LADDER Strength Training Plans',
    'Fitbit: Health & Fitness',
    'Headspace: Meditation & Sleep',
    'Zwift: Indoor Cycling Fitness',
    'WeightWatchers Program',
    'Carbon - Macro Coach & Tracker'
]

def load_api_key():
    config_path = 'config/api_keys.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')
        return True
    return False

def reanalyze_old_products():
    """重新分析旧产品"""
    print("\n" + "=" * 70)
    print("  STEP 1: 重新分析旧产品（使用新系统）")
    print("=" * 70)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_analysis'))
    from smart_analyzer import SmartAnalyzer
    
    results = []
    for i, project in enumerate(OLD_PRODUCTS, 1):
        print(f"\n[{i}/{len(OLD_PRODUCTS)}] {project}")
        print("-" * 50)
        
        try:
            analyzer = SmartAnalyzer(project, concurrent=5)
            analyzer.run()
            results.append({'project': project, 'status': 'success'})
            print(f"[OK] {project} 分析完成")
        except Exception as e:
            results.append({'project': project, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {project}: {e}")
    
    return results

def download_new_products():
    """下载P0新产品"""
    print("\n" + "=" * 70)
    print("  STEP 2: 下载P0新产品")
    print("=" * 70)
    
    from smart_batch_download import SmartBatchDownloader
    
    downloader = SmartBatchDownloader()
    
    results = []
    for i, app_name in enumerate(NEW_P0_PRODUCTS, 1):
        print(f"\n[{i}/{len(NEW_P0_PRODUCTS)}] {app_name}")
        print("-" * 50)
        
        try:
            success = downloader.process_product(app_name)
            results.append({'app': app_name, 'status': 'success' if success else 'failed'})
        except Exception as e:
            results.append({'app': app_name, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {app_name}: {e}")
    
    return results

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("  批量处理 - 第一批")
    print("=" * 70)
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  旧产品重分析: {len(OLD_PRODUCTS)} 个")
    print(f"  新产品下载: {len(NEW_P0_PRODUCTS)} 个")
    print("=" * 70)
    
    # 加载API Key
    if not load_api_key():
        print("[ERROR] 无法加载API Key")
        return
    
    # Step 1: 重分析旧产品
    old_results = reanalyze_old_products()
    
    # Step 2: 下载新产品
    print("\n" + "!" * 70)
    print("  请确保Chrome已打开并登录screensdesign.com")
    print("!" * 70)
    input("  按回车键继续下载新产品...")
    
    new_results = download_new_products()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("  处理完成")
    print("=" * 70)
    print(f"  总耗时: {duration:.1f} 分钟")
    print()
    print("  旧产品重分析:")
    for r in old_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['project']}")
    print()
    print("  新产品下载:")
    for r in new_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['app']}")
    print("=" * 70)

if __name__ == "__main__":
    main()


"""
第一批：重分析旧产品 + 下载P0新产品
"""

import os
import sys
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

# 配置
OLD_PRODUCTS = [
    'MyFitnessPal_Analysis',
    'Runna_Analysis', 
    'Strava_Analysis',
    'Flo_Analysis',
    'Cal_AI_-_Calorie_Tracker_Analysis'
]

NEW_P0_PRODUCTS = [
    'Peloton: Fitness & Workouts',
    'LADDER Strength Training Plans',
    'Fitbit: Health & Fitness',
    'Headspace: Meditation & Sleep',
    'Zwift: Indoor Cycling Fitness',
    'WeightWatchers Program',
    'Carbon - Macro Coach & Tracker'
]

def load_api_key():
    config_path = 'config/api_keys.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        os.environ['ANTHROPIC_API_KEY'] = config.get('ANTHROPIC_API_KEY', '')
        return True
    return False

def reanalyze_old_products():
    """重新分析旧产品"""
    print("\n" + "=" * 70)
    print("  STEP 1: 重新分析旧产品（使用新系统）")
    print("=" * 70)
    
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_analysis'))
    from smart_analyzer import SmartAnalyzer
    
    results = []
    for i, project in enumerate(OLD_PRODUCTS, 1):
        print(f"\n[{i}/{len(OLD_PRODUCTS)}] {project}")
        print("-" * 50)
        
        try:
            analyzer = SmartAnalyzer(project, concurrent=5)
            analyzer.run()
            results.append({'project': project, 'status': 'success'})
            print(f"[OK] {project} 分析完成")
        except Exception as e:
            results.append({'project': project, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {project}: {e}")
    
    return results

def download_new_products():
    """下载P0新产品"""
    print("\n" + "=" * 70)
    print("  STEP 2: 下载P0新产品")
    print("=" * 70)
    
    from smart_batch_download import SmartBatchDownloader
    
    downloader = SmartBatchDownloader()
    
    results = []
    for i, app_name in enumerate(NEW_P0_PRODUCTS, 1):
        print(f"\n[{i}/{len(NEW_P0_PRODUCTS)}] {app_name}")
        print("-" * 50)
        
        try:
            success = downloader.process_product(app_name)
            results.append({'app': app_name, 'status': 'success' if success else 'failed'})
        except Exception as e:
            results.append({'app': app_name, 'status': 'failed', 'error': str(e)})
            print(f"[ERROR] {app_name}: {e}")
    
    return results

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("  批量处理 - 第一批")
    print("=" * 70)
    print(f"  开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  旧产品重分析: {len(OLD_PRODUCTS)} 个")
    print(f"  新产品下载: {len(NEW_P0_PRODUCTS)} 个")
    print("=" * 70)
    
    # 加载API Key
    if not load_api_key():
        print("[ERROR] 无法加载API Key")
        return
    
    # Step 1: 重分析旧产品
    old_results = reanalyze_old_products()
    
    # Step 2: 下载新产品
    print("\n" + "!" * 70)
    print("  请确保Chrome已打开并登录screensdesign.com")
    print("!" * 70)
    input("  按回车键继续下载新产品...")
    
    new_results = download_new_products()
    
    # 总结
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    print("\n" + "=" * 70)
    print("  处理完成")
    print("=" * 70)
    print(f"  总耗时: {duration:.1f} 分钟")
    print()
    print("  旧产品重分析:")
    for r in old_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['project']}")
    print()
    print("  新产品下载:")
    for r in new_results:
        status = "✓" if r['status'] == 'success' else "✗"
        print(f"    {status} {r['app']}")
    print("=" * 70)

if __name__ == "__main__":
    main()










































