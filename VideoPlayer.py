from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl
from GetBilibiliApi import *
from threading import Thread

class VideoPlayer(QWidget):
    def __init__(self, parent=None, bvid=None, cid=None):
        super().__init__(parent)
        self.bvid = bvid
        self.cid = cid
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.video_widget)
        self.setLayout(self.layout)
        # Download().download_video(self.bvid, self.cid, f"./temp/{self.bvid}.mp4")
        self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(f"./temp/{self.bvid}.mp4")))
        self.media_player.play()

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    video_player = VideoPlayer(bvid="BV1aAhPzdEJ8", cid="31374511005")
    video_player.setGeometry(100, 100, 640, 480)
    video_player.show()
    sys.exit(app.exec_())
