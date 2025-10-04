from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest

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