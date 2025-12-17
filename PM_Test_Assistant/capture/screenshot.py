# -*- coding: utf-8 -*-
"""截图模块"""
import os
from datetime import datetime

class ScreenCapture:
    def __init__(self):
        self.save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'sessions')
        os.makedirs(self.save_dir, exist_ok=True)
    
    def capture_screen(self):
        """区域选择截图"""
        try:
            from capture.region_selector import select_region
            
            pixmap = select_region()
            
            if pixmap and not pixmap.isNull():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"screenshot_{timestamp}.png"
                filepath = os.path.join(self.save_dir, filename)
                pixmap.save(filepath, "PNG")
                return filepath
            return None
        except Exception as e:
            print(f"Screenshot error: {e}")
            return None
    
    def capture_fullscreen(self):
        """全屏截图"""
        try:
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            pixmap = screen.grabWindow(0)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"fullscreen_{timestamp}.png"
            filepath = os.path.join(self.save_dir, filename)
            pixmap.save(filepath, "PNG")
            return filepath
        except Exception as e:
            print(f"Fullscreen error: {e}")
            return None
