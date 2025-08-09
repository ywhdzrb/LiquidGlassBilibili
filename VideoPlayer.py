from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QScrollArea, QSlider, QLabel, QSizePolicy, QSpacerItem,
                            QMessageBox, QProgressBar, QApplication)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl, Qt, QTimer, QSize
from PyQt5.QtGui import QIcon, QFont, QPalette, QColor
import os
import time
import threading
import requests as rq
from GetBilibiliApi import GetVideoInfo
import subprocess
import logging
import sys
import tempfile
import socketserver
import http.server
import queue
import socket
import re
import json
import urllib.parse

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='./temp/bilibili_player.log',
    filemode='w'
)
logger = logging.getLogger("VideoPlayer")

class StreamingHTTPHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, file_queue, *args, **kwargs):
        self.file_queue = file_queue
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """禁用默认日志"""
        pass
    
    def check_connection(self):
        """检查客户端连接是否仍然有效"""
        try:
            # 尝试发送一个空数据包检测连接
            self.wfile.write(b'')
            return True
        except (ConnectionResetError, BrokenPipeError, OSError):
            return False
    
    def do_GET(self):
        if self.path == "/video.mp4":
            try:
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.end_headers()
                
                logger.info(f"开始流传输给客户端")
                
                bytes_sent = 0
                start_time = time.time()
                
                while True:
                    # 检查连接是否仍然有效
                    if not self.check_connection():
                        logger.debug("客户端已断开连接")
                        break
                    
                    try:
                        # 从队列获取数据块
                        chunk = self.file_queue.get(timeout=1)
                        if chunk is None:  # 结束信号
                            logger.debug("收到结束信号，停止传输")
                            break
                            
                        self.wfile.write(chunk)
                        bytes_sent += len(chunk)
                        
                        # 每秒记录一次
                        if time.time() - start_time > 1:
                            logger.debug(f"已发送: {bytes_sent/1024/1024:.2f} MB")
                            start_time = time.time()
                            bytes_sent = 0
                            
                    except queue.Empty:
                        # 等待新数据
                        logger.debug("等待新数据...")
                        continue
            except (ConnectionResetError, BrokenPipeError):
                # 客户端断开连接是正常现象
                logger.debug("客户端断开连接")
            except Exception as e:
                logger.error(f"流传输错误: {str(e)}")
            finally:
                # 确保关闭连接
                try:
                    self.wfile.flush()
                except:
                    pass
                logger.info("流传输结束")
        else:
            self.send_response(404)
            self.end_headers()
            logger.warning(f"请求未知路径: {self.path}")

