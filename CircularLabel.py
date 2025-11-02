from PyQt5.QtCore import Qt
from PyQt5.QtGui import (QPainter,
                         QPainterPath,
                         QColor)
from PyQt5.QtWidgets import QLabel


class CircularLabel(QLabel):
    """圆形标签类，用于显示圆形头像"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        
    def paintEvent(self, event):
        """重绘事件，将图片裁剪为圆形"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 创建圆形路径
        path = QPainterPath()
        path.addEllipse(0, 0, self.width(), self.height())
        painter.setClipPath(path)
        
        # 绘制图片
        if not self.pixmap().isNull():
            pixmap = self.pixmap().scaled(
                self.size(), 
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )
            painter.drawPixmap(0, 0, pixmap)
        
        # 绘制圆形边框
        painter.setPen(QColor(255, 255, 255, 100))
        painter.drawEllipse(0, 0, self.width()-1, self.height()-1)