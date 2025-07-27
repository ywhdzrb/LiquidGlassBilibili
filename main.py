from PyQt5.QtWidgets import (QApplication, 
                             QMainWindow, 
                             QFrame, 
                             QVBoxLayout, 
                             QWidget, 
                             QPushButton,
                             QLabel,
                             QLineEdit)
from PyQt5.QtGui import (QIcon, 
                         QPixmap, 
                         QColor, 
                         QFontDatabase,
                         QFont)
from PyQt5.QtCore import (Qt, 
                          QRect, 
                          QSize,
                          QPropertyAnimation,
                          QEasingCurve)
from AcrylicEffect import AcrylicEffect
from LiquidGlassWidget import LiquidGlassWidget
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

        # 设置窗口图标
        self.setWindowIcon(QIcon("BilibiliIcon.ico"))
        
        # 顶部窗口栏
        self.windowbar = QWidget()
        self.windowbar.setObjectName("windowBar")
        self.windowbar.setFixedHeight(40)
        self.windowbar.setStyleSheet("background-color: rgba(200, 220, 255, 150);")
        self.windowbar.setGeometry(QRect(0, 0, 1365, 40))
        self.windowbar.setParent(self)

        # 添加logo
        self.logo = QLabel()
        logo_icon = QPixmap("./img/logo.png")
        logo_icon = logo_icon.scaled(70, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.logo.setPixmap(logo_icon)
        self.logo.setGeometry(QRect(10, 0, 70, 40))
        self.logo.setParent(self.windowbar)
        self.logo.setStyleSheet("background-color: transparent;")
        

        # 关闭按钮
        self.closebtn = QPushButton()
        self.closebtn.setObjectName("closeBtn")
        self.closebtn.setFixedSize(40, 40)
        
        # 加载并缩放图标
        close_icon = QPixmap("./img/x3.png")
        close_icon = close_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.closebtn.setIcon(QIcon(close_icon))
        self.closebtn.setIconSize(QSize(20, 20))
        self.closebtn.setParent(self.windowbar)
        self.closebtn.setGeometry(QRect(1325, 0, 40, 40))
        self.closebtn.setStyleSheet("background-color: transparent; border: none;")
        self.closebtn.clicked.connect(self.close)

        # 当鼠标悬停时改变为红色
        self.closebtn.setStyleSheet("""
            QPushButton#closeBtn {
                background-color: transparent;
                border: none;
            }
            QPushButton#closeBtn:hover {
                background-color: rgba(255, 0, 0, 150);
            }
        """)

        # 最小化按钮
        self.minbtn = QPushButton()
        self.minbtn.setObjectName("minBtn")
        self.minbtn.setFixedSize(40, 40)

        # 加载并缩放图标
        min_icon = QPixmap("./img/min.png")
        min_icon = min_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.minbtn.setIcon(QIcon(min_icon))
        self.minbtn.setIconSize(QSize(20, 20))
        self.minbtn.setParent(self.windowbar)
        self.minbtn.setGeometry(QRect(1285, 0, 40, 40))
        self.minbtn.setStyleSheet("background-color: transparent; border: none;")
        self.minbtn.clicked.connect(self.showMinimized)

        # 当鼠标悬停时改变为蓝色
        self.minbtn.setStyleSheet("""
            QPushButton#minBtn {
                background-color: transparent;
                border: none;
            }
            QPushButton#minBtn:hover {
                background-color: rgba(10, 110, 230, 150);
            }
        """)

        # 搜索框
        self.searchbar = QLineEdit()
        self.searchbar.setObjectName("searchBar")
        self.searchbar.setStyleSheet("background-color: rgba(200, 220, 255, 150);")
        self.searchbar.setGeometry(QRect(500, 5, 300, 30))
        self.searchbar.setParent(self.windowbar)
        self.searchbar.setStyleSheet("border-radius: 5px;")

        # 设置搜索框的提示文本
        self.searchbar.setPlaceholderText("震惊！有人开发bilibili26!")

        # 图标
        self.search_icon = QPixmap("./img/search.png")
        self.search_icon = self.search_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.search_icon_label = QLabel()
        self.search_icon_label.setPixmap(self.search_icon)
        self.search_icon_label.setGeometry(QRect(770, 10, 20, 20))
        self.search_icon_label.setParent(self.windowbar)
        self.search_icon_label.setStyleSheet("background-color: transparent;")

        # 侧栏
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setStyleSheet("background-color: rgba(200, 220, 255, 150);")
        self.sidebar.setGeometry(QRect(0, 40, 50, 700))
        self.sidebar.setParent(self)

        # 选着功能区
        self.functionnum = 1

        # 首页
        self.home = QPushButton()
        self.home.setObjectName("homeBtn")
        self.home.setFixedSize(50, 40)

        # 加载并缩放图标
        home_icon = QPixmap("./img/home.png")
        home_icon = home_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.home.setIcon(QIcon(home_icon))
        self.home.setIconSize(QSize(20, 20))
        self.home.setParent(self.sidebar)
        self.home.setGeometry(QRect(0, 0, 50, 40))
        self.home.setStyleSheet("background-color: transparent; border: none;")
        self.home.clicked.connect(lambda : self.update_function(0))

        # 首页文本
        self.home_text = QLabel("首页")
        self.home_text.setObjectName("homeText")
        self.home_text.setStyleSheet("color: black; font-size: 12px; background-color: transparent;")
        self.home_text.setParent(self.sidebar)
        self.home_text.setGeometry(QRect(14, 30, 30, 20))

        # 设置
        self.setting = QPushButton()
        self.setting.setObjectName("settingBtn")
        self.setting.setFixedSize(50, 40)

        # 加载并缩放图标
        setting_icon = QPixmap("./img/setting.png")
        setting_icon = setting_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setting.setIcon(QIcon(setting_icon))
        self.setting.setIconSize(QSize(20, 20))
        self.setting.setParent(self.sidebar)
        self.setting.setGeometry(QRect(0, 650, 50, 40))
        self.setting.setStyleSheet("background-color: transparent; border: none;")
        self.setting.clicked.connect(lambda : self.update_function(1))

        # 设置文本
        self.setting_text = QLabel("设置")
        self.setting_text.setObjectName("settingText")
        self.setting_text.setStyleSheet("color: black; font-size: 12px; background-color: transparent;")
        self.setting_text.setParent(self.sidebar)
        self.setting_text.setGeometry(QRect(14, 680, 30, 20))

        # 液态玻璃蒙版
        self.liquid_glass = LiquidGlassWidget(self)
        self.liquid_glass.setGeometry(QRect(0, 40, 50, 60))
        self.liquid_glass.setParent(self)

        # 添加动画
        self.liquid_animation = QPropertyAnimation(self.liquid_glass, b"geometry")
        self.liquid_animation.setDuration(1000)  # 动画持续时间500ms
        self.liquid_animation.setEasingCurve(QEasingCurve.OutCubic)  # 平滑缓动效果
        
        
        # 更新
        self.update_function()
        







    def update_function(self, num=0):
        self.functionnum = num
        # 液态玻璃+换图标
        if self.functionnum == 0:
            self.home_function()
            setting_icon = QPixmap("./img/setting.png")
            setting_icon = setting_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setting.setIcon(QIcon(setting_icon))
            self.setting_text.setStyleSheet("color: black; font-size: 12px; background-color: transparent;")

        elif self.functionnum == 1:
            self.setting_function()
            home_icon = QPixmap("./img/home.png")
            home_icon = home_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.home.setIcon(QIcon(home_icon))
            self.home_text.setStyleSheet("color: black; font-size: 12px; background-color: transparent;")

             
    def home_function(self):
        """首页功能"""
        home_icon = QPixmap("./img/home_start.png")
        home_icon = home_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.home.setIcon(QIcon(home_icon))

        self.home_text.setStyleSheet("color: rgb(255,192,203); font-size: 12px; background-color: transparent;")

        self.liquid_animation.stop()
        self.liquid_animation.setStartValue(self.liquid_glass.geometry())
        self.liquid_animation.setEndValue(QRect(0, 40, 50, 60))
        self.liquid_animation.start()

    def setting_function(self):
        """设置功能"""
        setting_icon = QPixmap("./img/setting_start.png")
        setting_icon = setting_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setting.setIcon(QIcon(setting_icon))

        self.setting_text.setStyleSheet("color: rgb(255,192,203); font-size: 12px; background-color: transparent;")

        self.liquid_animation.stop()
        self.liquid_animation.setStartValue(self.liquid_glass.geometry())
        self.liquid_animation.setEndValue(QRect(0, 690, 50, 60))
        self.liquid_animation.start()

    def resizeEvent(self, event):
        """窗口大小改变时更新效果"""
        super().resizeEvent(event)
        self.acrylic_effect.apply_effect()

        

if __name__ == '__main__':
    app = QApplication(sys.argv)

    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())