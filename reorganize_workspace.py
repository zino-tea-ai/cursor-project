"""
工作区重组脚本
用于整理混乱的项目结构

运行方式：
  python reorganize_workspace.py --preview   # 预览变更（不执行）
  python reorganize_workspace.py --execute   # 执行重组
"""

import os
import sys

# 修复 Windows 控制台编码问题
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
import shutil
from pathlib import Path
from datetime import datetime

# 设置工作区根目录
WORKSPACE = Path(r"C:\Users\WIN\Desktop\Cursor Project")

# ============================================================
# 重组配置
# ============================================================

# 1. 可安全删除的垃圾文件
TRASH_FILES = [
    "nul",                                    # 空文件（Windows null设备）
    "database.db",                            # 空数据库
    "map_explorer",                           # 空文件夹
    "pob2-plus/nul",                          # 嵌套的空文件
    "pm-tool-v2/nul",                         # V2 里的空文件
    "pm-tool-v2/backend/nul",                 # V2 后端里的空文件
    "pm-tool-v2/frontend/nul",                # V2 前端里的空文件
    
    # === V1 版本相关（用户确认删除）===
    "PM_Screenshot_Tool",                     # V1 主目录（Flask 版本）⚠️ 大目录
    "PM_Test_Assistant",                      # PyQt6 测试助手（依赖 V1）
    "DEV_LOG.md",                             # V1 开发日志
    "PM_Assistant_Prompt.md",                 # V1 提示词文档
]

# 2. 需要移动的文件/文件夹
MOVES = {
    # === PM 工具 V2（移到 pm-tools/） ===
    # 注意：V1 (PM_Screenshot_Tool, PM_Test_Assistant) 已在 TRASH_FILES 中删除
    "pm-tool-v2": "pm-tools/v2",
    "UI_Design_Spec_Template.md": "pm-tools/docs/UI_Design_Spec_Template.md",
    "UI_Prompt_Templates.md": "pm-tools/docs/UI_Prompt_Templates.md",
    
    # === VitaFlow 相关（移到 vitaflow/） ===
    "vitaflow-replica": "vitaflow/app-replica",
    "vitaflow_clean_v4.jpeg": "vitaflow/design-iterations/vitaflow_clean_v4.jpeg",
    "vitaflow_dribbble_v3.jpeg": "vitaflow/design-iterations/vitaflow_dribbble_v3.jpeg",
    "vitaflow_improved_v1.jpeg": "vitaflow/design-iterations/vitaflow_improved_v1.jpeg",
    "vitaflow_premium_v2.jpeg": "vitaflow/design-iterations/vitaflow_premium_v2.jpeg",
    
    # === 竞品分析（移到 vitaflow/competitor-analysis/） ===
    "MFP_Analysis": "vitaflow/competitor-analysis/myfitnesspal",
    "Peloton_Analysis": "vitaflow/competitor-analysis/peloton",
    "video_analysis": "vitaflow/competitor-analysis/_video-analysis",
    "竞品分析_健康健身App.md": "vitaflow/competitor-analysis/竞品分析_健康健身App.md",
    
    # === POE2 相关（移到 poe2-tools/） ===
    "PathOfBuilding-PoE2": "poe2-tools/path-of-building",
    "pob2-plus": "poe2-tools/pob-plus",
    "pob2-poc": "poe2-tools/pob-poc",
    # POE Ninja 爬虫脚本
    "scrape_poe_ninja.py": "poe2-tools/ninja-scraper/scrape_poe_ninja.py",
    "scrape_poe_ninja_v2.py": "poe2-tools/ninja-scraper/scrape_poe_ninja_v2.py",
    "scrape_poe_ninja_v3.py": "poe2-tools/ninja-scraper/scrape_poe_ninja_v3.py",
    "scrape_poe_ninja_final.py": "poe2-tools/ninja-scraper/scrape_poe_ninja_final.py",
    # POE Ninja 数据文件
    "poe_ninja_shaman.html": "poe2-tools/ninja-scraper/output/poe_ninja_shaman.html",
    "poe_ninja_shaman.png": "poe2-tools/ninja-scraper/output/poe_ninja_shaman.png",
    "poe_ninja_shaman_v2.png": "poe2-tools/ninja-scraper/output/poe_ninja_shaman_v2.png",
    "poe_ninja_shaman_complete.json": "poe2-tools/ninja-scraper/output/poe_ninja_shaman_complete.json",
    "poe_ninja_shaman_data.json": "poe2-tools/ninja-scraper/output/poe_ninja_shaman_data.json",
    "poe_ninja_shaman_full.json": "poe2-tools/ninja-scraper/output/poe_ninja_shaman_full.json",
    "poe_ninja_build_detail.png": "poe2-tools/ninja-scraper/output/poe_ninja_build_detail.png",
    "poe_ninja_final.png": "poe2-tools/ninja-scraper/output/poe_ninja_final.png",
    "poe_ninja_heatmap.png": "poe2-tools/ninja-scraper/output/poe_ninja_heatmap.png",
    "poe_ninja_step1.png": "poe2-tools/ninja-scraper/output/poe_ninja_step1.png",
    
    # === YC 相关（移到 docs/yc/） ===
    "YC_2025_Analysis_Report.md": "docs/yc/YC_2025_Analysis_Report.md",
    "YC_Application_Final_Optimization.md": "docs/yc/YC_Application_Final_Optimization.md",
    "YC_Founder_Profile_Revisions.md": "docs/yc/YC_Founder_Profile_Revisions.md",
    "YC_NogicOS_Complete_Plan.md": "docs/yc/YC_NogicOS_Complete_Plan.md",
    "YC_Scoring_Framework.md": "docs/yc/YC_Scoring_Framework.md",
    "yc_companies.csv": "docs/yc/yc_companies.csv",
    
    # === 模板（移到 templates/） ===
    "zino-nextjs-template": "templates/nextjs-template",
    
    # === 独立脚本（移到 scripts/） ===
    "nano_banana_api.py": "scripts/api-tools/nano_banana_api.py",
    "nano_banana_20251219_052522.png": "scripts/api-tools/output/nano_banana_20251219_052522.png",
    "nano_banana_pro_20251219_052911.jpeg": "scripts/api-tools/output/nano_banana_pro_20251219_052911.jpeg",
    "test_openai_key.py": "scripts/api-tools/test_openai_key.py",
    "list_models.py": "scripts/api-tools/list_models.py",
    "extract_frames_with_ffmpeg.py": "scripts/video/extract_frames_with_ffmpeg.py",
    "ffmpeg.exe": "scripts/video/ffmpeg.exe",
    
    # === 通用文件（保留在根目录） ===
    # backup.bat, backup.py, env_example.txt - 保留
}

