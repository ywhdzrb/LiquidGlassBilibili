from PyQt5.QtWidgets import QApplication, QMainWindow, QFrame, QVBoxLayout, QWidget
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QImage, QColor
from PyQt5.QtCore import Qt
from AcrylicEffect import AcrylicEffect
import sys

class MainWindow(QMainWindow):
    def __init__(self, parent = None, flags = Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('液态玻璃bilibili')
        self.setGeometry(100, 100, 1200, 700)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)
        
        # 应用亚克力效果
        self.acrylic_effect = AcrylicEffect(self.content_frame)
        
        main_layout.addWidget(self.content_frame)

        self.acrylic_effect.set_background_image("background.jpg")  # 设置背景图片

        # 设置窗口最大化
        self.showMaximized()

        # 无边框
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.acrylic_effect.set_blur_radius(10)
        self.acrylic_effect.set_brightness(0.3)
        self.acrylic_effect.set_tint_strength(0.2)
        self.acrylic_effect.set_noise_strength(0.15)
        self.acrylic_effect.set_tint_color(QColor(200, 220, 255))

    def resizeEvent(self, event):
        """窗口大小改变时更新效果"""
        super().resizeEvent(event)
        self.acrylic_effect.apply_effect()

        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())