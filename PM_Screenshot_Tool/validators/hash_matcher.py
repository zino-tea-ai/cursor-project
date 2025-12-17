# -*- coding: utf-8 -*-
"""
图片哈希匹配器
用于建立 Downloads (原始顺序) 和 Screens (分类后) 的对应关系
"""

import os
import hashlib
from PIL import Image
import io


def compute_image_hash(image_path: str) -> str:
    """
    计算图片的内容哈希
    使用感知哈希，对轻微的尺寸变化不敏感
    """
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式和尺寸进行比较
            img = img.convert('RGB')
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            
            # 计算像素数据的哈希
            pixels = list(img.getdata())
            pixel_str = ''.join([f'{r}{g}{b}' for r, g, b in pixels])
            return hashlib.md5(pixel_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算哈希 {image_path}: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希（精确匹配）"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算文件哈希 {file_path}: {e}")
        return None


def build_hash_index(folder_path: str, use_image_hash: bool = True) -> dict:
    """
    为文件夹中的所有图片建立哈希索引
    
    Returns:
        {hash: filename, ...}
    """
    index = {}
    
    if not os.path.exists(folder_path):
        return index
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        if use_image_hash:
            file_hash = compute_image_hash(filepath)
        else:
            file_hash = compute_file_hash(filepath)
        
        if file_hash:
            index[file_hash] = filename
    
    return index


