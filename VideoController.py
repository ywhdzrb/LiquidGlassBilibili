# VideoController.py
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QTimer, QRect
from PyQt5.QtWidgets import (QWidget, QGridLayout, QLabel, QApplication, 
                             QSizePolicy, QScrollArea, QVBoxLayout, QSpacerItem)
from PyQt5.QtGui import QWheelEvent
from VideoWidget import VideoWidget
from GetBilibiliApi import *
import os
import threading

class DataLoaderSignals(QObject):
    data_ready = pyqtSignal(list)
    data_failed = pyqtSignal()

class DataLoader(threading.Thread):
    def __init__(self, page, pagesize):
        super().__init__()
        self.page = page
        self.pagesize = pagesize
        self.signals = DataLoaderSignals()

    def run(self):
        try:
            data = GetRecommendVideos(page=self.page, pagesize=self.pagesize).get_recommend_videos()
            if data:
                self.signals.data_ready.emit(data)
            else:
                raise ValueError("推荐数据为空")
        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            self.signals.data_failed.emit()

class ThumbnailDownloader(threading.Thread):
    def __init__(self, pic_url, bvid, index, controller):
        super().__init__()
        self.pic_url = pic_url
        self.bvid = bvid
        self.index = index
        self.controller = controller

    def run(self):
        try:
            save_path = f"./temp/{self.bvid}.jpg"
            if Download().download_thumbnail(self.pic_url, save_path):
                self.controller.thumbnail_loaded.emit(self.index, save_path)
        except Exception as e:
            print(f"缩略图下载失败: {str(e)}")