# 3. 需要创建的目录结构（即使为空）
CREATE_DIRS = [
    "pm-tools/docs",              # PM 工具文档
    "vitaflow/design-iterations",
    "vitaflow/competitor-analysis",
    "poe2-tools/ninja-scraper/output",
    "docs/yc",
    "scripts/api-tools/output",
    "scripts/video",
    "templates",
    "_archive",  # 归档旧项目
    "_temp",     # 临时文件
]


# ============================================================
# 执行函数
# ============================================================

def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_dir_size(path):
    """获取目录大小"""
    total = 0
    if path.is_file():
        return path.stat().st_size
    for item in path.rglob('*'):
        if item.is_file():
            total += item.stat().st_size
    return total


def preview_changes():
    """预览所有变更"""
    print("=" * 60)
    print("🔍 预览模式 - 不会执行任何操作")
    print("=" * 60)
    
    # 1. 删除列表
    print("\n🗑️  [1] 将删除的垃圾文件:")
    print("-" * 40)
    total_trash_size = 0
    for item in TRASH_FILES:
        path = WORKSPACE / item
        if path.exists():
            size = get_dir_size(path)
            total_trash_size += size
            icon = "📁" if path.is_dir() else "📄"
            print(f"  {icon} {item} ({format_size(size)})")
        else:
            print(f"  ⚠️  {item} (不存在，跳过)")
    print(f"\n  总计释放空间: {format_size(total_trash_size)}")
    
    # 2. 移动列表
    print("\n📦 [2] 将移动的文件/文件夹:")
    print("-" * 40)
    move_count = 0
    for src, dst in MOVES.items():
        src_path = WORKSPACE / src
        if src_path.exists():
            icon = "📁" if src_path.is_dir() else "📄"
            print(f"  {icon} {src}")
            print(f"     → {dst}")
            move_count += 1
        else:
            pass  # 不显示不存在的文件
    print(f"\n  总计移动: {move_count} 项")
    
    # 3. 创建目录
    print("\n📁 [3] 将创建的目录:")
    print("-" * 40)
    for dir_path in CREATE_DIRS:
        full_path = WORKSPACE / dir_path
        if not full_path.exists():
            print(f"  📁 {dir_path}")
    
    # 4. 最终结构预览
    print("\n🗂️  [4] 重组后的顶层结构:")
    print("-" * 40)
    final_structure = """
  Cursor Project/
  ├── 📁 pm-tools/              # PM 工具（仅 V2）
  │   ├── v2/                   # FastAPI + Next.js 版本
  │   └── docs/                 # PM 文档
  │
  ├── 📁 vitaflow/              # VitaFlow 产品
  │   ├── app-replica/          # App 复刻
  │   ├── design-iterations/    # 设计迭代图
  │   └── competitor-analysis/  # 竞品分析
  │       ├── myfitnesspal/
  │       ├── peloton/
  │       └── _video-analysis/
  │
  ├── 📁 poe2-tools/            # POE2 工具
  │   ├── path-of-building/
  │   ├── pob-plus/
  │   ├── pob-poc/
  │   └── ninja-scraper/
  │
  ├── 📁 docs/                  # 文档
  │   └── yc/                   # YC 申请资料
  │
  ├── 📁 templates/             # 代码模板
  │   └── nextjs-template/
  │
  ├── 📁 scripts/               # 独立脚本
  │   ├── api-tools/            # API 工具
  │   └── video/                # 视频处理
  │
  ├── 📁 _archive/              # 归档项目
  ├── 📁 _temp/                 # 临时文件
  │
  ├── 📄 backup.bat             # 备份脚本
  ├── 📄 backup.py
  └── 📄 env_example.txt
"""
    print(final_structure)
    
    print("\n" + "=" * 60)
    print("确认执行请运行: python reorganize_workspace.py --execute")
    print("=" * 60)


