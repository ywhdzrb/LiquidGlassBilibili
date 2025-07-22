from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt
import sys

class MainWindow(QMainWindow):
    def __init__(self, parent = None, flags = Qt.WindowFlags()):
        super().__init__(parent, flags)
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('液态玻璃bilibili')
        self.setGeometry(100, 100, 1200, 700)

        # 默认窗口最大化
        self.showMaximized()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())