class VideoController(QScrollArea):
    thumbnail_loaded = pyqtSignal(int, str)
    load_more_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_alive = True
        self.download_threads = []
        self.video_widgets = []
        self.video_info = []
        
        # 分页相关变量
        self.current_page = 1
        self.is_loading_more = False
        
        # 懒加载相关变量
        self.loaded_indices = set()
        self.visible_range = (0, 0)
        self.pending_loads = set()
        self.load_timer = QTimer()
        self.load_timer.setSingleShot(True)
        self.load_timer.timeout.connect(self.process_pending_loads)
        
        self.init_ui()
        self.load_initial_data()
        self.thumbnail_loaded.connect(self.update_thumbnail)
        self.load_more_requested.connect(self.load_more_data)

    def init_ui(self):
        # 设置滚动区域背景为透明
        self.setStyleSheet("""
            QScrollArea { 
                background: transparent; 
                border: none; 
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 50);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 150);
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 200);
            }
        """)
        self.setFrameShape(QScrollArea.NoFrame)
        
        # 创建内容部件
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        
        # 主布局
        self.main_layout = QVBoxLayout(self.scroll_content)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 网格布局容器
        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(20)  # 增加垂直间距
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # 顶部对齐
        
        self.main_layout.addWidget(self.grid_container)
        
        # 加载更多提示
        self.load_more_widget = QWidget()
        self.load_more_widget.setFixedHeight(60)
        self.load_more_widget.setStyleSheet("background: transparent;")
        load_more_layout = QVBoxLayout(self.load_more_widget)
        self.load_more_label = QLabel("加载更多...")
        self.load_more_label.setAlignment(Qt.AlignCenter)
        self.load_more_label.setStyleSheet("""
            color: white; 
            font-size: 14px; 
            background-color: rgba(0,0,0,100);
            border-radius: 10px;
            padding: 10px;
        """)
        load_more_layout.addWidget(self.load_more_label)
        self.load_more_widget.hide()
        
        self.main_layout.addWidget(self.load_more_widget)
        
        # 设置滚动区域
        self.setWidget(self.scroll_content)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 加载提示标签
        self.loading_label = QLabel("加载中...", self)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("""
            font-size: 24px; 
            color: white;
            background-color: rgba(0,0,0,150);
            border-radius: 10px;
        """)

    def load_initial_data(self):
        self.loading_label.show()
        self.loading_label.setGeometry(0, 0, self.width(), self.height())
        os.makedirs("./temp", exist_ok=True)
        
        self.current_page = 1
        self.load_data_page(self.current_page)

    def load_data_page(self, page):
        """加载指定页面的数据"""
        loader = DataLoader(page=page, pagesize=12)
        loader.signals.data_ready.connect(self.on_data_loaded)
        loader.signals.data_failed.connect(self.on_data_failed)
        loader.start()

    def on_data_loaded(self, data):
        if not self._is_alive:
            return
            
        self.loading_label.hide()
        
        if self.current_page == 1:
            # 第一页数据
            self.video_info = data
            self.create_video_grid()
        else:
            # 追加数据
            start_index = len(self.video_info)
            self.video_info.extend(data)
            self.append_video_grid(start_index, len(data))
            
        self.is_loading_more = False
        self.load_more_widget.hide()
        
        # 初始加载前几个视频的缩略图
        QTimer.singleShot(100, lambda: self.schedule_lazy_load(0))

    def on_data_failed(self):
        if not self._is_alive:
            return
            
        if self.current_page == 1:
            self.loading_label.setText("加载失败，点击重试")
            self.loading_label.mousePressEvent = lambda _: self.load_initial_data()
        else:
            self.is_loading_more = False
            self.load_more_label.setText("加载失败，点击重试")
            self.load_more_label.mousePressEvent = lambda _: self.load_more_data()

    def create_video_grid(self):
        """创建视频网格布局"""
        self.video_widgets = []
        
        # 清除现有布局
        for i in reversed(range(self.grid_layout.count())): 
            item = self.grid_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
        
        # 计算自适应尺寸
        card_width, card_height = self.calculate_widget_size()
        
        for i in range(len(self.video_info)):
            row, col = divmod(i, 4)
            video_widget = self.create_video_widget(i, card_width, card_height)
            self.video_widgets.append(video_widget)
            self.grid_layout.addWidget(video_widget, row, col)
            
            # 设置固定高度，防止挤压
            video_widget.setFixedHeight(card_height)
            
        # 显示加载更多提示
        self.load_more_widget.show()

    def append_video_grid(self, start_index, count):
        """追加视频到网格布局"""
        card_width, card_height = self.calculate_widget_size()
        
        for i in range(start_index, start_index + count):
            row, col = divmod(i, 4)
            video_widget = self.create_video_widget(i, card_width, card_height)
            self.video_widgets.append(video_widget)
            self.grid_layout.addWidget(video_widget, row, col)
            
            # 设置固定高度，防止挤压
            video_widget.setFixedHeight(card_height)

    def create_video_widget(self, index, width, height):
        """创建单个视频小部件"""
        info = self.video_info[index]
        widget = VideoWidget(
            title=info.get("title", ""),
            duration=info.get("duration", 0),
            thumbnail_path="./img/none.png",
            upname=info.get("owner", {}).get("name", ""),
            release_time=info.get("pubdate", 0),
            bvid=info.get("bvid", ""),
            cid=info.get("cid", "")
        )
        
        # 设置固定尺寸，确保布局稳定
        widget.setFixedSize(width, height)
        widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        return widget

    def calculate_widget_size(self):
        """计算自适应的小部件尺寸"""
        # 获取可用宽度（减去边距和间距）
        available_width = self.width() - 20 - 60  # 增加间距余量
        
        # 计算每个卡片的宽度（保持4列布局）
        card_width = available_width // 4
        
        # 根据宽高比计算高度（原比例300:210≈1.428）
        card_height = int(card_width / 1.428)
        
        # 确保最小高度
        min_height = 180
        if card_height < min_height:
            card_height = min_height
            card_width = int(card_height * 1.428)
            
        return card_width, card_height

    def schedule_lazy_load(self, start_index):
        """调度懒加载"""
        self.load_timer.stop()
        
        # 计算需要加载的范围（当前可见及后两个）
        end_index = min(start_index + 7, len(self.video_widgets) - 1)
        
        # 添加到待加载队列
        for i in range(start_index, end_index + 1):
            if i not in self.loaded_indices and i not in self.pending_loads:
                self.pending_loads.add(i)
        
        self.visible_range = (start_index, end_index)
        self.load_timer.start(50)

    def process_pending_loads(self):
        """处理待加载的缩略图"""
        if not self.pending_loads:
            return
            
        for index in list(self.pending_loads):
            if index < len(self.video_info):
                info = self.video_info[index]
                thread = ThumbnailDownloader(
                    pic_url=info["pic"],
                    bvid=info["bvid"],
                    index=index,
                    controller=self
                )
                self.download_threads.append(thread)
                thread.start()
                self.loaded_indices.add(index)
                self.pending_loads.remove(index)

    def update_thumbnail(self, index, path):
        """更新缩略图"""
        if self._is_alive and index < len(self.video_widgets):
            self.video_widgets[index].update_info(thumbnail_path=path)

    def scrollEvent(self, event):
        """滚动事件处理"""
        super().scrollEvent(event)
        self.handle_scroll()

    def wheelEvent(self, event: QWheelEvent):
        """滚轮事件处理"""
        super().wheelEvent(event)
        QTimer.singleShot(50, self.handle_scroll)

    def handle_scroll(self):
        """处理滚动，确定当前可见的视频索引"""
        if not self.video_widgets:
            return
            
        # 检查是否需要加载更多数据
        scrollbar = self.verticalScrollBar()
        if (scrollbar.maximum() - scrollbar.value() < 100 and 
            not self.is_loading_more and len(self.video_info) >= 12):
            self.load_more_data()
        
        # 获取可见区域
        viewport_rect = self.viewport().rect()
        scroll_pos = self.verticalScrollBar().value()
        visible_rect = viewport_rect.translated(0, scroll_pos)
        
        # 查找第一个可见的视频部件
        first_visible_index = None
        for i, widget in enumerate(self.video_widgets):
            widget_pos = widget.mapTo(self.scroll_content, widget.rect().topLeft())
            widget_rect = QRect(widget_pos, widget.size())
            
            if visible_rect.intersects(widget_rect):
                first_visible_index = i
                break
        
        if first_visible_index is not None:
            self.schedule_lazy_load(max(0, first_visible_index - 1))

    def load_more_data(self):
        """加载更多数据"""
        if self.is_loading_more:
            return
            
        self.is_loading_more = True
        self.load_more_label.setText("加载中...")
        self.current_page += 1
        self.load_data_page(self.current_page)

    def resizeEvent(self, event):
        """窗口大小改变时调整布局"""
        super().resizeEvent(event)
        self.loading_label.setGeometry(0, 0, self.width(), self.height())
        
        if self.video_widgets:
            card_width, card_height = self.calculate_widget_size()
            
            # 更新所有视频部件的尺寸
            for widget in self.video_widgets:
                widget.setFixedSize(card_width, card_height)
                widget.update_layout()
        
        # 重新触发懒加载检查
        QTimer.singleShot(100, self.handle_scroll)

    def showEvent(self, event):
        """显示事件 - 初始加载检查"""
        super().showEvent(event)
        QTimer.singleShot(100, self.handle_scroll)

    def closeEvent(self, event):
        """关闭事件处理"""
        self._is_alive = False
        self.load_timer.stop()
        for t in self.download_threads:
            t.join(timeout=1)
        super().closeEvent(event)

if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    controller = VideoController()
    controller.show()
    sys.exit(app.exec_())