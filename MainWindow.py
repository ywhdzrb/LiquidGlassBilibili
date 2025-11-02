import os
import sys

from PyQt5.QtCore import (Qt,
                          QRect,
                          QSize,
                          QPropertyAnimation,
                          QEasingCurve,
                          QTimer)
from PyQt5.QtGui import (QIcon,
                         QPixmap,
                         QColor,
                         QMouseEvent)
from PyQt5.QtWidgets import (QApplication,
                             QMainWindow,
                             QFrame,
                             QVBoxLayout,
                             QWidget,
                             QPushButton,
                             QLabel,
                             QLineEdit)

from AcrylicEffect import AcrylicEffect
from LiquidGlassWidget import LiquidGlassWidget
from VideoController import VideoController
from GetBilibiliApi import *
from CircularLabel import CircularLabel


class MainWindow(QMainWindow):
    def __init__(self, parent = None, flags = Qt.WindowFlags()):
        super().__init__(parent, flags)

        # 判断temp目录是否存在
        if os.path.exists("temp"):
            for file in os.listdir("temp"):
                os.remove(os.path.join("temp", file))
            
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # 判断cookie文件是否存在
        if not os.path.exists("Cookie"):
            with open("Cookie", "w") as f:
                f.write("")

        # 添加拖动相关变量
        self.dragging = False
        self.drag_position = None
        
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('液态玻璃bilibili')
        self.setFixedSize(1200, 700)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 应用亚克力效果到整个窗口 - 修改位置
        self.acrylic_effect = AcrylicEffect(central_widget)
        
        # 设置内容框架为透明，让亚克力效果透出来
        self.content_frame = QFrame()
        self.content_frame.setObjectName("contentFrame")
        self.content_frame.setStyleSheet("""
            QFrame#contentFrame {
                background-color: transparent;
                border: none;
            }
        """)
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(40, 40, 40, 40)
        
        main_layout.addWidget(self.content_frame)

        # 设置窗口图标
        self.setWindowIcon(QIcon("BilibiliIcon.ico"))

        # 初始化UI组件
        self.init_window_bar()
        self.init_sidebar()
        self.init_video_controller()
        self.init_refresh_button()

        # 无边框
        self.setWindowFlags(Qt.FramelessWindowHint)

        # 优化亚克力效果参数 - 实现更真实的亚克力材质
        self.acrylic_effect.set_blur_radius(25)  # 增加模糊半径
        self.acrylic_effect.set_brightness(0.8)  # 增加亮度
        self.acrylic_effect.set_tint_strength(0.15)  # 调整色调强度
        self.acrylic_effect.set_noise_strength(0.08)  # 增加噪点强度
        self.acrylic_effect.set_tint_color(QColor(245, 245, 255, 180))  # 使用更浅的半透明颜色
        
        # 设置窗口背景为半透明，让亚克力效果更明显
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 更新功能界面
        self.update_function()

    def init_window_bar(self):
        """初始化顶部窗口栏"""
        # 顶部窗口栏 - 使用半透明背景
        self.windowbar = QWidget()
        self.windowbar.setObjectName("windowBar")
        self.windowbar.setFixedHeight(40)
        self.windowbar.setStyleSheet("""
            #windowBar {
                background-color: rgba(255, 255, 255, 80);
                border-bottom: 1px solid rgba(255, 255, 255, 60);
            }
        """)
        self.windowbar.setGeometry(QRect(0, 0, self.width(), 40))
        self.windowbar.setParent(self)
        
        # 启用鼠标跟踪
        self.windowbar.setMouseTracking(True)

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
        self.closebtn.setStyleSheet("""
            QPushButton#closeBtn {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton#closeBtn:hover {
                background-color: rgba(255, 0, 0, 180);
            }
        """)
        self.closebtn.clicked.connect(self.close)

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
        self.minbtn.setStyleSheet("""
            QPushButton#minBtn {
                background-color: transparent;
                border: none;
                border-radius: 2px;
            }
            QPushButton#minBtn:hover {
                background-color: rgba(100, 100, 100, 100);
            }
        """)
        self.minbtn.clicked.connect(self.showMinimized)

        # 搜索框 - 使用亚克力风格
        self.searchbar = QLineEdit()
        self.searchbar.setObjectName("searchBar")
        self.searchbar.setStyleSheet("""
            QLineEdit#searchBar {
                background-color: rgba(255, 255, 255, 150);
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 15px;
                padding: 5px 15px;
                font-size: 14px;
                color: #333;
            }
            QLineEdit#searchBar:focus {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid rgba(100, 150, 255, 150);
            }
        """)
        self.searchbar.setGeometry(QRect(500, 5, 300, 30))
        self.searchbar.setParent(self.windowbar)
        self.searchbar.setPlaceholderText("震惊！有人开发bilibili26!")

        # 搜索图标
        self.search_icon = QPixmap("./img/search.png")
        self.search_icon = self.search_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.search_icon_label = QLabel()
        self.search_icon_label.setPixmap(self.search_icon)
        self.search_icon_label.setGeometry(QRect(770, 10, 20, 20))
        self.search_icon_label.setParent(self.windowbar)
        self.search_icon_label.setStyleSheet("background-color: transparent;")

    def init_sidebar(self):
        """初始化侧边栏"""
        # 侧栏 - 使用半透明背景
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setStyleSheet("""
            #sidebar {
                background-color: rgba(255, 255, 255, 80);
                border-right: 1px solid rgba(255, 255, 255, 60);
            }
        """)
        self.sidebar.setGeometry(QRect(0, 40, 50, self.height() - 40))
        self.sidebar.setParent(self)

        # 首页按钮
        self.home = QPushButton()
        self.home.setObjectName("homeBtn")
        self.home.setFixedSize(50, 40)

        home_icon = QPixmap("./img/home.png")
        home_icon = home_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.home.setIcon(QIcon(home_icon))
        self.home.setIconSize(QSize(20, 20))
        self.home.setParent(self.sidebar)
        self.home.setGeometry(QRect(0, 0, 50, 40))
        self.home.setStyleSheet("""
            QPushButton#homeBtn {
                background-color: transparent;
                border: none;
            }
        """)
        self.home.clicked.connect(lambda: self.update_function(0))

        # 首页文本
        self.home_text = QLabel("首页")
        self.home_text.setObjectName("homeText")
        self.home_text.setStyleSheet("color: #333; font-size: 12px; background-color: transparent;")
        self.home_text.setParent(self.sidebar)
        self.home_text.setGeometry(QRect(14, 30, 30, 20))

        # 设置按钮
        self.setting = QPushButton()
        self.setting.setObjectName("settingBtn")
        self.setting.setFixedSize(50, 40)

        setting_icon = QPixmap("./img/setting.png")
        setting_icon = setting_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setting.setIcon(QIcon(setting_icon))
        self.setting.setIconSize(QSize(20, 20))
        self.setting.setParent(self.sidebar)
        self.setting.setGeometry(QRect(0, 650, 50, 40))
        self.setting.setStyleSheet("""
            QPushButton#settingBtn {
                background-color: transparent;
                border: none;
            }
        """)
        self.setting.clicked.connect(lambda: self.update_function(1))

        # 设置文本
        self.setting_text = QLabel("设置")
        self.setting_text.setObjectName("settingText")
        self.setting_text.setStyleSheet("color: #333; font-size: 12px; background-color: transparent;")
        self.setting_text.setParent(self.sidebar)
        self.setting_text.setGeometry(QRect(14, 670, 30, 20))

        # 头像
        self.headshot = CircularLabel()
        self.headshot.setGeometry(QRect(10, 550, 30, 30))  # 调整位置使其居中
        self.headshot.setParent(self.sidebar)

        # 加载头像
        if GetUserInfo().get_user_info() == None:
            # 使用默认头像
            default_pixmap = QPixmap("./img/none.png")
            self.headshot.setPixmap(default_pixmap)
            from BilibiliLogin import BiliBiliLogin
            self.login_window = BiliBiliLogin()
            self.login_window.show()
        else:
            # 下载并设置用户头像
            Download().download_user_face("./temp/face.jpg")
            user_pixmap = QPixmap("./temp/face.jpg")
            self.headshot.setPixmap(user_pixmap)
            
            # 液态玻璃蒙版
            self.liquid_glass = LiquidGlassWidget(self)
            self.liquid_glass.setGeometry(QRect(0, 40, 50, 60))
            self.liquid_glass.setParent(self)

            # 添加动画
            self.liquid_animation = QPropertyAnimation(self.liquid_glass, b"geometry")
            self.liquid_animation.setDuration(1000)
            self.liquid_animation.setEasingCurve(QEasingCurve.OutCubic)

    def init_video_controller(self):
        """初始化视频控制器"""
        # 视频控制器
        self.video_controller = VideoController(self)
        self.video_controller.setGeometry(QRect(40, 40, self.width() - 50, self.height() - 50))
        self.video_controller.setParent(self)

    def init_refresh_button(self):
        """初始化刷新按钮"""
        # 刷新按钮 - 使用亚克力风格
        self.refresh_btn = QPushButton("", self)
        self.refresh_btn.setFixedSize(40, 40)
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.refresh_btn.setStyleSheet('''
            QPushButton {
                background-color: rgba(255, 255, 255, 150);
                border: 1px solid rgba(255, 255, 255, 100);
                border-radius: 15px;
                padding: 5px 10px;
                font-size: 13px;
                margin-right: 10px;
            }
            QPushButton:hover { 
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid rgba(100, 150, 255, 150);
            }
        ''')
        
        refresh_icon = QPixmap("./img/refresh.png")
        refresh_icon = refresh_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.refresh_btn.setIcon(QIcon(refresh_icon))
        self.refresh_btn.setIconSize(QSize(20, 20))
        self.refresh_btn.move(self.width() - 50, self.height() - 80)

        # 按钮底下液态玻璃
        self.liquid_glass_base = LiquidGlassWidget(self)
        self.liquid_glass_base.setGeometry(QRect(0, 0, 40, 40))
        self.liquid_glass_base.move(self.width() - 55, self.height() - 80)
        self.refresh_btn.raise_()

    def refresh_data(self):
        """刷新数据"""
        self.video_controller.hide()
        self.video_controller.deleteLater()
        QTimer.singleShot(100, self.recreate_video_controller)

    def recreate_video_controller(self):
        """重新创建视频控制器"""
        self.video_controller = VideoController(self)
        self.video_controller.setGeometry(QRect(40, 40, self.width()-50, self.height()-50))
        self.video_controller.setParent(self)
        self.video_controller.show()
        self.video_controller.raise_()
        self.refresh_btn.raise_()

    def update_function(self, num=0):
        """更新功能界面"""
        self.functionnum = num
        
        if self.functionnum == 0:
            self.home_function()
            setting_icon = QPixmap("./img/setting.png")
            setting_icon = setting_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setting.setIcon(QIcon(setting_icon))
            self.setting_text.setStyleSheet("color: #333; font-size: 12px; background-color: transparent;")

        elif self.functionnum == 1:
            self.setting_function()
            home_icon = QPixmap("./img/home.png")
            home_icon = home_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.home.setIcon(QIcon(home_icon))
            self.home_text.setStyleSheet("color: #333; font-size: 12px; background-color: transparent;")

    def home_function(self):
        """首页功能"""
        home_icon = QPixmap("./img/home_start.png")
        home_icon = home_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.home.setIcon(QIcon(home_icon))
        self.home_text.setStyleSheet("color: rgb(100, 150, 255); font-size: 12px; background-color: transparent;")

        self.liquid_animation.stop()
        self.liquid_animation.setStartValue(self.liquid_glass.geometry())
        self.liquid_animation.setEndValue(QRect(0, 40, 50, 60))
        self.liquid_animation.start()

    def setting_function(self):
        """设置功能"""
        setting_icon = QPixmap("./img/setting_start.png")
        setting_icon = setting_icon.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setting.setIcon(QIcon(setting_icon))
        self.setting_text.setStyleSheet("color: rgb(100, 150, 255); font-size: 12px; background-color: transparent;")

        self.liquid_animation.stop()
        self.liquid_animation.setStartValue(self.liquid_glass.geometry())
        self.liquid_animation.setEndValue(QRect(0, self.sidebar.height() - 60, 50, 60))
        self.liquid_animation.start()

    def showEvent(self, event):
        """窗口显示事件 - 新增"""
        super().showEvent(event)
        # 延迟一点时间确保窗口已经完全显示
        QTimer.singleShot(100, self.acrylic_effect.apply_effect)

    def resizeEvent(self, event):
        """窗口大小改变时更新效果"""
        super().resizeEvent(event)
        
        # 更新顶部栏
        self.windowbar.setGeometry(0, 0, self.width(), 40)
        
        # 更新侧栏
        self.sidebar.setGeometry(0, 40, 50, self.height())
        
        # 更新按钮位置
        self.closebtn.setGeometry(QRect(self.windowbar.width()-40, 0, 40, 40))
        self.minbtn.setGeometry(QRect(self.windowbar.width()-80, 0, 40, 40))
        
        # 更新搜索框及图标
        self.searchbar.setGeometry(QRect(
            (self.windowbar.width()-300)//2, 
            5, 
            300, 
            30
        ))
        self.search_icon_label.setGeometry(QRect(
            self.searchbar.geometry().x() + 270,
            10,
            20,
            20
        ))
        
        # 更新设置按钮位置
        self.setting.setGeometry(0, self.sidebar.height() - 100, 50, 40)
        self.setting_text.setGeometry(14, self.sidebar.height() - 70, 30, 20)
        
        # 更新亚克力效果
        self.acrylic_effect.apply_effect()
        
        # 更新功能界面
        if self.functionnum == 1:
            self.setting_function()
        else:
            self.home_function()
        
        # 更新视频控制器
        self.video_controller.setGeometry(QRect(40, 40, self.width() - 50, self.height() - 50))

        # 更新刷新按钮位置
        self.refresh_btn.move(self.width() - 50, self.height() - 80)
        self.liquid_glass_base.move(self.width() - 55, self.height() - 80)
    
    def closeEvent(self, a0):
        """关闭事件处理"""
        # 关闭所有线程
        self.video_controller._is_alive = False
        for thread in self.video_controller.download_threads:
            thread.join()

        return super().closeEvent(a0)

    # 添加鼠标事件处理方法
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 检查是否在顶栏范围内
            if (event.pos().y() <= 40 and 
                event.pos().x() <= self.width() - 80):  # 排除关闭和最小化按钮区域
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
            else:
                super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if self.dragging and self.drag_position is not None:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 设置全局样式
    app.setStyleSheet("""
    QLabel {
        font-family: 'Microsoft YaHei';
        font-size: 12px;
        font-weight: bold;
    }
    """)

    # 创建并显示主窗口
    mainWindow = MainWindow()
    mainWindow.show()
    
    # 运行应用程序
    sys.exit(app.exec_())