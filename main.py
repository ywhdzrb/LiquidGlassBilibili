import sys
from PyQt5.QtWidgets import QApplication
from MainWindow import MainWindow


def main():
    """应用程序主函数"""
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


if __name__ == '__main__':
    main()