# -*- coding: utf-8 -*-
"""
PM Screenshot Tool - 产品经理截图分析助手
Flask 后端应用 - 支持三层分类体系 (Stage/Module/Feature)
"""

import os
import sys
import time
import json
import time
import shutil
import hashlib
import requests
import subprocess
from datetime import datetime
from io import BytesIO
from PIL import Image
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# Database import
try:
    from data.db_manager import get_db, DBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("[WARN] Database module not available, using JSON fallback")

app = Flask(__name__)

# 禁用Flask模板缓存（开发时使用）
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# 禁用浏览器缓存
@app.after_request
def add_no_cache_headers(response):
    """为HTML页面添加禁用缓存的headers"""
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# 配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DOWNLOADS_2024_DIR = os.path.join(BASE_DIR, "downloads_2024")  # 新下载目录
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
TARGET_WIDTH = 402
THUMB_WIDTH = 120
THUMB_SIZES = {
    'small': 120,
    'medium': 240,
    'large': 480
}

# 确保目录存在
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# 加载API Keys
API_KEYS_FILE = os.path.join(CONFIG_DIR, "api_keys.json")
if os.path.exists(API_KEYS_FILE):
    with open(API_KEYS_FILE, 'r', encoding='utf-8') as f:
        api_keys = json.load(f)
        for key, value in api_keys.items():
            if value and not os.environ.get(key):
                os.environ[key] = value
    print(f"[CONFIG] API Keys loaded from {API_KEYS_FILE}")


# ==================== 工具函数 ====================

