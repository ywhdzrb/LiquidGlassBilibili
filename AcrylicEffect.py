import random
import math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from collections import Counter
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsScene
from PyQt5.QtGui import (QImage, QPainter, QPen, QColor, QPixmap, 
                         QPalette, QBrush, qRgba, QLinearGradient, 
                         QPainterPath)
from PyQt5.QtCore import Qt, QRect

class AcrylicEffect:
    """
    亚克力效果封装类 - 基于numpy和scipy的高性能实现
    提供高斯模糊、亮度混合、色调混合和噪声纹理效果
    """
    
    @staticmethod
    def numpy_array_to_qimage(image_array):
        """将numpy数组转换为QImage"""
        # 确保数值范围在0-255之间并转换为uint8类型
        if image_array.dtype != np.uint8:
            image_array = np.clip(image_array, 0, 255).astype(np.uint8)
            
        height, width, channel = image_array.shape
        bytes_per_line = 3 * width
        q_img = QImage(image_array.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return q_img.copy()  # 创建副本以确保数据不会被释放
    
    @staticmethod
    def gaussian_blur_numpy(image_path, blur_radius=18, bright_factor=1.0, blur_pic_size=None):
        """使用numpy和scipy进行高斯模糊处理"""
        try:
            # 打开图像
            if isinstance(image_path, str):
                image = Image.open(image_path)
            else:
                # 如果是QImage或QPixmap，转换为PIL Image
                image = Image.fromqpixmap(image_path)
            
            if blur_pic_size:
                # 调整图片尺寸，减小计算量
                w, h = image.size
                ratio = min(blur_pic_size[0] / w, blur_pic_size[1] / h)
                w_, h_ = w * ratio, h * ratio
                
                if w_ < w:
                    image = image.resize((int(w_), int(h_)), Image.Resampling.LANCZOS)
            
            image = np.array(image)
            
            # 处理图像是灰度图的情况
            if len(image.shape) == 2:
                image = np.stack([image, image, image], axis=-1)
            elif image.shape[2] == 4:
                # RGBA转RGB
                image = image[:, :, :3]
            
            # 当blur_radius为0时，不应用模糊效果
            if blur_radius > 0:
                # 对每一个颜色通道分别磨砂，并确保数值不会溢出
                for i in range(3):
                    blurred_channel = gaussian_filter(image[:, :, i], blur_radius) * bright_factor
                    # 确保数值在0-255范围内
                    image[:, :, i] = np.clip(blurred_channel, 0, 255)
            elif bright_factor != 1.0:
                # 当blur_radius为0但bright_factor不为1时，只调整亮度
                for i in range(3):
                    image[:, :, i] = np.clip(image[:, :, i] * bright_factor, 0, 255)
            
            return image
        except Exception as e:
            print(f"高斯模糊处理失败: {e}")
            # 返回一个白色图像作为后备
            return np.full((100, 100, 3), 255, dtype=np.uint8)
    
    @staticmethod
    def get_dominant_color(image_path, num_colors=5):
        """从图像中提取主色调"""
        try:
            # 打开图像并转换为RGB模式
            if isinstance(image_path, str):
                image = Image.open(image_path).convert('RGB')
            else:
                image = image_path.convert('RGB')
            
            # 调整图像大小以加快处理速度
            image = image.resize((150, 150), Image.Resampling.LANCZOS)
            
            # 获取所有像素颜色
            pixels = list(image.getdata())
            
            # 统计颜色频率
            color_count = Counter(pixels)
            
            # 获取最常见的几种颜色
            most_common_colors = color_count.most_common(num_colors)
            
            # 计算平均颜色作为主色调
            total_r, total_g, total_b = 0, 0, 0
            total_count = 0
            
            for (r, g, b), count in most_common_colors:
                total_r += r * count
                total_g += g * count
                total_b += b * count
                total_count += count
            
            # 计算平均值
            avg_r = int(total_r / total_count)
            avg_g = int(total_g / total_count)
            avg_b = int(total_b / total_count)
            
            # 返回QColor对象，带有一定的透明度
            return QColor(avg_r, avg_g, avg_b, 100)
        except Exception as e:
            print(f"提取主色调时出错: {e}")
            # 出错时返回默认的蓝色色调
            return QColor(200, 220, 255, 100)
    
    @staticmethod
    def generate_noise_texture_numpy(width, height, noise_opacity=0.03):
        """生成噪声纹理 - numpy实现"""
        # 创建随机噪声数组
        noise_array = np.random.randint(0, 255, (height, width), dtype=np.uint8)
        
        # 创建RGBA图像
        noise_image = QImage(width, height, QImage.Format_ARGB32)
        
        # 填充噪声数据
        for y in range(height):
            for x in range(width):
                noise_value = noise_array[y, x]
                # 创建半透明的噪声像素
                alpha = int(255 * noise_opacity)
                color = QColor(noise_value, noise_value, noise_value, alpha)
                noise_image.setPixelColor(x, y, color)
        
        return noise_image
    
    def __init__(self, widget, background_image=None, tint_color=QColor(245, 245, 255, 180)):
        """
        初始化亚克力效果
        
        参数:
            widget: 要应用效果的QWidget
            background_image: 背景图片路径或QImage对象
            tint_color: 默认的色调颜色 (默认为浅白色半透明)
        """
        self.widget = widget
        self.tint_color = tint_color
        
        # 默认效果参数
        self.blur_radius = 25
        self.blur_max = 64
        self.brightness = 0.8
        self.tint_strength = 0.15
        self.noise_strength = 0.08
        
        # 新的效果参数（来自main.py）
        self.bright_factor = 1.05
        self.process_resolution = (800, 600)
        
        # EBlurCard移植参数
        self.border_radius = 24
        self.border_color = QColor(255, 255, 255, 30)
        self.border_width = 1
        
        # 圆角开关 - 默认启用
        self.enable_rounded_corners = True
        
        # 设置背景图片
        if background_image is None:
            # 创建默认背景
            self.background_image = self.create_default_background()
        elif isinstance(background_image, str):
            self.background_image = QImage(background_image)
        else:
            self.background_image = background_image
        
        # 提取主色调
        if isinstance(background_image, str):
            self.dominant_color = self.get_dominant_color(background_image)
        else:
            self.dominant_color = tint_color
        
        # 生成噪声纹理
        self.noise_texture = self.generate_noise_texture_numpy(200, 200, 0.03)
        
        # 初始应用效果
        self.apply_effect()
    
    def create_default_background(self):
        """创建默认渐变背景"""
        width, height = 800, 600
        image = QImage(width, height, QImage.Format_RGB32)
        
        painter = QPainter(image)
        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0, QColor(50, 120, 180))
        gradient.setColorAt(1, QColor(80, 50, 140))
        painter.fillRect(0, 0, width, height, gradient)
        
        # 添加一些装饰性元素
        painter.setPen(QPen(QColor(255, 255, 255, 30), 2))
        for i in range(20):
            x = random.randint(0, width)
            y = random.randint(0, height)
            size = random.randint(20, 100)
            painter.drawEllipse(x, y, size, size)
            
        painter.end()
        return image
    
    def set_enable_rounded_corners(self, enabled):
        """启用或禁用圆角效果"""
        self.enable_rounded_corners = enabled
        self.apply_effect()
    
    def set_background_image(self, image):
        """设置背景图片"""
        if isinstance(image, str):
            self.background_image = QImage(image)
            # 提取主色调
            self.dominant_color = self.get_dominant_color(image)
        else:
            self.background_image = image
        self.apply_effect()
    
    def set_blur_radius(self, radius):
        """设置高斯模糊半径 (5-64)"""
        self.blur_radius = max(5, min(radius, self.blur_max))
        self.apply_effect()
    
    def set_blur_max(self, blur_max):
        """设置最大模糊半径"""
        self.blur_max = blur_max
        self.apply_effect()
    
    def set_brightness(self, brightness):
        """设置亮度混合强度 (0.0-1.0)"""
        self.brightness = max(0.0, min(brightness, 1.0))
        # 同时更新bright_factor
        self.bright_factor = 0.8 + (brightness * 0.4)  # 映射到0.8-1.2范围
        self.apply_effect()
    
    def set_tint_strength(self, strength):
        """设置色调混合强度 (0.0-1.0)"""
        self.tint_strength = max(0.0, min(strength, 1.0))
        self.apply_effect()
    
    def set_noise_strength(self, strength):
        """设置噪声纹理强度 (0.0-1.0)"""
        self.noise_strength = max(0.0, min(strength, 1.0))
        self.apply_effect()
    
    def set_tint_color(self, color):
        """设置色调颜色"""
        self.tint_color = color
        self.apply_effect()
    
    def set_border_radius(self, radius):
        """设置边框圆角半径"""
        self.border_radius = radius
        self.apply_effect()
    
    def set_border_color(self, color):
        """设置边框颜色"""
        self.border_color = color
        self.apply_effect()
    
    def set_border_width(self, width):
        """设置边框宽度"""
        self.border_width = width
        self.apply_effect()
    
    def set_bright_factor(self, factor):
        """设置亮度因子 (0.8-1.2)"""
        self.bright_factor = max(0.8, min(factor, 1.2))
        self.apply_effect()
    
    def set_process_resolution(self, resolution):
        """设置处理分辨率"""
        self.process_resolution = resolution
        self.apply_effect()
    
    def apply_effect(self):
        """应用亚克力效果 - 使用numpy/scipy高性能实现"""
        # 检查部件大小
        if self.widget.size().isEmpty():
            print("警告: 窗口大小为0，跳过亚克力效果应用")
            return
            
        try:
            # 1. 首先将背景图像保存为临时文件用于高斯模糊处理
            temp_background = self.background_image
            
            # 如果背景是QImage，需要先保存到临时文件
            if isinstance(temp_background, QImage):
                temp_path = "./temp/temp_background.png"
                temp_background.save(temp_path, "PNG")
                bg_path = temp_path
            else:
                bg_path = temp_background
            
            # 2. 使用numpy/scipy进行高斯模糊处理
            blurred_array = self.gaussian_blur_numpy(
                bg_path,
                blur_radius=self.blur_radius,
                bright_factor=self.bright_factor,
                blur_pic_size=self.process_resolution
            )
            
            # 3. 转换为QImage
            acrylic_img = self.numpy_array_to_qimage(blurred_array)
            
            # 4. 缩放图像以匹配部件大小
            acrylic_img = acrylic_img.scaled(
                self.widget.size(),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 5. 转换为正确的格式用于进一步处理
            acrylic_img = acrylic_img.convertToFormat(QImage.Format_ARGB32_Premultiplied)
            
            # 6. 应用色调混合
            acrylic_img = self.apply_tint(acrylic_img, self.tint_color, self.tint_strength)
            
            # 7. 应用噪声纹理
            acrylic_img = self.apply_noise(acrylic_img, self.noise_strength)
            
            # 8. 应用圆角遮罩 - 根据开关决定是否启用
            if self.enable_rounded_corners and self.border_radius > 0:
                acrylic_img = self.apply_improved_rounded_mask(acrylic_img, self.border_radius)
            
            # 9. 应用边框 - 如果圆角禁用，则使用直角边框
            if self.border_width > 0:
                if self.enable_rounded_corners:
                    acrylic_img = self.apply_rounded_border(acrylic_img, self.border_color, self.border_width)
                else:
                    acrylic_img = self.apply_rectangular_border(acrylic_img, self.border_color, self.border_width)
            
            # 10. 设置部件背景
            palette = self.widget.palette()
            palette.setBrush(QPalette.Window, QBrush(acrylic_img))
            self.widget.setPalette(palette)
            self.widget.setAutoFillBackground(True)
            
            print(f"亚克力效果应用成功 (模糊半径: {self.blur_radius}, 亮度因子: {self.bright_factor})")
            
        except Exception as e:
            print(f"应用亚克力效果时出错: {e}")
            # 出错时使用备用方法
            self.apply_fallback_effect()
    
    def apply_fallback_effect(self):
        """备用效果应用方法"""
        try:
            # 创建简单的半透明背景
            acrylic_img = QImage(self.widget.size(), QImage.Format_ARGB32_Premultiplied)
            acrylic_img.fill(QColor(240, 240, 245, 200))
            
            # 应用圆角
            if self.enable_rounded_corners and self.border_radius > 0:
                acrylic_img = self.apply_improved_rounded_mask(acrylic_img, self.border_radius)
            
            palette = self.widget.palette()
            palette.setBrush(QPalette.Window, QBrush(acrylic_img))
            self.widget.setPalette(palette)
            self.widget.setAutoFillBackground(True)
            
            print("应用备用亚克力效果")
        except Exception as e:
            print(f"备用效果也失败: {e}")
    
    def apply_improved_rounded_mask(self, image, radius):
        """改进的圆角遮罩应用方法"""
        width, height = image.width(), image.height()
        
        # 创建结果图像
        result = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # 创建圆角矩形路径
        path = QPainterPath()
        path.addRoundedRect(0, 0, width, height, radius, radius)
        
        # 设置剪辑路径 - 确保只有圆角矩形内部被绘制
        painter.setClipPath(path)
        
        # 绘制原始图像
        painter.drawImage(0, 0, image)
        
        painter.end()
        
        return result
    
    def apply_rounded_border(self, image, border_color, border_width):
        """应用圆角边框"""
        result = QImage(image)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.NoBrush)
        
        # 绘制圆角边框，考虑边框宽度
        half_border = border_width / 2
        rect = QRect(half_border, half_border, 
                    image.width() - border_width, image.height() - border_width)
        painter.drawRoundedRect(rect, self.border_radius, self.border_radius)
        painter.end()
        
        return result
    
    def apply_rectangular_border(self, image, border_color, border_width):
        """应用直角边框"""
        result = QImage(image)
        
        painter = QPainter(result)
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(Qt.NoBrush)
        
        # 绘制直角边框
        half_border = border_width / 2
        rect = QRect(half_border, half_border, 
                    image.width() - border_width, image.height() - border_width)
        painter.drawRect(rect)
        painter.end()
        
        return result
    
    def apply_tint(self, image, color, strength):
        """应用色调混合效果"""
        # 创建色调层
        tint_layer = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        tint_alpha = int(180 * strength)
        tint_layer.fill(QColor(color.red(), color.green(), color.blue(), tint_alpha))
        
        # 混合图像
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(0, 0, image)
        painter.setCompositionMode(QPainter.CompositionMode_SourceAtop)
        painter.drawImage(0, 0, tint_layer)
        painter.end()
        
        return result
    
    def apply_noise(self, image, strength):
        """应用噪声纹理"""
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(0, 0, image)
        
        # 绘制噪声纹理
        noise_alpha = int(50 * strength)
        if noise_alpha > 0:
            painter.setOpacity(noise_alpha / 255.0)
            
            # 平铺噪声纹理
            noise_width = self.noise_texture.width()
            noise_height = self.noise_texture.height()
            
            for x in range(0, self.widget.width(), noise_width):
                for y in range(0, self.widget.height(), noise_height):
                    painter.drawImage(x, y, self.noise_texture)
        
        painter.end()
        return result