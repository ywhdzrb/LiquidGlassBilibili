from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QScrollArea, QSlider, QLabel, QSizePolicy, QSpacerItem,
                            QMessageBox, QProgressBar, QApplication)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize, QObject, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
from PyQt5.QtNetwork import QNetworkRequest, QNetworkAccessManager, QNetworkReply
import os
import time
import threading
import requests as rq
from GetBilibiliApi import GetVideoInfo
import ffmpeg
import subprocess
import logging
import sys
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BilibiliPlayer")

class CustomNetworkAccessManager(QNetworkAccessManager):
    """自定义网络访问管理器，添加必要的HTTP头部"""
    def __init__(self, cookies, headers, parent=None):
        super().__init__(parent)
        self.cookies = cookies
        self.headers = headers
    
    def createRequest(self, op, request, outgoingData=None):
        # 添加自定义头部
        for key, value in self.headers.items():
            request.setRawHeader(key.encode(), value.encode())
        
        # 添加Cookie
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        if cookie_str:
            request.setRawHeader(b"Cookie", cookie_str.encode())
        
        return super().createRequest(op, request, outgoingData)

class FFmpegProxyServer(threading.Thread):
    """FFmpeg代理服务器，合并视频/音频流"""
    def __init__(self, video_url, audio_url, cookies, headers):
        super().__init__()
        self.video_url = video_url
        self.audio_url = audio_url
        self.cookies = cookies
        self.headers = headers
        self.port = 0
        self.server = None
        self.process = None
        self.ready = threading.Event()
        self.output_url = ""
        
    def run(self):
        # 创建临时文件作为输出
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            output_file = temp_file.name
        
        try:
            # 设置FFmpeg输入参数
            input_video = ffmpeg.input(self.video_url, headers=self._format_headers())
            input_audio = ffmpeg.input(self.audio_url, headers=self._format_headers())
            
            # 配置FFmpeg输出参数
            (
                ffmpeg
                .output(input_video, input_audio, output_file, 
                        vcodec='copy', acodec='copy', 
                        movflags='frag_keyframe+empty_moov+faststart')
                .overwrite_output()
                .run_async(pipe_stdout=True, pipe_stderr=True)
            )
            
            # 等待FFmpeg生成足够的数据
            while not os.path.exists(output_file) or os.path.getsize(output_file) < 1024 * 1024:
                time.sleep(0.5)
            
            # 启动HTTP服务器
            self.port = self._find_available_port()
            self.output_url = f"http://127.0.0.1:{self.port}/video.mp4"
            
            # 启动HTTP服务器
            self.server = HTTPServer(('127.0.0.1', self.port), self._make_handler(output_file))
            self.ready.set()
            logger.info(f"FFmpeg代理服务器启动: {self.output_url}")
            
            # 在单独的线程中运行服务器
            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # 监控FFmpeg进程
            while True:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"FFmpeg代理服务器错误: {str(e)}")
            self.ready.set()  # 确保不会死锁
    
    def _format_headers(self):
        """格式化FFmpeg可用的headers字符串"""
        headers = []
        for key, value in self.headers.items():
            headers.append(f"{key}: {value}")
        return "\r\n".join(headers)
    
    def _find_available_port(self):
        """查找可用端口"""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port
    
    def _make_handler(self, file_path):
        """创建HTTP请求处理程序"""
        class VideoHandler(BaseHTTPRequestHandler):
            def do_GET(inner_self):
                if inner_self.path == "/video.mp4":
                    inner_self.send_response(200)
                    inner_self.send_header('Content-type', 'video/mp4')
                    inner_self.end_headers()
                    
                    # 流式传输文件
                    with open(file_path, 'rb') as f:
                        while True:
                            data = f.read(1024 * 1024)  # 1MB chunks
                            if not data:
                                break
                            inner_self.wfile.write(data)
                else:
                    inner_self.send_response(404)
                    inner_self.end_headers()
        
        return VideoHandler
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
        if self.process:
            self.process.terminate()

