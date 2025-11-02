from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QSlider, QLabel, QSizePolicy, QMessageBox, QApplication,
                            QFrame, QGraphicsDropShadowEffect)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize, pyqtSignal, QProcess
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor, QPainter, QPainterPath
import os
import time
import logging
import sys
import subprocess
from NetworkManager import CustomNetworkAccessManager
from ProxyServer import MP4ProxyServer
from GetBilibiliApi import GetVideoInfo

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BilibiliPlayer")

class FullScreenVideoPlayer(QWidget):
    """独立的顶级全屏播放器"""
    closed = pyqtSignal()  # 添加关闭信号
    
    def __init__(self, video_widget, media_player, parent=None):
        super().__init__(parent)
        self.video_widget = video_widget
        self.media_player = media_player
        self.original_parent = video_widget.parent()
        self.original_layout = self.original_parent.layout() if self.original_parent else None
        
        self.setup_ui()
        
    def setup_ui(self):
        """设置全屏界面"""
        self.setWindowTitle("全屏播放")
        
        # 在 Wayland 环境下使用不同的窗口标志
        if "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower():
            # Wayland 环境
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        else:
            # X11 环境
            self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # 获取屏幕尺寸并设置全屏
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        self.setGeometry(screen_geometry)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 将视频控件移动到全屏窗口
        self.video_widget.setParent(self)
        layout.addWidget(self.video_widget)
        
        # 全屏控制栏
        self.control_container = QFrame()
        self.control_container.setObjectName("control_container")
        self.control_container.setStyleSheet("""
            #control_container {
                background: rgba(45, 45, 45, 220);
                border-top: 1px solid rgba(255, 255, 255, 100);
                padding: 15px;
            }
        """)
        
        control_layout = QVBoxLayout(self.control_container)
        control_layout.setContentsMargins(20, 10, 20, 10)
        control_layout.setSpacing(10)
        
        self.setup_fullscreen_controls(control_layout)
        layout.addWidget(self.control_container)
        
        # 初始隐藏控制栏
        self.control_container.hide()
        self.control_bar_visible = False
        
        # 鼠标移动计时器
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self.hide_controls)
        self.mouse_timer.start(100)
        
        self.last_mouse_move = time.time()
        
    def setup_fullscreen_controls(self, layout):
        """设置全屏控制栏"""
        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: rgba(255, 255, 255, 100);
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 20px;
                height: 20px;
                margin: -6px 0;
                background: rgba(255, 255, 255, 200);
                border: 2px solid rgba(255, 255, 255, 150);
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(100, 150, 255, 200);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_slider)
        
        # 控制按钮
        control_buttons = QHBoxLayout()
        
        # 播放/暂停
        self.play_btn = QPushButton()
        self.play_btn.setIcon(QIcon("./img/pause.png"))
        self.play_btn.setIconSize(QSize(24, 24))
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 180);
            }
        """)
        self.play_btn.clicked.connect(self.toggle_playback)
        
        # 时间显示
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        self.time_label.setFixedWidth(120)
        
        # 音量
        self.volume_btn = QPushButton()
        self.volume_btn.setIcon(QIcon("./img/volume.png"))
        self.volume_btn.setIconSize(QSize(24, 24))
        self.volume_btn.setFixedSize(40, 40)
        self.volume_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 180);
            }
        """)
        self.volume_btn.clicked.connect(self.toggle_mute)
        
        # 退出全屏
        self.exit_btn = QPushButton()
        self.exit_btn.setIcon(QIcon("./img/fullscreen_exit.png"))
        self.exit_btn.setIconSize(QSize(24, 24))
        self.exit_btn.setFixedSize(40, 40)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 180);
            }
        """)
        self.exit_btn.clicked.connect(self.exit_fullscreen)
        
        control_buttons.addWidget(self.play_btn)
        control_buttons.addWidget(self.time_label)
        control_buttons.addStretch()
        control_buttons.addWidget(self.volume_btn)
        control_buttons.addWidget(self.exit_btn)
        
        layout.addLayout(control_buttons)
    
    def toggle_playback(self):
        """切换播放状态"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
            self.play_btn.setIcon(QIcon("./img/play.png"))
        else:
            self.media_player.play()
            self.play_btn.setIcon(QIcon("./img/pause.png"))
    
    def toggle_mute(self):
        """切换静音"""
        self.media_player.setMuted(not self.media_player.isMuted())
        if self.media_player.isMuted():
            self.volume_btn.setIcon(QIcon("./img/mute.png"))
        else:
            self.volume_btn.setIcon(QIcon("./img/volume.png"))
    
    def exit_fullscreen(self):
        """退出全屏"""
        # 发射关闭信号，让父窗口处理
        self.closed.emit()
    
    def mouseMoveEvent(self, event):
        """鼠标移动显示控制栏"""
        self.last_mouse_move = time.time()
        if not self.control_bar_visible:
            self.control_container.show()
            self.control_bar_visible = True
    
    def hide_controls(self):
        """隐藏控制栏"""
        if time.time() - self.last_mouse_move > 3 and self.control_bar_visible:
            self.control_container.hide()
            self.control_bar_visible = False
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Escape or event.key() == Qt.Key_F:
            self.exit_fullscreen()
        elif event.key() == Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == Qt.Key_Left:
            self.jump_backward()
        elif event.key() == Qt.Key_Right:
            self.jump_forward()
        else:
            super().keyPressEvent(event)
    
    def jump_backward(self):
        """后退5秒"""
        current_pos = self.media_player.position()
        self.media_player.setPosition(max(0, current_pos - 5000))
    
    def jump_forward(self):
        """前进5秒"""
        current_pos = self.media_player.position()
        duration = self.media_player.duration()
        self.media_player.setPosition(min(duration, current_pos + 5000))
    
    def closeEvent(self, event):
        """关闭事件 - 确保资源正确清理"""
        # 停止计时器
        if hasattr(self, 'mouse_timer') and self.mouse_timer.isActive():
            self.mouse_timer.stop()
        
        # 发射关闭信号
        self.closed.emit()
        event.accept()

