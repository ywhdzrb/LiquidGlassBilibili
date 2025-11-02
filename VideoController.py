from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QApplication, QSizePolicy
from VideoWidget import VideoWidget
from GetBilibiliApi import *
import os
import threading

class DataLoaderSignals(QObject):
    data_ready = pyqtSignal(list)
    data_failed = pyqtSignal()

class DataLoader(threading.Thread):
    def __init__(self, page, pagesize):
        super().__init__()
        self.page = page
        self.pagesize = pagesize
        self.signals = DataLoaderSignals()

    def run(self):
        try:
            data = GetRecommendVideos(page=self.page, pagesize=self.pagesize).get_recommend_videos()
            if data and len(data) >= 12:
                self.signals.data_ready.emit(data[:12])
            else:
                raise ValueError("推荐数据不足或格式错误")
        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            self.signals.data_failed.emit()

class ThumbnailDownloader(threading.Thread):
    def __init__(self, pic_url, bvid, index, controller):
        super().__init__()
        self.pic_url = pic_url
        self.bvid = bvid
        self.index = index
        self.controller = controller

    def run(self):
        try:
            save_path = f"./temp/{self.bvid}.jpg"
            if Download().download_thumbnail(self.pic_url, save_path):
                self.controller.thumbnail_loaded.emit(self.index, save_path)
        except Exception as e:
            print(f"缩略图下载失败: {str(e)}")

class VideoController(QWidget):
    thumbnail_loaded = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_alive = True
        self.download_threads = []
        self.video_widgets = []
        self.video_info = []
        
        self.init_ui()
        self.load_initial_data()
        self.thumbnail_loaded.connect(self.update_thumbnail)

    def init_ui(self):
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignCenter)
        
        self.loading_label = QLabel("加载中...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            font-size: 24px; 
            color: white;
            background-color: rgba(0,0,0,150);
            border-radius: 10px;
        """)

    def load_initial_data(self):
        self.loading_label.show()
        self.loading_label.setGeometry(0, 0, self.width(), self.height())
        os.makedirs("./temp", exist_ok=True)
        
        loader = DataLoader(page=1, pagesize=12)
        loader.signals.data_ready.connect(self.on_data_loaded)
        loader.signals.data_failed.connect(self.on_data_failed)
        loader.start()

    def on_data_loaded(self, data):
        if not self._is_alive:
            return
        self.loading_label.hide()
        self.video_info = data
        self.create_video_grid()
        self.start_thumbnail_downloads()

    def on_data_failed(self):
        if not self._is_alive:
            return
        self.loading_label.setText("加载失败，点击重试")
        self.loading_label.mousePressEvent = lambda _: self.load_initial_data()

    def calculate_widget_size(self):
        """计算自适应的小部件尺寸"""
        # 获取可用宽度（减去边距和间距）
        available_width = self.width() - 20 - 45  # 20是左右边距，45是3个间距（4列有3个间距）
        
        # 计算每个卡片的宽度（保持4列布局）
        card_width = available_width // 4
        
        # 根据宽高比计算高度（原比例300:210≈1.428）
        card_height = int(card_width / 1.428)
        
        return card_width, card_height

    def create_video_grid(self):
        """创建视频网格布局"""
        valid_count = min(len(self.video_info), 12)
        self.video_widgets = []
        
        # 清除现有布局
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # 计算自适应尺寸
        card_width, card_height = self.calculate_widget_size()
        
        for i in range(valid_count):
            row, col = divmod(i, 4)  # 固定每行4个
            video_widget = self.create_video_widget(i, card_width, card_height)
            self.video_widgets.append(video_widget)
            self.grid_layout.addWidget(video_widget, row, col)

    def create_video_widget(self, index, width, height):
        """创建单个视频小部件"""
        info = self.video_info[index]
        widget = VideoWidget(
            title=info.get("title", ""),
            duration=info.get("duration", 0),
            thumbnail_path="./img/none.png",
            upname=info.get("owner", {}).get("name", ""),
            release_time=info.get("pubdate", 0),
            bvid=info.get("bvid", ""),
            cid=info.get("cid", "")
        )
        # 不再设置固定大小，而是设置最小和最大尺寸
        widget.setMinimumSize(width // 2, height // 2)  # 最小尺寸为计算尺寸的一半
        widget.setMaximumSize(width * 2, height * 2)    # 最大尺寸为计算尺寸的两倍
        
        # 设置大小策略为可扩展
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        return widget

    def start_thumbnail_downloads(self):
        """开始下载缩略图"""
        self.download_threads = [t for t in self.download_threads if t.is_alive()]
        
        for i, info in enumerate(self.video_info[:12]):
            thread = ThumbnailDownloader(
                pic_url=info["pic"],
                bvid=info["bvid"],
                index=i,
                controller=self
            )
            self.download_threads.append(thread)
            thread.start()

    def update_thumbnail(self, index, path):
        """更新缩略图"""
        if self._is_alive and index < len(self.video_widgets):
            self.video_widgets[index].update_info(thumbnail_path=path)

    def resizeEvent(self, event):
        """窗口大小改变时调整布局"""
        super().resizeEvent(event)
        self.loading_label.setGeometry(0, 0, self.width(), self.height())
        
        # 重新计算并设置所有视频卡片的推荐尺寸
        if self.video_widgets:
            card_width, card_height = self.calculate_widget_size()
            for widget in self.video_widgets:
                # 更新最小和最大尺寸，但不设置固定尺寸
                widget.setMinimumSize(card_width // 2, card_height // 2)
                widget.setMaximumSize(card_width * 2, card_height * 2)
                
                # 强制更新布局
                widget.update_layout()

    def closeEvent(self, event):
        """关闭事件处理"""
        self._is_alive = False
        for t in self.download_threads:
            t.join(timeout=1)
        super().closeEvent(event)

if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    controller = VideoController()
    controller.show()
    sys.exit(app.exec_())