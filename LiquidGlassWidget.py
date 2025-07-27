import sys
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, QLayout, QLayoutItem
from PyQt5.QtCore import Qt, QRectF, QPoint, QSize
from PyQt5.QtGui import QPainter, QLinearGradient, QColor, QPainterPath, QRegion, QPen, QBrush, QFont, QCursor

class LiquidGlassWidget(QWidget):
    
    def __init__(self, parent=None, title="透明玻璃窗口", size=(320, 150), position=(100, 100)):
        """
        初始化透明玻璃窗口
        
        :param parent: 父窗口
        :param title: 窗口标题
        :param size: 窗口大小 (宽, 高)
        :param position: 窗口初始位置 (x, y)
        """
        super().__init__(parent)
        
        # 窗口属性
        self._title = title
        self._size = QSize(size[0], size[1])
        self._position = position
        self._radius = 20
        self._glass_margin = 8
        self._glass_radius = 15
        
    


    def create_rounded_mask(self, radius=20):
        """创建圆角矩形区域蒙版"""
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), radius, radius)
        region = QRegion(0, 0, self.width(), self.height())
        return region.intersected(QRegion(path.toFillPolygon().toPolygon()))
    
    def setTitle(self, title):
        """设置窗口标题"""
        self._title = title
        self.title_label.setText(title)
        self.update()
    
    def setSize(self, width, height):
        """设置窗口大小"""
        self._size = QSize(width, height)
        self.setFixedSize(self._size)
        self.setMask(self.create_rounded_mask(radius=self._radius))
        self.update()
    
    def setPosition(self, x, y):
        """设置窗口位置"""
        self._position = (x, y)
        screen_geo = QApplication.primaryScreen().availableGeometry()
        x = max(screen_geo.left(), min(x, screen_geo.right() - self.width()))
        y = max(screen_geo.top(), min(y, screen_geo.bottom() - self.height()))
        self.move(x, y)
    
    def setCornerRadius(self, radius):
        """设置窗口圆角半径"""
        self._radius = radius
        self.setMask(self.create_rounded_mask(radius=self._radius))
        self.update()
    
    def setGlassMargin(self, margin):
        """设置玻璃效果边距"""
        self._glass_margin = margin
        self.update()
    
    def setGlassRadius(self, radius):
        """设置玻璃效果圆角半径"""
        self._glass_radius = radius
        self.update()
    
    def addWidget(self, widget):
        """添加小部件到内容区域"""
        if not hasattr(self, 'content_layout'):
            self.initUI()
        
        # 如果内容区域还没有布局，创建一个
        if self.content_widget.layout() is None:
            content_layout = QVBoxLayout(self.content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(5)
            self.content_widget.setLayout(content_layout)
        
        # 添加小部件到内容布局
        self.content_widget.layout().addWidget(widget)
    
    def addLayout(self, layout):
        """添加布局到内容区域"""
        if not hasattr(self, 'content_layout'):
            self.initUI()
        
        # 如果内容区域还没有布局，创建一个
        if self.content_widget.layout() is None:
            content_layout = QVBoxLayout(self.content_widget)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(5)
            self.content_widget.setLayout(content_layout)
        
        # 添加布局到内容布局
        self.content_widget.layout().addLayout(layout)
    
    def clearContent(self):
        """清空内容区域"""
        if self.content_widget.layout():
            while self.content_widget.layout().count():
                item = self.content_widget.layout().takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
    

    def paintEvent(self, event):
        """绘制透明玻璃效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # 玻璃效果区域
        glass_rect = QRectF(
            self._glass_margin, 
            self._glass_margin, 
            self.width() - 2 * self._glass_margin, 
            self.height() - 2 * self._glass_margin
        )
        
        # 绘制玻璃效果 - 接近完全透明
        glass_path = QPainterPath()
        glass_path.addRoundedRect(glass_rect, self._glass_radius, self._glass_radius)
        
        # 玻璃渐变 - 极低的不透明度
        glass_gradient = QLinearGradient(glass_rect.topLeft(), glass_rect.bottomRight())
        glass_gradient.setColorAt(0.0, QColor(220, 240, 255, 30))
        glass_gradient.setColorAt(0.3, QColor(200, 230, 255, 20))
        glass_gradient.setColorAt(0.7, QColor(200, 230, 255, 20))
        glass_gradient.setColorAt(1.0, QColor(220, 240, 255, 30))
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(glass_gradient)
        painter.drawPath(glass_path)
        
        # 绘制边框高光效果
        border_width = 1.2
        border_rect = glass_rect.adjusted(
            -border_width/2, 
            -border_width/2, 
            border_width/2, 
            border_width/2
        )
        
        # 创建边框路径
        border_path = QPainterPath()
        border_path.addRoundedRect(border_rect, self._glass_radius + 1, self._glass_radius + 1)
        
        # 减去内部路径，只保留边框
        inner_path = QPainterPath()
        inner_path.addRoundedRect(glass_rect, self._glass_radius, self._glass_radius)
        border_path = border_path.subtracted(inner_path)
        
        # 边框高光渐变
        border_gradient = QLinearGradient(border_rect.topLeft(), border_rect.bottomRight())
        border_gradient.setColorAt(0.0, QColor(255, 255, 255, 100))
        border_gradient.setColorAt(0.2, QColor(240, 250, 255, 80))
        border_gradient.setColorAt(0.8, QColor(150, 200, 230, 60))
        border_gradient.setColorAt(1.0, QColor(120, 180, 220, 40))
        
        # 设置画笔绘制边框高光
        painter.setPen(QPen(QBrush(border_gradient), border_width))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(border_path)
        
        # 添加顶部高光反射
        highlight_height = 15
        highlight_rect = QRectF(
            glass_rect.x(), 
            glass_rect.y(), 
            glass_rect.width(), 
            highlight_height
        )
        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(highlight_rect, self._glass_radius, self._glass_radius)
        
        # 裁剪到玻璃区域
        painter.setClipPath(glass_path)
        
        # 绘制高光
        highlight_gradient = QLinearGradient(highlight_rect.topLeft(), highlight_rect.bottomLeft())
        highlight_gradient.setColorAt(0.0, QColor(255, 255, 255, 40))
        highlight_gradient.setColorAt(0.4, QColor(255, 255, 255, 10))
        highlight_gradient.setColorAt(1.0, Qt.transparent)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(highlight_gradient)
        painter.drawPath(highlight_path)
        
        # 添加底部反光
        reflection_height = 10
        reflection_rect = QRectF(
            glass_rect.x(), 
            glass_rect.bottom() - reflection_height, 
            glass_rect.width(), 
            reflection_height
        )
        reflection_path = QPainterPath()
        reflection_path.addRoundedRect(reflection_rect, self._glass_radius, self._glass_radius)
        
        # 绘制底部反光
        reflection_gradient = QLinearGradient(reflection_rect.topLeft(), reflection_rect.bottomLeft())
        reflection_gradient.setColorAt(0.0, Qt.transparent)
        reflection_gradient.setColorAt(0.4, QColor(180, 220, 255, 15))
        reflection_gradient.setColorAt(1.0, QColor(180, 220, 255, 5))
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(reflection_gradient)
        painter.drawPath(reflection_path)
        
        # 重置裁剪区域
        painter.setClipPath(QPainterPath())

