import os
import sys
import ctypes
from ctypes.util import find_library

# 手动设置 VLC 库路径
def setup_vlc_path():
    # 常见的 VLC 安装路径
    possible_paths = [
        r"C:\Program Files\VideoLAN\VLC",
        r"C:\Program Files (x86)\VideoLAN\VLC",
        os.path.expanduser(r"~\AppData\Local\VideoLAN\VLC"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            os.environ['PYTHON_VLC_LIB_PATH'] = path
            os.add_dll_directory(path)  # Python 3.8+
            break

# 在导入 vlc 前调用
setup_vlc_path()

import vlc
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QSlider, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

class VideoPlayer(QMainWindow):
    """使用VLC作为后端的视频播放器"""
    
    videoStateChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 尝试创建 VLC 实例
        try:
            self.instance = vlc.Instance()
            self.media_player = self.instance.media_player_new()
        except Exception as e:
            QMessageBox.critical(None, "VLC错误", f"无法初始化VLC: {str(e)}\n请确保已安装VLC播放器")
            sys.exit(1)
            
        self.current_media = None
        self.is_playing = False
        self.is_muted = False
        self.volume = 50
        
        self.setup_ui()
        self.setup_connections()
        self.setup_timer()
        
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("B站视频播放器 - VLC后端")
        self.setGeometry(100, 100, 1200, 800)
        
        # 中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 视频显示区域
        self.video_frame = QWidget()
        self.video_frame.setMinimumSize(800, 450)
        self.video_frame.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.video_frame)
        
        # 在Windows上设置视频输出
        if os.name == 'nt':
            self.media_player.set_hwnd(int(self.video_frame.winId()))
        else:
            self.media_player.set_xwindow(int(self.video_frame.winId()))
        
        # 控制区域
        control_layout = QHBoxLayout()
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("播放")
        self.play_btn.setFixedSize(60, 30)
        control_layout.addWidget(self.play_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setFixedSize(60, 30)
        control_layout.addWidget(self.stop_btn)
        
        # 静音按钮
        self.mute_btn = QPushButton("静音")
        self.mute_btn.setFixedSize(60, 30)
        control_layout.addWidget(self.mute_btn)
        
        # 音量滑块
        control_layout.addWidget(QLabel("音量:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.volume)
        self.volume_slider.setFixedWidth(100)
        control_layout.addWidget(self.volume_slider)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        control_layout.addWidget(self.progress_slider)
        
        # 时间标签
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)
        control_layout.addWidget(self.time_label)
        
        main_layout.addLayout(control_layout)
        
        # 状态栏
        self.status_label = QLabel("准备就绪")
        main_layout.addWidget(self.status_label)
        
        # 设置初始音量
        self.media_player.audio_set_volume(self.volume)
        
    def setup_connections(self):
        """设置信号连接"""
        self.play_btn.clicked.connect(self.toggle_play_pause)
        self.stop_btn.clicked.connect(self.stop)
        self.mute_btn.clicked.connect(self.toggle_mute)
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.progress_slider.sliderPressed.connect(self.progress_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.progress_slider_released)
        self.progress_slider.sliderMoved.connect(self.set_position)
        
    def setup_timer(self):
        """设置定时器用于更新进度"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(100)  # 每100ms更新一次
        
    def load_video_from_bilibili(self, bvid, cid):
        """从B站加载视频"""
        try:
            from GetBilibiliApi import GetVideoInfo
            
            # 获取视频信息
            video_info = GetVideoInfo(bvid, cid)
            
            # 获取MP4格式视频流URL
            video_url = video_info.get_video_streaming_info_mp4()
            
            if not video_url:
                QMessageBox.warning(self, "错误", "无法获取视频流URL")
                return False
                
            return self.load_video_from_url(video_url, bvid)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载视频失败: {str(e)}")
            return False
    
    def load_video_from_url(self, video_url, title="视频"):
        """直接从URL加载视频"""
        try:
            self.status_label.setText(f"正在加载: {title}")
            
            # 设置VLC选项，包括请求头
            options = [
                f'http-referrer=https://www.bilibili.com/',
                f'http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            ]
            
            # 创建媒体对象
            media = self.instance.media_new(video_url, *options)
            media.get_mrl()
            
            # 设置媒体
            self.media_player.set_media(media)
            self.current_media = media
            
            self.status_label.setText("视频加载完成，点击播放")
            self.videoStateChanged.emit("loaded")
            
            return True
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载视频失败: {str(e)}")
            return False
    
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.media_player.is_playing():
            self.media_player.pause()
            self.is_playing = False
            self.play_btn.setText("播放")
            self.status_label.setText("已暂停")
        else:
            if self.current_media is None:
                QMessageBox.warning(self, "警告", "请先加载视频")
                return
                
            if self.media_player.play() == -1:
                QMessageBox.warning(self, "错误", "无法播放视频")
                return
                
            self.is_playing = True
            self.play_btn.setText("暂停")
            self.status_label.setText("播放中")
    
    def stop(self):
        """停止播放"""
        self.media_player.stop()
        self.is_playing = False
        self.play_btn.setText("播放")
        self.status_label.setText("已停止")
        self.progress_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
    
    def toggle_mute(self):
        """切换静音状态"""
        self.is_muted = not self.is_muted
        self.media_player.audio_set_mute(self.is_muted)
        self.mute_btn.setText("取消静音" if self.is_muted else "静音")
    
    def set_volume(self, volume):
        """设置音量"""
        self.volume = volume
        self.media_player.audio_set_volume(volume)
    
    def progress_slider_pressed(self):
        """进度条按下时暂停定时器"""
        self.timer.stop()
    
    def progress_slider_released(self):
        """进度条释放时恢复定时器"""
        self.timer.start(100)
    
    def set_position(self, position):
        """设置播放位置"""
        if self.media_player.is_playing():
            # 将滑块值转换为媒体位置
            media_length = self.media_player.get_length()
            if media_length > 0:
                new_position = int((position / 100.0) * media_length)
                self.media_player.set_time(new_position)
    
    def update_ui(self):
        """更新UI状态"""
        if self.media_player.is_playing():
            # 更新进度条
            current_time = self.media_player.get_time()
            total_time = self.media_player.get_length()
            
            if total_time > 0:
                # 更新进度滑块
                progress = int((current_time / total_time) * 100)
                self.progress_slider.setValue(progress)
                
                # 更新时间显示
                current_str = self.format_time(current_time)
                total_str = self.format_time(total_time)
                self.time_label.setText(f"{current_str} / {total_str}")
    
    def format_time(self, milliseconds):
        """格式化时间显示"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        hours = minutes // 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
        else:
            return f"{minutes:02d}:{seconds%60:02d}"
    
    def play(self):
        """开始播放"""
        self.toggle_play_pause()
    
    def pause(self):
        """暂停播放"""
        if self.media_player.is_playing():
            self.media_player.pause()
            self.is_playing = False
            self.play_btn.setText("播放")
    
    def get_current_state(self):
        """获取当前播放状态"""
        if self.media_player.is_playing():
            return "playing"
        else:
            return "paused" if self.current_media else "stopped"
    
    def closeEvent(self, event):
        """关闭事件处理"""
        self.stop()
        if hasattr(self, 'media_player'):
            self.media_player.release()
        if hasattr(self, 'instance'):
            self.instance.release()
        super().closeEvent(event)


# 使用示例
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    player = VideoPlayer()
    player.show()
    
    # 测试播放
    # player.load_video_from_bilibili("BV1aAhPzdEJ8", "31374511005")
    
    sys.exit(app.exec_())