def load_history():
    """加载历史记录"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projects": [], "recent_actions": []}


def save_history(data):
    """保存历史记录"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_action(action_type, description):
    """添加操作记录"""
    history = load_history()
    action = {
        "type": action_type,
        "description": description,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    history["recent_actions"].insert(0, action)
    history["recent_actions"] = history["recent_actions"][:20]
    save_history(history)


def get_project_path(project_name):
    """获取项目路径"""
    # 支持 downloads_2024 目录
    if project_name.startswith("downloads_2024/"):
        app_name = project_name.replace("downloads_2024/", "")
        return os.path.join(DOWNLOADS_2024_DIR, app_name)
    
    safe_name = "".join(c for c in project_name if c.isalnum() or c in "_ -").strip()
    return os.path.join(PROJECTS_DIR, safe_name)


def generate_thumbnail(src_path, thumb_path, width=None, webp=True):
    """生成缩略图"""
    try:
        img = Image.open(src_path)
        target_width = width if width else THUMB_WIDTH
        ratio = target_width / img.width
        new_height = int(img.height * ratio)
        thumb = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
        
        thumb.save(thumb_path, 'PNG', optimize=True)
        
        if webp:
            webp_path = thumb_path.replace('.png', '.webp')
            if thumb.mode in ('RGBA', 'P'):
                thumb_rgb = thumb.convert('RGB')
            else:
                thumb_rgb = thumb
            thumb_rgb.save(webp_path, 'WEBP', quality=85, method=6)
        
        return True
    except Exception as e:
        print(f"Thumbnail generation error: {e}")
        return False


def load_taxonomy():
    """加载标准分类词表"""
    taxonomy_file = os.path.join(CONFIG_DIR, "taxonomy.json")
    if os.path.exists(taxonomy_file):
        with open(taxonomy_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_synonyms():
    """加载同义词映射"""
    synonyms_file = os.path.join(CONFIG_DIR, "synonyms.json")
    if os.path.exists(synonyms_file):
        with open(synonyms_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ==================== 页面路由 ====================

@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/classify")
def classify_page():
    """手动分类工具页面"""
    return render_template("classify.html")


@app.route("/quick-classify")
def quick_classify_page():
    """快速分类调整页面"""
    return render_template("quick_classify.html")


@app.route("/test")
def test_page():
    """测试页面"""
    return render_template("test.html")


@app.route("/sort")
def sort_screens_page():
    """截图排序工具页面"""
    return render_template("sort_screens.html")


# ==================== 项目管理API ====================

@app.route("/api/projects", methods=["GET"])
def list_projects():
    """获取项目列表"""
    products_config = {}
    config_path = os.path.join(CONFIG_DIR, "products.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            products_config = json.load(f)
    
    projects = []
    
    # 扫描原有 projects 目录
    if os.path.exists(PROJECTS_DIR):
        for name in os.listdir(PROJECTS_DIR):
            if name.lower() == "null":
                continue
            project_path = os.path.join(PROJECTS_DIR, name)
            if os.path.isdir(project_path):
                screens_path = os.path.join(project_path, "Screens")
                screen_count = 0
                if os.path.exists(screens_path):
                    screen_count = len([f for f in os.listdir(screens_path) if f.endswith(".png")])
                
                created = datetime.fromtimestamp(os.path.getctime(project_path))
                product_info = products_config.get(name, {})
                display_name = product_info.get("name", name.replace("_Analysis", ""))
                
                projects.append({
                    "name": name,
                    "display_name": display_name,
                    "color": product_info.get("color", "#5E6AD2"),
                    "initial": product_info.get("initial", display_name[0].upper() if display_name else "?"),
                    "category": product_info.get("category", ""),
                    "description_cn": product_info.get("description_cn", ""),
                    "description_en": product_info.get("description_en", ""),
                    "screen_count": screen_count,
                    "created": created.strftime("%Y-%m-%d %H:%M"),
                    "source": "projects"
                })
    
    # 添加 downloads_2024 目录的项目到首页
    MOBBIN_APPS = {"Cal_AI", "Fitbit"}
    if os.path.exists(DOWNLOADS_2024_DIR):
        for name in os.listdir(DOWNLOADS_2024_DIR):
            dir_path = os.path.join(DOWNLOADS_2024_DIR, name)
            if os.path.isdir(dir_path) and not name.endswith("_backup"):
                screen_count = len([f for f in os.listdir(dir_path) if f.endswith(".png")])
                if screen_count == 0:
                    continue
                
                # 根据来源设置显示名和颜色
                if name in MOBBIN_APPS:
                    display_name = f"[Mobbin] {name}"
                    color = "#8B5CF6"
                else:
                    display_name = f"[SD] {name}"
                    color = "#10B981"
                
                projects.append({
                    "name": f"downloads_2024/{name}",
                    "display_name": display_name,
                    "color": color,
                    "initial": name[0].upper() if name else "?",
                    "category": "Health & Fitness",
                    "description_cn": "",
                    "description_en": "",
                    "screen_count": screen_count,
                    "created": "",
                    "source": "downloads_2024"
                })
    
    # 过滤掉截图数为0的项目
    projects = [p for p in projects if p["screen_count"] > 0]
    projects.sort(key=lambda x: -x["screen_count"])
    
    return jsonify({"projects": projects})


@app.route("/api/projects", methods=["POST"])
def create_project():
    """创建新项目"""
    data = request.json
    project_name = data.get("name", "").strip()
    
    if not project_name:
        return jsonify({"success": False, "error": "项目名称不能为空"})
    
    project_path = get_project_path(project_name)
    
    if os.path.exists(project_path):
        return jsonify({"success": False, "error": "项目已存在"})
    
    os.makedirs(project_path)
    os.makedirs(os.path.join(project_path, "Downloads"))
    os.makedirs(os.path.join(project_path, "Screens"))
    
    add_action("create", f"创建项目: {project_name}")
    
    return jsonify({"success": True, "path": project_path})


@app.route("/api/sort-projects", methods=["GET"])
def list_sort_projects():
    """获取排序工具的项目列表（包含 downloads_2024），含检查状态和 Onboarding 范围"""
    # 标识数据来源
    MOBBIN_APPS = {"Cal_AI", "Fitbit"}
    
    projects = []
    
    # 扫描 downloads_2024 目录
    if os.path.exists(DOWNLOADS_2024_DIR):
        for name in os.listdir(DOWNLOADS_2024_DIR):
            # 跳过 backup 文件夹
            if "_backup" in name:
                continue
            
            project_path = os.path.join(DOWNLOADS_2024_DIR, name)
            if os.path.isdir(project_path):
                screen_count = len([f for f in os.listdir(project_path) if f.endswith(".png")])
                if screen_count == 0:
                    continue
                
                # 根据来源设置显示名
                if name in MOBBIN_APPS:
                    display_name = f"[Mobbin] {name}"
                    color = "#8B5CF6"
                else:
                    display_name = f"[SD] {name}"
                    color = "#10B981"
                
                # 读取检查状态
                check_status = {"checked": False}
                check_file = os.path.join(project_path, "check_status.json")
                if os.path.exists(check_file):
                    try:
                        with open(check_file, "r", encoding="utf-8") as f:
                            check_status = json.load(f)
                    except:
                        pass
                
                # 读取 Onboarding 范围
                onboarding = {"start": -1, "end": -1}
                ob_file = os.path.join(project_path, "onboarding_range.json")
                if os.path.exists(ob_file):
                    try:
                        with open(ob_file, "r", encoding="utf-8") as f:
                            onboarding = json.load(f)
                    except:
                        pass
                
                projects.append({
                    "name": f"downloads_2024/{name}",
                    "display_name": display_name,
                    "color": color,
                    "screen_count": screen_count,
                    "source": "downloads_2024",
                    "checked": check_status.get("checked", False),
                    "checked_at": check_status.get("checked_at"),
                    "onboarding_start": onboarding.get("start", -1),
                    "onboarding_end": onboarding.get("end", -1)
                })
    
    # 按截图数量排序
    projects.sort(key=lambda x: -x["screen_count"])
    
    # 统计进度
    total = len(projects)
    checked_count = sum(1 for p in projects if p.get("checked"))
    onboarding_count = sum(1 for p in projects if p.get("onboarding_start", -1) > 0)
    
    return jsonify({
        "projects": projects,
        "stats": {
            "total": total,
            "checked": checked_count,
            "onboarding_marked": onboarding_count
        }
    })


@app.route("/api/projects/<project_name>", methods=["DELETE"])
def delete_project(project_name):
    """删除项目"""
    project_path = get_project_path(project_name)
    
    if os.path.exists(project_path):
        shutil.rmtree(project_path)
        add_action("delete", f"删除项目: {project_name}")
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "项目不存在"})


# ==================== 截图API ====================

@app.route("/api/screenshots/<path:project_name>", methods=["GET"])
def get_screenshots(project_name):
    """获取项目截图列表 - 支持三层分类"""
    project_path = get_project_path(project_name)
    
    # downloads_2024 目录结构不同：截图直接在文件夹下
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    
    if is_downloads_2024:
        screens_path = project_path  # 截图直接在文件夹下
        downloads_path = None
    else:
        screens_path = os.path.join(project_path, "Screens")
        downloads_path = os.path.join(project_path, "Downloads")
    
    descriptions_file = os.path.join(project_path, "descriptions.json")
    
    result = {
        "screens": [],
        "downloads": [],
        "descriptions": {},
        "screen_types": {},
        "classifications": {}  # 新增：三层分类数据
    }
    
    # 获取分类后的截图
    if os.path.exists(screens_path):
        for f in sorted(os.listdir(screens_path)):
            if f.endswith(".png"):
                result["screens"].append(f)
    
    # 获取原始下载截图
    if downloads_path and os.path.exists(downloads_path):
        for f in sorted(os.listdir(downloads_path)):
            if f.endswith(".png"):
                result["downloads"].append(f)
    
    # 获取截图说明
    if os.path.exists(descriptions_file):
        with open(descriptions_file, "r", encoding="utf-8") as f:
            result["descriptions"] = json.load(f)
    
    # 从JSON文件获取分类数据
    ai_file = os.path.join(project_path, "ai_analysis.json")
    
    if os.path.exists(ai_file):
        try:
            with open(ai_file, "r", encoding="utf-8") as f:
                ai_data = json.load(f)
            for filename, data in ai_data.get("results", {}).items():
                if data:
                    # 兼容旧格式 screen_type
                    if data.get("screen_type"):
                        result["screen_types"][filename] = data["screen_type"]
                    
                    # 新格式：三层分类
                    result["classifications"][filename] = {
                        "stage": data.get("stage"),
                        "module": data.get("module"),
                        "feature": data.get("feature"),
                        "page_role": data.get("page_role"),
                        "screen_type": data.get("screen_type"),  # 兼容
                        "confidence": data.get("confidence", 0)
                    }
        except Exception as e:
            print(f"[ERROR] Loading ai_analysis.json: {e}")
    
    # 回退到数据库
    if not result["classifications"] and DB_AVAILABLE:
        try:
            db = get_db()
            structured = db.get_structured_descriptions(project_name)
            if structured:
                for filename, data in structured.items():
                    result["classifications"][filename] = {
                        "stage": data.get("stage"),
                        "module": data.get("module"),
                        "feature": data.get("feature"),
                        "page_role": data.get("page_role"),
                        "screen_type": data.get("screen_type"),
                        "confidence": data.get("confidence", 0)
                    }
                    if data.get("screen_type"):
                        result["screen_types"][filename] = data["screen_type"]
        except Exception as e:
            print(f"[DB] Error getting classifications: {e}")
    
    return jsonify(result)


@app.route("/api/screenshot/<path:project_name>/<folder>/<filename>")
def serve_screenshot(project_name, folder, filename):
    """提供截图文件"""
    project_path = get_project_path(project_name)
    
    # downloads_2024 目录：截图直接在文件夹下
    if project_name.startswith("downloads_2024/"):
        folder_path = project_path
    elif folder == "screens":
        folder_path = os.path.join(project_path, "Screens")
    else:
        folder_path = os.path.join(project_path, "Downloads")
    
    return send_from_directory(folder_path, filename)


@app.route("/api/thumb/<path:project_name>/<folder>/<filename>")
def serve_thumbnail(project_name, folder, filename):
    """提供缩略图文件"""
    project_path = get_project_path(project_name)
    size = request.args.get('size', 'small')
    width = THUMB_SIZES.get(size, THUMB_SIZES['small'])
    
    # downloads_2024 目录：截图直接在文件夹下
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    
    if is_downloads_2024:
        src_folder = project_path
        thumb_folder = os.path.join(project_path, f"thumbs_{size}")
    elif folder == "screens":
        src_folder = os.path.join(project_path, "Screens")
        thumb_folder = os.path.join(project_path, f"Screens_thumbs_{size}")
    else:
        src_folder = os.path.join(project_path, "Downloads")
        thumb_folder = os.path.join(project_path, f"Downloads_thumbs_{size}")
    
    os.makedirs(thumb_folder, exist_ok=True)
    
    src_path = os.path.join(src_folder, filename)
    thumb_path = os.path.join(thumb_folder, filename)
    webp_path = thumb_path.replace('.png', '.webp')
    
    # 检查是否需要重新生成缩略图
    need_regenerate = False
    if not os.path.exists(thumb_path):
        need_regenerate = True
    elif os.path.exists(src_path):
        src_mtime = os.path.getmtime(src_path)
        thumb_mtime = os.path.getmtime(thumb_path)
        # 如果原图比缩略图新，或者原图在最近5秒内被修改过，强制重新生成
        if src_mtime > thumb_mtime or (time.time() - src_mtime < 5):
            need_regenerate = True
    
    if need_regenerate and os.path.exists(src_path):
        # 删除旧的缓存文件（包括 png 和 webp）
        if os.path.exists(thumb_path):
            os.remove(thumb_path)
        if os.path.exists(webp_path):
            os.remove(webp_path)
        generate_thumbnail(src_path, thumb_path, width)
    
    accept = request.headers.get('Accept', '')
    use_webp = 'image/webp' in accept and os.path.exists(webp_path)
    
    if use_webp:
        serve_folder = thumb_folder
        serve_filename = filename.replace('.png', '.webp')
    elif os.path.exists(thumb_path):
        serve_folder = thumb_folder
        serve_filename = filename
    elif os.path.exists(src_path):
        serve_folder = src_folder
        serve_filename = filename
    else:
        return "File not found", 404
    
    serve_path = os.path.join(serve_folder, serve_filename)
    stat = os.stat(serve_path)
    etag = hashlib.md5(f"{stat.st_mtime}-{stat.st_size}-{use_webp}".encode()).hexdigest()[:16]
    
    if_none_match = request.headers.get('If-None-Match')
    
    if if_none_match and if_none_match == etag:
        return '', 304
    
    response = make_response(send_from_directory(serve_folder, serve_filename))
    # 使用 no-cache 让浏览器每次都验证 ETag，确保文件更新时能获取新版本
    response.headers['Cache-Control'] = 'public, no-cache, must-revalidate'
    response.headers['ETag'] = etag
    response.headers['Vary'] = 'Accept'
    if use_webp:
        response.headers['Content-Type'] = 'image/webp'
    return response


# ==================== 分类API ====================

@app.route("/api/taxonomy", methods=["GET"])
def get_taxonomy():
    """获取标准分类词表"""
    taxonomy = load_taxonomy()
    synonyms = load_synonyms()
    
    return jsonify({
        "success": True,
        "taxonomy": taxonomy,
        "synonyms": synonyms.get("mappings", {})
    })


@app.route("/api/update-classification", methods=["POST"])
def update_classification():
    """更新截图的三层分类"""
    data = request.json
    project_name = data.get("project", "")
    changes = data.get("changes", {})
    
    if not project_name or not changes:
        return jsonify({"success": False, "error": "Missing data"})
    
    project_path = os.path.join(PROJECTS_DIR, project_name)
    ai_file = os.path.join(project_path, "ai_analysis.json")
    
    if not os.path.exists(ai_file):
        return jsonify({"success": False, "error": "Analysis file not found"})
    
    try:
        with open(ai_file, "r", encoding="utf-8") as f:
            ai_data = json.load(f)
        
        results = ai_data.get("results", {})
        updated = 0
        
        for filename, new_classification in changes.items():
            if filename in results:
                # 支持三层分类更新
                if isinstance(new_classification, dict):
                    if "stage" in new_classification:
                        results[filename]["stage"] = new_classification["stage"]
                    if "module" in new_classification:
                        results[filename]["module"] = new_classification["module"]
                    if "feature" in new_classification:
                        results[filename]["feature"] = new_classification["feature"]
                    if "page_role" in new_classification:
                        results[filename]["page_role"] = new_classification["page_role"]
                    # 兼容旧格式
                    if "screen_type" in new_classification:
                        results[filename]["screen_type"] = new_classification["screen_type"]
                else:
                    # 兼容旧API：直接传screen_type字符串
                    results[filename]["screen_type"] = new_classification
                
                results[filename]["manually_adjusted"] = True
                results[filename]["adjusted_at"] = datetime.now().isoformat()
                updated += 1
        
        with open(ai_file, "w", encoding="utf-8") as f:
            json.dump(ai_data, f, indent=2, ensure_ascii=False)
        
        # 同步更新数据库
        if DB_AVAILABLE:
            try:
                db = get_db()
                product = db.get_product(project_name.replace("_Analysis", "").replace("_", " "))
                if product:
                    for filename, new_classification in changes.items():
                        # 这里需要更新单个截图的分类
                        pass  # TODO: 添加db.update_screenshot_classification方法
            except Exception as e:
                print(f"[DB] Error updating database: {e}")
        
        return jsonify({"success": True, "count": updated})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/update-screen-types", methods=["POST"])
def update_screen_types():
    """更新截图分类（兼容旧API）"""
    data = request.json
    project_name = data.get("project", "")
    changes = data.get("changes", {})
    
    # 转换为新格式
    new_changes = {}
    for filename, screen_type in changes.items():
        new_changes[filename] = {"screen_type": screen_type}
    
    # 复用新API
    data["changes"] = new_changes
    return update_classification()


# ==================== 结构化数据API ====================

@app.route("/api/structured-descriptions/<project_name>")
def get_structured_descriptions(project_name):
    """获取项目的结构化描述"""
    # 优先使用数据库
    if DB_AVAILABLE:
        try:
            db = get_db()
            structured = db.get_structured_descriptions(project_name)
            if structured:
                return jsonify(structured)
        except Exception as e:
            print(f"[DB] Error reading from database: {e}")
    
    # 回退到JSON文件
    project_path = get_project_path(project_name)
    
    data_sources = [
        os.path.join(project_path, "ai_analysis.json"),
        os.path.join(project_path, "structured_descriptions.json")
    ]
    
    structured = {}
    
    for source_file in data_sources:
        if os.path.exists(source_file):
            try:
                with open(source_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if "results" in data:
                    for filename, result in data.get("results", {}).items():
                        structured[filename] = result
                else:
                    for filename, result in data.items():
                        if isinstance(result, dict):
                            structured[filename] = result
                
                if structured:
                    break
            except Exception as e:
                print(f"Error loading {source_file}: {e}")
                continue
    
    return jsonify(structured)


# ==================== 数据库查询API ====================

@app.route("/api/db/products", methods=["GET"])
def db_get_products():
    """获取所有产品列表"""
    if not DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"})
    
    try:
        db = get_db()
        products = db.get_all_products()
        return jsonify({"success": True, "products": products})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/stats/classification", methods=["GET"])
def db_get_classification_stats():
    """获取三层分类统计"""
    if not DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"})
    
    try:
        db = get_db()
        stats = db.get_classification_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/query/by-stage/<stage>", methods=["GET"])
def db_query_by_stage(stage):
    """按Stage查询截图"""
    if not DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"})
    
    try:
        db = get_db()
        results = db.find_by_stage(stage)
        return jsonify({"success": True, "count": len(results), "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/query/by-module/<module>", methods=["GET"])
def db_query_by_module(module):
    """按Module查询截图"""
    if not DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"})
    
    try:
        db = get_db()
        results = db.find_by_module(module)
        return jsonify({"success": True, "count": len(results), "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/stats/onboarding", methods=["GET"])
def db_get_onboarding_stats():
    """获取Onboarding统计"""
    if not DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"})
    
    try:
        db = get_db()
        stats = db.get_onboarding_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/db/stats/paywall", methods=["GET"])
def db_get_paywall_stats():
    """获取Paywall统计"""
    if not DB_AVAILABLE:
        return jsonify({"success": False, "error": "Database not available"})
    
    try:
        db = get_db()
        stats = db.get_paywall_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== 视频帧对齐API ====================

@app.route("/api/align", methods=["POST"])
def align_video_frames():
    """视频帧与截图对齐"""
    data = request.json
    project_name = data.get("project", "")
    keyframes_dir = data.get("keyframes_dir", "")
    
    if not project_name:
        return jsonify({"success": False, "error": "Missing project name"})
    
    project_path = get_project_path(project_name)
    alignment_file = os.path.join(project_path, "video_alignment.json")
    
    # 如果已有对齐结果，直接返回
    if os.path.exists(alignment_file):
        with open(alignment_file, "r", encoding="utf-8") as f:
            alignment_data = json.load(f)
        return jsonify({"success": True, "alignments": alignment_data})
    
    return jsonify({
        "success": False,
        "error": "Alignment not found. Run align_frames.py first.",
        "hint": "python video_analysis/align_frames.py"
    })


@app.route("/api/video-analysis/<project_name>", methods=["GET"])
def get_video_analysis(project_name):
    """获取视频分析结果"""
    project_path = get_project_path(project_name)
    
    # 查找视频分析结果文件
    analysis_files = [
        os.path.join(project_path, "video_analysis.json"),
        os.path.join(project_path, "keyframe_analysis.json")
    ]
    
    for analysis_file in analysis_files:
        if os.path.exists(analysis_file):
            with open(analysis_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"success": True, "analysis": data})
    
    # 尝试从数据库获取
    if DB_AVAILABLE:
        try:
            db = get_db()
            product = db.get_product(project_name.replace("_Analysis", "").replace("_", " "))
            if product:
                video_frames = db.get_video_frames(product['id'])
                alignments = db.get_alignments(product['id'])
                return jsonify({
                    "success": True,
                    "analysis": {
                        "video_frames": video_frames,
                        "alignments": alignments
                    }
                })
        except Exception as e:
            print(f"[DB] Error getting video analysis: {e}")
    
    return jsonify({"success": False, "error": "No video analysis found"})


# ==================== 导出API ====================

@app.route("/api/export/<project_name>/<format_type>")
def export_project(project_name, format_type):
    """导出项目数据"""
    project_path = get_project_path(project_name)
    
    if not os.path.exists(project_path):
        return jsonify({"success": False, "error": "项目不存在"})
    
    if format_type == "json":
        ai_file = os.path.join(project_path, "ai_analysis.json")
        if os.path.exists(ai_file):
            with open(ai_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        
        response = make_response(json.dumps(data, ensure_ascii=False, indent=2))
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["Content-Disposition"] = f"attachment; filename={project_name}_data.json"
        return response
    
    elif format_type == "csv":
        screens_path = os.path.join(project_path, "Screens")
        ai_file = os.path.join(project_path, "ai_analysis.json")
        
        classifications = {}
        if os.path.exists(ai_file):
            with open(ai_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            classifications = data.get("results", {})
        
        lines = ["Filename,Stage,Module,Feature,PageRole,ScreenType,Confidence"]
        if os.path.exists(screens_path):
            for f in sorted(os.listdir(screens_path)):
                if f.endswith(".png"):
                    c = classifications.get(f, {})
                    stage = c.get("stage", "")
                    module = c.get("module", "")
                    feature = c.get("feature", "")
                    page_role = c.get("page_role", "")
                    screen_type = c.get("screen_type", "")
                    confidence = c.get("confidence", 0)
                    lines.append(f'{f},{stage},{module},{feature},{page_role},{screen_type},{confidence}')
        
        csv_content = "\n".join(lines)
        response = make_response(csv_content)
        response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
        response.headers["Content-Disposition"] = f"attachment; filename={project_name}_classifications.csv"
        return response
    
    else:
        return jsonify({"success": False, "error": f"不支持的格式: {format_type}"})


# ==================== 配置API ====================

@app.route("/api/config/page-types", methods=["GET"])
def get_page_types_config():
    """获取页面类型配置"""
    config_file = os.path.join(CONFIG_DIR, "page_types.json")
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])


@app.route("/api/tag-library", methods=["GET"])
def get_tag_library():
    """获取标签库"""
    config_file = os.path.join(CONFIG_DIR, "tags_library.json")
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"tags": []})


@app.route("/api/project-tags/<project_name>", methods=["GET"])
@app.route("/api/tags/<project_name>", methods=["GET"])
def get_project_tags(project_name):
    """获取项目的标签"""
    project_path = get_project_path(project_name)
    tags_file = os.path.join(project_path, "tags.json")
    if os.path.exists(tags_file):
        with open(tags_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route("/api/project-steps/<project_name>", methods=["GET"])
@app.route("/api/steps/<project_name>", methods=["GET"])
def get_project_steps(project_name):
    """获取项目的步骤信息"""
    project_path = get_project_path(project_name)
    steps_file = os.path.join(project_path, "steps.json")
    if os.path.exists(steps_file):
        with open(steps_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({})


# ==================== 其他API ====================

@app.route("/api/history", methods=["GET"])
def get_history():
    """获取历史记录"""
    history = load_history()
    return jsonify(history)


@app.route("/api/open-folder", methods=["POST"])
def open_folder():
    """打开项目文件夹"""
    data = request.json
    project_name = data.get("project_name", "")
    
    project_path = get_project_path(project_name)
    
    if os.path.exists(project_path):
        os.startfile(project_path)
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "项目不存在"})


@app.route("/api/analysis-status/<project_name>")
def get_analysis_status(project_name):
    """获取项目的AI分析状态"""
    project_path = get_project_path(project_name)
    
    ai_file = os.path.join(project_path, "ai_analysis.json")
    screens_path = os.path.join(project_path, "Screens")
    
    total_screens = 0
    if os.path.exists(screens_path):
        total_screens = len([f for f in os.listdir(screens_path) if f.endswith(".png")])
    
    if os.path.exists(ai_file):
        with open(ai_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        analyzed_count = len(data.get("results", {}))
        status = "completed" if analyzed_count >= total_screens else "partial"
        return jsonify({
            "status": status,
            "analyzed": analyzed_count,
            "total": total_screens,
            "message": f"已分析 {analyzed_count}/{total_screens} 张截图"
        })
    else:
        return jsonify({
            "status": "not_started",
            "analyzed": 0,
            "total": total_screens,
            "message": "尚未进行AI分析"
        })


# ==================== 截图排序API ====================

@app.route("/api/save-sort-order", methods=["POST"])
def save_sort_order():
    """保存排序结果（不重命名文件）"""
    data = request.json
    project_name = data.get("project")
    order = data.get("order", [])
    
    if not project_name or not order:
        return jsonify({"success": False, "error": "缺少参数"})
    
    project_path = get_project_path(project_name)
    sort_file = os.path.join(project_path, "sort_order.json")
    
    try:
        sort_data = {
            "project": project_name,
            "saved_at": datetime.now().isoformat(),
            "order": order
        }
        with open(sort_file, "w", encoding="utf-8") as f:
            json.dump(sort_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True, "message": f"排序已保存到 {sort_file}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/apply-sort-order", methods=["POST"])
def apply_sort_order():
    """应用排序并重命名文件"""
    data = request.json
    project_name = data.get("project")
    order = data.get("order", [])
    
    if not project_name or not order:
        return jsonify({"success": False, "error": "缺少参数"})
    
    project_path = get_project_path(project_name)
    
    # downloads_2024 目录：截图直接在文件夹下，需要特殊处理
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    
    if is_downloads_2024:
        screens_dir = project_path
    else:
        screens_dir = os.path.join(project_path, "screens")
        if not os.path.exists(screens_dir):
            # 尝试 Screens 目录
            screens_dir = os.path.join(project_path, "Screens")
    
    if not os.path.exists(screens_dir):
        return jsonify({"success": False, "error": "截图目录不存在"})
    
    try:
        # 1. 创建备份到上级目录（避免被删除）
        if is_downloads_2024:
            backup_base = os.path.dirname(project_path)  # downloads_2024 目录
            folder_name = os.path.basename(project_path)
            backup_dir = os.path.join(backup_base, f"{folder_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        else:
            backup_dir = os.path.join(project_path, "screens_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        shutil.copytree(screens_dir, backup_dir)
        
        # 2. 对于 downloads_2024，直接在原地重命名文件（不删除目录）
        if is_downloads_2024:
            # 先复制到临时目录
            temp_dir = os.path.join(os.path.dirname(project_path), f"{os.path.basename(project_path)}_temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            for item in order:
                old_name = item["original_file"]
                new_idx = item["new_index"]
                # 保持原有命名格式
                ext = os.path.splitext(old_name)[1]
                new_name = f"{new_idx:04d}{ext}"
                
                old_path = os.path.join(screens_dir, old_name)
                new_path = os.path.join(temp_dir, new_name)
                
                if os.path.exists(old_path):
                    shutil.copy(old_path, new_path)
            
            # 删除原目录中的图片文件（但保留目录和其他文件）
            for f in os.listdir(screens_dir):
                if f.endswith(('.png', '.jpg', '.webp')):
                    os.remove(os.path.join(screens_dir, f))
            
            # 移动新文件回来
            for f in os.listdir(temp_dir):
                shutil.move(os.path.join(temp_dir, f), os.path.join(screens_dir, f))
            
            # 删除临时目录
            shutil.rmtree(temp_dir)
        else:
            # 原有逻辑：创建临时目录
            temp_dir = os.path.join(project_path, "screens_temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 按新顺序复制文件
            for item in order:
                old_name = item["original_file"]
                new_idx = item["new_index"]
                new_name = f"Screen_{new_idx:03d}.png"
                
                old_path = os.path.join(screens_dir, old_name)
                new_path = os.path.join(temp_dir, new_name)
                
                if os.path.exists(old_path):
                    shutil.copy(old_path, new_path)
            
            # 替换原目录
            shutil.rmtree(screens_dir)
            shutil.move(temp_dir, screens_dir)
        
        # 5. 更新 AI 分析结果
        ai_file = os.path.join(project_path, "ai_analysis.json")
        if os.path.exists(ai_file):
            with open(ai_file, "r", encoding="utf-8") as f:
                ai_data = json.load(f)
            
            old_results = ai_data.get("results", {})
            new_results = {}
            
            for item in order:
                old_name = item["original_file"]
                new_idx = item["new_index"]
                new_name = f"Screen_{new_idx:03d}.png"
                
                if old_name in old_results:
                    new_results[new_name] = old_results[old_name]
            
            ai_data["results"] = new_results
            ai_data["order_applied_at"] = datetime.now().isoformat()
            
            with open(ai_file, "w", encoding="utf-8") as f:
                json.dump(ai_data, f, ensure_ascii=False, indent=2)
        
        # 6. 保存排序记录
        sort_file = os.path.join(project_path, "sort_order_applied.json")
        with open(sort_file, "w", encoding="utf-8") as f:
            json.dump({
                "project": project_name,
                "applied_at": datetime.now().isoformat(),
                "backup_dir": backup_dir,
                "order": order
            }, f, ensure_ascii=False, indent=2)
        
        add_action("sort", f"重新排序 {project_name} 的 {len(order)} 张截图")
        
        return jsonify({
            "success": True, 
            "message": f"已重命名 {len(order)} 张截图，备份在 {backup_dir}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/delete-screens", methods=["POST"])
def delete_screens():
    """删除选中的截图（移动到 deleted 文件夹备份）"""
    data = request.json
    project_name = data.get("project")
    files = data.get("files", [])
    
    if not project_name or not files:
        return jsonify({"success": False, "error": "缺少参数"})
    
    project_path = get_project_path(project_name)
    
    # downloads_2024 项目：截图直接在项目文件夹下
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    
    if is_downloads_2024:
        screens_dir = project_path  # 截图直接在项目文件夹
    else:
        screens_dir = os.path.join(project_path, "screens")
        if not os.path.exists(screens_dir):
            # 尝试 Screens 目录
            screens_dir = os.path.join(project_path, "Screens")
    
    if not os.path.exists(screens_dir):
        return jsonify({"success": False, "error": "截图目录不存在"})
    
    try:
        # 创建 deleted 备份目录
        deleted_dir = os.path.join(project_path, "deleted")
        os.makedirs(deleted_dir, exist_ok=True)
        
        # 为本次删除创建时间戳子目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_deleted_dir = os.path.join(deleted_dir, timestamp)
        os.makedirs(batch_deleted_dir, exist_ok=True)
        
        deleted_count = 0
        deleted_files = []
        
        for filename in files:
            src_path = os.path.join(screens_dir, filename)
            if os.path.exists(src_path):
                dst_path = os.path.join(batch_deleted_dir, filename)
                shutil.move(src_path, dst_path)
                deleted_count += 1
                deleted_files.append(filename)
        
        # 记录删除日志
        log_file = os.path.join(deleted_dir, "delete_log.json")
        log_data = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        
        log_data.append({
            "timestamp": timestamp,
            "files": deleted_files,
            "backup_dir": batch_deleted_dir
        })
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
        
        add_action("delete", f"删除 {project_name} 的 {deleted_count} 张截图")
        
        return jsonify({
            "success": True,
            "deleted_count": deleted_count,
            "backup_dir": batch_deleted_dir,
            "message": f"已删除 {deleted_count} 张截图，备份在 {batch_deleted_dir}"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/restore-screens", methods=["POST"])
def restore_screens():
    """从 deleted 文件夹恢复截图"""
    data = request.json
    project_name = data.get("project")
    timestamp = data.get("timestamp")  # 恢复哪个批次
    
    if not project_name:
        return jsonify({"success": False, "error": "缺少项目名称"})
    
    project_path = get_project_path(project_name)
    deleted_dir = os.path.join(project_path, "deleted")
    
    # downloads_2024 项目：截图直接在项目文件夹下
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    
    if is_downloads_2024:
        screens_dir = project_path
    else:
        screens_dir = os.path.join(project_path, "screens")
        if not os.path.exists(screens_dir):
            screens_dir = os.path.join(project_path, "Screens")
    
    try:
        if timestamp:
            # 恢复指定批次
            batch_dir = os.path.join(deleted_dir, timestamp)
            if not os.path.exists(batch_dir):
                return jsonify({"success": False, "error": f"备份目录不存在: {timestamp}"})
            
            restored = 0
            for f in os.listdir(batch_dir):
                if f.endswith(".png"):
                    src = os.path.join(batch_dir, f)
                    dst = os.path.join(screens_dir, f)
                    shutil.move(src, dst)
                    restored += 1
            
            # 清理空目录
            if not os.listdir(batch_dir):
                os.rmdir(batch_dir)
            
            return jsonify({
                "success": True,
                "restored_count": restored,
                "message": f"已恢复 {restored} 张截图"
            })
        else:
            # 列出可恢复的批次
            batches = []
            if os.path.exists(deleted_dir):
                for d in sorted(os.listdir(deleted_dir), reverse=True):
                    batch_path = os.path.join(deleted_dir, d)
                    if os.path.isdir(batch_path):
                        files = [f for f in os.listdir(batch_path) if f.endswith(".png")]
                        if files:
                            batches.append({
                                "timestamp": d,
                                "count": len(files),
                                "files": files[:5]  # 只返回前5个作为预览
                            })
            
            return jsonify({
                "success": True,
                "batches": batches
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== Onboarding 范围API ====================

@app.route("/onboarding")
def onboarding_page():
    """Onboarding 专属查看页面"""
    return render_template("onboarding.html")


@app.route("/store")
def store_comparison_page():
    """App Store 商城对比页面"""
    return render_template("store_comparison.html")


@app.route("/api/onboarding-range/<path:project_name>", methods=["GET"])
def get_onboarding_range(project_name):
    """获取项目的 Onboarding 范围"""
    project_path = get_project_path(project_name)
    range_file = os.path.join(project_path, "onboarding_range.json")
    
    if os.path.exists(range_file):
        with open(range_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    
    return jsonify({"start": -1, "end": -1})


@app.route("/api/onboarding-range/<path:project_name>", methods=["POST"])
def save_onboarding_range(project_name):
    """保存项目的 Onboarding 范围"""
    data = request.json
    start = data.get("start", -1)
    end = data.get("end", -1)
    
    project_path = get_project_path(project_name)
    range_file = os.path.join(project_path, "onboarding_range.json")
    
    try:
        range_data = {
            "start": start,
            "end": end,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(range_file, "w", encoding="utf-8") as f:
            json.dump(range_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== 检查状态 API ====================

@app.route("/api/check-status/<path:project_name>", methods=["GET"])
def get_check_status(project_name):
    """获取项目的检查状态"""
    project_path = get_project_path(project_name)
    status_file = os.path.join(project_path, "check_status.json")
    
    if os.path.exists(status_file):
        with open(status_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    
    return jsonify({"checked": False})


@app.route("/api/check-status/<path:project_name>", methods=["POST"])
def set_check_status(project_name):
    """设置项目的检查状态"""
    data = request.json
    checked = data.get("checked", False)
    
    project_path = get_project_path(project_name)
    status_file = os.path.join(project_path, "check_status.json")
    
    # 获取当前截图数量
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    if is_downloads_2024:
        screens_path = project_path
    else:
        screens_path = os.path.join(project_path, "Screens")
    
    screen_count = 0
    if os.path.exists(screens_path):
        screen_count = len([f for f in os.listdir(screens_path) if f.endswith(".png")])
    
    try:
        status_data = {
            "checked": checked,
            "checked_at": datetime.now().isoformat() if checked else None,
            "screen_count": screen_count
        }
        
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({"success": True, "data": status_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/deleted-screens/<path:project_name>", methods=["GET"])
def get_deleted_screens(project_name):
    """获取项目已删除的截图列表"""
    project_path = get_project_path(project_name)
    deleted_dir = os.path.join(project_path, "deleted")
    
    result = {
        "total": 0,
        "batches": []
    }
    
    if not os.path.exists(deleted_dir):
        return jsonify(result)
    
    # 遍历所有批次文件夹
    for batch_name in sorted(os.listdir(deleted_dir), reverse=True):
        batch_path = os.path.join(deleted_dir, batch_name)
        if not os.path.isdir(batch_path):
            continue
        
        files = [f for f in os.listdir(batch_path) if f.endswith(".png")]
        if files:
            result["batches"].append({
                "timestamp": batch_name,
                "files": sorted(files),
                "count": len(files)
            })
            result["total"] += len(files)
    
    return jsonify(result)


@app.route("/api/deleted-thumb/<path:project_name>/<timestamp>/<filename>")
def serve_deleted_thumb(project_name, timestamp, filename):
    """提供已删除截图的缩略图"""
    project_path = get_project_path(project_name)
    deleted_dir = os.path.join(project_path, "deleted", timestamp)
    
    if not os.path.exists(os.path.join(deleted_dir, filename)):
        return "File not found", 404
    
    # 直接返回原图（已删除的不生成缩略图）
    return send_from_directory(deleted_dir, filename)


@app.route("/api/restore-single/<path:project_name>", methods=["POST"])
def restore_single_screen(project_name):
    """恢复单张已删除的截图"""
    data = request.json
    timestamp = data.get("timestamp")
    filename = data.get("filename")
    
    if not timestamp or not filename:
        return jsonify({"success": False, "error": "缺少参数"})
    
    project_path = get_project_path(project_name)
    deleted_dir = os.path.join(project_path, "deleted")
    batch_dir = os.path.join(deleted_dir, timestamp)
    
    # 确定目标目录
    is_downloads_2024 = project_name.startswith("downloads_2024/")
    if is_downloads_2024:
        screens_dir = project_path
    else:
        screens_dir = os.path.join(project_path, "Screens")
    
    src_path = os.path.join(batch_dir, filename)
    
    if not os.path.exists(src_path):
        return jsonify({"success": False, "error": "文件不存在"})
    
    # 找一个不冲突的文件名
    dst_filename = filename
    dst_path = os.path.join(screens_dir, dst_filename)
    counter = 1
    while os.path.exists(dst_path):
        name, ext = os.path.splitext(filename)
        dst_filename = f"{name}_restored{counter}{ext}"
        dst_path = os.path.join(screens_dir, dst_filename)
        counter += 1
    
    try:
        shutil.move(src_path, dst_path)
        
        # 如果批次文件夹空了，删除它
        remaining = [f for f in os.listdir(batch_dir) if f.endswith(".png")]
        if not remaining:
            shutil.rmtree(batch_dir)
        
        return jsonify({
            "success": True,
            "restored_as": dst_filename,
            "message": f"已恢复为 {dst_filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/all-onboarding", methods=["GET"])
def get_all_onboarding():
    """获取所有项目的 Onboarding 截图"""
    result = []
    
    # 扫描 downloads_2024 目录
    if os.path.exists(DOWNLOADS_2024_DIR):
        for name in sorted(os.listdir(DOWNLOADS_2024_DIR)):
            project_path = os.path.join(DOWNLOADS_2024_DIR, name)
            if not os.path.isdir(project_path):
                continue
            
            # 检查是否有 onboarding_range.json
            range_file = os.path.join(project_path, "onboarding_range.json")
            if not os.path.exists(range_file):
                continue
            
            with open(range_file, "r", encoding="utf-8") as f:
                range_data = json.load(f)
            
            start = range_data.get("start", -1)
            end = range_data.get("end", -1)
            
            if start <= 0 or end <= 0:
                continue
            
            # 获取截图列表
            all_screens = sorted([f for f in os.listdir(project_path) if f.endswith(".png")])
            
            # 根据范围筛选
            onboarding_screens = []
            for i, screen in enumerate(all_screens):
                screen_idx = i + 1
                if start <= screen_idx <= end:
                    onboarding_screens.append(screen)
            
            if onboarding_screens:
                result.append({
                    "name": name,
                    "project_path": f"downloads_2024/{name}",
                    "start": start,
                    "end": end,
                    "count": len(onboarding_screens),
                    "screens": onboarding_screens
                })
    
    return jsonify({"projects": result})


# ==================== App Store 商城数据 API ====================

@app.route("/api/store-comparison", methods=["GET"])
def get_store_comparison():
    """获取所有 APP 的商城对比数据，整合竞品 CSV 数据"""
    comparison_file = os.path.join(DOWNLOADS_2024_DIR, "store_comparison.json")
    csv_file = os.path.join(os.path.dirname(__file__), "data", "top30_must_study.csv")
    
    if not os.path.exists(comparison_file):
        return jsonify({"error": "对比数据不存在，请先运行 fetch_store_data.py"}), 404
    
    try:
        # 读取商城数据
        with open(comparison_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 读取竞品 CSV 数据
        csv_data = {}
        if os.path.exists(csv_file):
            import csv
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 使用 app_name 作为键（需要清理匹配）
                    app_name = row.get("app_name", "")
                    csv_data[app_name.lower()] = {
                        "revenue": int(float(row.get("revenue", 0) or 0)),
                        "downloads": int(float(row.get("downloads", 0) or 0)),
                        "arpu": float(row.get("arpu", 0) or 0),
                        "growth_rate": float(row.get("growth_rate", 0) or 0),
                        "dau": int(float(row.get("dau", 0) or 0)),
                        "priority": row.get("priority", "P1"),
                        "csv_rank": int(row.get("rank", 99) or 99),
                        "developer": row.get("publisher", "")
                    }
        
        # 合并数据
        for app in data.get("apps", []):
            track_name = (app.get("track_name") or "").lower()
            app_name = (app.get("name") or "").lower()
            
            # 尝试多种匹配方式
            matched_data = None
            for csv_key, csv_val in csv_data.items():
                csv_key_clean = csv_key.lower()
                # 精确匹配或包含匹配
                if (csv_key_clean == track_name or 
                    csv_key_clean in track_name or 
                    track_name in csv_key_clean or
                    app_name.replace("_", " ") in csv_key_clean or
                    csv_key_clean.split(":")[0].strip() == app_name.replace("_", " ")):
                    matched_data = csv_val
                    break
            
            if matched_data:
                app.update(matched_data)
            else:
                # 默认值
                app["revenue"] = 0
                app["downloads"] = 0
                app["arpu"] = 0
                app["growth_rate"] = 0
                app["dau"] = 0
                app["priority"] = "P1"
                app["csv_rank"] = 99
        
        # 按收入排序
        data["apps"].sort(key=lambda x: x.get("revenue", 0), reverse=True)
        
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/store-info/<path:project_name>", methods=["GET"])
def get_store_info(project_name):
    """获取单个 APP 的商城详细信息"""
    # 处理项目路径
    if project_name.startswith("downloads_2024/"):
        app_name = project_name.replace("downloads_2024/", "")
        project_path = os.path.join(DOWNLOADS_2024_DIR, app_name)
    else:
        project_path = os.path.join(DOWNLOADS_2024_DIR, project_name)
    
    info_file = os.path.join(project_path, "store_info.json")
    
    if not os.path.exists(info_file):
        return jsonify({"error": "商城信息不存在"}), 404
    
    try:
        with open(info_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 添加商城截图列表
        store_dir = os.path.join(project_path, "store")
        if os.path.exists(store_dir):
            screenshots = sorted([f for f in os.listdir(store_dir) if f.startswith("screenshot_")])
            data["local_screenshots"] = screenshots
        
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/store-screenshot/<path:project_name>/<filename>", methods=["GET"])
def get_store_screenshot(project_name, filename):
    """获取商城截图"""
    # 处理项目路径
    if project_name.startswith("downloads_2024/"):
        app_name = project_name.replace("downloads_2024/", "")
        store_dir = os.path.join(DOWNLOADS_2024_DIR, app_name, "store")
    else:
        store_dir = os.path.join(DOWNLOADS_2024_DIR, project_name, "store")
    
    if not os.path.exists(store_dir):
        return jsonify({"error": "商城截图目录不存在"}), 404
    
    file_path = os.path.join(store_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "文件不存在"}), 404
    
    return send_from_directory(store_dir, filename)


# ==================== 截图插入功能 ====================

@app.route("/api/insert-screenshot", methods=["POST"])
def insert_screenshot():
    """插入截图到指定位置"""
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400
    
    file = request.files['file']
    project = request.form.get('project')
    insert_after = int(request.form.get('insert_after', 0))
    
    if not file or not project:
        return jsonify({"success": False, "error": "缺少参数"}), 400
    
    # 获取项目路径
    project_path = get_project_path(project)
    
    # 确定截图目录
    if project.startswith("downloads_2024/"):
        screens_dir = project_path
    else:
        screens_dir = os.path.join(project_path, "Screens")
    
    if not os.path.exists(screens_dir):
        return jsonify({"success": False, "error": "截图目录不存在"}), 404
    
    # 获取现有截图列表
    existing_files = sorted([
        f for f in os.listdir(screens_dir) 
        if f.endswith(('.png', '.jpg', '.jpeg', '.webp')) and not f.startswith('.')
    ])
    
    # 计算新文件名
    # 如果插入到中间，需要重命名后续文件
    if insert_after < len(existing_files):
        # 从后往前重命名，避免覆盖
        for i in range(len(existing_files) - 1, insert_after - 1, -1):
            old_name = existing_files[i]
            old_path = os.path.join(screens_dir, old_name)
            
            # 提取扩展名
            ext = os.path.splitext(old_name)[1]
            new_num = i + 2  # +2 因为索引从0开始，且要为新文件腾位置
            new_name = f"{new_num:04d}{ext}"
            new_path = os.path.join(screens_dir, new_name)
            
            # 使用临时文件名避免冲突
            temp_path = os.path.join(screens_dir, f"_temp_{new_name}")
            shutil.move(old_path, temp_path)
        
        # 将临时文件重命名为正式文件名
        for f in os.listdir(screens_dir):
            if f.startswith("_temp_"):
                old_path = os.path.join(screens_dir, f)
                new_name = f.replace("_temp_", "")
                new_path = os.path.join(screens_dir, new_name)
                shutil.move(old_path, new_path)
    
    # 保存新文件
    new_num = insert_after + 1
    # 保持原始扩展名或使用 png
    original_ext = os.path.splitext(file.filename)[1].lower()
    if original_ext not in ['.png', '.jpg', '.jpeg']:
        original_ext = '.png'
    
    new_filename = f"{new_num:04d}{original_ext}"
    new_path = os.path.join(screens_dir, new_filename)
    
    # 保存上传的文件
    file.save(new_path)
    
    # 处理图片（可选：调整大小、转换格式等）
    try:
        img = Image.open(new_path)
        # 如果是 RGBA 模式且保存为 JPG，转换为 RGB
        if img.mode == 'RGBA' and original_ext in ['.jpg', '.jpeg']:
            img = img.convert('RGB')
        img.save(new_path, quality=95)
    except Exception as e:
        print(f"[WARN] Image processing error: {e}")
    
    # 清除缩略图缓存（清除正确的目录）
    for size in ['small', 'medium', 'large']:
        if project.startswith("downloads_2024/"):
            thumb_dir = os.path.join(screens_dir, f"thumbs_{size}")
        else:
            thumb_dir = os.path.join(project_path, f"Screens_thumbs_{size}")
        
        if os.path.exists(thumb_dir):
            shutil.rmtree(thumb_dir)
    
    return jsonify({
        "success": True,
        "filename": new_filename,
        "position": new_num,
        "total": len(existing_files) + 1
    })


# ==================== 商城截图 AI 分析 ====================

# AI 分析结果缓存目录
STORE_ANALYSIS_CACHE_DIR = os.path.join(BASE_DIR, "cache", "store_analysis")
os.makedirs(STORE_ANALYSIS_CACHE_DIR, exist_ok=True)


def get_analysis_cache_path(app_name, filename):
    """获取分析缓存文件路径"""
    safe_name = f"{app_name}_{filename}".replace("/", "_").replace("\\", "_")
    return os.path.join(STORE_ANALYSIS_CACHE_DIR, f"{safe_name}.json")


@app.route("/api/analyze-store-screenshot", methods=["POST"])
def analyze_store_screenshot():
    """使用 Claude Opus 4.5 分析商城截图"""
    data = request.get_json()
    app_name = data.get("app_name")
    filename = data.get("filename")
    force = data.get("force", False)  # 是否强制重新分析
    
    if not app_name or not filename:
        return jsonify({"success": False, "error": "缺少参数"}), 400
    
    # 检查缓存
    cache_path = get_analysis_cache_path(app_name, filename)
    if not force and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        cached["from_cache"] = True
        return jsonify(cached)
    
    # 检查截图是否存在
    store_dir = os.path.join(DOWNLOADS_2024_DIR, app_name, "store")
    image_path = os.path.join(store_dir, filename)
    
    if not os.path.exists(image_path):
        return jsonify({"success": False, "error": "截图文件不存在"}), 404
    
    # 获取 Anthropic API Key
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return jsonify({"success": False, "error": "未配置 ANTHROPIC_API_KEY"}), 500
    
    # 读取图片并转为 base64
    import base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    # 判断图片类型
    media_type = "image/png"
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        media_type = "image/jpeg"
    elif filename.lower().endswith(".webp"):
        media_type = "image/webp"
    
    # 构建分析 prompt
    analysis_prompt = """分析这张 App Store 商城截图，请从以下三个维度进行分析：

## 1. 营销策略 (Marketing)
- 核心卖点是什么？
- 使用了什么情感诉求？
- 有什么促销或转化技巧？

## 2. 设计元素 (Design)
- 配色方案和视觉风格
- 布局结构和视觉层级
- 有什么设计亮点？

## 3. ASO 洞察 (ASO)
- 截图传达了什么关键功能？
- 针对用户什么痛点？
- 与竞品相比有什么差异化？

请用简洁的中文回答，每个维度 2-3 个要点。"""

    try:
        # 调用 Claude API (Opus 4.5)
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": analysis_prompt
                            }
                        ]
                    }
                ]
            },
            timeout=90
        )
        
        if response.status_code != 200:
            return jsonify({
                "success": False, 
                "error": f"Claude API 错误: {response.status_code}",
                "detail": response.text
            }), 500
        
        result = response.json()
        analysis_text = result["content"][0]["text"]
        
        # 解析分析结果
        analysis_result = {
            "success": True,
            "app_name": app_name,
            "filename": filename,
            "analysis": analysis_text,
            "model": "claude-sonnet-4-20250514",
            "analyzed_at": datetime.now().isoformat(),
            "from_cache": False
        }
        
        # 保存到缓存
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        return jsonify(analysis_result)
        
    except requests.exceptions.Timeout:
        return jsonify({"success": False, "error": "AI 分析超时，请重试"}), 504
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/store-analysis-cache/<app_name>/<filename>", methods=["GET"])
def get_store_analysis_cache(app_name, filename):
    """获取已缓存的分析结果"""
    cache_path = get_analysis_cache_path(app_name, filename)
    
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    
    return jsonify({"success": False, "cached": False})


# ==================== 启动 ====================

if __name__ == "__main__":
    print("=" * 50)
    print("PM Screenshot Tool - 产品经理截图分析助手")
    print("=" * 50)
    print(f"项目目录: {PROJECTS_DIR}")
    print("启动服务器: http://localhost:5000")
    print("=" * 50)
    
    import webbrowser
    webbrowser.open("http://localhost:5000")
    
    app.run(debug=False, port=5000)
