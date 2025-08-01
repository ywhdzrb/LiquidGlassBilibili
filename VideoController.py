from PyQt5.QtCore import QThreadPool, QRunnable
from VideoWidget import VideoWidget
from GetBilibiliApi import *
from PyQt5.QtWidgets import QWidget, QGridLayout

class DownloadTask(QRunnable):
    """异步缩略图下载任务"""
    def __init__(self, pic_url, bvid, index, controller):
        super().__init__()
        self.pic_url = pic_url
        self.bvid = bvid
        self.index = index
        self.controller = controller

    def run(self):
        try:
            save_path = f"./temp/{self.bvid}.jpg"
            Download().download_thumbnail(self.pic_url, save_path)
            if self.index < len(self.controller.video_widgets):
                self.controller.video_widgets[self.index].update_info(
                    thumbnail_path=save_path
                )
        except Exception as e:
            print(f"缩略图下载失败: {str(e)}")

class VideoController(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)  # 限制最大并发数
        self.grid_layout = QGridLayout(self)
        self.video_widgets = []
        self.page = 1
        self.video_info = GetRecommendVideos(page=self.page, pagesize=12).get_recommend_videos()
        
        self._create_video_grid()

    def _create_video_grid(self):
        """创建3行4列的视频网格布局"""
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        
        self.grid_layout.setHorizontalSpacing(5)
        self.grid_layout.setVerticalSpacing(5)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        for i in range(12):
            row = i // 4
            col = i % 4
            video_info = self.video_info[i]
            bvid = video_info['bvid']
            
            video_widget = VideoWidget(
                title=video_info["title"],
                duration=video_info["duration"],
                thumbnail_path="",
                upname=video_info["owner"]["name"],
                release_time=video_info["pubdate"]
            )
            
            task = DownloadTask(
                pic_url=video_info["pic"],
                bvid=bvid,
                index=i,
                controller=self
            )
            self.thread_pool.start(task)
            
            self.video_widgets.append(video_widget)
            self.grid_layout.addWidget(video_widget, row, col)

    def get_video_widget(self, index):
        if 0 <= index < len(self.video_widgets):
            return self.video_widgets[index]
        return None

    def get_all_widgets(self):
        return self.video_widgets
    
    def update_video_info(self):
        self.page += 1
        video_info_list = GetRecommendVideos(page=self.page, pagesize=12).get_recommend_videos()
        for i, video_widget in enumerate(self.video_widgets):
            video_widget.update_info(
                title=video_info_list[i]["title"],
                duration=video_info_list[i]["duration"],
                thumbnail_path=video_info_list[i]["thumbnail_path"],
                upname=video_info_list[i]["upname"],
                release_time=video_info_list[i]["release_time"]
            )

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    video_controller = VideoController()
    video_controller.show()
    sys.exit(app.exec_())
