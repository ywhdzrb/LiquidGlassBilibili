import time
import os

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter, QColor, QBitmap
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QSizePolicy

from LiquidGlassWidget import LiquidGlassWidget
from VideoPlayer import VideoPlayer


class VideoWidget(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None, title="", duration=0, cover_path="./img/none.png", upname="", release_time=0, bvid=None, cid=None):
        super().__init__(parent)

        self.title = title
        self.duration = duration
        self.cover_path = cover_path
        self.upname = upname
        self.bvid = bvid
        self.cid = cid
        
        # 原始参考尺寸（300x210）
        self.original_width = 300
        self.original_height = 210
        
        # 如果点击了此部件播放视频
        self.clicked.connect(self.play_video)

        if len(self.title) > 15:
            self.title = self.title[:15] + "..."

        # 计算视频时间
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

        # 视频封面标签
        self.cover_label = QLabel(self)
        self.cover_label.setAlignment(Qt.AlignCenter)  # 居中对齐
        
        # 视频标题标签
        self.title_label = QLabel(self)
        self.title_label.setText(self.title)
        self.title_label.setWordWrap(True)  # 允许文本换行
        self.title_label.setStyleSheet("""
            color: #2c3e50; 
            font-size: 13px; 
            font-weight: bold;
            background-color: transparent;
            padding: 2px;
        """)

        # 视频时间标签
        self.time_label = QLabel(self)
        self.time_label.setText(f"{self.duration // 60:02}:{self.duration % 60:02}")
        self.time_label.setStyleSheet("""
            color: #ffffff; 
            font-size: 10px; 
            font-weight: bold;
            background-color: rgba(0, 0, 0, 180); 
            border-radius: 4px;
            padding: 2px 4px;
        """)
        self.time_label.setAlignment(Qt.AlignCenter)

        # UP主名称标签
        self.upname_label = QLabel(self)
        self.upname_label.setText(f"UP: {self.upname} · {self.relative_time_str}")
        self.upname_label.setStyleSheet("""
            color: #7f8c8d; 
            font-size: 11px; 
            background-color: transparent;
            padding: 2px;
        """)
        
        # 设置大小策略为可扩展
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 初始化布局
        self.update_layout()

    def calculate_scaled_geometry(self, x_ratio, y_ratio, width_ratio, height_ratio):
        """根据当前尺寸计算缩放后的几何位置"""
        current_width = self.width()
        current_height = self.height()
        
        x = int(x_ratio * current_width)
        y = int(y_ratio * current_height)
        width = int(width_ratio * current_width)
        height = int(height_ratio * current_height)
        
        return x, y, width, height

    def update_layout(self):
        """更新内部布局（基于比例）"""
        # 液态玻璃底板 - 占满整个widget
        self.liquid_glass.setGeometry(0, 0, self.width(), self.height())
        
        # 封面标签 - 相对位置计算
        thumb_x, thumb_y, thumb_w, thumb_h = self.calculate_scaled_geometry(
            0.05, 0.095, 0.9, 0.714  # 原位置：15,20,270,150 → 比例：0.05,0.095,0.9,0.714
        )
        self.cover_label.setGeometry(thumb_x, thumb_y, thumb_w, thumb_h)
        
        # 标题标签
        title_x, title_y, title_w, title_h = self.calculate_scaled_geometry(
            0.05, 0.786, 0.9, 0.143  # 原位置：15,165,270,30 → 比例：0.05,0.786,0.9,0.143
        )
        self.title_label.setGeometry(title_x, title_y, title_w, title_h)
        
        # 时间标签
        time_x, time_y, time_w, time_h = self.calculate_scaled_geometry(
            0.767, 0.69, 0.167, 0.095  # 原位置：230,145,50,20 → 比例：0.767,0.69,0.167,0.095
        )
        self.time_label.setGeometry(time_x, time_y, time_w, time_h)
        
        # UP主标签
        up_x, up_y, up_w, up_h = self.calculate_scaled_geometry(
            0.05, 0.857, 0.9, 0.143  # 原位置：15,180,270,30 → 比例：0.05,0.857,0.9,0.143
        )
        self.upname_label.setGeometry(up_x, up_y, up_w, up_h)
        
        # 重新加载封面以适应新尺寸
        self.load_cover()

    def load_cover(self):
        """加载并显示封面"""
        if os.path.exists(self.cover_path):
            try:
                # 加载原始图片
                original_pixmap = QPixmap(self.cover_path)
                if not original_pixmap.isNull():
                    # 创建圆角封面，使用当前封面标签的尺寸
                    thumb_width = self.cover_label.width()
                    thumb_height = self.cover_label.height()
                    rounded_pixmap = self.create_rounded_cover(original_pixmap, thumb_width, thumb_height, 10)
                    self.cover_label.setPixmap(rounded_pixmap)
                else:
                    self.set_default_cover()
            except Exception as e:
                print(f"加载封面失败: {e}")
                self.set_default_cover()
        else:
            self.set_default_cover()

    def set_default_cover(self):
        """设置默认封面（不触发加载）"""
        thumb_width = self.cover_label.width()
        thumb_height = self.cover_label.height()
        
        default_pixmap = QPixmap(thumb_width, thumb_height)
        default_pixmap.fill(QColor(60, 60, 60))  # 深灰色背景
        
        # 绘制一个简单的视频图标
        painter = QPainter(default_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(100, 100, 100))
        painter.drawRoundedRect(0, 0, thumb_width, thumb_height, 10, 10)
        
        # 绘制播放按钮
        painter.setBrush(QColor(200, 200, 200, 180))
        triangle_size = min(thumb_width, thumb_height) * 0.3
        x_center = thumb_width // 2
        y_center = thumb_height // 2
        from PyQt5.QtCore import QPoint
        points = [
            QPoint(x_center - triangle_size//3, y_center - triangle_size//2),
            QPoint(x_center - triangle_size//3, y_center + triangle_size//2),
            QPoint(x_center + triangle_size//2, y_center)
        ]
        painter.drawPolygon(*points)
        painter.end()
        
        self.cover_label.setPixmap(default_pixmap)

    def create_rounded_cover(self, pixmap, width, height, radius):
        """创建圆角封面"""
        # 计算缩放比例，保持宽高比
        scaled_pixmap = pixmap.scaled(
            width, height, 
            Qt.KeepAspectRatioByExpanding,  # 保持宽高比填充
            Qt.SmoothTransformation
        )
        
        # 创建目标尺寸的透明图像
        result = QPixmap(width, height)
        result.fill(Qt.transparent)
        
        # 创建圆角遮罩
        mask = QBitmap(width, height)
        mask.fill(Qt.color0)
        
        painter = QPainter(mask)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(Qt.color1)
        painter.drawRoundedRect(0, 0, width, height, radius, radius)
        painter.end()
        
        # 绘制图像
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算居中裁剪的位置
        x_offset = (scaled_pixmap.width() - width) // 2
        y_offset = (scaled_pixmap.height() - height) // 2
        
        # 绘制裁剪后的图像
        painter.drawPixmap(0, 0, scaled_pixmap, x_offset, y_offset, width, height)
        painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        painter.drawPixmap(0, 0, mask)
        painter.end()
        
        return result

    def play_video(self):
        self.video_player = VideoPlayer(bvid=self.bvid, cid=self.cid)
        self.video_player.setFixedSize(740, 480)
        self.video_player.show()

    def update_info(self, title=None, duration=None, cover_path=None, upname=None, release_time=None):
        """更新视频信息"""
        if title is not None:
            self.title = title
            if len(self.title) > 20:
                self.title = self.title[:20] + "..."
            self.title_label.setText(self.title)

        if duration is not None:
            self.duration = duration
            self.time_label.setText(f"{self.duration // 60:02}:{self.duration % 60:02}")

        if upname is not None:
            self.upname = upname

        if release_time is not None:
            self.release_time = release_time
            # 重新计算相对时间
            current_time = int(time.time())
            relative_time = current_time - self.release_time
            if relative_time < 24 * 3600:
                hours = relative_time // 3600
                self.relative_time_str = f"{hours}小时前"
            elif self.release_time // 86400 == current_time // 86400:
                self.relative_time_str = time.strftime("%H:%M", time.localtime(self.release_time))
            elif self.release_time // 31536000 == current_time // 31536000:
                self.relative_time_str = time.strftime("%m-%d", time.localtime(self.release_time))
            else:
                self.relative_time_str = time.strftime("%Y-%m-%d", time.localtime(self.release_time))

        if cover_path is not None:
            self.cover_path = cover_path
            self.load_cover()

        # 更新UP主信息
        self.upname_label.setText(f"UP: {self.upname} · {self.relative_time_str}")

    def resizeEvent(self, event):
        """尺寸改变时更新内部布局"""
        super().resizeEvent(event)
        self.update_layout()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


if __name__ == "__main__": 
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    video_widget = VideoWidget(
        title="视频标题啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊", 
        duration=121, 
        cover_path="./temp/BV1A1HPzRE3U.jpg", 
        upname="ywhdzrb", 
        release_time=1752641588
    )
    video_widget.setGeometry(100, 100, 300, 210)
    video_widget.show()
    
    sys.exit(app.exec_())