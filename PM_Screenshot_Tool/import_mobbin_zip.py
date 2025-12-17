"""
Mobbin 压缩包导入工具
从 Downloads 文件夹导入 Mobbin 下载的截图压缩包到项目中
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 配置
DOWNLOADS_FOLDER = r"C:\Users\WIN\Downloads"
PROJECTS_FOLDER = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects"

# App 名称映射（压缩包名称关键词 -> 项目文件夹）
APP_MAPPING = {
    "cal ai": "Cal_AI_Analysis",
    "calai": "Cal_AI_Analysis",
    "peloton": "Peloton_Analysis",
    "myfitnesspal": "MyFitnessPal_Analysis",
    "my fitness pal": "MyFitnessPal_Analysis",
    "flo": "Flo_Analysis",
    "strava": "Strava_Analysis",
    "calm": "Calm_Analysis",
    "headspace": "Headspace_Analysis",
    "ladder": "LADDER_Analysis",
    "fitbit": "Fitbit_Analysis",
    "runna": "Runna_Analysis",
    "noom": "Noom_Analysis",
    "yazio": "Yazio_Analysis",
}


def find_mobbin_zips():
    """查找 Downloads 里的 Mobbin 压缩包"""
    downloads = Path(DOWNLOADS_FOLDER)
    zips = []
    
    for f in downloads.glob("*.zip"):
        # Mobbin 压缩包通常包含 "ios" 和日期
        name_lower = f.name.lower()
        if "ios" in name_lower or any(app in name_lower for app in APP_MAPPING.keys()):
            zips.append(f)
    
    return sorted(zips, key=lambda x: x.stat().st_mtime, reverse=True)


def detect_app_name(zip_name):
    """从压缩包名称识别 App"""
    name_lower = zip_name.lower()
    for keyword, folder in APP_MAPPING.items():
        if keyword in name_lower:
            return folder
    return None


def import_zip(zip_path, target_folder=None):
    """导入压缩包到项目"""
    zip_name = zip_path.name
    
    # 自动检测或使用指定的目标文件夹
    if target_folder is None:
        target_folder = detect_app_name(zip_name)
        if target_folder is None:
            print(f"❌ 无法识别 App: {zip_name}")
            print("   请手动指定目标文件夹")
            return False
    
    # 创建目标路径
    target_path = Path(PROJECTS_FOLDER) / target_folder / "screens"
    target_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 导入: {zip_name}")
    print(f"   目标: {target_path}")
    
    # 解压
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # 获取所有 png 文件
        png_files = [f for f in zf.namelist() if f.lower().endswith('.png')]
        print(f"   发现 {len(png_files)} 张截图")
        
        for i, png_file in enumerate(png_files, 1):
            # 提取文件名
            original_name = os.path.basename(png_file)
            
            # 重命名为序号格式，保持排序
            # 从原始名称提取序号
            try:
                # "Cal AI ios Sep 2025 123.png" -> 123
                num_part = original_name.rsplit(' ', 1)[-1].replace('.png', '')
                num = int(num_part)
                new_name = f"{num:04d}.png"
            except:
                new_name = f"{i:04d}.png"
            
            target_file = target_path / new_name
            
            # 解压并重命名
            with zf.open(png_file) as src:
                with open(target_file, 'wb') as dst:
                    dst.write(src.read())
        
        print(f"   ✅ 已导入 {len(png_files)} 张截图")
    
    return True


def list_available_zips():
    """列出可导入的压缩包"""
    zips = find_mobbin_zips()
    
    if not zips:
        print("📂 Downloads 文件夹中没有找到 Mobbin 压缩包")
        return
    
    print("\n📂 发现以下压缩包:")
    print("-" * 60)
    
    for i, z in enumerate(zips, 1):
        size_mb = z.stat().st_size / (1024 * 1024)
        detected = detect_app_name(z.name)
        status = f"→ {detected}" if detected else "⚠️ 未识别"
        print(f"  {i}. {z.name}")
        print(f"     {size_mb:.1f} MB | {status}")
    
    return zips


def main():
    print("=" * 60)
    print("🎨 Mobbin 压缩包导入工具")
    print("=" * 60)
    
    zips = list_available_zips()
    
    if not zips:
        return
    
    print("\n" + "-" * 60)
    print("选项:")
    print("  输入序号 - 导入指定压缩包")
    print("  all     - 导入所有可识别的压缩包")
    print("  q       - 退出")
    print("-" * 60)
    
    while True:
        choice = input("\n请选择: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'all':
            for z in zips:
                if detect_app_name(z.name):
                    import_zip(z)
            print("\n✅ 批量导入完成!")
            break
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(zips):
                    import_zip(zips[idx])
                else:
                    print("❌ 无效序号")
            except ValueError:
                print("❌ 请输入有效选项")


if __name__ == "__main__":
    main()

