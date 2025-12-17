# -*- coding: utf-8 -*-
"""
PM Test Assistant - 产品经理实时测试助手
主程序入口
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def load_config():
    """加载配置"""
    config_path = BASE_DIR / "config" / "settings.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def setup_api_keys(config):
    """设置 API Keys"""
    api_keys = config.get("api_keys", {})
    
    # 尝试从 PM_Screenshot_Tool 加载已有的 API Keys
    pm_tool_config = BASE_DIR.parent / "PM_Screenshot_Tool" / "config" / "api_keys.json"
    if pm_tool_config.exists():
        try:
            with open(pm_tool_config, "r", encoding="utf-8") as f:
                existing_keys = json.load(f)
                for key, value in existing_keys.items():
                    if value and not os.environ.get(key):
                        os.environ[key] = value
                        print(f"[CONFIG] 从 PM_Screenshot_Tool 加载 {key}")
        except Exception as e:
            print(f"[WARN] 加载 PM_Screenshot_Tool API Keys 失败: {e}")
    
    # 加载本地配置的 API Keys
    if api_keys.get("openai"):
        os.environ["OPENAI_API_KEY"] = api_keys["openai"]
    if api_keys.get("anthropic"):
        os.environ["ANTHROPIC_API_KEY"] = api_keys["anthropic"]


def main():
    """主程序入口"""
    print("=" * 50)
    print("PM Test Assistant - 产品经理实时测试助手")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    setup_api_keys(config)
    
    # 启用高DPI支持
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("PM Test Assistant")
    app.setOrganizationName("PM Tools")
    app.setStyle("Fusion")
    
    # 导入并创建主窗口
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    
    print("[APP] 应用已启动")
    print("[TIP] 使用 F1 截图, F2 短录屏, F3 长录屏")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
