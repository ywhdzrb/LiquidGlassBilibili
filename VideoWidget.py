from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPixmap, QPainterPath
from PyQt5.QtCore import QRect, QSize, Qt
import time
from LiquidGlassWidget import LiquidGlassWidget

class VideoWidget(QWidget):
    def __init__(self, parent=None, title="", duration=0, thumbnail_path=None, upname="", release_time=0):
        super().__init__(parent)

        self.title = title
        self.duration = duration
        self.thumbnail_path = thumbnail_path
        self.upname = upname

        if len(self.title) > 20:
            self.title = self.title[:20] + "..."

        # 计算视频时间（如果相对时间小于24，则显示几小时前。如果在今年，则显示月日。如果不在今年，则显示年月日）
        self.release_time = release_time
        current_time = int(time.time())
        relative_time = current_time - self.release_time
        if relative_time < 24 * 3600:  # 小于24小时
            hours = relative_time // 3600
            self.relative_time_str = f"{hours}小时前"
        elif self.release_time // 86400 == current_time // 86400:  # 今天
            self.relative_time_str = time.strftime("%H:%M", time.localtime(self.release_time))
        elif self.release_time // 31536000 == current_time // 31536000:
            self.relative_time_str = time.strftime("%m-%d", time.localtime(self.release_time))
        else:
            self.relative_time_str = time.strftime("%Y-%m-%d", time.localtime(self.release_time))

        # 液态玻璃底板
        self.liquid_glass = LiquidGlassWidget(self)
        self.liquid_glass.setGeometry(0, 0, 300, 200)


        # 视频缩略图标签,使用裁剪
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setGeometry(10, 10, 270, 150)  # 固定尺寸为300x150
        
        # 使用保持宽高比的缩放并裁剪多余部分
        thumbnail = QPixmap(self.thumbnail_path).scaled(
            QSize(300, 150),  # 固定目标尺寸
            Qt.KeepAspectRatioByExpanding,  # 保持宽高比并扩展填充
            Qt.SmoothTransformation
        )
        # 创建裁剪后的缩略图
        self.thumbnail_label.setPixmap(thumbnail.copy(
            (thumbnail.width() - 300) // 2,  # 水平居中裁剪
            (thumbnail.height() - 150) // 2,  # 垂直居中裁剪
            300,
            150
        ))

        # 视频标题标签
        self.title_label = QLabel(self)
        self.title_label.setText(self.title)
        self.title_label.setGeometry(10, 155, 300, 30)  # 调整位置和大小

        # 视频时间标签
        self.time_label = QLabel(self)
        self.time_label.setText(f"{self.duration // 60:02}:{self.duration % 60:02}")
        self.time_label.setGeometry(245, 140, 300, 30)  # 调整位置和大小

        # UP主名称标签
        self.upname_label = QLabel(self)
        self.upname_label.setText(f"UP:{self.upname} · {self.relative_time_str}")
        self.upname_label.setGeometry(10, 170, 300, 30)  # 调整位置和大小


    # 更改封面
    def change_thumbnail(self, thumbnail_path):
        self.thumbnail_path = thumbnail_path
        thumbnail = QPixmap(self.thumbnail_path).scaled(
            QSize(300, 150),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.thumbnail_label.setPixmap(thumbnail.copy(
            (thumbnail.width() - 300) // 2,
            (thumbnail.height() - 150) // 2,
            300,
            150
        ))




if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    video_widget = VideoWidget(title="视频标题啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊", duration=121, thumbnail_path="./temp/2025-07-27 16.31.54.png", upname="ywhdzrb", release_time=1752641588)
    video_widget.setGeometry(100, 100, 320, 320)
    video_widget.show()
    
    sys.exit(app.exec_())