def match_downloads_to_screens(project_path: str) -> dict:
    """
    匹配 Downloads 和 Screens 文件夹中的图片
    
    Returns:
        {
            "Screen_001.png": "02_Welcome_03.png",  # Downloads -> Screens
            "Screen_002.png": "02_Welcome_01.png",
            ...
        }
    """
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path) or not os.path.exists(screens_path):
        print(f"[ERROR] 缺少必要文件夹: Downloads或Screens")
        return {}
    
    print("[MATCH] Computing Downloads hashes...")
    downloads_index = {}
    downloads_files = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    
    for filename in downloads_files:
        filepath = os.path.join(downloads_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            downloads_index[filename] = file_hash
    
    print(f"       Downloads: {len(downloads_index)} files")
    
    print("[MATCH] Computing Screens hashes...")
    screens_hash_to_name = {}
    screens_files = [f for f in os.listdir(screens_path) if f.endswith('.png')]
    
    for filename in screens_files:
        filepath = os.path.join(screens_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            screens_hash_to_name[file_hash] = filename
    
    print(f"       Screens: {len(screens_hash_to_name)} files")
    
    # 建立映射
    mapping = {}
    unmatched = []
    
    for download_name, download_hash in downloads_index.items():
        if download_hash in screens_hash_to_name:
            mapping[download_name] = screens_hash_to_name[download_hash]
        else:
            unmatched.append(download_name)
    
    print(f"[MATCH] Matched: {len(mapping)} files")
    if unmatched:
        print(f"[MATCH] Unmatched: {len(unmatched)} files")
    
    return mapping


def get_original_order(project_path: str) -> list:
    """
    获取原始下载顺序
    
    Returns:
        ["Screen_001.png", "Screen_002.png", ...]
    """
    downloads_path = os.path.join(project_path, "Downloads")
    
    if not os.path.exists(downloads_path):
        return []
    
    files = [f for f in os.listdir(downloads_path) if f.endswith('.png')]
    return sorted(files)  # Screen_001, Screen_002, ... 自然排序


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试哈希匹配器: {project}")
    print('='*60)
    
    mapping = match_downloads_to_screens(project_path)
    
    print(f"\n前10个映射:")
    for i, (download, screen) in enumerate(sorted(mapping.items())[:10]):
        print(f"  {download} -> {screen}")


图片哈希匹配器
用于建立 Downloads (原始顺序) 和 Screens (分类后) 的对应关系
"""

import os
import hashlib
from PIL import Image
import io


def compute_image_hash(image_path: str) -> str:
    """
    计算图片的内容哈希
    使用感知哈希，对轻微的尺寸变化不敏感
    """
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式和尺寸进行比较
            img = img.convert('RGB')
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            
            # 计算像素数据的哈希
            pixels = list(img.getdata())
            pixel_str = ''.join([f'{r}{g}{b}' for r, g, b in pixels])
            return hashlib.md5(pixel_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算哈希 {image_path}: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希（精确匹配）"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算文件哈希 {file_path}: {e}")
        return None


def build_hash_index(folder_path: str, use_image_hash: bool = True) -> dict:
    """
    为文件夹中的所有图片建立哈希索引
    
    Returns:
        {hash: filename, ...}
    """
    index = {}
    
    if not os.path.exists(folder_path):
        return index
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        if use_image_hash:
            file_hash = compute_image_hash(filepath)
        else:
            file_hash = compute_file_hash(filepath)
        
        if file_hash:
            index[file_hash] = filename
    
    return index


def match_downloads_to_screens(project_path: str) -> dict:
    """
    匹配 Downloads 和 Screens 文件夹中的图片
    
    Returns:
        {
            "Screen_001.png": "02_Welcome_03.png",  # Downloads -> Screens
            "Screen_002.png": "02_Welcome_01.png",
            ...
        }
    """
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path) or not os.path.exists(screens_path):
        print(f"[ERROR] 缺少必要文件夹: Downloads或Screens")
        return {}
    
    print("[MATCH] Computing Downloads hashes...")
    downloads_index = {}
    downloads_files = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    
    for filename in downloads_files:
        filepath = os.path.join(downloads_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            downloads_index[filename] = file_hash
    
    print(f"       Downloads: {len(downloads_index)} files")
    
    print("[MATCH] Computing Screens hashes...")
    screens_hash_to_name = {}
    screens_files = [f for f in os.listdir(screens_path) if f.endswith('.png')]
    
    for filename in screens_files:
        filepath = os.path.join(screens_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            screens_hash_to_name[file_hash] = filename
    
    print(f"       Screens: {len(screens_hash_to_name)} files")
    
    # 建立映射
    mapping = {}
    unmatched = []
    
    for download_name, download_hash in downloads_index.items():
        if download_hash in screens_hash_to_name:
            mapping[download_name] = screens_hash_to_name[download_hash]
        else:
            unmatched.append(download_name)
    
    print(f"[MATCH] Matched: {len(mapping)} files")
    if unmatched:
        print(f"[MATCH] Unmatched: {len(unmatched)} files")
    
    return mapping


def get_original_order(project_path: str) -> list:
    """
    获取原始下载顺序
    
    Returns:
        ["Screen_001.png", "Screen_002.png", ...]
    """
    downloads_path = os.path.join(project_path, "Downloads")
    
    if not os.path.exists(downloads_path):
        return []
    
    files = [f for f in os.listdir(downloads_path) if f.endswith('.png')]
    return sorted(files)  # Screen_001, Screen_002, ... 自然排序


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试哈希匹配器: {project}")
    print('='*60)
    
    mapping = match_downloads_to_screens(project_path)
    
    print(f"\n前10个映射:")
    for i, (download, screen) in enumerate(sorted(mapping.items())[:10]):
        print(f"  {download} -> {screen}")


图片哈希匹配器
用于建立 Downloads (原始顺序) 和 Screens (分类后) 的对应关系
"""

import os
import hashlib
from PIL import Image
import io


def compute_image_hash(image_path: str) -> str:
    """
    计算图片的内容哈希
    使用感知哈希，对轻微的尺寸变化不敏感
    """
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式和尺寸进行比较
            img = img.convert('RGB')
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            
            # 计算像素数据的哈希
            pixels = list(img.getdata())
            pixel_str = ''.join([f'{r}{g}{b}' for r, g, b in pixels])
            return hashlib.md5(pixel_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算哈希 {image_path}: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希（精确匹配）"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算文件哈希 {file_path}: {e}")
        return None


def build_hash_index(folder_path: str, use_image_hash: bool = True) -> dict:
    """
    为文件夹中的所有图片建立哈希索引
    
    Returns:
        {hash: filename, ...}
    """
    index = {}
    
    if not os.path.exists(folder_path):
        return index
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        if use_image_hash:
            file_hash = compute_image_hash(filepath)
        else:
            file_hash = compute_file_hash(filepath)
        
        if file_hash:
            index[file_hash] = filename
    
    return index


def match_downloads_to_screens(project_path: str) -> dict:
    """
    匹配 Downloads 和 Screens 文件夹中的图片
    
    Returns:
        {
            "Screen_001.png": "02_Welcome_03.png",  # Downloads -> Screens
            "Screen_002.png": "02_Welcome_01.png",
            ...
        }
    """
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path) or not os.path.exists(screens_path):
        print(f"[ERROR] 缺少必要文件夹: Downloads或Screens")
        return {}
    
    print("[MATCH] Computing Downloads hashes...")
    downloads_index = {}
    downloads_files = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    
    for filename in downloads_files:
        filepath = os.path.join(downloads_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            downloads_index[filename] = file_hash
    
    print(f"       Downloads: {len(downloads_index)} files")
    
    print("[MATCH] Computing Screens hashes...")
    screens_hash_to_name = {}
    screens_files = [f for f in os.listdir(screens_path) if f.endswith('.png')]
    
    for filename in screens_files:
        filepath = os.path.join(screens_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            screens_hash_to_name[file_hash] = filename
    
    print(f"       Screens: {len(screens_hash_to_name)} files")
    
    # 建立映射
    mapping = {}
    unmatched = []
    
    for download_name, download_hash in downloads_index.items():
        if download_hash in screens_hash_to_name:
            mapping[download_name] = screens_hash_to_name[download_hash]
        else:
            unmatched.append(download_name)
    
    print(f"[MATCH] Matched: {len(mapping)} files")
    if unmatched:
        print(f"[MATCH] Unmatched: {len(unmatched)} files")
    
    return mapping


def get_original_order(project_path: str) -> list:
    """
    获取原始下载顺序
    
    Returns:
        ["Screen_001.png", "Screen_002.png", ...]
    """
    downloads_path = os.path.join(project_path, "Downloads")
    
    if not os.path.exists(downloads_path):
        return []
    
    files = [f for f in os.listdir(downloads_path) if f.endswith('.png')]
    return sorted(files)  # Screen_001, Screen_002, ... 自然排序


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试哈希匹配器: {project}")
    print('='*60)
    
    mapping = match_downloads_to_screens(project_path)
    
    print(f"\n前10个映射:")
    for i, (download, screen) in enumerate(sorted(mapping.items())[:10]):
        print(f"  {download} -> {screen}")


图片哈希匹配器
用于建立 Downloads (原始顺序) 和 Screens (分类后) 的对应关系
"""

import os
import hashlib
from PIL import Image
import io


def compute_image_hash(image_path: str) -> str:
    """
    计算图片的内容哈希
    使用感知哈希，对轻微的尺寸变化不敏感
    """
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式和尺寸进行比较
            img = img.convert('RGB')
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            
            # 计算像素数据的哈希
            pixels = list(img.getdata())
            pixel_str = ''.join([f'{r}{g}{b}' for r, g, b in pixels])
            return hashlib.md5(pixel_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算哈希 {image_path}: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希（精确匹配）"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算文件哈希 {file_path}: {e}")
        return None


def build_hash_index(folder_path: str, use_image_hash: bool = True) -> dict:
    """
    为文件夹中的所有图片建立哈希索引
    
    Returns:
        {hash: filename, ...}
    """
    index = {}
    
    if not os.path.exists(folder_path):
        return index
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        if use_image_hash:
            file_hash = compute_image_hash(filepath)
        else:
            file_hash = compute_file_hash(filepath)
        
        if file_hash:
            index[file_hash] = filename
    
    return index


def match_downloads_to_screens(project_path: str) -> dict:
    """
    匹配 Downloads 和 Screens 文件夹中的图片
    
    Returns:
        {
            "Screen_001.png": "02_Welcome_03.png",  # Downloads -> Screens
            "Screen_002.png": "02_Welcome_01.png",
            ...
        }
    """
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path) or not os.path.exists(screens_path):
        print(f"[ERROR] 缺少必要文件夹: Downloads或Screens")
        return {}
    
    print("[MATCH] Computing Downloads hashes...")
    downloads_index = {}
    downloads_files = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    
    for filename in downloads_files:
        filepath = os.path.join(downloads_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            downloads_index[filename] = file_hash
    
    print(f"       Downloads: {len(downloads_index)} files")
    
    print("[MATCH] Computing Screens hashes...")
    screens_hash_to_name = {}
    screens_files = [f for f in os.listdir(screens_path) if f.endswith('.png')]
    
    for filename in screens_files:
        filepath = os.path.join(screens_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            screens_hash_to_name[file_hash] = filename
    
    print(f"       Screens: {len(screens_hash_to_name)} files")
    
    # 建立映射
    mapping = {}
    unmatched = []
    
    for download_name, download_hash in downloads_index.items():
        if download_hash in screens_hash_to_name:
            mapping[download_name] = screens_hash_to_name[download_hash]
        else:
            unmatched.append(download_name)
    
    print(f"[MATCH] Matched: {len(mapping)} files")
    if unmatched:
        print(f"[MATCH] Unmatched: {len(unmatched)} files")
    
    return mapping


def get_original_order(project_path: str) -> list:
    """
    获取原始下载顺序
    
    Returns:
        ["Screen_001.png", "Screen_002.png", ...]
    """
    downloads_path = os.path.join(project_path, "Downloads")
    
    if not os.path.exists(downloads_path):
        return []
    
    files = [f for f in os.listdir(downloads_path) if f.endswith('.png')]
    return sorted(files)  # Screen_001, Screen_002, ... 自然排序


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试哈希匹配器: {project}")
    print('='*60)
    
    mapping = match_downloads_to_screens(project_path)
    
    print(f"\n前10个映射:")
    for i, (download, screen) in enumerate(sorted(mapping.items())[:10]):
        print(f"  {download} -> {screen}")


图片哈希匹配器
用于建立 Downloads (原始顺序) 和 Screens (分类后) 的对应关系
"""

import os
import hashlib
from PIL import Image
import io


def compute_image_hash(image_path: str) -> str:
    """
    计算图片的内容哈希
    使用感知哈希，对轻微的尺寸变化不敏感
    """
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式和尺寸进行比较
            img = img.convert('RGB')
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            
            # 计算像素数据的哈希
            pixels = list(img.getdata())
            pixel_str = ''.join([f'{r}{g}{b}' for r, g, b in pixels])
            return hashlib.md5(pixel_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算哈希 {image_path}: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希（精确匹配）"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算文件哈希 {file_path}: {e}")
        return None


def build_hash_index(folder_path: str, use_image_hash: bool = True) -> dict:
    """
    为文件夹中的所有图片建立哈希索引
    
    Returns:
        {hash: filename, ...}
    """
    index = {}
    
    if not os.path.exists(folder_path):
        return index
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        if use_image_hash:
            file_hash = compute_image_hash(filepath)
        else:
            file_hash = compute_file_hash(filepath)
        
        if file_hash:
            index[file_hash] = filename
    
    return index


def match_downloads_to_screens(project_path: str) -> dict:
    """
    匹配 Downloads 和 Screens 文件夹中的图片
    
    Returns:
        {
            "Screen_001.png": "02_Welcome_03.png",  # Downloads -> Screens
            "Screen_002.png": "02_Welcome_01.png",
            ...
        }
    """
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path) or not os.path.exists(screens_path):
        print(f"[ERROR] 缺少必要文件夹: Downloads或Screens")
        return {}
    
    print("[MATCH] Computing Downloads hashes...")
    downloads_index = {}
    downloads_files = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    
    for filename in downloads_files:
        filepath = os.path.join(downloads_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            downloads_index[filename] = file_hash
    
    print(f"       Downloads: {len(downloads_index)} files")
    
    print("[MATCH] Computing Screens hashes...")
    screens_hash_to_name = {}
    screens_files = [f for f in os.listdir(screens_path) if f.endswith('.png')]
    
    for filename in screens_files:
        filepath = os.path.join(screens_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            screens_hash_to_name[file_hash] = filename
    
    print(f"       Screens: {len(screens_hash_to_name)} files")
    
    # 建立映射
    mapping = {}
    unmatched = []
    
    for download_name, download_hash in downloads_index.items():
        if download_hash in screens_hash_to_name:
            mapping[download_name] = screens_hash_to_name[download_hash]
        else:
            unmatched.append(download_name)
    
    print(f"[MATCH] Matched: {len(mapping)} files")
    if unmatched:
        print(f"[MATCH] Unmatched: {len(unmatched)} files")
    
    return mapping


def get_original_order(project_path: str) -> list:
    """
    获取原始下载顺序
    
    Returns:
        ["Screen_001.png", "Screen_002.png", ...]
    """
    downloads_path = os.path.join(project_path, "Downloads")
    
    if not os.path.exists(downloads_path):
        return []
    
    files = [f for f in os.listdir(downloads_path) if f.endswith('.png')]
    return sorted(files)  # Screen_001, Screen_002, ... 自然排序


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试哈希匹配器: {project}")
    print('='*60)
    
    mapping = match_downloads_to_screens(project_path)
    
    print(f"\n前10个映射:")
    for i, (download, screen) in enumerate(sorted(mapping.items())[:10]):
        print(f"  {download} -> {screen}")


图片哈希匹配器
用于建立 Downloads (原始顺序) 和 Screens (分类后) 的对应关系
"""

import os
import hashlib
from PIL import Image
import io


def compute_image_hash(image_path: str) -> str:
    """
    计算图片的内容哈希
    使用感知哈希，对轻微的尺寸变化不敏感
    """
    try:
        with Image.open(image_path) as img:
            # 转换为统一格式和尺寸进行比较
            img = img.convert('RGB')
            img = img.resize((64, 64), Image.Resampling.LANCZOS)
            
            # 计算像素数据的哈希
            pixels = list(img.getdata())
            pixel_str = ''.join([f'{r}{g}{b}' for r, g, b in pixels])
            return hashlib.md5(pixel_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算哈希 {image_path}: {e}")
        return None


def compute_file_hash(file_path: str) -> str:
    """计算文件的MD5哈希（精确匹配）"""
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"[ERROR] 无法计算文件哈希 {file_path}: {e}")
        return None


def build_hash_index(folder_path: str, use_image_hash: bool = True) -> dict:
    """
    为文件夹中的所有图片建立哈希索引
    
    Returns:
        {hash: filename, ...}
    """
    index = {}
    
    if not os.path.exists(folder_path):
        return index
    
    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.png')]
    
    for filename in files:
        filepath = os.path.join(folder_path, filename)
        
        if use_image_hash:
            file_hash = compute_image_hash(filepath)
        else:
            file_hash = compute_file_hash(filepath)
        
        if file_hash:
            index[file_hash] = filename
    
    return index


def match_downloads_to_screens(project_path: str) -> dict:
    """
    匹配 Downloads 和 Screens 文件夹中的图片
    
    Returns:
        {
            "Screen_001.png": "02_Welcome_03.png",  # Downloads -> Screens
            "Screen_002.png": "02_Welcome_01.png",
            ...
        }
    """
    downloads_path = os.path.join(project_path, "Downloads")
    screens_path = os.path.join(project_path, "Screens")
    
    if not os.path.exists(downloads_path) or not os.path.exists(screens_path):
        print(f"[ERROR] 缺少必要文件夹: Downloads或Screens")
        return {}
    
    print("[MATCH] Computing Downloads hashes...")
    downloads_index = {}
    downloads_files = sorted([f for f in os.listdir(downloads_path) if f.endswith('.png')])
    
    for filename in downloads_files:
        filepath = os.path.join(downloads_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            downloads_index[filename] = file_hash
    
    print(f"       Downloads: {len(downloads_index)} files")
    
    print("[MATCH] Computing Screens hashes...")
    screens_hash_to_name = {}
    screens_files = [f for f in os.listdir(screens_path) if f.endswith('.png')]
    
    for filename in screens_files:
        filepath = os.path.join(screens_path, filename)
        file_hash = compute_image_hash(filepath)
        if file_hash:
            screens_hash_to_name[file_hash] = filename
    
    print(f"       Screens: {len(screens_hash_to_name)} files")
    
    # 建立映射
    mapping = {}
    unmatched = []
    
    for download_name, download_hash in downloads_index.items():
        if download_hash in screens_hash_to_name:
            mapping[download_name] = screens_hash_to_name[download_hash]
        else:
            unmatched.append(download_name)
    
    print(f"[MATCH] Matched: {len(mapping)} files")
    if unmatched:
        print(f"[MATCH] Unmatched: {len(unmatched)} files")
    
    return mapping


def get_original_order(project_path: str) -> list:
    """
    获取原始下载顺序
    
    Returns:
        ["Screen_001.png", "Screen_002.png", ...]
    """
    downloads_path = os.path.join(project_path, "Downloads")
    
    if not os.path.exists(downloads_path):
        return []
    
    files = [f for f in os.listdir(downloads_path) if f.endswith('.png')]
    return sorted(files)  # Screen_001, Screen_002, ... 自然排序


if __name__ == "__main__":
    # 测试
    import sys
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "Calm_Analysis"
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_path = os.path.join(base_path, "projects", project)
    
    print(f"\n{'='*60}")
    print(f"测试哈希匹配器: {project}")
    print('='*60)
    
    mapping = match_downloads_to_screens(project_path)
    
    print(f"\n前10个映射:")
    for i, (download, screen) in enumerate(sorted(mapping.items())[:10]):
        print(f"  {download} -> {screen}")