def execute_changes():
    """执行所有变更"""
    print("=" * 60)
    print("🚀 执行模式 - 开始重组")
    print("=" * 60)
    
    # 创建备份时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 创建目录结构
    print("\n📁 [1/3] 创建目录结构...")
    for dir_path in CREATE_DIRS:
        full_path = WORKSPACE / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ 创建: {dir_path}")
    
    # 2. 移动文件
    print("\n📦 [2/3] 移动文件...")
    move_success = 0
    move_fail = 0
    for src, dst in MOVES.items():
        src_path = WORKSPACE / src
        dst_path = WORKSPACE / dst
        
        if not src_path.exists():
            continue
        
        try:
            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 如果目标已存在，跳过
            if dst_path.exists():
                print(f"  ⚠️  跳过 (目标已存在): {src}")
                continue
            
            # 移动
            shutil.move(str(src_path), str(dst_path))
            print(f"  ✅ {src} → {dst}")
            move_success += 1
            
        except Exception as e:
            print(f"  ❌ 失败: {src} - {e}")
            move_fail += 1
    
    print(f"\n  成功: {move_success}, 失败: {move_fail}")
    
    # 3. 删除垃圾文件
    print("\n🗑️  [3/3] 清理垃圾文件...")
    for item in TRASH_FILES:
        path = WORKSPACE / item
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"  ✅ 删除: {item}")
            except Exception as e:
                print(f"  ❌ 删除失败: {item} - {e}")
    
    print("\n" + "=" * 60)
    print("✅ 重组完成！")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n请指定模式: --preview 或 --execute")
        return
    
    mode = sys.argv[1]
    
    if mode == "--preview":
        preview_changes()
    elif mode == "--execute":
        confirm = input("⚠️  即将执行重组操作，确认继续？(yes/no): ")
        if confirm.lower() == "yes":
            execute_changes()
        else:
            print("已取消")
    else:
        print(f"未知参数: {mode}")
        print("请使用 --preview 或 --execute")


if __name__ == "__main__":
    main()

