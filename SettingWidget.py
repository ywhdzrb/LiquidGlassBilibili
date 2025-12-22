import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QCheckBox,
    QGroupBox, QScrollArea, QFrame,
    QSpinBox, QColorDialog, QComboBox, QMessageBox,
    QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient, QPen, QBrush
import json
import os

class GlassButton(QPushButton):
    """玻璃效果按钮"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Microsoft YaHei", 10))
        self.setFixedHeight(40)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 玻璃效果背景
        glass_rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        glass_path = QPainterPath()
        glass_path.addRoundedRect(glass_rect, 8, 8)
        
        # 玻璃渐变
        glass_gradient = QLinearGradient(glass_rect.topLeft(), glass_rect.bottomLeft())
        if self.isEnabled():
            glass_gradient.setColorAt(0.0, QColor(100, 150, 255, 150))
            glass_gradient.setColorAt(0.4, QColor(80, 130, 220, 120))
            glass_gradient.setColorAt(1.0, QColor(60, 110, 200, 100))
        else:
            glass_gradient.setColorAt(0.0, QColor(150, 150, 150, 100))
            glass_gradient.setColorAt(1.0, QColor(120, 120, 120, 80))
        
        painter.fillPath(glass_path, glass_gradient)
        
        # 边框高光
        border_path = QPainterPath()
        border_rect = glass_rect.adjusted(-1, -1, 1, 1)
        border_path.addRoundedRect(border_rect, 9, 9)
        border_path = border_path.subtracted(glass_path)
        
        border_gradient = QLinearGradient(border_rect.topLeft(), border_rect.bottomLeft())
        border_gradient.setColorAt(0.0, QColor(255, 255, 255, 80))
        border_gradient.setColorAt(1.0, QColor(200, 220, 255, 60))
        
        painter.fillPath(border_path, border_gradient)
        
        # 顶部高光
        highlight_rect = glass_rect.adjusted(0, 0, 0, glass_rect.height() // 2)
        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(highlight_rect, 8, 8)
        highlight_path = highlight_path.intersected(glass_path)
        
        highlight_gradient = QLinearGradient(highlight_rect.topLeft(), highlight_rect.bottomLeft())
        highlight_gradient.setColorAt(0.0, QColor(255, 255, 255, 60))
        highlight_gradient.setColorAt(1.0, QColor(255, 255, 255, 20))
        
        painter.fillPath(highlight_path, highlight_gradient)
        
        # 绘制文字
        painter.setPen(QPen(QColor(255, 255, 255, 220)))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

class GlassSlider(QSlider):
    """玻璃效果滑块"""
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算滑块位置
        if self.maximum() == self.minimum():
            return
            
        ratio = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        handle_pos = ratio * (self.width() - 20) + 10
        
        # 绘制轨道
        track_rect = QRectF(10, self.height()//2 - 2, self.width() - 20, 4)
        
        # 轨道背景
        track_bg = QPainterPath()
        track_bg.addRoundedRect(track_rect, 2, 2)
        painter.fillPath(track_bg, QColor(255, 255, 255, 40))
        
        # 进度条
        progress_rect = QRectF(track_rect.x(), track_rect.y(), 
                              ratio * track_rect.width(), track_rect.height())
        
        progress_path = QPainterPath()
        progress_path.addRoundedRect(progress_rect, 2, 2)
        
        progress_gradient = QLinearGradient(progress_rect.topLeft(), progress_rect.bottomLeft())
        progress_gradient.setColorAt(0.0, QColor(100, 150, 255, 200))
        progress_gradient.setColorAt(1.0, QColor(80, 130, 220, 180))
        
        painter.fillPath(progress_path, progress_gradient)
        
        # 绘制滑块手柄
        handle_rect = QRectF(handle_pos - 8, self.height()//2 - 10, 16, 20)
        
        handle_path = QPainterPath()
        handle_path.addRoundedRect(handle_rect, 8, 8)
        
        handle_gradient = QLinearGradient(handle_rect.topLeft(), handle_rect.bottomLeft())
        handle_gradient.setColorAt(0.0, QColor(255, 255, 255, 220))
        handle_gradient.setColorAt(0.4, QColor(220, 230, 255, 200))
        handle_gradient.setColorAt(1.0, QColor(180, 200, 255, 180))
        
        painter.fillPath(handle_path, handle_gradient)
        
        # 手柄高光
        highlight_rect = handle_rect.adjusted(2, 2, -2, handle_rect.height() // 2)
        highlight_path = QPainterPath()
        highlight_path.addRoundedRect(highlight_rect, 6, 6)
        
        highlight_gradient = QLinearGradient(highlight_rect.topLeft(), highlight_rect.bottomLeft())
        highlight_gradient.setColorAt(0.0, QColor(255, 255, 255, 120))
        highlight_gradient.setColorAt(1.0, QColor(255, 255, 255, 40))
        
        painter.fillPath(highlight_path, highlight_gradient)

class SettingItemWidget(QWidget):
    """单个设置项的控件"""
    valueChanged = pyqtSignal(str, object)  # 改为发射键值对
    
    def __init__(self, key, title, description, widget_type="slider", 
                 min_val=0, max_val=100, default_val=50, options=None):
        super().__init__()
        self.key = key  # 设置项的键
        self.title = title
        self.description = description
        self.widget_type = widget_type
        self.default_val = default_val
        
        self.init_ui()
        self.setup_widget(widget_type, min_val, max_val, default_val, options)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 标题
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.title_label.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.title_label)
        
        # 描述
        self.desc_label = QLabel(self.description)
        self.desc_label.setFont(QFont("Microsoft YaHei", 9))
        self.desc_label.setStyleSheet("color: rgba(255, 255, 255, 180);")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # 控件容器
        self.widget_container = QWidget()
        self.widget_container.setStyleSheet("background: transparent;")
        self.widget_layout = QHBoxLayout(self.widget_container)
        self.widget_layout.setContentsMargins(0, 0, 0, 0)
        self.widget_layout.setSpacing(15)
        layout.addWidget(self.widget_container)
        
        self.setLayout(layout)
        
    def setup_widget(self, widget_type, min_val, max_val, default_val, options):
        if widget_type == "slider":
            self.setup_slider(min_val, max_val, default_val)
        elif widget_type == "checkbox":
            self.setup_checkbox(default_val)
        elif widget_type == "combobox":
            self.setup_combobox(options, default_val)
        elif widget_type == "spinbox":
            self.setup_spinbox(min_val, max_val, default_val)
        elif widget_type == "color":
            self.setup_color_button(default_val)
    
    def setup_slider(self, min_val, max_val, default_val):
        # 滑块
        self.slider = GlassSlider(Qt.Horizontal)
        self.slider.setMinimum(min_val)
        self.slider.setMaximum(max_val)
        self.slider.setValue(default_val)
        self.slider.valueChanged.connect(lambda v: self.on_value_changed(v))
        
        # 值显示标签
        self.value_label = QLabel(str(default_val))
        self.value_label.setFixedWidth(45)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.value_label.setStyleSheet("""
            QLabel {
                background-color: rgba(100, 150, 255, 60);
                color: white;
                border-radius: 6px;
                padding: 4px 8px;
                border: 1px solid rgba(255, 255, 255, 80);
            }
        """)
        
        self.widget_layout.addWidget(self.slider, 1)
        self.widget_layout.addWidget(self.value_label)
    
    def setup_checkbox(self, default_val):
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(default_val)
        self.checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
                border: 2px solid rgba(100, 150, 255, 150);
                border-radius: 6px;
                background-color: rgba(255, 255, 255, 30);
            }
            QCheckBox::indicator:checked {
                background-color: rgba(100, 150, 255, 200);
                border: 2px solid rgba(100, 150, 255, 220);
            }
            QCheckBox::indicator:hover {
                border: 2px solid rgba(120, 170, 255, 200);
            }
        """)
        self.checkbox.stateChanged.connect(lambda v: self.on_value_changed(v))
        self.widget_layout.addWidget(self.checkbox)
        self.widget_layout.addStretch()
    
    def setup_combobox(self, options, default_val):
        self.combobox = QComboBox()
        self.combobox.addItems(options)
        self.combobox.setCurrentText(default_val)
        self.combobox.setFont(QFont("Microsoft YaHei", 10))
        self.combobox.setStyleSheet("""
            QComboBox {
                background-color: rgba(255, 255, 255, 100);
                border: 1px solid rgba(100, 150, 255, 120);
                border-radius: 6px;
                padding: 8px 15px;
                color: white;
                min-height: 30px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                border: none;
                background: transparent;
                image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 10l5 5 5-5z"/></svg>');
            }
            QComboBox QAbstractItemView {
                background-color: rgba(40, 40, 60, 220);
                border: 1px solid rgba(100, 150, 255, 150);
                border-radius: 6px;
                color: white;
                selection-background-color: rgba(100, 150, 255, 150);
                outline: none;
            }
        """)
        self.combobox.currentTextChanged.connect(lambda v: self.on_value_changed(v))
        self.widget_layout.addWidget(self.combobox)
    
    def setup_spinbox(self, min_val, max_val, default_val):
        self.spinbox = QSpinBox()
        self.spinbox.setMinimum(min_val)
        self.spinbox.setMaximum(max_val)
        self.spinbox.setValue(default_val)
        self.spinbox.setFont(QFont("Microsoft YaHei", 10))
        self.spinbox.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 255, 255, 100);
                border: 1px solid rgba(100, 150, 255, 120);
                border-radius: 6px;
                padding: 8px;
                color: white;
                min-height: 30px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: rgba(100, 150, 255, 80);
                border: none;
                border-radius: 4px;
                width: 20px;
                margin: 1px;
            }
            QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 8px;
                height: 8px;
                border: none;
                background: transparent;
                image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 14l5-5 5 5z"/></svg>');
            }
            QSpinBox::down-arrow {
                image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white"><path d="M7 10l5 5 5-5z"/></svg>');
            }
        """)
        self.spinbox.valueChanged.connect(lambda v: self.on_value_changed(v))
        self.widget_layout.addWidget(self.spinbox)
    
    def setup_color_button(self, default_color):
        self.color_button = GlassButton("选择颜色")
        self.color_button.setFixedSize(120, 35)
        self.current_color = default_color if isinstance(default_color, QColor) else QColor(100, 150, 255, 180)
        self.update_color_button()
        self.color_button.clicked.connect(self.select_color)
        self.widget_layout.addWidget(self.color_button)
    
    def select_color(self):
        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.on_value_changed(None)
    
    def update_color_button(self):
        # 添加颜色预览到按钮
        self.color_button.setText(f"RGB({self.current_color.red()}, {self.current_color.green()}, {self.current_color.blue()})")
    
    def on_value_changed(self, value):
        # 根据控件类型获取实际值
        if self.widget_type == "slider":
            actual_value = self.slider.value()
            self.value_label.setText(str(actual_value))
        elif self.widget_type == "checkbox":
            actual_value = self.checkbox.isChecked()
        elif self.widget_type == "combobox":
            actual_value = self.combobox.currentText()
        elif self.widget_type == "spinbox":
            actual_value = self.spinbox.value()
        elif self.widget_type == "color":
            actual_value = self.current_color
        
        # 发射信号，包含键和值
        self.valueChanged.emit(self.key, actual_value)
    
    def get_value(self):
        if self.widget_type == "slider":
            return self.slider.value()
        elif self.widget_type == "checkbox":
            return self.checkbox.isChecked()
        elif self.widget_type == "combobox":
            return self.combobox.currentText()
        elif self.widget_type == "spinbox":
            return self.spinbox.value()
        elif self.widget_type == "color":
            return self.current_color
    
    def set_value(self, value):
        if self.widget_type == "slider":
            self.slider.setValue(value)
        elif self.widget_type == "checkbox":
            self.checkbox.setChecked(value)
        elif self.widget_type == "combobox":
            self.combobox.setCurrentText(value)
        elif self.widget_type == "spinbox":
            self.spinbox.setValue(value)
        elif self.widget_type == "color":
            self.current_color = value
            self.update_color_button()

class SettingWidget(QScrollArea):
    """主设置界面"""
    settings_changed = pyqtSignal(dict)  # 当设置变化时发出信号
    apply_now = pyqtSignal()  # 立即应用设置
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_settings = {}
        self.setting_items = {}
        self.is_first_show = True
        
        # 防抖定时器
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.on_debounce_timeout)
        
        # 待应用的设置
        self.pending_settings = {}
        
        self.init_ui()
        self.load_default_settings()
        
        # 连接所有设置项的valueChanged信号
        self.connect_settings_signals()
    
    def init_ui(self):
        # 创建内容部件
        self.content_widget = QWidget()
        
        # 主布局
        main_layout = QVBoxLayout(self.content_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # 标题
        title_label = QLabel("⚙️ 设 置")
        title_label.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        title_label.setStyleSheet("""
            color: white;
            background-color: rgba(100, 150, 255, 60);
            border-radius: 15px;
            padding: 20px;
            border: 2px solid rgba(255, 255, 255, 80);
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建设置组
        self.create_acrylic_group(main_layout)
        self.create_video_group(main_layout)
        self.create_appearance_group(main_layout)
        self.create_about_group(main_layout)
        
        # 按钮区域
        self.create_button_area(main_layout)
        
        # 设置滚动区域
        self.setWidget(self.content_widget)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 设置样式
        self.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 30);
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 150, 255, 120);
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(100, 150, 255, 180);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QWidget {
                background: transparent;
            }
        """)
    
    def create_acrylic_group(self, parent_layout):
        """创建亚克力效果设置组"""
        group = QGroupBox("🎨 亚克力效果")
        group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid rgba(100, 150, 255, 100);
                border-radius: 15px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 15);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 15px 0 15px;
                background-color: rgba(100, 150, 255, 80);
                border-radius: 8px;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 模糊半径
        self.setting_items["blur_radius"] = SettingItemWidget(
            "blur_radius", "模糊半径",
            "控制亚克力背景的模糊程度 (值越大越模糊)",
            "slider", 5, 50, 25
        )
        layout.addWidget(self.setting_items["blur_radius"])
        
        # 亮度
        self.setting_items["brightness"] = SettingItemWidget(
            "brightness", "亮度",
            "调整亚克力效果的亮度 (值越大越亮)",
            "slider", 50, 150, 105
        )
        layout.addWidget(self.setting_items["brightness"])
        
        # 色调强度
        self.setting_items["tint_strength"] = SettingItemWidget(
            "tint_strength", "色调强度",
            "控制亚克力色调的强度 (0为无色调)",
            "slider", 0, 100, 15
        )
        layout.addWidget(self.setting_items["tint_strength"])
        
        # 色调颜色
        self.setting_items["tint_color"] = SettingItemWidget(
            "tint_color", "色调颜色",
            "选择亚克力效果的主色调",
            "color", default_val=QColor(245, 245, 255, 180)
        )
        layout.addWidget(self.setting_items["tint_color"])
        
        # 噪点强度
        self.setting_items["noise_strength"] = SettingItemWidget(
            "noise_strength", "噪点强度",
            "控制亚克力纹理的噪点程度 (模拟材质感)",
            "slider", 0, 100, 8
        )
        layout.addWidget(self.setting_items["noise_strength"])
        
        # 圆角开关
        self.setting_items["rounded_corners"] = SettingItemWidget(
            "rounded_corners", "启用圆角",
            "启用或禁用窗口圆角效果",
            "checkbox", default_val=True
        )
        layout.addWidget(self.setting_items["rounded_corners"])
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_video_group(self, parent_layout):
        """创建视频播放设置组"""
        group = QGroupBox("🎬 视频播放")
        group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid rgba(46, 204, 113, 80);
                border-radius: 15px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 15);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 15px 0 15px;
                background-color: rgba(46, 204, 113, 80);
                border-radius: 8px;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 默认播放质量
        self.setting_items["default_quality"] = SettingItemWidget(
            "default_quality", "默认播放质量",
            "选择视频播放的默认清晰度",
            "combobox", 
            options=["360P", "480P", "720P", "1080P", "自动"],
            default_val="自动"
        )
        layout.addWidget(self.setting_items["default_quality"])
        
        # 默认音量
        self.setting_items["default_volume"] = SettingItemWidget(
            "default_volume", "默认音量",
            "设置视频播放的默认音量",
            "slider", 0, 100, 80
        )
        layout.addWidget(self.setting_items["default_volume"])
        
        # 硬件加速
        self.setting_items["hardware_acceleration"] = SettingItemWidget(
            "hardware_acceleration", "启用硬件加速",
            "使用GPU加速视频解码和界面渲染",
            "checkbox", default_val=True
        )
        layout.addWidget(self.setting_items["hardware_acceleration"])
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_appearance_group(self, parent_layout):
        """创建外观设置组"""
        group = QGroupBox("✨ 外观设置")
        group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid rgba(155, 89, 182, 80);
                border-radius: 15px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 15);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 15px 0 15px;
                background-color: rgba(155, 89, 182, 80);
                border-radius: 8px;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 主题选择
        self.setting_items["theme"] = SettingItemWidget(
            "theme", "主题",
            "选择应用程序的整体配色主题",
            "combobox",
            options=["深色主题", "浅色主题", "自动跟随系统"],
            default_val="深色主题"
        )
        layout.addWidget(self.setting_items["theme"])
        
        # 字体大小
        self.setting_items["font_size"] = SettingItemWidget(
            "font_size", "字体大小",
            "调整应用程序的字体大小",
            "slider", 10, 18, 12
        )
        layout.addWidget(self.setting_items["font_size"])
        
        # 动画效果
        self.setting_items["enable_animations"] = SettingItemWidget(
            "enable_animations", "启用动画效果",
            "启用界面切换和交互的动画效果",
            "checkbox", default_val=True
        )
        layout.addWidget(self.setting_items["enable_animations"])
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_about_group(self, parent_layout):
        """创建关于信息组"""
        group = QGroupBox("ℹ️ 关于")
        group.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        group.setStyleSheet("""
            QGroupBox {
                color: white;
                border: 2px solid rgba(52, 152, 219, 80);
                border-radius: 15px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: rgba(255, 255, 255, 15);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 15px 0 15px;
                background-color: rgba(52, 152, 219, 80);
                border-radius: 8px;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # 应用信息
        info_text = """
        <div style="color: white; font-size: 11px; line-height: 1.6;">
        <p><b>液态玻璃Bilibili客户端</b></p>
        <p>版本: 0.0.1</p>
        <p>开发者: ywhdzrb</p>
        <p>描述: 基于PyQt5开发的Bilibili客户端，具有亚克力玻璃效果界面</p>
        <p>功能特性:</p>
        <ul>
            <li>• 亚克力玻璃视觉效果</li>
            <li>• 流畅的视频播放体验</li>
            <li>• 推荐视频流式加载</li>
            <li>• 高清视频播放支持</li>
            <li>• 用户登录功能</li>
        </ul>
        <p>技术支持: intmainreturn@outlook.com</p>
        </div>
        """
        
        info_label = QLabel(info_text)
        info_label.setFont(QFont("Microsoft YaHei", 9))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: rgba(255, 255, 255, 180); background: transparent;")
        layout.addWidget(info_label)
        
        # 缓存信息
        cache_info = QLabel()
        cache_info.setFont(QFont("Microsoft YaHei", 9))
        cache_info.setStyleSheet("color: rgba(255, 255, 255, 180); background: transparent;")
        
        # 计算缓存大小
        cache_size = self.calculate_cache_size()
        cache_text = f"<p><b>缓存信息:</b></p>"
        cache_text += f"<p>缓存目录: ./temp</p>"
        cache_text += f"<p>缓存大小: {cache_size}</p>"
        
        cache_info.setText(cache_text)
        layout.addWidget(cache_info)
        
        # 清理缓存按钮
        self.clear_cache_btn = GlassButton("清理缓存")
        self.clear_cache_btn.setFixedHeight(35)
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        layout.addWidget(self.clear_cache_btn)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_button_area(self, parent_layout):
        """创建按钮区域"""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 10, 0, 0)
        button_layout.setSpacing(20)
        
        # 恢复默认按钮
        self.reset_button = GlassButton("恢复默认")
        self.reset_button.clicked.connect(self.reset_to_defaults)
        
        # 应用按钮
        self.apply_button = GlassButton("应用设置")
        self.apply_button.clicked.connect(self.apply_settings)
        
        # 保存按钮
        self.save_button = GlassButton("保存并关闭")
        self.save_button.clicked.connect(self.save_and_close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch()
        
        parent_layout.addWidget(button_widget)
    
    def load_default_settings(self):
        """加载默认设置值"""
        self.default_settings = {
            "blur_radius": 25,
            "brightness": 105,  # 1.05 * 100
            "tint_strength": 15,
            "tint_color": QColor(245, 245, 255, 180),
            "noise_strength": 8,
            "rounded_corners": True,
            "default_quality": "自动",
            "default_volume": 80,
            "hardware_acceleration": True,
            "theme": "深色主题",
            "font_size": 12,
            "enable_animations": True
        }
        
        # 从配置文件加载已保存的设置（如果有）
        self.load_settings_from_file()
    
    def connect_settings_signals(self):
        """连接所有设置项的valueChanged信号"""
        for key, item in self.setting_items.items():
            item.valueChanged.connect(self.on_setting_changed)
    
    def on_setting_changed(self, key, value):
        """单个设置项改变时的处理"""
        # 保存到待处理设置中
        self.pending_settings[key] = value
        
        # 重启防抖定时器（延迟300ms，避免频繁更新）
        self.debounce_timer.start(300)
    
    def on_debounce_timeout(self):
        """防抖定时器超时，应用累积的设置"""
        if not self.pending_settings:
            return
            
        # 获取当前所有设置（合并已保存的和待处理的）
        settings = self.get_current_settings()
        
        # 只发送亚克力相关的设置用于实时预览
        acrylic_keys = ["blur_radius", "brightness", "tint_strength", 
                       "tint_color", "noise_strength", "rounded_corners"]
        
        acrylic_settings = {}
        for key in acrylic_keys:
            if key in settings:
                acrylic_settings[key] = settings[key]
        
        if acrylic_settings:
            # 发出预览信号（只包含亚克力相关设置）
            self.settings_changed.emit(acrylic_settings)
        
        # 清空待处理设置
        self.pending_settings.clear()
    
    def calculate_cache_size(self):
        """计算缓存大小"""
        cache_dir = "./temp"
        total_size = 0
        
        if os.path.exists(cache_dir):
            for file in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, file)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
        
        # 转换为合适的单位
        if total_size < 1024:
            return f"{total_size} B"
        elif total_size < 1024 * 1024:
            return f"{total_size / 1024:.2f} KB"
        elif total_size < 1024 * 1024 * 1024:
            return f"{total_size / (1024 * 1024):.2f} MB"
        else:
            return f"{total_size / (1024 * 1024 * 1024):.2f} GB"
    
    def clear_cache(self):
        """清理缓存"""
        reply = QMessageBox.question(
            self, "清理缓存",
            "确定要清理所有缓存文件吗？\n这可能会删除下载的视频封面和临时文件。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            cache_dir = "./temp"
            try:
                if os.path.exists(cache_dir):
                    for file in os.listdir(cache_dir):
                        file_path = os.path.join(cache_dir, file)
                        try:
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                        except Exception as e:
                            print(f"删除文件 {file_path} 失败: {e}")
                
                # 更新缓存信息
                QMessageBox.information(self, "清理完成", "缓存已清理成功！")
                
                # 刷新缓存显示
                if hasattr(self.parent(), 'update_function'):
                    self.parent().update_function(1)  # 重新加载设置界面
            except Exception as e:
                QMessageBox.warning(self, "清理失败", f"清理缓存时出错:\n{str(e)}")
    
    def load_settings_from_file(self):
        """从配置文件加载设置"""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)
                    
                # 应用保存的设置
                for key, value in saved_settings.items():
                    if key in self.setting_items:
                        # 处理颜色值
                        if key == "tint_color" and isinstance(value, list):
                            color = QColor(*value)
                            self.setting_items[key].set_value(color)
                        elif key == "brightness":
                            # 亮度值转换
                            self.setting_items[key].set_value(int(value))
                        else:
                            self.setting_items[key].set_value(value)
                            
                print("设置已从文件加载")
        except Exception as e:
            print(f"加载设置文件失败: {e}")
    
    def get_current_settings(self):
        """获取当前所有设置"""
        settings = {}
        for key, item in self.setting_items.items():
            settings[key] = item.get_value()
        return settings
    
    def apply_settings(self):
        """应用当前设置"""
        # 立即应用所有设置（不经过防抖）
        self.current_settings = self.get_current_settings()
        self.settings_changed.emit(self.current_settings)
        
        # 保存到文件
        self.save_settings_to_file()
        
        # 显示成功提示
        self.show_success_message("设置已应用")
    
    def show_success_message(self, message):
        """显示成功消息"""
        print(message)
    
    def reset_to_defaults(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self, "确认恢复默认设置",
            "确定要恢复所有设置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for key, item in self.setting_items.items():
                if key in self.default_settings:
                    item.set_value(self.default_settings[key])
            
            # 立即应用默认设置
            QTimer.singleShot(100, self.apply_settings)
    
    def save_and_close(self):
        """保存设置并关闭"""
        # 保存设置
        self.apply_settings()
        
        # 延迟发出关闭信号
        QTimer.singleShot(100, self.apply_now.emit)
    
    def save_settings_to_file(self):
        """保存设置到文件"""
        try:
            settings = self.get_current_settings()
            
            # 转换QColor为可序列化的列表
            for key, value in settings.items():
                if isinstance(value, QColor):
                    settings[key] = [value.red(), value.green(), value.blue(), value.alpha()]
            
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
            print("设置已保存到文件")
        except Exception as e:
            print(f"保存设置文件失败: {e}")
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        
        if self.is_first_show:
            self.is_first_show = False
            # 刷新缓存显示
            self.update()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置深色背景
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e2e;
            font-family: 'Microsoft YaHei';
            font-size: 12px;
        }
    """)
    
    window = SettingWidget()
    window.setGeometry(100, 100, 800, 600)
    window.show()
    
    sys.exit(app.exec_())