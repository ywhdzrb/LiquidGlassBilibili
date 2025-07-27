from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPixmap, QPainterPath
from PyQt5.QtCore import QRect, QSize, Qt
from LiquidGlassWidget import LiquidGlassWidget

class VideoWidget(QWidget):
    def __init__(self, parent=None, title="", time=0, thumbnail_path="", upname="", concerned=False, release_time=0):
        super().__init__(parent)

        self.title = title
        self.time = time
        self.thumbnail_path = thumbnail_path
        self.upname = upname
        self.concerned = concerned

        if len(self.title) > 35:
            self.title = self.title[:35] + "..."
        
        # 视频缩略图标签,使用裁剪
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setGeometry(0, 0, 300, 150)  # 恢复合理尺寸
        thumbnail = QPixmap(self.thumbnail_path).scaled(
            self.thumbnail_label.size(),  # 使用标签尺寸作为基准
            Qt.KeepAspectRatio,           # 保持宽高比
            Qt.SmoothTransformation       # 平滑缩放
        )
        self.thumbnail_label.setPixmap(thumbnail)

        # 视频标题标签
        self.title_label = QLabel(self)
        self.title_label.setText(self.title)
        self.title_label.setGeometry(0, 145, 300, 30)  # 调整位置和大小

        # 视频时间标签
        self.time_label = QLabel(self)
        self.time_label.setText(f"{self.time // 60:02}:{self.time % 60:02}")
        self.time_label.setGeometry(235, 130, 300, 30)  # 调整位置和大小

        # UP主名称标签
        self.upname_label = QLabel(self)
        self.upname_label.setText(f"UP:{self.upname}")
        self.upname_label.setGeometry(0, 160, 300, 30)  # 调整位置和大小





if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    video_widget = VideoWidget(title="视频标题", time=121, thumbnail_path="./temp/2025-07-27 16.31.54.png", upname="ywhdzrb", concerned=False, release_time="7-21")
    video_widget.setGeometry(100, 100, 320, 320)
    video_widget.show()
    
    sys.exit(app.exec_())
