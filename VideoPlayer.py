from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QScrollArea, QSlider, QLabel, QSizePolicy)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize
from PyQt5.QtGui import QIcon
from GetBilibiliApi import Download

class VideoPlayer(QWidget):
    def __init__(self, parent=None, bvid=None, cid=None):
        super().__init__(parent)
        self.bvid = bvid
        self.cid = cid
        self.media_player = None  # 确保media_player初始化为None
        self.timer = None  # 确保timer初始化为None
        self.setup_ui()
        Download().download_video(self.bvid, self.cid, f"./temp/{self.bvid}.mp4", self.on_download_complete)
    
    def on_download_complete(self):
        self.setup_media_player()
        self.video_widget.show()
        
    def setup_ui(self):
        # 主水平布局（侧边栏 + 内容区域）
        main_layout = QHBoxLayout()
        self.setup_content_area(main_layout)
        self.setLayout(main_layout)


    def create_nav_button(self, icon_path, tooltip):
        btn = QPushButton()
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(24, 24))
        btn.setToolTip(tooltip)
        btn.setStyleSheet("QPushButton { background: transparent; border: none; padding: 8px; }"
                         "QPushButton:hover { background: #404040; }")
        return btn

    def setup_content_area(self, main_layout):
        # 内容区域（视频播放器 + 推荐列表）
        content_layout = QVBoxLayout()
        
        # 视频播放区域
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 360)
        content_layout.addWidget(self.video_widget)
        
        # 添加控制栏
        self.setup_control_bar(content_layout)
        
        # 右侧推荐列表
        self.setup_recommendation_list(main_layout)
        
        main_layout.addLayout(content_layout, stretch=3)

    def setup_control_bar(self, parent_layout):
        # 播放控制栏
        control_bar = QWidget()
        control_layout = QHBoxLayout()
        
        # 播放/暂停按钮
        self.play_btn = QPushButton()
        self.play_btn.setIcon(QIcon("./img/play.png"))
        self.play_btn.clicked.connect(self.toggle_playback)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.sliderMoved.connect(self.set_position)
        
        # 音量控制
        self.volume_btn = QPushButton()
        self.volume_btn.setIcon(QIcon("./img/volume.png"))
        
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.progress_slider)
        control_layout.addWidget(self.volume_btn)
        control_bar.setLayout(control_layout)
        parent_layout.addWidget(control_bar)

    def setup_recommendation_list(self, main_layout):
        # 右侧推荐列表
        scroll_area = QScrollArea()
        scroll_area.setFixedWidth(240)
        scroll_area.setWidgetResizable(True)
        
        # 推荐列表内容（需要集成VideoController中的视频网格）
        self.recommend_list = QWidget()
        self.recommend_layout = QVBoxLayout()
        # 这里可以集成VideoController.create_video_grid()的逻辑
        self.recommend_list.setLayout(self.recommend_layout)
        scroll_area.setWidget(self.recommend_list)
        
        main_layout.addWidget(scroll_area)

    def setup_media_player(self):

        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(f"./temp/{self.bvid}.mp4")))
        
        # 定时更新进度条
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)
        
        self.media_player.play()

    def toggle_playback(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setIcon(QIcon("./img/play.png"))
        else:
            self.media_player.play()
            self.play_btn.setIcon(QIcon("./img/pause.png"))

    def update_progress(self):
        # 安全检查：确保媒体播放器和定时器存在
        if not self.media_player or not self.timer:
            return
            
        # 确保媒体状态正常
        if self.media_player.state() == QMediaPlayer.StoppedState:
            return
            
        duration = self.media_player.duration()
        position = self.media_player.position()
        
        # 防止除以零错误
        if duration > 0:
            self.progress_slider.setValue(int(position * 100 / duration))

    def set_position(self, position):
        self.media_player.setPosition(position * self.media_player.duration() // 100)
    
    def closeEvent(self, event):
        # 停止定时器
        if self.timer and self.timer.isActive():
            self.timer.stop()
            
        # 清理媒体播放器
        if self.media_player:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            self.media_player.deleteLater()
            self.media_player = None
            
        event.accept()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    video_player = VideoPlayer(bvid="BV1aAhPzdEJ8", cid="31374511005")
    video_player.setGeometry(100, 100, 640, 480)
    video_player.show()
    sys.exit(app.exec_())
