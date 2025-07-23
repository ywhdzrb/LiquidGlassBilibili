import random
from PyQt5.QtWidgets import QGraphicsBlurEffect, QGraphicsScene
from PyQt5.QtGui import QImage, QPainter, QPen, QColor, QPixmap, QPalette, QBrush, qRgba, QLinearGradient
from PyQt5.QtCore import Qt

class AcrylicEffect:
    """
    亚克力效果封装类
    提供高斯模糊、亮度混合、色调混合和噪声纹理效果
    """
    def __init__(self, widget, background_image=None, tint_color=QColor(200, 220, 255)):
        """
        初始化亚克力效果
        
        参数:
            widget: 要应用效果的QWidget
            background_image: 背景图片路径或QImage对象
            tint_color: 默认的色调颜色 (默认为淡蓝色)
        """
        self.widget = widget
        self.tint_color = tint_color
        self.noise_texture = self.generate_noise_texture(200, 200)
        
        # 默认效果参数
        self.blur_radius = 20
        self.brightness = 0.7
        self.tint_strength = 0.3
        self.noise_strength = 0.15
        
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
        """设置高斯模糊半径 (5-50)"""
        self.blur_radius = max(5, min(radius, 50))
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
        """应用亚克力效果"""
        # 创建用于亚克力效果的图像
        acrylic_img = QImage(self.widget.size(), QImage.Format_ARGB32_Premultiplied)
        acrylic_img.fill(Qt.transparent)
        
        # 绘制背景（缩放背景图片）
        painter = QPainter(acrylic_img)
        scaled_bg = self.background_image.scaled(
            self.widget.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        painter.drawImage(0, 0, scaled_bg)
        painter.end()
        
        # 1. 应用高斯模糊
        acrylic_img = self.apply_gaussian_blur(acrylic_img, self.blur_radius)
        
        # 2. 应用亮度混合
        acrylic_img = self.apply_brightness(acrylic_img, self.brightness)
        
        # 3. 应用色调混合
        acrylic_img = self.apply_tint(acrylic_img, self.tint_color, self.tint_strength)
        
        # 4. 应用噪声纹理
        acrylic_img = self.apply_noise(acrylic_img, self.noise_strength)
        
        # 设置部件背景
        palette = self.widget.palette()
        palette.setBrush(QPalette.Window, QBrush(acrylic_img))
        self.widget.setPalette(palette)
        self.widget.setAutoFillBackground(True)
    
    def apply_gaussian_blur(self, image, radius):
        """应用高斯模糊效果"""
        # 创建临时图像
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        # 使用QGraphicsBlurEffect进行模糊
        scene = QGraphicsScene()
        pixmap_item = scene.addPixmap(QPixmap.fromImage(image))
        
        blur_effect = QGraphicsBlurEffect()
        blur_effect.setBlurRadius(radius)
        blur_effect.setBlurHints(QGraphicsBlurEffect.QualityHint)
        pixmap_item.setGraphicsEffect(blur_effect)
        
        # 渲染到结果图像
        painter = QPainter(result)
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
        painter.drawImage(0, 0, image)
        painter.setCompositionMode(QPainter.CompositionMode_SoftLight)
        painter.drawImage(0, 0, brightness_layer)
        painter.end()
        
        return result
    
    def apply_tint(self, image, color, strength):
        """应用色调混合效果"""
        # 创建色调层
        tint_layer = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        tint_layer.fill(QColor(color.red(), color.green(), color.blue(), int(180 * strength)))
        
        # 混合图像
        result = QImage(image.size(), QImage.Format_ARGB32_Premultiplied)
        result.fill(Qt.transparent)
        
        painter = QPainter(result)
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
