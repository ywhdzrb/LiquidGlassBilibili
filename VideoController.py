from VideoWidget import VideoWidget
from GetBilibiliApi import *
from PyQt5.QtWidgets import QWidget, QGridLayout

class VideoController(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_layout = QGridLayout(self)
        self.video_widgets = []
        self.page = 1
        self.video_info = GetRecommendVideos(page=self.page, pagesize=12).get_recommend_videos()
        
        # 创建12个视频组件
        self._create_video_grid()
        
    def _create_video_grid(self):
        """创建3行4列的视频网格布局"""
        # 清空现有布局
        while self.grid_layout.count():
            self.grid_layout.takeAt(0)
        
        # 自动计算间距（保留5px的间隙）
        self.grid_layout.setHorizontalSpacing(5)
        self.grid_layout.setVerticalSpacing(5)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建12个视频组件
        for i in range(12):
            row = i // 4
            col = i % 4
            Download().download_thumbnail(self.video_info[i]["pic"], f"./temp/{self.video_info[i]['bvid']}.jpg")
            video_widget = VideoWidget(
                title=self.video_info[i]["title"],
                duration=self.video_info[i]["duration"],
                thumbnail_path=f"./temp/{self.video_info[i]['bvid']}.jpg",  
                upname=self.video_info[i]["owner"]["name"],  
                release_time=self.video_info[i]["pubdate"]   
            )
            self.video_widgets.append(video_widget)
            self.grid_layout.addWidget(video_widget, row, col)

    def get_video_widget(self, index):
        """获取指定索引的视频组件"""
        if 0 <= index < len(self.video_widgets):
            return self.video_widgets[index]
        return None

    def get_all_widgets(self):
        """获取全部视频组件"""
        return self.video_widgets
    
    def update_video_info(self):
        """更新视频信息"""
        self.page += 1
        video_info_list = GetRecommendVideos(page=self.page, pagesize=12).get_recommend_videos()
        for i, video_widget in enumerate(self.video_widgets):
            video_widget.update_info(title=video_info_list[i]["title"], duration=video_info_list[i]["duration"], thumbnail_path=video_info_list[i]["thumbnail_path"], upname=video_info_list[i]["upname"], release_time=video_info_list[i]["release_time"])

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    video_controller = VideoController()
    video_controller.show()
    sys.exit(app.exec_())
    