class FFmpegProxyServer(threading.Thread):
    """改进的FFmpeg代理服务器，使用队列传输数据"""
    def __init__(self, video_url, audio_url, cookies, headers, bvid):
        super().__init__(daemon=True)
        self.video_url = self._sanitize_url(video_url)
        self.audio_url = self._sanitize_url(audio_url)
        self.cookies = cookies
        self.headers = headers
        self.bvid = bvid
        self.port = 0
        self.server = None
        self.process = None
        self.ready = threading.Event()
        self.output_url = ""
        self.file_queue = queue.Queue(maxsize=50)  # 限制队列大小防止内存溢出
        self.stop_event = threading.Event()
        self.ffmpeg_log = []
        
    def _sanitize_url(self, url):
        """清理URL中的特殊字符"""
        # 保留必要的特殊字符，只移除非ASCII字符
        return re.sub(r'[^\x20-\x7E]+', '', url)
        
    def run(self):
        try:
            # 创建FFmpeg进程
            self.process = self._create_ffmpeg_process()
            if not self.process:
                raise Exception("无法创建FFmpeg进程")
            
            # 启动数据读取线程
            reader_thread = threading.Thread(target=self._read_ffmpeg_output)
            reader_thread.daemon = True
            reader_thread.start()
            
            # 启动HTTP服务器
            self.port = self._find_available_port()
            self.output_url = f"http://127.0.0.1:{self.port}/video.mp4"
            
            # 创建自定义服务器
            class StreamingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
                daemon_threads = True
                allow_reuse_address = True
                request_queue_size = 10  # 增加队列大小
            
            # 使用自定义处理程序
            def handler_factory(*args, **kwargs):
                return StreamingHTTPHandler(self.file_queue, *args, **kwargs)
            
            self.server = StreamingHTTPServer(
                ('127.0.0.1', self.port), 
                handler_factory
            )
            
            logger.info(f"FFmpeg代理服务器启动: {self.output_url}")
            self.ready.set()
            
            # 运行服务器
            logger.info("HTTP服务器开始运行...")
            self.server.serve_forever()
            logger.info("HTTP服务器已停止")
            
        except Exception as e:
            logger.error(f"FFmpeg代理服务器错误: {str(e)}", exc_info=True)
            self.ready.set()
        finally:
            self.stop()
    
    def _create_ffmpeg_process(self):
        """创建FFmpeg进程"""
        try:
            # 构建命令 - 添加额外的头部参数
            cmd = [
                'ffmpeg',
                '-loglevel', 'verbose',  # 更详细的日志级别
                '-user_agent', self.headers['User-Agent'],
                '-headers', self._format_headers(),
                '-i', self.video_url,
                '-i', self.audio_url,
                '-c:v', 'copy',
                '-c:a', 'copy',  # 直接复制音频流
                '-f', 'mp4',
                '-movflags', 'frag_keyframe+empty_moov+faststart',
                '-'  # 输出到stdout
            ]
            
            logger.info(f"执行FFmpeg命令: {' '.join(cmd)}")
            
            # 创建进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10*1024*1024,  # 10MB缓冲区
                text=False
            )
            
            # 启动错误监控线程
            threading.Thread(
                target=self._monitor_ffmpeg_errors, 
                args=(process,),
                daemon=True
            ).start()
            
            return process
        except Exception as e:
            logger.error(f"创建FFmpeg进程失败: {str(e)}", exc_info=True)
            return None
    
    def _monitor_ffmpeg_errors(self, process):
        """监控FFmpeg错误输出"""
        try:
            while not self.stop_event.is_set():
                line = process.stderr.readline()
                if not line:
                    # 检查进程是否意外退出
                    if process.poll() is not None:
                        logger.error(f"FFmpeg进程意外退出，返回码: {process.returncode}")
                        # 收集并记录详细的错误信息
                        error_details = "\n".join(self.ffmpeg_log)
                        logger.error(f"FFmpeg错误详情:\n{error_details}")
                        self.stop_event.set()
                    break
                    
                try:
                    decoded_line = line.decode(errors='ignore').strip()
                except UnicodeDecodeError:
                    decoded_line = str(line)
                
                # 保存日志行
                self.ffmpeg_log.append(decoded_line)
                
                # 记录重要信息
                if "error" in decoded_line.lower() or "403" in decoded_line or "404" in decoded_line:
                    logger.error(f"FFmpeg错误: {decoded_line}")
                else:
                    logger.debug(f"FFmpeg: {decoded_line}")
        except Exception as e:
            logger.error(f"FFmpeg错误监控失败: {str(e)}")
    
    def _read_ffmpeg_output(self):
        """读取FFmpeg输出并放入队列"""
        try:
            logger.info("开始读取FFmpeg输出...")
            bytes_read = 0
            start_time = time.time()
            chunk_size = 1024 * 512  # 512KB
            
            while not self.stop_event.is_set():
                # 读取数据块
                chunk = self.process.stdout.read(chunk_size)
                if not chunk:
                    logger.info("FFmpeg输出结束")
                    break
                
                bytes_read += len(chunk)
                
                # 每秒记录一次
                if time.time() - start_time > 1:
                    logger.info(f"从FFmpeg读取: {bytes_read/1024/1024:.2f} MB")
                    start_time = time.time()
                    bytes_read = 0
                
                try:
                    # 添加超时和队列满的处理
                    self.file_queue.put(chunk, timeout=1.0)
                except queue.Full:
                    logger.warning("队列已满，丢弃数据块")
                    # 可以考虑降低读取速度或跳过部分帧
                    time.sleep(0.1)
            
            # 发送结束信号
            self.file_queue.put(None)
            logger.info("FFmpeg输出读取完成")
            
        except Exception as e:
            logger.error(f"FFmpeg输出读取错误: {str(e)}", exc_info=True)
        finally:
            # 确保进程终止
            if self.process and self.process.poll() is None:
                logger.warning("FFmpeg进程仍在运行，尝试终止")
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except:
                    logger.warning("强制终止FFmpeg进程")
                    self.process.kill()
    
    def _format_headers(self):
        """格式化FFmpeg可用的headers字符串"""
        headers = []
        # 确保必要的头部存在
        essential_headers = [
            "User-Agent",
            "Referer",
            "Origin",
            "Accept",
            "Accept-Language",
            "Connection",
            "DNT",
            "Sec-Fetch-Dest",
            "Sec-Fetch-Mode",
            "Sec-Fetch-Site"
        ]
        
        for key in essential_headers:
            if key in self.headers:
                # 避免特殊字符问题
                safe_value = self.headers[key].replace('"', '\\"')
                headers.append(f"{key}: {safe_value}")
        
        # 添加Cookie
        cookie_str = "; ".join([f"{k}={v}" for k, v in self.cookies.items()])
        if cookie_str:
            headers.append(f"Cookie: {cookie_str}")
        
        headers_str = "\\r\\n".join(headers)
        logger.debug(f"FFmpeg头部: {headers_str}")
        return headers_str
    
    def _find_available_port(self):
        """查找可用端口"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        logger.info(f"找到可用端口: {port}")
        return port
    
    def stop(self):
        """停止服务器和FFmpeg进程"""
        if self.stop_event.is_set():
            return  # 避免重复停止
        
        logger.info("停止FFmpeg代理服务器...")
        self.stop_event.set()
        
        # 停止HTTP服务器
        if self.server:
            logger.info("关闭HTTP服务器...")
            try:
                self.server.shutdown()
                self.server.server_close()
                logger.info("HTTP服务器已关闭")
            except Exception as e:
                logger.error(f"关闭HTTP服务器时出错: {str(e)}")
        
        # 停止FFmpeg进程
        if self.process:
            try:
                logger.info("终止FFmpeg进程...")
                self.process.terminate()
                self.process.wait(timeout=2)
                logger.info("FFmpeg进程已终止")
            except Exception as e:
                logger.error(f"终止FFmpeg进程时出错: {str(e)}")
                try:
                    logger.warning("强制终止FFmpeg进程")
                    self.process.kill()
                except:
                    pass
        logger.info("FFmpeg代理服务器已停止")

class VideoPlayer(QWidget):
    """Bilibili视频播放器（流媒体版本）"""
    def __init__(self, parent=None, bvid=None, cid=None):
        super().__init__(parent)
        self.bvid = bvid
        self.cid = cid
        self.media_player = None
        self.timer = None
        self.network_timer = None
        self.proxy_server = None
        self.is_fullscreen = False
        self.last_mouse_move_time = 0
        self.error_count = 0
        self.max_retries = 3
        
        # 加载Cookie
        self.cookies = self.load_cookies()
        self.headers = self.create_headers()
        
        self.setup_ui()
        self.start_stream_loading()
        
        # 启动网络状态监控
        self.network_timer = QTimer()
        self.network_timer.timeout.connect(self.check_network_status)
        self.network_timer.start(5000)  # 每5秒检查一次
    
    def create_headers(self):
        """创建符合Bilibili防盗链要求的头部"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Origin": "https://www.bilibili.com",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "video",
            "Sec-Fetch-Mode": "no-cors",
            "Sec-Fetch-Site": "same-site"
        }
    
    def load_cookies(self):
        """从文件加载Cookie"""
        cookies = {}
        cookie_path = "Cookie"
        if os.path.exists(cookie_path):
            logger.info(f"从文件加载Cookie: {cookie_path}")
            try:
                with open(cookie_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            cookies[parts[5]] = parts[6]
                logger.debug(f"加载的Cookie: {cookies}")
            except Exception as e:
                logger.error(f"加载Cookie失败: {str(e)}")
        else:
            logger.warning("未找到Cookie文件")
        return cookies
    
    def start_stream_loading(self):
        """开始流媒体加载过程"""
        try:
            logger.info(f"开始加载视频: BV{self.bvid}, CID={self.cid}")
            
            # 获取视频流信息
            video_info = GetVideoInfo(self.bvid, self.cid)
            video_url, audio_url = video_info.get_video_streaming_info()
            
            # 确保URL是ASCII编码
            video_url = self.ensure_ascii_url(video_url)
            audio_url = self.ensure_ascii_url(audio_url)
            
            logger.info(f"获取到视频流: {video_url}")
            logger.info(f"获取到音频流: {audio_url}")
            
            # 启动FFmpeg代理服务器
            self.proxy_server = FFmpegProxyServer(video_url, audio_url, self.cookies, self.headers, self.bvid)
            self.proxy_server.start()
            
            # 等待服务器准备就绪
            self.status_label.setText("正在初始化流媒体服务器...")
            logger.info("等待代理服务器就绪...")
            if not self.proxy_server.ready.wait(timeout=60):
                raise Exception("代理服务器启动超时")
            
            if not self.proxy_server.output_url:
                raise Exception("流媒体服务器启动失败")
            
            logger.info(f"代理服务器就绪: {self.proxy_server.output_url}")
            
            # 设置媒体播放器
            self.setup_media_player(self.proxy_server.output_url)
            self.status_label.setText("准备播放")
            logger.info("媒体播放器初始化完成")
            
        except Exception as e:
            self.status_label.setText("初始化失败")
            logger.error(f"初始化失败: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "错误", f"无法初始化播放器:\n{str(e)}")

    def ensure_ascii_url(self, url):
        """确保URL是ASCII编码，处理特殊字符"""
        if not url:
            return url
            
        # 解析URL
        parsed = urllib.parse.urlparse(url)
        
        # 处理查询参数中的特殊字符
        query = urllib.parse.parse_qs(parsed.query)
        safe_query = {}
        for key, values in query.items():
            safe_values = [urllib.parse.quote(v, safe='') for v in values]
            safe_query[key] = safe_values
        
        # 重新构建URL
        new_query = urllib.parse.urlencode(safe_query, doseq=True)
        new_url = urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        # 移除非ASCII字符
        ascii_url = re.sub(r'[\x00-\x1F\x7F-\xFF]', '', url)
        
        logger.debug(f"原始URL: {url}")
        logger.debug(f"安全URL: {ascii_url}")
        
        return ascii_url

    def setup_ui(self):
        """设置用户界面"""
        # 主水平布局（侧边栏 + 内容区域）
        main_layout = QHBoxLayout()
        self.setup_content_area(main_layout)
        self.setup_recommendation_list(main_layout)
        self.setLayout(main_layout)
        
        # 设置窗口属性
        self.setWindowTitle(f"B站视频播放器 - {self.bvid}")
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
        logger.info(f"设置媒体播放器: {stream_url}")
        
        try:
            # 如果已有媒体播放器，先清理
            if self.media_player:
                self.cleanup_media_player()
                
            # 重置错误计数器
            self.error_count = 0
            
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
            self.media_player.error.connect(self.handle_player_error)
            
            # 设置初始音量
            self.media_player.setVolume(self.volume_slider.value())
            
            # 设置进度更新定时器
            self.timer = QTimer()
            self.timer.timeout.connect(self.update_progress)
            self.timer.start(100)  # 100ms更新一次
            
            # 开始播放
            logger.info("启动播放...")
            self.media_player.play()
            
            # 检查播放状态
            def check_play_state():
                if self.media_player.state() != QMediaPlayer.PlayingState:
                    logger.warning("播放未启动，尝试重新连接")
                    self.media_player.play()
                else:
                    logger.info("播放已启动")
            
            QTimer.singleShot(2000, check_play_state)
            
        except Exception as e:
            logger.error(f"媒体播放器设置失败: {str(e)}", exc_info=True)
            self.status_label.setText(f"播放器初始化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法设置媒体播放器:\n{str(e)}")

    def cleanup_media_player(self):
        """清理媒体播放器资源"""
        try:
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            # 断开所有信号连接
            try:
                self.media_player.positionChanged.disconnect()
                self.media_player.durationChanged.disconnect()
                self.media_player.volumeChanged.disconnect()
                self.media_player.bufferStatusChanged.disconnect()
                self.media_player.mediaStatusChanged.disconnect()
                self.media_player.error.disconnect()
            except:
                pass
            self.media_player.deleteLater()
        except:
            pass
        finally:
            self.media_player = None

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

    def handle_player_error(self, error):
        """处理播放器错误"""
        # 增加错误计数
        self.error_count += 1
        
        if self.error_count > self.max_retries:
            # 超过最大重试次数
            error_msg = "播放失败: 超过最大重试次数"
            self.status_label.setText(error_msg)
            QMessageBox.critical(self, "播放错误", error_msg)
            return
        
        # 尝试重新加载
        self.status_label.setText(f"尝试重新连接 ({self.error_count}/{self.max_retries})")
        logger.warning(f"播放错误，尝试重新连接 ({self.error_count}/{self.max_retries})")
        
        # 延迟后重新加载
        QTimer.singleShot(2000, lambda: self.setup_media_player(self.proxy_server.output_url))

    def toggle_playback(self):
        """切换播放/暂停状态"""
        if self.media_player:
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
        """更新播放进度"""
        if not self.media_player or self.media_player.duration() <= 0:
            return
            
        position = self.media_player.position()
        duration = self.media_player.duration()
        progress = int((position / duration) * 100)
        
        # 只有当用户没有拖动滑块时才更新
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(progress)
            
        # 自动隐藏控制栏（全屏时）
        if self.is_fullscreen and time.time() - self.last_mouse_move_time > 3:
            control_bar = self.findChild(QWidget, "control_bar")
            if control_bar and control_bar.isVisible():
                control_bar.hide()

    def update_time_display(self, position):
        """更新时间显示"""
        if self.media_player:
            duration = self.media_player.duration()
            self.time_label.setText(
                f"{self.format_time(position)} / {self.format_time(duration)}"
            )

    def update_duration_display(self, duration):
        """更新持续时间显示"""
        self.progress_slider.setEnabled(duration > 0)

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
        """设置播放位置"""
        if self.media_player:
            duration = self.media_player.duration()
            if duration > 0:
                self.media_player.setPosition(position * duration // 100)

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
        
        # 全屏时显示控制栏3秒后自动隐藏
        if self.is_fullscreen:
            control_bar = self.findChild(QWidget, "control_bar")
            if control_bar:
                control_bar.show()
                QTimer.singleShot(3000, lambda: 
                    control_bar.hide() if time.time() - self.last_mouse_move_time > 2.9 else None)

    def mouseMoveEvent(self, event):
        """鼠标移动时显示控制栏"""
        super().mouseMoveEvent(event)
        self.last_mouse_move_time = time.time()
        
        if self.is_fullscreen:
            control_bar = self.findChild(QWidget, "control_bar")
            if control_bar and not control_bar.isVisible():
                control_bar.show()
                
                # 3秒后自动隐藏
                QTimer.singleShot(3000, lambda: 
                    control_bar.hide() if time.time() - self.last_mouse_move_time > 2.9 else None)

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
        if self.media_player:
            current_pos = self.media_player.position()
            self.media_player.setPosition(max(0, current_pos - 5000))

    def jump_forward(self):
        """向前跳转5秒"""
        if self.media_player:
            current_pos = self.media_player.position()
            duration = self.media_player.duration()
            self.media_player.setPosition(min(duration, current_pos + 5000))

    def check_network_status(self):
        """检查网络连接状态 - 使用更可靠的方法"""
        try:
            # 使用更可靠的网络检查方法
            test_url = "https://www.gstatic.com/generate_204"
            response = rq.get(test_url, timeout=3)
            if response.status_code != 204:
                raise Exception(f"网络测试失败，状态码: {response.status_code}")
                
        except Exception as e:
            if self.media_player and self.media_player.state() == QMediaPlayer.PlayingState:
                logger.warning(f"网络连接问题: {str(e)}")
                self.status_label.setText("网络连接不稳定...")
                # 暂停播放
                self.media_player.pause()
                self.play_btn.setIcon(QIcon("./img/play.png"))
                
                # 10秒后尝试恢复
                QTimer.singleShot(10000, self.try_reconnect)
    
    def try_reconnect(self):
        """尝试恢复播放"""
        try:
            self.status_label.setText("尝试重新连接...")
            if self.media_player:
                self.media_player.play()
                # 检查是否成功恢复
                QTimer.singleShot(2000, lambda: 
                    self.status_label.setText("播放中" if self.media_player and 
                                             self.media_player.state() == QMediaPlayer.PlayingState 
                                             else "重连失败"))
        except Exception as e:
            logger.error(f"重连失败: {str(e)}")
            self.status_label.setText("重连失败")

    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止网络检查定时器
        if self.network_timer and self.network_timer.isActive():
            self.network_timer.stop()
            self.network_timer = None
            
        # 停止代理服务器
        if self.proxy_server:
            self.proxy_server.stop()
            self.proxy_server = None
            
        # 停止定时器
        if self.timer and self.timer.isActive():
            self.timer.stop()
            self.timer = None
            
        # 清理媒体播放器
        if self.media_player:
            self.cleanup_media_player()
            
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    video_player = VideoPlayer(bvid="BV1aAhPzdEJ8", cid="31374511005")
    video_player.show()
    sys.exit(app.exec_())