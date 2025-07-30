from GetBilibiliApi import GetVideoInfo
from VideoWidget import VideoWidget

class VideoController:
    def __init__(self, video_id):
        self.video_id = video_id
        self.video_info = GetVideoInfo(video_id).get_video_info()
        self.video_widget = VideoWidget(title=self.video_info["title"], duration=self.video_info["duration"], thumbnail_path=self.video_info["thumbnail_path"], upname=self.video_info["upname"], release_time=self.video_info["release_time"])


