import random
import math
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsScene
from PyQt5.QtGui import (QImage, QPainter, QPen, QColor, QPixmap, 
                         QPalette, QBrush, qRgba, QLinearGradient, 
                         QPainterPath)
from PyQt5.QtCore import Qt, QRect

class AcrylicEffect:
    """
    亚克力效果封装类
    提供高斯模糊、亮度混合、色调混合和噪声纹理效果
    修复了圆角边缘白色问题，并添加圆角开关
    """
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
        self.noise_texture = self.generate_noise_texture(200, 200)
        
        # 默认效果参数
        self.blur_radius = 25
        self.blur_max = 64
        self.brightness = 0.8
        self.tint_strength = 0.15
        self.noise_strength = 0.08
        
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
            
        # 初始应用效果
        self.apply_effect()
    
    def set_enable_rounded_corners(self, enabled):
        """启用或禁用圆角效果"""
        self.enable_rounded_corners = enabled
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
    
    def set_background_image(self, image):
        """设置背景图片"""
        if isinstance(image, str):
            self.background_image = QImage(image)
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
    
    def generate_noise_texture(self, width, height):
        """生成噪声纹理"""
        image = QImage(width, height, QImage.Format_ARGB32)
        
        for x in range(width):
            for y in range(height):
                # 生成随机灰度值，alpha值控制噪声强度
                value = random.randint(0, 255)
                image.setPixel(x, y, qRgba(value, value, value, 30))
        
        return image
    
    def apply_effect(self):
        """应用亚克力效果 - 修复圆角边缘白色问题"""
        # 检查部件大小
        if self.widget.size().isEmpty():
            print("警告: 窗口大小为0，跳过亚克力效果应用")
            return
            
        # 创建用于亚克力效果的图像
        acrylic_img = QImage(self.widget.size(), QImage.Format_ARGB32_Premultiplied)
        # 使用透明填充而不是白色
        acrylic_img.fill(Qt.transparent)
        
        # 绘制背景（缩放背景图片）
        painter = QPainter(acrylic_img)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        scaled_bg = self.background_image.scaled(
            self.widget.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        painter.drawImage(0, 0, scaled_bg)
        painter.end()
        
        # 1. 应用高斯模糊
        acrylic_img = self.apply_eblur_gaussian_blur(acrylic_img, self.blur_radius)
        
        # 2. 应用亮度混合
        acrylic_img = self.apply_brightness(acrylic_img, self.brightness)
        
        # 3. 应用色调混合
        acrylic_img = self.apply_tint(acrylic_img, self.tint_color, self.tint_strength)
        
        # 4. 应用噪声纹理
        acrylic_img = self.apply_noise(acrylic_img, self.noise_strength)
        
        # 5. 应用圆角遮罩 - 根据开关决定是否启用
        if self.enable_rounded_corners and self.border_radius > 0:
            acrylic_img = self.apply_improved_rounded_mask(acrylic_img, self.border_radius)
        
        # 6. 应用边框 - 如果圆角禁用，则使用直角边框
        if self.border_width > 0:
            if self.enable_rounded_corners:
                acrylic_img = self.apply_rounded_border(acrylic_img, self.border_color, self.border_width)
            else:
                acrylic_img = self.apply_rectangular_border(acrylic_img, self.border_color, self.border_width)
        
        # 设置部件背景
        palette = self.widget.palette()
        palette.setBrush(QPalette.Window, QBrush(acrylic_img))
        self.widget.setPalette(palette)
        self.widget.setAutoFillBackground(True)
        
        print("亚克力效果应用成功")
    
    def apply_improved_rounded_mask(self, image, radius):
        """
        改进的圆角遮罩应用方法
        专门修复边缘白色问题
        """
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
    
    def apply_eblur_gaussian_blur(self, image, radius):
        """
        移植EBlurCard的高斯模糊算法
        使用更高质量的多重模糊效果
        """
        # 限制模糊半径
        actual_radius = min(radius, self.blur_max)
        
        # 创建临时图像用于模糊处理
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        # 使用QGraphicsBlurEffect进行模糊，但应用多重模糊以获得更好效果
        scene = QGraphicsScene()
        pixmap_item = scene.addPixmap(QPixmap.fromImage(image))
        
        # 应用多重模糊效果 (模拟EBlurCard的MultiEffect)
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(actual_radius)
        blur_effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
        pixmap_item.setGraphicsEffect(blur_effect)
        
        # 渲染到结果图像
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        scene.render(painter)
        painter.end()
        
        return result
    
    def apply_brightness(self, image, strength):
        """应用亮度混合效果"""
        # 创建一个白色层进行混合
        brightness_layer = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        brightness_layer.fill(QColor(255, 255, 255, int(150 * strength)))
        
        # 混合图像
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawImage(0, 0, image)
        painter.setCompositionMode(QPainter.CompositionMode_SoftLight)
        painter.drawImage(0, 0, brightness_layer)
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
            for x in range(0, self.widget.width(), self.noise_texture.width()):
                for y in range(0, self.widget.height(), self.noise_texture.height()):
                    painter.drawImage(x, y, self.noise_texture)
        
        painter.end()
        return result