content = '''# -*- coding: utf-8 -*-
import os
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont

class CaptureDialog(QDialog):
    def __init__(self, media_path, capture_type, parent=None):
        super().__init__(parent)
        self.media_path = media_path
        self.capture_type = capture_type
        self.note = ""
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("已捕获")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("QDialog{background:white;}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        title = QLabel("✓ 已捕获")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title.setStyleSheet("color:#4caf50;")
        layout.addWidget(title)
        
        # 预览区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea{border:2px solid #ddd;border-radius:8px;background:#f5f5f5;}
            QScrollBar:vertical{width:10px;}
            QScrollBar:horizontal{height:10px;}
        """)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 根据图片大小设置窗口
        if os.path.exists(self.media_path):
            pixmap = QPixmap(self.media_path)
            if not pixmap.isNull():
                img_w, img_h = pixmap.width(), pixmap.height()
                
                # 预览区域最大尺寸
                max_preview_w, max_preview_h = 800, 550
                
                # 计算合适的预览尺寸
                if img_w <= max_preview_w and img_h <= max_preview_h:
                    # 小图：原尺寸显示
                    self.preview_label.setPixmap(pixmap)
                    preview_w, preview_h = img_w + 20, img_h + 20
                else:
                    # 大图：等比缩小
                    ratio = min(max_preview_w / img_w, max_preview_h / img_h)
                    new_w, new_h = int(img_w * ratio), int(img_h * ratio)
                    scaled = pixmap.scaled(new_w, new_h, 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
                    self.preview_label.setPixmap(scaled)
                    preview_w, preview_h = new_w + 20, new_h + 20
                
                # 设置滚动区域大小
                scroll.setMinimumSize(min(preview_w, max_preview_w + 20), min(preview_h, max_preview_h + 20))
        
        scroll.setWidget(self.preview_label)
        layout.addWidget(scroll)
        
        # 补充说明
        note_label = QLabel("💬 补充说明（可选）：")
        note_label.setStyleSheet("color:#333;font-weight:bold;")
        layout.addWidget(note_label)
        
        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText("简单描述问题...")
        self.note_input.setFixedHeight(60)
        self.note_input.setStyleSheet("QTextEdit{border:2px solid #e0e0e0;border-radius:6px;padding:8px;}QTextEdit:focus{border-color:#2196f3;}")
        layout.addWidget(self.note_input)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        save_btn = QPushButton("✓ 保存")
        save_btn.setStyleSheet("QPushButton{background:#4caf50;color:white;border:none;border-radius:6px;padding:12px 30px;font-size:14px;font-weight:bold;}")
        save_btn.clicked.connect(self.on_save)
        btn_layout.addWidget(save_btn)
        
        retry_btn = QPushButton("🔄 重新截图")
        retry_btn.setStyleSheet("QPushButton{background:#ff9800;color:white;border:none;border-radius:6px;padding:12px 30px;font-size:14px;}")
        retry_btn.clicked.connect(self.on_retry)
        btn_layout.addWidget(retry_btn)
        
        cancel_btn = QPushButton("✕ 取消")
        cancel_btn.setStyleSheet("QPushButton{background:#9e9e9e;color:white;border:none;border-radius:6px;padding:12px 30px;font-size:14px;}")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 自动调整窗口大小
        self.adjustSize()
        self.setMinimumWidth(500)
        
        self.note_input.setFocus()
    
    def on_save(self):
        self.note = self.note_input.toPlainText().strip()
        self.accept()
    
    def on_retry(self):
        if os.path.exists(self.media_path):
            try: os.remove(self.media_path)
            except: pass
        self.reject()
        if self.parent(): self.parent().on_screenshot()
    
    def get_note(self):
        return self.note
'''
with open(r'c:\Users\WIN\Desktop\Cursor Project\PM_Test_Assistant\ui\capture_dialog.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
