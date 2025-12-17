# -*- coding: utf-8 -*-
content = '''# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from capture.screenshot import ScreenCapture
from ui.capture_dialog import CaptureDialog
from ai.analyzer import AIAnalyzer
from report.generator import ReportGenerator

class IssueItem(QFrame):
    clicked = pyqtSignal(dict)
    def __init__(self, issue_data, parent=None):
        super().__init__(parent)
        self.issue_data = issue_data
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        num = QLabel(f"#{issue_data.get('id', 0)}")
        num.setStyleSheet("color:#333;font-weight:bold;")
        num.setFixedWidth(30)
        layout.addWidget(num)
        title = QLabel(issue_data.get('title', ''))
        title.setStyleSheet("color:#333;")
        layout.addWidget(title, 1)
        cat = issue_data.get('category', '')
        colors = {'设计':'#e91e63','开发':'#2196f3','待讨论':'#ff9800'}
        cat_lbl = QLabel(f"[{cat}]")
        cat_lbl.setStyleSheet(f"color:{colors.get(cat,'#666')};")
        layout.addWidget(cat_lbl)
        btn = QPushButton("▶")
        btn.setFixedSize(26,26)
        btn.setStyleSheet("background:#4CAF50;color:white;border-radius:13px;")
        btn.clicked.connect(lambda: self.clicked.emit(self.issue_data))
        layout.addWidget(btn)
        self.setStyleSheet("background:#f5f5f5;border-radius:6px;margin:2px;")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.issues = []
        self.issue_counter = 0
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screen_capture = ScreenCapture()
        self.ai_analyzer = AIAnalyzer()
        self.report_generator = ReportGenerator()
        self.setup_ui()
        self.setup_hotkeys()

    def setup_ui(self):
        self.setWindowTitle("PM测试助手")
        self.setFixedSize(360, 520)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setStyleSheet("QMainWindow{background:#fff;}")
        c = QWidget()
        self.setCentralWidget(c)
        L = QVBoxLayout(c)
        L.setContentsMargins(12,12,12,12)
        L.setSpacing(10)
        
        h = QHBoxLayout()
        t = QLabel("🔍 PM测试助手")
        t.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        t.setStyleSheet("color:#333;")
        h.addWidget(t)
        h.addStretch()
        sb = QPushButton("⚙")
        sb.setFixedSize(32,32)
        sb.setStyleSheet("background:#eee;border-radius:16px;font-size:16px;border:none;")
        sb.clicked.connect(self.show_settings)
        h.addWidget(sb)
        L.addLayout(h)
        
        hk = QLabel("⌨️ F1 截图 | F2 录屏 | F3 长录")
        hk.setStyleSheet("background:#e3f2fd;color:#1565c0;padding:10px;border-radius:6px;")
        L.addWidget(hk)
        
        self.stats_label = QLabel("📋 已记录: 0 个问题")
        self.stats_label.setStyleSheet("color:#333;font-size:13px;")
        L.addWidget(self.stats_label)
        
        self.issue_list = QListWidget()
        self.issue_list.setStyleSheet("QListWidget{background:#fafafa;border:1px solid #ddd;border-radius:8px;}")
        L.addWidget(self.issue_list, 1)
        
        bl = QHBoxLayout()
        bl.setSpacing(8)
        b1 = QPushButton("📄 生成报告")
        b1.setStyleSheet("background:#2196f3;color:white;padding:10px;border-radius:6px;border:none;")
        b1.clicked.connect(self.generate_report)
        bl.addWidget(b1)
        b2 = QPushButton("🆕 新建")
        b2.setStyleSheet("background:#4CAF50;color:white;padding:10px;border-radius:6px;border:none;")
        b2.clicked.connect(self.new_session)
        bl.addWidget(b2)
        b3 = QPushButton("🗑️ 清空")
        b3.setStyleSheet("background:#ff5722;color:white;padding:10px;border-radius:6px;border:none;")
        b3.clicked.connect(self.clear_issues)
        bl.addWidget(b3)
        L.addLayout(bl)
        
        self.status_label = QLabel("✅ 就绪")
        self.status_label.setStyleSheet("color:#666;font-size:11px;")
        L.addWidget(self.status_label)

    def setup_hotkeys(self):
        try:
            import keyboard
            keyboard.add_hotkey('F1', self.on_screenshot)
            keyboard.add_hotkey('F2', lambda: self.status_label.setText("🎬 录屏开发中"))
            keyboard.add_hotkey('F3', lambda: self.status_label.setText("🎬 长录屏开发中"))
            self.status_label.setText("✅ 快捷键已启用")
        except Exception as e:
            self.status_label.setText(f"❌ {e}")

    def on_screenshot(self):
        QTimer.singleShot(100, self._do_screenshot)

    def _do_screenshot(self):
        try:
            self.status_label.setText("📷 截图中...")
            p = self.screen_capture.capture_screen()
            if p:
                d = CaptureDialog(p, 'screenshot', self)
                if d.exec():
                    self.process_capture(p, 'screenshot', d.get_note())
                else:
                    self.status_label.setText("✅ 已取消")
        except Exception as e:
            self.status_label.setText(f"❌ {e}")

    def process_capture(self, path, ctype, note):
        self.status_label.setText("🤖 AI分析中...")
        self.issue_counter += 1
        issue = {'id':self.issue_counter,'media_path':path,'capture_type':ctype,'user_note':note,'title':'分析中...','category':'待分析','description':'','suggestion':''}
        self.issues.append(issue)
        self.update_list()
        QTimer.singleShot(100, lambda: self.analyze(issue))

    def analyze(self, issue):
        try:
            r = self.ai_analyzer.analyze(issue['media_path'], issue['user_note'])
            issue['title'] = r.get('title','问题')
            issue['category'] = r.get('category','待讨论')
            issue['description'] = r.get('description','')
            issue['suggestion'] = r.get('suggestion','')
            self.status_label.setText("✅ 分析完成")
        except Exception as e:
            issue['title'] = issue['user_note'] or '截图'
            issue['category'] = '待分析'
            self.status_label.setText(f"⚠️ {str(e)[:30]}")
        self.update_list()

    def update_list(self):
        self.issue_list.clear()
        for issue in reversed(self.issues):
            item = QListWidgetItem()
            w = IssueItem(issue)
            w.clicked.connect(self.view_issue)
            item.setSizeHint(w.sizeHint())
            self.issue_list.addItem(item)
            self.issue_list.setItemWidget(item, w)
        self.stats_label.setText(f"📋 已记录: {len(self.issues)} 个问题")

    def view_issue(self, d):
        p = d.get('media_path','')
        if os.path.exists(p): os.startfile(p)

    def generate_report(self):
        if not self.issues:
            QMessageBox.warning(self,"提示","没有问题")
            return
        try:
            p = self.report_generator.generate(self.issues, self.session_id)
            if os.path.exists(p): os.startfile(p)
        except Exception as e:
            QMessageBox.warning(self,"错误",str(e))

    def new_session(self):
        self.issues=[]
        self.issue_counter=0
        self.session_id=datetime.now().strftime("%Y%m%d_%H%M%S")
        self.update_list()
        self.status_label.setText("✅ 新会话")

    def clear_issues(self):
        if self.issues:
            if QMessageBox.question(self,"确认","清空?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                self.issues=[]
                self.issue_counter=0
                self.update_list()

    def show_settings(self):
        QMessageBox.information(self,"设置","F1截图\nF2/F3录屏(开发中)")

    def closeEvent(self, e):
        try:
            import keyboard
            keyboard.unhook_all()
        except: pass
        e.accept()
'''
with open(r'c:\Users\WIN\Desktop\Cursor Project\PM_Test_Assistant\ui\main_window.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