class GlassButton(QPushButton):
    """玻璃效果按钮"""
    def __init__(self, icon_path=None, text="", parent=None):
        super().__init__(text, parent)
        self.setFixedSize(40, 40)
        if icon_path and os.path.exists(icon_path):
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))
        
        self.setStyleSheet("""
            GlassButton {
                background-color: rgba(255, 255, 255, 120);
                border: 1px solid rgba(255, 255, 255, 80);
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            GlassButton:hover {
                background-color: rgba(255, 255, 255, 180);
                border: 1px solid rgba(255, 255, 255, 120);
            }
            GlassButton:pressed {
                background-color: rgba(255, 255, 255, 100);
            }
        """)

class GlassSlider(QSlider):
    """玻璃效果滑块"""
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 80);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: rgba(255, 255, 255, 200);
                border: 1px solid rgba(255, 255, 255, 150);
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: rgba(100, 150, 255, 180);
                border-radius: 3px;
            }
        """)

class GlassLabel(QLabel):
    """玻璃效果标签"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet("""
            GlassLabel {
                background-color: rgba(255, 255, 255, 80);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 8px;
                padding: 4px 8px;
                color: white;
                font-weight: bold;
            }
        """)

class VideoPlayer(QWidget):
    """Bilibili视频播放器（修复Waybar恢复问题）"""
    def __init__(self, parent=None, bvid=None, cid=None):
        super().__init__(parent)
        self.bvid = bvid
        self.cid = cid
        self.media_player = None
        self.timer = None
        self.proxy_server = None
        self.is_fullscreen = False
        self.last_mouse_move_time = 0
        self.api_duration = 0
        self.control_bar_visible = True
        self.dragging = False
        self.drag_position = None
        self.fullscreen_window = None
        
        # 检测是否在Wayland环境下
        self.is_wayland = "wayland" in os.environ.get("XDG_SESSION_TYPE", "").lower()
        print(f"Running in Wayland: {self.is_wayland}")
        
        # Waybar 控制
        self.waybar_was_running = False
        self.original_gaps_out = None
        self.original_rounding = None
        
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
        """开始MP4流媒体加载过程"""
        try:
            # 获取视频流信息 - 使用MP4格式
            video_info = GetVideoInfo(self.bvid, self.cid)
            mp4_url = video_info.get_video_streaming_info_mp4()
            
            # 获取API返回的视频时长（秒）并转换为毫秒
            self.api_duration = video_info.get_video_duration() * 1000
            
            # 启动MP4代理服务器
            self.proxy_server = MP4ProxyServer(mp4_url, self.cookies, self.headers)
            self.proxy_server.start()
            
            # 等待服务器准备就绪
            self.proxy_server.ready.wait(timeout=30)
            
            if not self.proxy_server.output_url:
                raise Exception("MP4流媒体服务器启动失败")
            
            # 设置媒体播放器
            self.setup_media_player(self.proxy_server.output_url)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法初始化播放器:\n{str(e)}")
            logger.exception("播放器初始化失败")

    def setup_ui(self):
        """设置用户界面"""
        # 设置窗口属性
        self.setWindowTitle(f"视频播放器 - {self.bvid}")
        self.setMinimumSize(800, 500)
        
        # 应用亚克力玻璃风格
        self.apply_acrylic_style()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建视频容器
        self.video_container = QFrame()
        self.video_container.setObjectName("videoContainer")
        self.video_container.setStyleSheet("""
            #videoContainer {
                background-color: black;
                border-radius: 8px;
                margin: 10px;
            }
        """)
        
        video_container_layout = QVBoxLayout(self.video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        video_container_layout.setSpacing(0)
        
        # 视频播放区域
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(640, 360)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_container_layout.addWidget(self.video_widget)
        
        main_layout.addWidget(self.video_container)
        
        # 控制栏容器
        self.control_container = QFrame()
        self.control_container.setObjectName("control_container")
        self.control_container.setStyleSheet("""
            #control_container {
                background: rgba(45, 45, 45, 180);
                border-top: 1px solid rgba(255, 255, 255, 60);
                border-radius: 0 0 12px 12px;
                padding: 10px;
            }
        """)
        
        control_layout = QVBoxLayout(self.control_container)
        control_layout.setContentsMargins(15, 10, 15, 10)
        control_layout.setSpacing(10)
        
        # 添加控制栏
        self.setup_control_bar(control_layout)
        
        main_layout.addWidget(self.control_container)
        
        self.setLayout(main_layout)

    def apply_acrylic_style(self):
        """应用亚克力玻璃风格"""
        # 设置窗口为无边框和半透明
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 应用样式表
        self.setStyleSheet("""
            VideoPlayer {
                background: rgba(30, 30, 30, 180);
                border: 1px solid rgba(255, 255, 255, 60);
                border-radius: 12px;
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def setup_control_bar(self, parent_layout):
        """设置播放控制栏"""
        # 进度条
        self.progress_slider = GlassSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_position)
        parent_layout.addWidget(self.progress_slider)
        
        # 控制按钮栏
        control_bar_layout = QHBoxLayout()
        control_bar_layout.setSpacing(10)
        
        # 播放/暂停按钮
        self.play_btn = GlassButton("./img/play.png")
        self.play_btn.clicked.connect(self.toggle_playback)
        
        # 时间标签
        self.time_label = GlassLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(120)
        self.time_label.setAlignment(Qt.AlignCenter)
        
        # 音量控制
        self.volume_btn = GlassButton("./img/volume.png")
        self.volume_btn.clicked.connect(self.toggle_mute)
        
        self.volume_slider = GlassSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.valueChanged.connect(self.set_volume)
        
        # 全屏按钮
        self.fullscreen_btn = GlassButton("./img/fullscreen.png")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
        # 关闭按钮
        self.close_btn = GlassButton("./img/x3.png")
        self.close_btn.clicked.connect(self.close)
        
        # 布局控制
        control_bar_layout.addWidget(self.play_btn)
        control_bar_layout.addWidget(self.time_label)
        control_bar_layout.addStretch()
        control_bar_layout.addWidget(self.volume_btn)
        control_bar_layout.addWidget(self.volume_slider)
        control_bar_layout.addWidget(self.fullscreen_btn)
        control_bar_layout.addWidget(self.close_btn)
        
        parent_layout.addLayout(control_bar_layout)

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
        self.media_player.stateChanged.connect(self.on_playback_state_changed)
        
        # 设置初始音量
        self.media_player.setVolume(self.volume_slider.value())
        
        # 设置进度更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(100)  # 100ms更新一次
        
        # 开始播放
        self.media_player.play()

    def on_playback_state_changed(self, state):
        """播放状态改变时的处理"""
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(QIcon("./img/pause.png"))
        else:
            self.play_btn.setIcon(QIcon("./img/play.png"))

    def toggle_playback(self):
        """切换播放/暂停状态"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
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
        if volume == 0 or self.media_player.isMuted():
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
        """切换全屏状态 - 修复版本"""
        if self.is_fullscreen:
            # 如果已经全屏，则退出全屏
            self.exit_fullscreen()
        else:
            # 进入全屏
            self.enter_fullscreen()
    
    def enter_fullscreen(self):
        """进入全屏"""
        try:
            # 保存当前的 Hyprland 设置
            if self.is_wayland:
                self.save_hyprland_settings()
            
            self.fullscreen_window = FullScreenVideoPlayer(self.video_widget, self.media_player, self)
            # 连接关闭信号
            self.fullscreen_window.closed.connect(self.exit_fullscreen)
            self.fullscreen_window.show()
            self.is_fullscreen = True
            self.fullscreen_btn.setIcon(QIcon("./img/fullscreen_exit.png"))
            
            # 在 Wayland 环境下隐藏 Waybar
            if self.is_wayland:
                self.hide_waybar()
                
        except Exception as e:
            print(f"进入全屏失败: {e}")
            # 如果全屏失败，确保状态正确
            self.is_fullscreen = False
            self.fullscreen_btn.setIcon(QIcon("./img/fullscreen.png"))
    
    def exit_fullscreen(self):
        """退出全屏"""
        try:
            if self.fullscreen_window:
                # 断开信号连接，避免重复调用
                try:
                    self.fullscreen_window.closed.disconnect()
                except:
                    pass
                
                # 将视频控件移回原窗口
                try:
                    self.video_widget.setParent(self)
                    self.video_container.layout().addWidget(self.video_widget)
                except Exception as e:
                    print(f"恢复视频控件失败: {e}")
                
                # 关闭全屏窗口
                try:
                    self.fullscreen_window.close()
                    self.fullscreen_window.deleteLater()
                except Exception as e:
                    print(f"关闭全屏窗口失败: {e}")
                
                self.fullscreen_window = None
            
            self.is_fullscreen = False
            self.fullscreen_btn.setIcon(QIcon("./img/fullscreen.png"))
            
            # 在 Wayland 环境下恢复 Waybar
            if self.is_wayland:
                self.restore_waybar()
                
        except Exception as e:
            print(f"退出全屏失败: {e}")
            # 强制重置状态
            self.is_fullscreen = False
            self.fullscreen_window = None
            self.fullscreen_btn.setIcon(QIcon("./img/fullscreen.png"))

    def save_hyprland_settings(self):
        """保存当前的 Hyprland 设置"""
        try:
            # 获取当前的 gaps_out 设置
            result = subprocess.run(
                ["hyprctl", "getoption", "general:gaps_out"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "int:" in line:
                        self.original_gaps_out = int(line.split(":")[1].strip())
                        break
            
            # 获取当前的 rounding 设置
            result = subprocess.run(
                ["hyprctl", "getoption", "decoration:rounding"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "int:" in line:
                        self.original_rounding = int(line.split(":")[1].strip())
                        break
            
            print(f"保存的 Hyprland 设置: gaps_out={self.original_gaps_out}, rounding={self.original_rounding}")
            
        except Exception as e:
            print(f"保存 Hyprland 设置失败: {e}")
            # 设置默认值
            self.original_gaps_out = 10
            self.original_rounding = 10

    def hide_waybar(self):
        """隐藏 Waybar - 改进版本"""
        try:
            print("开始隐藏 Waybar...")
            
            # 检查 Waybar 是否在运行
            waybar_running = subprocess.run(["pgrep", "waybar"], capture_output=True).returncode == 0
            self.waybar_was_running = waybar_running
            
            if waybar_running:
                # 方法1: 优雅地停止 Waybar
                print("Waybar 正在运行，尝试停止...")
                subprocess.run(["pkill", "-SIGTERM", "waybar"], timeout=5)
                time.sleep(1)  # 等待 Waybar 停止
                
                # 检查是否真的停止了
                waybar_still_running = subprocess.run(["pgrep", "waybar"], capture_output=True).returncode == 0
                if waybar_still_running:
                    print("Waybar 仍在运行，强制停止...")
                    subprocess.run(["pkill", "-SIGKILL", "waybar"])
            
            # 方法2: 调整 Hyprland 设置
            if self.original_gaps_out is not None:
                subprocess.run(["hyprctl", "keyword", "general:gaps_out", "0"])
            
            if self.original_rounding is not None:
                subprocess.run(["hyprctl", "keyword", "decoration:rounding", "0"])
            
            print("Waybar 隐藏完成")
            
        except Exception as e:
            print(f"隐藏 Waybar 失败: {e}")

    def restore_waybar(self):
        """恢复 Waybar - 改进版本"""
        try:
            print("开始恢复 Waybar...")
            
            # 恢复 Hyprland 设置
            if self.original_gaps_out is not None:
                subprocess.run(["hyprctl", "keyword", "general:gaps_out", str(self.original_gaps_out)])
                print(f"恢复 gaps_out: {self.original_gaps_out}")
            
            if self.original_rounding is not None:
                subprocess.run(["hyprctl", "keyword", "decoration:rounding", str(self.original_rounding)])
                print(f"恢复 rounding: {self.original_rounding}")
            
            # 如果 Waybar 原本在运行，重新启动它
            if self.waybar_was_running:
                print("重新启动 Waybar...")
                
                # 使用 subprocess 启动 Waybar
                subprocess.Popen(["waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # 等待 Waybar 启动
                time.sleep(2)
                
                # 检查 Waybar 是否成功启动
                waybar_running = subprocess.run(["pgrep", "waybar"], capture_output=True).returncode == 0
                if waybar_running:
                    print("Waybar 恢复成功")
                else:
                    print("警告: Waybar 可能没有成功启动")
            else:
                print("Waybar 原本没有运行，不需要重启")
            
        except Exception as e:
            print(f"恢复 Waybar 失败: {e}")

    def mouseMoveEvent(self, event):
        """鼠标移动时显示控制栏"""
        super().mouseMoveEvent(event)
        self.last_mouse_move_time = time.time()

    def mouseDoubleClickEvent(self, event):
        """双击切换全屏"""
        self.toggle_fullscreen()

    def keyPressEvent(self, event):
        """键盘快捷键"""
        if event.key() == Qt.Key_Space:
            self.toggle_playback()
        elif event.key() == Qt.Key_Left:
            self.jump_backward()
        elif event.key() == Qt.Key_Right:
            self.jump_forward()
        elif event.key() == Qt.Key_Escape and self.is_fullscreen:
            self.exit_fullscreen()
        elif event.key() == Qt.Key_F:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_M:
            self.toggle_mute()
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

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于窗口拖动"""
        if event.button() == Qt.LeftButton and not self.is_fullscreen:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于窗口拖动"""
        if self.dragging and self.drag_position is not None and not self.is_fullscreen:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        # 确保视频控件适应窗口大小
        if self.is_fullscreen:
            # 全屏时让视频填满整个窗口
            self.video_container.setStyleSheet("background-color: black; margin: 0px; border-radius: 0px;")
        else:
            # 非全屏时恢复样式
            self.video_container.setStyleSheet("""
                #videoContainer {
                    background-color: black;
                    border-radius: 8px;
                    margin: 10px;
                }
            """)

    def closeEvent(self, event):
        """关闭事件处理"""
        print("关闭视频播放器")
        # 如果全屏窗口存在，先退出全屏
        if self.is_fullscreen and self.fullscreen_window:
            self.exit_fullscreen()
            
        # 确保 Waybar 被恢复
        if self.is_wayland:
            self.restore_waybar()
            
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
        
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    video_player = VideoPlayer(bvid="BV1zNt8zzEZX", cid="31583111084")
    video_player.show()
    sys.exit(app.exec_())