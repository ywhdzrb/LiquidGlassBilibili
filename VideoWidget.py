import time
import os

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBitmap
from PyQt5.QtWidgets import QWidget, QLabel, QApplication

from LiquidGlassWidget import LiquidGlassWidget
from VideoPlayer import VideoPlayer


class VideoWidget(QWidget):
    clicked = pyqtSignal()
    def __init__(self, parent=None, title="", duration=0, thumbnail_path="./img/none.png", upname="", release_time=0, bvid=None, cid=None):
        super().__init__(parent)

        self.title = title
        self.duration = duration
        self.thumbnail_path = thumbnail_path
        self.upname = upname
        self.bvid = bvid
        self.cid = cid

        # 如果点击了此部件播放视频
        self.clicked.connect(self.play_video)

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

        if os.path.exists(thumbnail_path):
            thumbnail = QPixmap(thumbnail_path).scaled(
                QSize(300, 150),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
        else:
            thumbnail = QPixmap(300, 150)  # 创建空图像
            thumbnail.fill(Qt.gray)  # 填充灰色背景

        # 液态玻璃底板
        self.liquid_glass = LiquidGlassWidget(self)
        self.liquid_glass.setGeometry(0, 0, 300, 210)


        # 视频缩略图标签,使用裁剪
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setGeometry(15, 20, 270, 150)  # 注意尺寸改为270x150
        
        # 使用保持宽高比的缩放并裁剪多余部分
        thumbnail = QPixmap(self.thumbnail_path).scaled(
            QSize(270, 150),  # 修改目标尺寸为实际显示尺寸
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        # 应用圆角处理（使用修正后的changeImage方法）
        rounded_thumbnail = self.changeImage(thumbnail, 10)
        self.thumbnail_label.setPixmap(rounded_thumbnail)

        # 视频标题标签
        self.title_label = QLabel(self)
        self.title_label.setText(self.title)
        self.title_label.setGeometry(15, 165, 300, 30)  # 调整位置和大小

        # 视频时间标签
        self.time_label = QLabel(self)
        self.time_label.setText(f"{self.duration // 60:02}:{self.duration % 60:02}")
        self.time_label.setGeometry(250, 150, 300, 30)  # 调整位置和大小

        # UP主名称标签
        self.upname_label = QLabel(self)
        self.upname_label.setText(f"UP:{self.upname} · {self.relative_time_str}")
        self.upname_label.setGeometry(15, 180, 300, 30)  # 调整位置和大小

    def changeImage(self, img_in, radius):
        target_size = QSize(270, 150)
        # 创建与目标尺寸相同的遮罩
        mask = QBitmap(target_size)
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制白色圆角区域（可见部分）
        painter.fillRect(mask.rect(), Qt.color0)  # 背景设为透明
        painter.setBrush(Qt.color1)               # 圆角区域设为可见
        painter.drawRoundedRect(mask.rect(), radius, radius)
        painter.end()

        # 缩放图像到目标尺寸
        scaled_img = img_in.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        # 居中裁剪
        cropped_img = scaled_img.copy(
            (scaled_img.width() - target_size.width()) // 2,
            (scaled_img.height() - target_size.height()) // 2,
            target_size.width(),
            target_size.height()
        )
        cropped_img.setMask(mask)
        return cropped_img

    def play_video(self):
        self.video_player = VideoPlayer(bvid=self.bvid, cid=self.cid)
        self.video_player.setGeometry(100, 100, 640, 480)
        self.video_player.show()

    # 更新视频信息
    def update_info(self, title=None, duration=None, thumbnail_path=None, upname=None, release_time=None):
        if title == None:
            title = self.title
        if duration == None:
            duration = self.duration
        if thumbnail_path == None:
            thumbnail_path = self.thumbnail_path
        if upname == None:
            upname = self.upname
        if release_time == None:
            release_time = self.release_time

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
        
        if thumbnail_path and os.path.exists(thumbnail_path):
            self.thumbnail_path = thumbnail_path
            thumbnail = QPixmap(self.thumbnail_path).scaled(
                QSize(300, 150),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )
        else:
            # 使用默认占位图或保持原有图像
            return  # 如果路径无效则不更新
        
        self.title_label.setText(self.title)
        self.time_label.setText(f"{self.duration // 60:02}:{self.duration % 60:02}")
        self.upname_label.setText(f"UP:{self.upname} · {self.relative_time_str}")

        # 使用保持宽高比的缩放并裁剪多余部分
        thumbnail = QPixmap(self.thumbnail_path).scaled(
            QSize(270, 150),  # 修改目标尺寸为实际显示尺寸
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        # 应用圆角处理
        rounded_thumbnail = self.changeImage(thumbnail, 10)
        self.thumbnail_label.setPixmap(rounded_thumbnail)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)




if __name__ == "__main__": 
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    video_widget = VideoWidget(title="视频标题啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊", duration=121, thumbnail_path="./temp/2025-07-27 16.31.54.png", upname="ywhdzrb", release_time=1752641588)
    video_widget.setGeometry(100, 100, 320, 320)
    video_widget.show()
    
    sys.exit(app.exec_())
