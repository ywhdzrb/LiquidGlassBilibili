from BilibiliApi import QrLogin
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class BiliBiliLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bilibili登录")
        self.setGeometry(100, 100, 300, 500)

        self.qrlogin = QrLogin()
        qr_path = self.qrlogin.get_qrcode()
        
        self.label = QLabel(self)
        self.label.setGeometry(50, 50, 200, 200)
        # 拉升到合适大小
        qr = QPixmap(qr_path)
        qr = qr.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(qr)

        self.button = QPushButton("扫码完点这个登录",self)
        self.button.setGeometry(50, 250, 200, 50)
        self.button.clicked.connect(self.login)

    def login(self):
        code = self.qrlogin.check_login()
        if code == 0:
            self.button.setText("登录成功")
        else:
            self.button.setText("登录失败")

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    login_window = BiliBiliLogin()
    login_window.show()
    sys.exit(app.exec_())