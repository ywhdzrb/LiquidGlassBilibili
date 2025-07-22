# 液态玻璃实现效果（希望不要太麻烦）
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt

class LiquidGlass(QWidget):
    def __init__(self, parent = None, flags = Qt.WindowFlags()):
        super().__init__(parent, flags)