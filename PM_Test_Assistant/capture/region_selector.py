# -*- coding: utf-8 -*-
"""区域选择截图 - 支持高DPI"""
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QGuiApplication

class RegionSelector(QWidget):
    def __init__(self):
        super().__init__()
        self.start_pos = None
        self.end_pos = None
        self.is_selecting = False
        self.selected_rect = None
        
        # 获取屏幕和设备像素比
        screen = QGuiApplication.primaryScreen()
        self.device_ratio = screen.devicePixelRatio()
        
        # 全屏截图
        self.full_screenshot = screen.grabWindow(0)
        
        # 全屏窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # 绘制背景（缩放到窗口大小）
        painter.drawPixmap(self.rect(), self.full_screenshot)
        
        # 半透明遮罩
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        
        if self.start_pos and self.end_pos:
            rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # 显示选中区域的原图
            # 计算实际像素坐标
            src_rect = QRect(
                int(rect.x() * self.device_ratio),
                int(rect.y() * self.device_ratio),
                int(rect.width() * self.device_ratio),
                int(rect.height() * self.device_ratio)
            )
            painter.drawPixmap(rect, self.full_screenshot, src_rect)
            
            # 边框
            pen = QPen(QColor(0, 174, 255), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # 尺寸
            real_w = int(rect.width() * self.device_ratio)
            real_h = int(rect.height() * self.device_ratio)
            size_text = f"{real_w} x {real_h}"
            painter.fillRect(rect.x(), rect.y() - 25, len(size_text) * 9 + 10, 22, QColor(0, 174, 255))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(rect.x() + 5, rect.y() - 8, size_text)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.is_selecting = True
            
    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_pos = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.end_pos = event.pos()
            self.is_selecting = False
            rect = QRect(self.start_pos, self.end_pos).normalized()
            
            if rect.width() > 10 and rect.height() > 10:
                # 保存实际像素坐标的区域
                self.selected_rect = QRect(
                    int(rect.x() * self.device_ratio),
                    int(rect.y() * self.device_ratio),
                    int(rect.width() * self.device_ratio),
                    int(rect.height() * self.device_ratio)
                )
                self.close()
            else:
                self.update()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selected_rect = None
            self.close()
        
    def get_selected_region(self):
        if self.selected_rect:
            return self.full_screenshot.copy(self.selected_rect)
        return None


def select_region():
    selector = RegionSelector()
    selector.showFullScreen()
    selector.activateWindow()
    
    while selector.isVisible():
        QApplication.processEvents()
    
    return selector.get_selected_region()
