from PyQt5.QtWidgets import QMainWindow, QApplication, QVBoxLayout, QWidget, QFrame, QLabel, QPushButton, QSlider, QTextEdit, QAction, QFileDialog, QColorDialog, QHBoxLayout, QFormLayout
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt, QSize
from AcrylicEffect import AcrylicEffect
import sys

class AcrylicDemo(QMainWindow):
    """亚克力效果演示窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("亚克力效果 - 带背景图片")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(600, 400)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建应用亚克力效果的容器
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)
        
        # 应用亚克力效果
        self.acrylic_effect = AcrylicEffect(self.content_frame)
        
        # 添加内容
        self.create_content(content_layout)
        
        main_layout.addWidget(self.content_frame)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 应用样式
        self.apply_styles()
        
        # 更新状态
        self.update_status()
    
    def create_content(self, layout):
        """创建内容区域"""
        # 标题
        title = QLabel("亚克力效果演示")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("title")
        layout.addWidget(title)
        
        # 参数控制
        self.create_controls(layout)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setObjectName("separator")
        layout.addWidget(separator)
        
        # 添加示例内容
        layout.addSpacing(20)
        layout.addWidget(QLabel("示例内容区域"))
        
        # 文本编辑框
        text_edit = QTextEdit()
        text_edit.setPlaceholderText("在此输入文本...")
        text_edit.setFixedHeight(100)
        layout.addWidget(text_edit)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 状态标签
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
    
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = self.addToolBar("工具")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        
        # 背景选择动作
        bg_action = QAction(QIcon(":bg_icon.png"), "选择背景", self)
        bg_action.triggered.connect(self.choose_background)
        toolbar.addAction(bg_action)
        
        # 效果重置动作
        reset_action = QAction(QIcon(":reset_icon.png"), "重置效果", self)
        reset_action.triggered.connect(self.reset_effect)
        toolbar.addAction(reset_action)
        
        # 添加分隔线
        toolbar.addSeparator()
        
        # 退出动作
        exit_action = QAction(QIcon(":exit_icon.png"), "退出", self)
        exit_action.triggered.connect(self.close)
        toolbar.addAction(exit_action)
    
    def create_controls(self, layout):
        """创建效果控制面板"""
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        
        # 模糊半径控制
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(5, 50)
        self.blur_slider.setValue(20)
        self.blur_slider.valueChanged.connect(self.on_blur_changed)
        form_layout.addRow("模糊半径:", self.blur_slider)
        
        # 亮度控制
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(70)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        form_layout.addRow("亮度混合:", self.brightness_slider)
        
        # 色调控制
        self.tint_slider = QSlider(Qt.Horizontal)
        self.tint_slider.setRange(0, 100)
        self.tint_slider.setValue(30)
        self.tint_slider.valueChanged.connect(self.on_tint_changed)
        form_layout.addRow("色调混合:", self.tint_slider)
        
        # 噪点强度控制
        self.noise_slider = QSlider(Qt.Horizontal)
        self.noise_slider.setRange(0, 100)
        self.noise_slider.setValue(15)
        self.noise_slider.valueChanged.connect(self.on_noise_changed)
        form_layout.addRow("噪点强度:", self.noise_slider)
        
        # 色调选择器
        self.color_btn = QPushButton("选择色调")
        self.color_btn.clicked.connect(self.choose_tint_color)
        form_layout.addRow("色调颜色:", self.color_btn)
        
        layout.addLayout(form_layout)
    
    def choose_background(self):
        """选择背景图片"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", "", "图片文件 (*.png *.jpg *.bmp)")
        if file_name:
            self.acrylic_effect.set_background_image(file_name)
            self.update_status()
    
    def choose_tint_color(self):
        """选择色调颜色"""
        color = QColorDialog.getColor(self.acrylic_effect.tint_color, self, "选择色调颜色")
        if color.isValid():
            self.acrylic_effect.set_tint_color(color)
            self.update_status()
    
    def reset_effect(self):
        """重置效果参数"""
        self.acrylic_effect.set_blur_radius(20)
        self.acrylic_effect.set_brightness(0.7)
        self.acrylic_effect.set_tint_strength(0.3)
        self.acrylic_effect.set_noise_strength(0.15)
        self.acrylic_effect.set_tint_color(QColor(200, 220, 255))
        
        # 更新UI
        self.blur_slider.setValue(20)
        self.brightness_slider.setValue(70)
        self.tint_slider.setValue(30)
        self.noise_slider.setValue(15)
        
        self.update_status()
    
    def on_blur_changed(self):
        self.acrylic_effect.set_blur_radius(self.blur_slider.value())
        self.update_status()
    
    def on_brightness_changed(self):
        self.acrylic_effect.set_brightness(self.brightness_slider.value() / 100.0)
        self.update_status()
    
    def on_tint_changed(self):
        self.acrylic_effect.set_tint_strength(self.tint_slider.value() / 100.0)
        self.update_status()
    
    def on_noise_changed(self):
        self.acrylic_effect.set_noise_strength(self.noise_slider.value() / 100.0)
        self.update_status()
    
    def update_status(self):
        """更新状态标签"""
        status_text = (
            f"效果参数: 模糊半径={self.acrylic_effect.blur_radius}px, "
            f"亮度={int(self.acrylic_effect.brightness*100)}%, "
            f"色调={int(self.acrylic_effect.tint_strength*100)}%, "
            f"噪点={int(self.acrylic_effect.noise_strength*100)}%"
        )
        self.status_label.setText(status_text)
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2D2D30;
            }
            
            QFrame#contentFrame {
                border-radius: 12px;
            }
            
            QLabel#title {
                font-size: 28px;
                font-weight: bold;
                color: #FFFFFF;
                padding: 15px;
            }
            
            QFormLayout QLabel {
                color: #E0E0E0;
                font-size: 14px;
            }
            
            QSlider::groove:horizontal {
                height: 8px;
                background: #3F3F46;
                border-radius: 4px;
            }
            
            QSlider::handle:horizontal {
                background: #007ACC;
                width: 18px;
                height: 18px;
                border-radius: 9px;
                margin: -5px 0;
            }
            
            QSlider::sub-page:horizontal {
                background: #007ACC;
                border-radius: 4px;
            }
            
            QPushButton {
                background-color: #007ACC;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 14px;
            }
            
            QPushButton:hover {
                background-color: #1C97EA;
            }
            
            QPushButton:pressed {
                background-color: #005A9E;
            }
            
            QLabel#status {
                font-size: 12px;
                color: #A0A0A0;
                margin-top: 20px;
            }
            
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid #3F3F46;
                border-radius: 6px;
                padding: 8px;
            }
            
            #separator {
                background-color: #3F3F46;
                margin: 20px 0;
            }
            
            QToolBar {
                background-color: #252526;
                border: none;
                padding: 5px;
            }
            
            QToolButton {
                background-color: transparent;
                color: #CCCCCC;
                padding: 5px 10px;
                border-radius: 4px;
            }
            
            QToolButton:hover {
                background-color: #2A2D2E;
            }
        """)
    
    def resizeEvent(self, event):
        """窗口大小改变时更新效果"""
        super().resizeEvent(event)
        self.acrylic_effect.apply_effect()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = AcrylicDemo()
    window.show()
    
    sys.exit(app.exec_())