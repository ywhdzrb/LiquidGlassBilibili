from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel
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
        self.init_ui()
        self.load_initial_data()
        self.thumbnail_loaded.connect(self.update_thumbnail)

    def init_ui(self):
        self.grid_layout = QGridLayout(self)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(5)
        self.video_widgets = []
        
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

    def create_video_grid(self):
        valid_count = min(len(self.video_info), 12)
        for i in range(valid_count):
            row, col = divmod(i, 4)
            video_widget = self.create_video_widget(i)
            self.video_widgets.append(video_widget)
            self.grid_layout.addWidget(video_widget, row, col)

    def create_video_widget(self, index):
        info = self.video_info[index]
        return VideoWidget(
            title=info.get("title", ""),
            duration=info.get("duration", 0),
            thumbnail_path="./img/none.png",
            upname=info.get("owner", {}).get("name", ""),
            release_time=info.get("pubdate", 0),
            bvid=info.get("bvid", ""),
            cid=info.get("cid", "")
        )

    def start_thumbnail_downloads(self):
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
        if self._is_alive and index < len(self.video_widgets):
            self.video_widgets[index].update_info(thumbnail_path=path)

    def closeEvent(self, event):
        self._is_alive = False
        for t in self.download_threads:
            t.join(timeout=1)
        super().closeEvent(event)

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    controller = VideoController()
    controller.show()
    sys.exit(app.exec_())
