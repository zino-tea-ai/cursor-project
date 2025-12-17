# -*- coding: utf-8 -*-
import os

# main_window.py 内容
main_window_content = '''# -*- coding: utf-8 -*-
"""
主窗口 - 悬浮小窗口
"""

import os
import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

from capture.screenshot import ScreenCapture
from ui.capture_dialog import CaptureDialog
from ai.analyzer import AIAnalyzer
from report.generator import ReportGenerator


class IssueItem(QFrame):
    """问题条目组件"""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, issue_data, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        
        num_label = QLabel(f"#{self.issue_data.get('id', 0)}")
        num_label.setFixedWidth(32)
        num_label.setStyleSheet("color: #667eea; font-weight: bold;")
        layout.addWidget(num_label)
        
        desc = self.issue_data.get("summary", "未分析")
        desc_label = QLabel(desc[:25] + "..." if len(desc) > 25 else desc)
        desc_label.setStyleSheet("color: #333;")
        layout.addWidget(desc_label, 1)
        
        owner = self.issue_data.get("owner", "待讨论")
        colors = {"设计": "#e91e63", "开发": "#2196f3", "待讨论": "#ff9800"}
        cat_label = QLabel(owner)
        cat_label.setStyleSheet(f"""
            background-color: {colors.get(owner, "#999")};
            color: white; padding: 2px 8px;
            border-radius: 4px; font-size: 11px;
        """)
        layout.addWidget(cat_label)
        
        view_btn = QPushButton("▶")
        view_btn.setFixedSize(26, 26)
        view_btn.setStyleSheet("""
            QPushButton { background: #f0f0f0; border-radius: 4px; }
            QPushButton:hover { background: #e0e0e0; }
        """)
        view_btn.clicked.connect(lambda: self.clicked.emit(self.issue_data))
        layout.addWidget(view_btn)
        
        self.setStyleSheet("""
            IssueItem { background-color: #f8f9fa; border-radius: 6px; }
            IssueItem:hover { background-color: #e9ecef; }
        """)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        self.issues = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path(__file__).parent.parent
        self.session_dir = self.base_dir / "data" / "sessions" / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self.screen_capture = ScreenCapture()
        self.ai_analyzer = AIAnalyzer(config)
        self.report_generator = ReportGenerator()
        
        self.setup_ui()
        self.setup_hotkeys()
    
    def setup_ui(self):
        self.setWindowTitle("PM测试助手")
        self.setFixedSize(360, 500)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        title_layout = QHBoxLayout()
        title_label = QLabel("PM测试助手")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(28, 28)
        settings_btn.setStyleSheet("background: #f0f0f0; border-radius: 4px;")
        settings_btn.clicked.connect(self.show_settings)
        title_layout.addWidget(settings_btn)
        layout.addLayout(title_layout)
        
        hotkey_frame = QFrame()
        hotkey_frame.setStyleSheet("background: #e3f2fd; border-radius: 6px;")
        hotkey_layout = QHBoxLayout(hotkey_frame)
        hotkey_layout.setContentsMargins(12, 8, 12, 8)
        hotkey_label = QLabel("快捷键: F1 截图 | F2 短录屏 | F3 长录屏")
        hotkey_label.setStyleSheet("color: #1565c0; font-size: 11px;")
        hotkey_layout.addWidget(hotkey_label)
        layout.addWidget(hotkey_frame)
        
        self.count_label = QLabel("已记录: 0 个问题")
        self.count_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.count_label)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #ddd; border-radius: 6px; background: white; }")
        self.issue_container = QWidget()
        self.issue_layout = QVBoxLayout(self.issue_container)
        self.issue_layout.setContentsMargins(6, 6, 6, 6)
        self.issue_layout.setSpacing(6)
        self.issue_layout.addStretch()
        scroll.setWidget(self.issue_container)
        layout.addWidget(scroll, 1)
        
        btn_layout = QHBoxLayout()
        btn_style = """
            QPushButton { background: #667eea; color: white; border: none;
                padding: 10px 16px; border-radius: 6px; font-size: 12px; }
            QPushButton:hover { background: #5a67d8; }
        """
        
        capture_btn = QPushButton("📷 截图")
        capture_btn.setStyleSheet(btn_style)
        capture_btn.clicked.connect(self.do_screenshot)
        btn_layout.addWidget(capture_btn)
        
        report_btn = QPushButton("📄 生成报告")
        report_btn.setStyleSheet(btn_style)
        report_btn.clicked.connect(self.generate_report)
        btn_layout.addWidget(report_btn)
        
        new_btn = QPushButton("🔄 新建")
        new_btn.setStyleSheet(btn_style.replace("#667eea", "#6c757d").replace("#5a67d8", "#5a6268"))
        new_btn.clicked.connect(self.new_session)
        btn_layout.addWidget(new_btn)
        
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        self.setStyleSheet("QMainWindow { background: #ffffff; }")
    
    def setup_hotkeys(self):
        try:
            from pynput import keyboard
            
            def on_press(key):
                try:
                    if key == keyboard.Key.f1:
                        QTimer.singleShot(0, self.do_screenshot)
                    elif key == keyboard.Key.f2:
                        QTimer.singleShot(0, self.do_short_record)
                    elif key == keyboard.Key.f3:
                        QTimer.singleShot(0, self.do_long_record)
                except: pass
            
            self.hotkey_listener = keyboard.Listener(on_press=on_press)
            self.hotkey_listener.start()
            self.status_label.setText("快捷键已启用 (F1/F2/F3)")
        except ImportError:
            self.status_label.setText("pynput未安装，快捷键不可用")
    
    def do_screenshot(self):
        self.status_label.setText("正在截图...")
        self.hide()
        QTimer.singleShot(300, self._capture_screenshot)
    
    def _capture_screenshot(self):
        image_path = self.screen_capture.capture_screen(self.session_dir)
        self.show()
        
        if image_path:
            dialog = CaptureDialog(image_path, self)
            if dialog.exec():
                user_note = dialog.get_note()
                self.process_capture(str(image_path), user_note, "screenshot")
                self.status_label.setText("截图已保存")
            else:
                self.status_label.setText("已取消")
        else:
            self.status_label.setText("截图失败")
    
    def do_short_record(self):
        QMessageBox.information(self, "提示", "短录屏功能开发中...")
    
    def do_long_record(self):
        QMessageBox.information(self, "提示", "长录屏功能开发中...")
    
    def process_capture(self, media_path, user_note, capture_type):
        self.status_label.setText("AI分析中...")
        QApplication.processEvents()
  
