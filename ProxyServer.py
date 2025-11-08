import threading
import socket
import requests as rq
from http.server import HTTPServer, BaseHTTPRequestHandler
import logging

logger = logging.getLogger("BilibiliPlayer")

class MP4ProxyServer(threading.Thread):
    """MP4代理服务器，直接提供MP4格式视频"""
    
    def __init__(self, mp4_url, cookies, headers):
        super().__init__()
        self.mp4_url = mp4_url
        self.cookies = cookies
        self.headers = headers
        self.port = 0
        self.server = None
        self.ready = threading.Event()
        self.output_url = ""
        self.daemon = True  # 添加守护线程
        
    def run(self):
        try:
            # 查找可用端口
            self.port = self._find_available_port()
            self.output_url = f"http://127.0.0.1:{self.port}/video.mp4"
            
            # 启动HTTP服务器
            self.server = HTTPServer(('127.0.0.1', self.port), self._make_handler())
            self.ready.set()
            logger.info(f"MP4代理服务器启动: {self.output_url}")
            logger.info(f"源URL: {self.mp4_url}")
            
            # 运行服务器
            self.server.serve_forever()
            
        except Exception as e:
            logger.error(f"MP4代理服务器错误: {str(e)}")
            self.ready.set()  # 确保不会死锁
    
    def _find_available_port(self):
        """查找可用端口"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port
    
    def _make_handler(self):
        """创建HTTP请求处理程序，直接转发MP4流"""
        mp4_url = self.mp4_url
        cookies = self.cookies
        headers = self.headers
        
        class MP4Handler(BaseHTTPRequestHandler):
            def do_GET(inner_self):
                if inner_self.path == "/video.mp4":
                    try:
                        # 创建请求头
                        request_headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                            "Referer": "https://www.bilibili.com/",
                            "Range": inner_self.headers.get('Range', '')  # 支持范围请求
                        }
                        
                        # 添加Cookie
                        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                        if cookie_str:
                            request_headers["Cookie"] = cookie_str
                        
                        # 添加其他头部
                        for key, value in headers.items():
                            if key.lower() not in ['user-agent', 'referer', 'cookie']:
                                request_headers[key] = value
                        
                        logger.info(f"代理请求头: {request_headers}")
                        
                        # 流式传输MP4数据
                        response = rq.get(mp4_url, headers=request_headers, stream=True, cookies=cookies, timeout=30)
                        response.raise_for_status()
                        
                        # 设置响应头
                        inner_self.send_response(200)
                        inner_self.send_header('Content-type', 'video/mp4')
                        inner_self.send_header('Content-Length', str(len(response.content)))
                        inner_self.send_header('Accept-Ranges', 'bytes')
                        inner_self.send_header('Access-Control-Allow-Origin', '*')
                        inner_self.send_header('Access-Control-Allow-Headers', '*')
                        inner_self.end_headers()
                        
                        # 传输数据
                        for chunk in response.iter_content(chunk_size=8192):  # 8KB chunks
                            if chunk:
                                try:
                                    inner_self.wfile.write(chunk)
                                except (ConnectionResetError, BrokenPipeError):
                                    # 客户端断开连接
                                    logger.info("客户端断开连接")
                                    break
                                    
                    except Exception as e:
                        logger.error(f"MP4流传输错误: {str(e)}")
                        inner_self.send_response(500)
                        inner_self.end_headers()
                else:
                    inner_self.send_response(404)
                    inner_self.end_headers()
            
            def log_message(self, format, *args):
                """禁用默认日志输出"""
                pass
        
        return MP4Handler
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()