class VideoPlayer(QWidget):
    """Bilibili视频播放器（流媒体版本）"""
    def __init__(self, parent=None, bvid=None, cid=None):
        super().__init__(parent)
        self.bvid = bvid
        self.cid = cid
        self.media_player = None
        self.timer = None
        self.proxy_server = None
        self.is_fullscreen = False
        self.last_mouse_move_time = 0
        self.api_duration = 0  # 存储从API获取的时长（毫秒）
        
        # 加载Cookie
        self.cookies = self.load_cookies()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }
        
        # 设置自定义网络访问管理器
        self.network_manager = CustomNetworkAccessManager(self.cookies, self.headers)
        
        self.setup_ui()
        self.start_stream_loading()
    
    def load_cookies(self):
        """从文件加载Cookie"""
        cookies = {}
        if os.path.exists("Cookie"):
            with open("Cookie", "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        cookies[parts[5]] = parts[6]
        return cookies
    
    def start_stream_loading(self):
        """开始流媒体加载过程"""
        try:
            # 获取视频流信息
            video_info = GetVideoInfo(self.bvid, self.cid)
            video_url, audio_url = video_info.get_video_streaming_info()
            
            # 获取API返回的视频时长（秒）并转换为毫秒
            self.api_duration = video_info.get_video_duration() * 1000
            
            # 启动FFmpeg代理服务器
            self.proxy_server = FFmpegProxyServer(video_url, audio_url, self.cookies, self.headers)
            self.proxy_server.start()
            
            # 等待服务器准备就绪
            self.status_label.setText("正在初始化流媒体服务器...")
            self.proxy_server.ready.wait(timeout=30)
            
            if not self.proxy_server.output_url:
                raise Exception("流媒体服务器启动失败")
            
            # 设置媒体播放器
            self.setup_media_player(self.proxy_server.output_url)
            self.status_label.setText("准备播放")
            
        except Exception as e:
            self.status_label.setText("初始化失败")
            QMessageBox.critical(self, "错误", f"无法初始化播放器:\n{str(e)}")
            logger.exception("播放器初始化失败")

    def setup_ui(self):
        """设置用户界面"""
        # 主水平布局（侧边栏 + 内容区域）
        main_layout = QHBoxLayout()
        self.setup_content_area(main_layout)
        self.setup_recommendation_list(main_layout)
        self.setLayout(main_layout)
        
        # 设置窗口属性
        self.setWindowTitle(f"视频播放器 - {self.bvid}")
        self.setMinimumSize(800, 500)
        
        # 应用深色主题
        self.apply_dark_theme()

    def apply_dark_theme(self):
        """应用深色主题样式"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(65, 65, 65))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Highlight, QColor(0, 161, 214))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(dark_palette)
        
        # 额外的样式表
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #505050;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin: -4px 0;
                background: #FFFFFF;
                border-radius: 7px;
            }
            QSlider::sub-page:horizontal {
                background: #00A1D6;
                border-radius: 3px;
            }
            QPushButton {
                background: transparent;
                border: none;
                padding: 8px;
            }
            QPushButton:hover {
                background: #404040;
            }
            QLabel {
                color: #FFFFFF;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 3px;
                background: #333;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #00A1D6;
                width: 10px;
            }
        """)

    def create_nav_button(self, icon_path, tooltip, callback=None):
        """创建导航按钮"""
        btn = QPushButton()
        btn.setIcon(QIcon(icon_path))
        btn.setIconSize(QSize(24, 24))
        btn.setToolTip(tooltip)
        if callback:
            btn.clicked.connect(callback)
        return btn

    def setup_content_area(self, main_layout):
        """设置内容区域（视频播放器 + 控制栏）"""
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 视频播放区域
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 360)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.setStyleSheet("background-color: black;")
        content_layout.addWidget(self.video_widget)
        
        # 状态标签（加载状态）
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: #1A1A1A; padding: 5px;")
        content_layout.addWidget(self.status_label)
        
        # 缓冲进度条
        self.buffer_progress = QProgressBar()
        self.buffer_progress.setRange(0, 100)
        self.buffer_progress.setValue(0)
        self.buffer_progress.setTextVisible(True)
        self.buffer_progress.setFormat("缓冲中: %p%")
        content_layout.addWidget(self.buffer_progress)
        
        # 添加控制栏
        self.setup_control_bar(content_layout)
        
        main_layout.addLayout(content_layout, stretch=3)

    def setup_control_bar(self, parent_layout):
        """设置播放控制栏"""
        control_bar = QWidget()
        control_layout = QHBoxLayout()
        control_bar.setLayout(control_layout)
        control_bar.setObjectName("control_bar")  # 用于全屏时隐藏/显示
        
        # 播放/暂停按钮
        self.play_btn = self.create_nav_button("./img/play.png", "播放/暂停", self.toggle_playback)
        
        # 时间标签
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(120)
        self.time_label.setFont(QFont("Arial", 9))
        
        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_position)
        
        # 音量控制
        self.volume_btn = self.create_nav_button("./img/volume.png", "音量", self.toggle_mute)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        # 全屏按钮
        self.fullscreen_btn = self.create_nav_button("./img/fullscreen.png", "全屏", self.toggle_fullscreen)
        
        # 布局控制
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.time_label)
        control_layout.addWidget(self.progress_slider)
        control_layout.addWidget(self.volume_btn)
        control_layout.addWidget(self.volume_slider)
        control_layout.addWidget(self.fullscreen_btn)
        
        parent_layout.addWidget(control_bar)

    def setup_recommendation_list(self, main_layout):
        """设置右侧推荐列表"""
        scroll_area = QScrollArea()
        scroll_area.setFixedWidth(240)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #252525;")
        
        # 推荐列表容器
        self.recommend_list = QWidget()
        self.recommend_layout = QVBoxLayout()
        self.recommend_layout.setContentsMargins(5, 5, 5, 5)
        self.recommend_layout.setSpacing(10)
        
        # 添加推荐标题
        title = QLabel("推荐视频")
        title.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        self.recommend_layout.addWidget(title)
        
        # 添加一些示例推荐项
        for i in range(5):
            item = QPushButton(f"推荐视频 {i+1}")
            item.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px;
                    background: #353535;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: #454545;
                }
            """)
            self.recommend_layout.addWidget(item)
        
        # 添加弹性空间
        self.recommend_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        self.recommend_list.setLayout(self.recommend_layout)
        scroll_area.setWidget(self.recommend_list)
        
        main_layout.addWidget(scroll_area)

    def setup_media_player(self, stream_url):
        """设置媒体播放器"""
        self.media_player = QMediaPlayer()
        self.media_player.setVideoOutput(self.video_widget)
        
        # 创建媒体内容
        media_content = QMediaContent(QUrl(stream_url))
        self.media_player.setMedia(media_content)
        
        # 连接信号
        self.media_player.positionChanged.connect(self.update_time_display)
        self.media_player.durationChanged.connect(self.update_duration_display)
        self.media_player.volumeChanged.connect(self.update_volume_display)
        self.media_player.bufferStatusChanged.connect(self.update_buffer_status)
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)
        
        # 设置初始音量
        self.media_player.setVolume(self.volume_slider.value())
        
        # 设置进度更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)  # 100ms更新一次
        
        # 开始播放
        self.media_player.play()

    def update_buffer_status(self, percent_filled):
        """更新缓冲状态"""
        self.buffer_progress.setValue(percent_filled)
        
        # 根据缓冲状态更新UI
        if percent_filled < 100:
            self.status_label.setText(f"缓冲中: {percent_filled}%")
        else:
            self.status_label.setText("播放中")

    def handle_media_status(self, status):
        """处理媒体状态变化"""
        status_text = {
            QMediaPlayer.NoMedia: "无媒体",
            QMediaPlayer.LoadingMedia: "加载中...",
            QMediaPlayer.LoadedMedia: "已加载",
            QMediaPlayer.StalledMedia: "缓冲中...",
            QMediaPlayer.BufferingMedia: "缓冲中...",
            QMediaPlayer.BufferedMedia: "已缓冲",
            QMediaPlayer.EndOfMedia: "播放结束",
            QMediaPlayer.InvalidMedia: "无效媒体"
        }.get(status, f"未知状态: {status}")
        
        self.status_label.setText(status_text)

    def toggle_playback(self):
        """切换播放/暂停状态"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setIcon(QIcon("./img/play.png"))
            self.status_label.setText("已暂停")
        else:
            self.media_player.play()
            self.play_btn.setIcon(QIcon("./img/pause.png"))
            self.status_label.setText("播放中")
            # 鼠标移动时显示控制栏
            self.last_mouse_move_time = time.time()

    def update_progress(self):
        """更新播放进度 - 使用API返回的时长"""
        # 使用API返回的时长而不是播放器的时长
        if not self.media_player or self.api_duration <= 0:
            return
            
        position = self.media_player.position()
        progress = int((position / self.api_duration) * 100)
        
        # 只有当用户没有拖动滑块时才更新
        if not self.progress_slider.isSliderDown():
            try:
                self.progress_slider.setValue(progress)
            except RuntimeError:
                pass
            
        # 自动隐藏控制栏（全屏时）
        if self.is_fullscreen and time.time() - self.last_mouse_move_time > 3:
            self.findChild(QWidget, "control_bar").hide()

    def update_time_display(self, position):
        """更新时间显示 - 使用API返回的时长"""
        self.time_label.setText(
            f"{self.format_time(position)} / {self.format_time(self.api_duration)}"
        )

    def update_duration_display(self, duration):
        """更新持续时间显示 - 使用API返回的时长"""
        # 使用API时长而不是播放器返回的时长
        self.progress_slider.setEnabled(self.api_duration > 0)

    def update_volume_display(self, volume):
        """更新音量显示"""
        # 更新音量按钮图标
        if volume == 0:
            self.volume_btn.setIcon(QIcon("./img/mute.png"))
        else:
            self.volume_btn.setIcon(QIcon("./img/volume.png"))
        
        # 更新音量滑块位置
        self.volume_slider.setValue(volume)

    def format_time(self, ms):
        """将毫秒转换为 mm:ss 格式"""
        seconds = ms // 1000
        minutes = seconds // 60
        seconds %= 60
        return f"{minutes:02d}:{seconds:02d}"

    def set_position(self, position):
        """设置播放位置 - 使用API返回的时长"""
        if self.media_player and self.api_duration > 0:
            # 添加有效性检查
            if not hasattr(self, 'is_seeking'):
                self.is_seeking = False
                
            if not self.is_seeking:
                self.is_seeking = True
                target_position = position * self.api_duration // 100
                
                # 添加范围限制
                target_position = max(0, min(self.api_duration, target_position))
                
                try:
                    # 添加阻塞信号防止重复触发
                    self.progress_slider.blockSignals(True)
                    self.media_player.setPosition(target_position)
                except RuntimeError as e:
                    print(f"Seek error: {str(e)}")
                finally:
                    self.progress_slider.blockSignals(False)
                    self.is_seeking = False

    def set_volume(self, volume):
        """设置音量"""
        if self.media_player:
            self.media_player.setVolume(volume)

    def toggle_mute(self):
        """切换静音状态"""
        if self.media_player:
            self.media_player.setMuted(not self.media_player.isMuted())

    def toggle_fullscreen(self):
        """切换全屏状态"""
        if self.is_fullscreen:
            self.showNormal()
            self.recommend_list.parent().show()  # 显示推荐列表
        else:
            self.showFullScreen()
            self.recommend_list.parent().hide()  # 隐藏推荐列表
            
        self.is_fullscreen = not self.is_fullscreen
        self.last_mouse_move_time = time.time()

    def mouseMoveEvent(self, event):
        """鼠标移动时显示控制栏"""
        super().mouseMoveEvent(event)
        self.last_mouse_move_time = time.time()
        if self.is_fullscreen:
            self.findChild(QWidget, "control_bar").show()

    def keyPressEvent(self, event):
        """键盘快捷键"""
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == Qt.Key_Left:
            self.jump_backward()
        elif event.key() == Qt.Key_Right:
            self.jump_forward()
        elif event.key() == Qt.Key_Escape and self.is_fullscreen:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_F:
            self.toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def jump_backward(self):
        """向后跳转5秒"""
        if self.media_player and self.api_duration > 0:
            current_pos = self.media_player.position()
            self.media_player.setPosition(max(0, current_pos - 5000))

    def jump_forward(self):
        """向前跳转5秒"""
        if self.media_player and self.api_duration > 0:
            current_pos = self.media_player.position()
            self.media_player.setPosition(min(self.api_duration, current_pos + 5000))

    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止代理服务器
        if self.proxy_server:
            self.proxy_server.stop()
            
        # 停止定时器
        if self.timer and self.timer.isActive():
            self.timer.stop()
            
        # 清理媒体播放器
        if self.media_player:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            self.media_player.deleteLater()
            self.media_player = None
        
        # 关闭ffmpeg服务器
        


            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    video_player = VideoPlayer(bvid="BV1zNt8zzEZX", cid="31583111084")
    video_player.show()
    sys.exit(app.exec_())