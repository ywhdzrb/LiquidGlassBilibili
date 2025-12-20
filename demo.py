import glfw
import numpy as np
import math
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image
import os

class LiquidGlassEffect:
    """
    液态玻璃效果类
    
    参数:
        width: 窗口宽度
        height: 窗口高度
        shape: 'circle' 或 'rectangle'，玻璃形状
        radius: 圆形半径（当shape='circle'时）
        rect_size: 矩形大小 (width, height)（当shape='rectangle'时）
        corner_radius: 矩形圆角大小
        refraction_radius: 折射半径大小（边缘折射区域）
        blur_amount: 模糊效果大小（0表示无模糊）
        glass_color: 玻璃颜色 (R, G, B)，范围0-1
        max_transparency: 最大透明度（中心透明度），范围0-1
        refraction_strength: 折射强度，控制折射偏移量
        noise_strength: 噪声强度，控制动态扰动效果
        edge_opacity: 边缘不透明度，控制边缘区域的透明度
    """
    def __init__(self, width=1200, height=800, shape='circle', radius=0.15, 
                 rect_size=(0.2, 0.3), corner_radius=0.05, refraction_radius=0.05,
                 blur_amount=0.0, glass_color=(0.9, 0.95, 1.0), max_transparency=1.0,
                 refraction_strength=-0., noise_strength=0.01, edge_opacity=0.8):
        self.width = width
        self.height = height
        
        # 玻璃参数
        self.shape = shape  # 'circle' 或 'rectangle'
        self.radius = radius
        self.rect_size = np.array(rect_size, dtype=np.float32)
        self.corner_radius = corner_radius
        self.refraction_radius = refraction_radius
        self.blur_amount = blur_amount
        self.glass_color = np.array(glass_color, dtype=np.float32)
        self.max_transparency = max_transparency  # 1.0 = 100%透明
        self.refraction_strength = refraction_strength  # 折射强度
        self.noise_strength = noise_strength  # 噪声强度
        self.edge_opacity = edge_opacity  # 边缘不透明度
        
        # 鼠标位置
        self.mouse_x = 0.5
        self.mouse_y = 0.5
        
        # 渲染状态
        self.background_texture = None
        self.glass_shader = None
        self.background_shader = None
        self.quad_vao = None
        self.frame_count = 0
        self.last_time = 0
        self.fps = 0
        
        # 初始化GLFW和OpenGL
        self.init_glfw()
        self.create_shaders()
        self.create_quad()
        
        # 创建默认背景
        self.set_background_texture(self.create_default_background())
        
        self.print_initialization_info()
    
    def print_initialization_info(self):
        """打印初始化信息"""
        print(f"液态玻璃效果初始化完成")
        print(f"形状: {self.shape}")
        if self.shape == 'circle':
            print(f"半径: {self.radius}")
        else:
            print(f"矩形大小: {self.rect_size[0]}x{self.rect_size[1]}")
            print(f"圆角半径: {self.corner_radius}")
        print(f"折射半径: {self.refraction_radius}")
        print(f"折射强度: {self.refraction_strength}")
        print(f"噪声强度: {self.noise_strength}")
        print(f"模糊强度: {self.blur_amount}")
        print(f"边缘不透明度: {self.edge_opacity}")
    
    def init_glfw(self):
        """初始化GLFW窗口"""
        if not glfw.init():
            raise Exception("GLFW初始化失败")
        
        # 创建窗口
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)
        
        self.window = glfw.create_window(self.width, self.height, "Liquid Glass Effect", None, None)
        if not self.window:
            glfw.terminate()
            raise Exception("窗口创建失败")
        
        glfw.make_context_current(self.window)
        
        # OpenGL初始化
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.1, 0.1, 0.15, 1.0)
    
    def create_shaders(self):
        """创建着色器"""
        # 背景着色器
        background_vertex = """
        #version 330 core
        layout(location = 0) in vec2 aPos;
        layout(location = 1) in vec2 aTexCoord;
        out vec2 TexCoord;
        void main() {
            gl_Position = vec4(aPos, 0.0, 1.0);
            TexCoord = aTexCoord;
        }
        """
        
        background_fragment = """
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        uniform sampler2D u_texture;
        void main() {
            FragColor = texture(u_texture, TexCoord);
        }
        """
        
        self.background_shader = compileProgram(
            compileShader(background_vertex, GL_VERTEX_SHADER),
            compileShader(background_fragment, GL_FRAGMENT_SHADER)
        )
        
        # 玻璃着色器 - 根据形状动态生成
        glass_shader_code = self.generate_glass_shader()
        self.glass_shader = compileProgram(
            compileShader(glass_shader_code['vertex'], GL_VERTEX_SHADER),
            compileShader(glass_shader_code['fragment'], GL_FRAGMENT_SHADER)
        )
        
        # 获取uniform位置
        self.get_uniform_locations()
    
    def generate_glass_shader(self):
        """根据参数生成玻璃着色器代码"""
        vertex_shader = """
        #version 330 core
        layout(location = 0) in vec2 aPos;
        layout(location = 1) in vec2 aTexCoord;
        out vec2 TexCoord;
        void main() {
            gl_Position = vec4(aPos, 0.0, 1.0);
            TexCoord = aTexCoord;
        }
        """
        
        # 动态生成片段着色器
        fragment_shader = f"""
        #version 330 core
        in vec2 TexCoord;
        out vec4 FragColor;
        
        uniform sampler2D backgroundTexture;
        uniform float u_radius;
        uniform vec2 u_rect_size;
        uniform float u_corner_radius;
        uniform float u_refraction_radius;
        uniform float u_blur_amount;
        uniform float u_time;
        uniform vec2 u_mouse_pos;
        uniform vec2 u_resolution;
        uniform vec3 u_glass_color;
        uniform float u_max_transparency;
        uniform float u_refraction_strength;
        uniform float u_noise_strength;
        uniform float u_edge_opacity;
        
        // 噪声函数
        float hash(vec2 p) {{
            return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
        }}
        
        // 平滑噪声
        float smoothNoise(vec2 p) {{
            vec2 ip = floor(p);
            vec2 u = fract(p);
            u = u * u * (3.0 - 2.0 * u);
            
            float a = hash(ip);
            float b = hash(ip + vec2(1.0, 0.0));
            float c = hash(ip + vec2(0.0, 1.0));
            float d = hash(ip + vec2(1.0, 1.0));
            
            return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
        }}
        
        // 分形噪声
        float fractalNoise(vec2 p) {{
            float total = 0.0;
            float frequency = 1.0;
            float amplitude = 1.0;
            float maxAmplitude = 0.0;
            
            for(int i = 0; i < 4; i++) {{
                total += smoothNoise(p * frequency) * amplitude;
                maxAmplitude += amplitude;
                amplitude *= 0.5;
                frequency *= 2.0;
            }}
            
            return total / maxAmplitude;
        }}
        
        // 修正后的圆形距离函数 - 确保在任何宽高比下都是圆形
        float circleDistance(vec2 p, vec2 center, float radius, vec2 resolution) {{
            // 将纹理坐标转换为屏幕空间坐标
            vec2 screenCoord = p * resolution;
            vec2 centerScreen = center * resolution;
            
            // 计算像素距离
            float distPixel = length(screenCoord - centerScreen);
            
            // 将像素距离转换为归一化距离
            // 使用较小的维度进行归一化，以确保圆形
            float normalizedDist = distPixel / min(resolution.x, resolution.y);
            
            return normalizedDist - radius;
        }}
        
        // 矩形距离函数（带圆角）
        float roundedBoxDistance(vec2 p, vec2 center, vec2 size, float cornerRadius) {{
            vec2 q = abs(p - center) - size + cornerRadius;
            return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - cornerRadius;
        }}
        
        // 简单的高斯模糊
        vec4 gaussianBlur(sampler2D tex, vec2 uv, vec2 direction, float amount) {{
            if (amount <= 0.0) return texture(tex, uv);
            
            vec4 color = vec4(0.0);
            float total = 0.0;
            
            // 高斯核权重
            float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
            
            for(int i = -4; i <= 4; i++) {{
                float weight = weights[abs(i)];
                vec2 offset = direction * float(i) * amount / u_resolution;
                color += texture(tex, uv + offset) * weight;
                total += weight;
            }}
            
            return color / total;
        }}
        
        void main() {{
            vec2 uv = TexCoord;
            vec2 center = u_mouse_pos;
            
            // 计算到玻璃边界的距离
            float dist;
            if (u_radius > 0.0) {{
                // 圆形玻璃 - 使用修正后的距离计算
                dist = circleDistance(uv, center, u_radius, u_resolution);
            }} else {{
                // 矩形玻璃（带圆角）
                dist = roundedBoxDistance(uv, center, u_rect_size, u_corner_radius);
            }}
            
            // 归一化距离（负值表示在玻璃内部）
            float normDist = dist / u_refraction_radius;
            
            // 获取原始背景颜色
            vec3 bgColor = texture(backgroundTexture, uv).rgb;
            
            // 如果完全在玻璃外，直接显示背景
            if (dist > u_refraction_radius) {{
                FragColor = vec4(bgColor, 1.0);
                return;
            }}
            
            // 计算边缘折射因子（夸张的折射效果，只在边缘区域）
            float edgeFactor = 0.0;
            if (dist > 0.0) {{
                // 在玻璃外部边缘区域
                edgeFactor = smoothstep(0.0, 1.0, dist / u_refraction_radius);
            }} else {{
                // 在玻璃内部，靠近边缘的区域
                edgeFactor = smoothstep(0.0, -1.0, dist / u_refraction_radius);
            }}
            
            // 减小中心的折射效果：使用平方函数使中心区域折射更小
            float centerFactor = 1.0 - smoothstep(0.0, u_refraction_radius, -dist);
            edgeFactor *= centerFactor;
            
            // 夸张的折射偏移（只在边缘区域）
            vec2 refractDir = normalize(uv - center);
            vec2 refractOffset = refractDir * edgeFactor * u_refraction_strength;
            
            // 添加噪声扰动，但在中心区域减小噪声
            float noiseStrengthFactor = 1.0 - smoothstep(0.0, u_refraction_radius * 0.5, -dist);
            float noise = fractalNoise((uv - center) * 10.0 + u_time * 0.5);
            refractOffset += refractDir * noise * u_noise_strength * noiseStrengthFactor;
            
            // 折射后的UV坐标
            vec2 refractUV = uv + refractOffset;
            refractUV = clamp(refractUV, 0.001, 0.999);
            
            // 应用模糊效果
            vec3 refractColor;
            if (u_blur_amount > 0.0) {{
                // 水平模糊
                vec4 horizontalBlur = gaussianBlur(backgroundTexture, refractUV, vec2(1.0, 0.0), u_blur_amount);
                // 垂直模糊
                vec4 verticalBlur = gaussianBlur(backgroundTexture, refractUV, vec2(0.0, 1.0), u_blur_amount);
                refractColor = mix(horizontalBlur.rgb, verticalBlur.rgb, 0.5);
            }} else {{
                refractColor = texture(backgroundTexture, refractUV).rgb;
            }}
            
            // 计算透明度 - 100%透明
            float alpha = u_max_transparency;  // 完全透明
            
            // 边缘区域增加不透明度
            if (abs(dist) < u_refraction_radius * 0.3) {{
                alpha = mix(alpha, u_edge_opacity, smoothstep(0.0, 1.0, abs(dist) / (u_refraction_radius * 0.3)));
            }}
            
            // 最终颜色 - 无高光效果
            vec3 finalColor = refractColor;
            
            // 应用透明度
            FragColor = vec4(finalColor, alpha);
        }}
        """
        
        return {
            'vertex': vertex_shader,
            'fragment': fragment_shader
        }
    
    def get_uniform_locations(self):
        """获取着色器uniform位置"""
        # 玻璃着色器uniform
        glUseProgram(self.glass_shader)
        self.glass_uniforms = {
            'u_radius': glGetUniformLocation(self.glass_shader, 'u_radius'),
            'u_rect_size': glGetUniformLocation(self.glass_shader, 'u_rect_size'),
            'u_corner_radius': glGetUniformLocation(self.glass_shader, 'u_corner_radius'),
            'u_refraction_radius': glGetUniformLocation(self.glass_shader, 'u_refraction_radius'),
            'u_blur_amount': glGetUniformLocation(self.glass_shader, 'u_blur_amount'),
            'u_time': glGetUniformLocation(self.glass_shader, 'u_time'),
            'u_mouse_pos': glGetUniformLocation(self.glass_shader, 'u_mouse_pos'),
            'u_resolution': glGetUniformLocation(self.glass_shader, 'u_resolution'),
            'u_glass_color': glGetUniformLocation(self.glass_shader, 'u_glass_color'),
            'u_max_transparency': glGetUniformLocation(self.glass_shader, 'u_max_transparency'),
            'u_refraction_strength': glGetUniformLocation(self.glass_shader, 'u_refraction_strength'),
            'u_noise_strength': glGetUniformLocation(self.glass_shader, 'u_noise_strength'),
            'u_edge_opacity': glGetUniformLocation(self.glass_shader, 'u_edge_opacity'),
            'backgroundTexture': glGetUniformLocation(self.glass_shader, 'backgroundTexture')
        }
        
        # 背景着色器uniform
        glUseProgram(self.background_shader)
        self.background_uniforms = {
            'u_texture': glGetUniformLocation(self.background_shader, 'u_texture')
        }
        
        glUseProgram(0)
    
    def create_quad(self):
        """创建全屏四边形"""
        vertices = np.array([
            -1.0, -1.0, 0.0, 0.0,
             1.0, -1.0, 1.0, 0.0,
             1.0,  1.0, 1.0, 1.0,
            -1.0,  1.0, 0.0, 1.0,
        ], dtype=np.float32)
        
        indices = np.array([
            0, 1, 2,
            2, 3, 0
        ], dtype=np.uint32)
        
        self.quad_vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        ebo = glGenBuffers(1)
        
        glBindVertexArray(self.quad_vao)
        
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        
        # 位置属性
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        
        # 纹理坐标属性
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(2 * 4))
        glEnableVertexAttribArray(1)
        
        glBindVertexArray(0)
    
    def create_default_background(self):
        """创建默认背景纹理"""
        width, height = 512, 512
        texture_data = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 创建网格背景
        cell_size = 32
        for y in range(height):
            for x in range(width):
                # 网格线
                if x % cell_size == 0 or y % cell_size == 0:
                    texture_data[y, x] = [100, 100, 120]
                else:
                    # 棋盘格
                    if ((x // cell_size) + (y // cell_size)) % 2 == 0:
                        texture_data[y, x] = [60, 60, 80]
                    else:
                        texture_data[y, x] = [40, 40, 60]
        
        # 创建纹理
        texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, 
                    GL_RGB, GL_UNSIGNED_BYTE, texture_data)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        
        glBindTexture(GL_TEXTURE_2D, 0)
        
        return texture
    
    def set_background_texture(self, texture):
        """设置背景纹理"""
        self.background_texture = texture
    
    def set_background_from_file(self, filepath):
        """从文件设置背景纹理"""
        try:
            img = Image.open(filepath)
            img = img.convert("RGB")
            img_data = np.array(img, dtype=np.uint8)
            
            # 创建纹理
            texture = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture)
            
            # 设置纹理参数
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            
            # 上传纹理数据
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, img.width, img.height, 0, 
                        GL_RGB, GL_UNSIGNED_BYTE, img_data)
            
            glGenerateMipmap(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, 0)
            
            self.set_background_texture(texture)
            return True
        except Exception as e:
            print(f"加载背景图片失败: {e}")
            return False
    
    def set_shape(self, shape, radius=None, rect_size=None, corner_radius=None):
        """设置玻璃形状和参数"""
        self.shape = shape
        if radius is not None:
            self.radius = radius
        if rect_size is not None:
            self.rect_size = np.array(rect_size, dtype=np.float32)
        if corner_radius is not None:
            self.corner_radius = corner_radius
        
        # 重新创建着色器以应用新的形状
        glass_shader_code = self.generate_glass_shader()
        new_shader = compileProgram(
            compileShader(glass_shader_code['vertex'], GL_VERTEX_SHADER),
            compileShader(glass_shader_code['fragment'], GL_FRAGMENT_SHADER)
        )
        
        # 删除旧着色器，使用新着色器
        if self.glass_shader:
            glDeleteProgram(self.glass_shader)
        self.glass_shader = new_shader
        self.get_uniform_locations()
    
    def set_refraction(self, refraction_radius):
        """设置折射半径"""
        self.refraction_radius = refraction_radius
    
    def set_blur(self, blur_amount):
        """设置模糊强度"""
        self.blur_amount = blur_amount
    
    def set_color(self, color):
        """设置玻璃颜色"""
        self.glass_color = np.array(color, dtype=np.float32)
    
    def set_transparency(self, transparency):
        """设置透明度"""
        self.max_transparency = transparency
    
    def set_refraction_strength(self, strength):
        """设置折射强度"""
        self.refraction_strength = max(0.0, min(0.2, strength))
    
    def set_noise_strength(self, strength):
        """设置噪声强度"""
        self.noise_strength = max(0.0, min(0.1, strength))
    
    def set_edge_opacity(self, opacity):
        """设置边缘不透明度"""
        self.edge_opacity = max(0.0, min(1.0, opacity))
    
    def update_mouse_position(self, x, y):
        """更新鼠标位置"""
        self.mouse_x = x / self.width
        self.mouse_y = 1.0 - y / self.height
    
    def update_window_size(self, width, height):
        """更新窗口大小"""
        self.width = width
        self.height = height
        glViewport(0, 0, width, height)
    
    def render(self, time):
        """渲染一帧"""
        # 清除缓冲区
        glClear(GL_COLOR_BUFFER_BIT)
        
        # 渲染背景
        glUseProgram(self.background_shader)
        glBindVertexArray(self.quad_vao)
        
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.background_texture)
        glUniform1i(self.background_uniforms['u_texture'], 0)
        
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        
        # 渲染玻璃效果
        glUseProgram(self.glass_shader)
        
        # 设置uniform值
        glUniform1f(self.glass_uniforms['u_radius'], self.radius if self.shape == 'circle' else 0.0)
        glUniform2f(self.glass_uniforms['u_rect_size'], self.rect_size[0], self.rect_size[1])
        glUniform1f(self.glass_uniforms['u_corner_radius'], self.corner_radius)
        glUniform1f(self.glass_uniforms['u_refraction_radius'], self.refraction_radius)
        glUniform1f(self.glass_uniforms['u_blur_amount'], self.blur_amount)
        glUniform1f(self.glass_uniforms['u_time'], time)
        glUniform2f(self.glass_uniforms['u_mouse_pos'], self.mouse_x, self.mouse_y)
        glUniform2f(self.glass_uniforms['u_resolution'], float(self.width), float(self.height))
        glUniform3f(self.glass_uniforms['u_glass_color'], 
                   self.glass_color[0], self.glass_color[1], self.glass_color[2])
        glUniform1f(self.glass_uniforms['u_max_transparency'], self.max_transparency)
        glUniform1f(self.glass_uniforms['u_refraction_strength'], self.refraction_strength)
        glUniform1f(self.glass_uniforms['u_noise_strength'], self.noise_strength)
        glUniform1f(self.glass_uniforms['u_edge_opacity'], self.edge_opacity)
        
        # 绑定背景纹理
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.background_texture)
        glUniform1i(self.glass_uniforms['backgroundTexture'], 0)
        
        # 启用混合
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # 绘制玻璃效果
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        
        glBindVertexArray(0)
        glUseProgram(0)
    
    def update_fps(self):
        """更新FPS显示"""
        self.frame_count += 1
        current_time = glfw.get_time()
        
        if current_time - self.last_time >= 2.0:
            self.fps = self.frame_count / 2
            self.frame_count = 0
            self.last_time = current_time
            
            # 打印FPS和参数
            shape_info = f"半径: {self.radius:.2f}" if self.shape == 'circle' else f"尺寸: {self.rect_size[0]:.2f}x{self.rect_size[1]:.2f}"
            print(f"FPS: {self.fps:.1f} | 形状: {self.shape} | {shape_info} | "
                  f"折射半径: {self.refraction_radius:.2f} | 折射强度: {self.refraction_strength:.2f} | "
                  f"噪声强度: {self.noise_strength:.2f} | 模糊: {self.blur_amount:.2f}")


# 演示程序
class LiquidGlassDemo:
    def __init__(self):
        self.width = 1200
        self.height = 800
        self.effect = None
        self.window = None
        self.current_shape = 'circle'
        
    def init(self):
        """初始化演示"""
        # 创建液态玻璃效果
        self.effect = LiquidGlassEffect(
            width=self.width,
            height=self.height,
            shape=self.current_shape,
            radius=0.15,  # 圆形半径
            rect_size=(0.2, 0.3),  # 矩形大小
            corner_radius=0.05,  # 矩形圆角
            refraction_radius=0.03,  # 折射半径
            blur_amount=0.0,  # 无模糊
            glass_color=(0.9, 0.95, 1.0),  # 淡蓝色
            max_transparency=1.0,  # 100%透明
            refraction_strength=0.03,  # 折射强度
            noise_strength=0.01,  # 噪声强度
            edge_opacity=0.8  # 边缘不透明度
        )
        
        # 获取窗口引用
        self.window = self.effect.window
        
        # 设置回调函数
        glfw.set_key_callback(self.window, self.key_callback)
        glfw.set_cursor_pos_callback(self.window, self.mouse_callback)
        glfw.set_window_size_callback(self.window, self.window_size_callback)
        
        # 尝试加载背景图片
        self.load_background_image()
        
        self.print_controls()
    
    def load_background_image(self):
        """加载背景图片"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
        image_files = []
        
        # 查找所有图片文件
        for ext in image_extensions:
            if os.path.exists(f"background{ext}"):
                image_files.append(f"background{ext}")
        
        if image_files:
            # 加载第一个找到的图片
            success = self.effect.set_background_from_file(image_files[0])
            if success:
                print(f"已加载背景图片: {image_files[0]}")
            else:
                print("使用默认背景")
        else:
            print("使用默认背景")
    
    def print_controls(self):
        """打印控制说明"""
        print("\n控制说明:")
        print("  1: 切换为圆形玻璃")
        print("  2: 切换为矩形玻璃")
        print("  上下箭头: 调整玻璃大小")
        print("  左右箭头: 调整折射半径")
        print("  +/-: 调整模糊强度")
        print("  C: 随机改变玻璃颜色")
        print("  R: 重置参数")
        print("  数字键:")
        print("    3: 增加折射强度")
        print("    4: 减小折射强度")
        print("    5: 增加噪声强度")
        print("    6: 减小噪声强度")
        print("    7: 增加边缘不透明度")
        print("    8: 减小边缘不透明度")
        print("    9: 增加透明度")
        print("    0: 减小透明度")
        print("  ESC: 退出程序")
    
    def key_callback(self, window, key, scancode, action, mods):
        """键盘回调函数"""
        if action == glfw.PRESS or action == glfw.REPEAT:
            if key == glfw.KEY_ESCAPE:
                glfw.set_window_should_close(window, True)
            elif key == glfw.KEY_1:
                self.current_shape = 'circle'
                self.effect.set_shape('circle', radius=0.15)
                print("切换到圆形玻璃")
            elif key == glfw.KEY_2:
                self.current_shape = 'rectangle'
                self.effect.set_shape('rectangle', rect_size=(0.2, 0.3), corner_radius=0.05)
                print("切换到矩形玻璃")
            elif key == glfw.KEY_UP:
                if self.current_shape == 'circle':
                    self.effect.radius = min(0.4, self.effect.radius + 0.02)
                    print(f"圆形半径: {self.effect.radius:.2f}")
                else:
                    self.effect.rect_size[0] = min(0.5, self.effect.rect_size[0] + 0.02)
                    self.effect.rect_size[1] = min(0.5, self.effect.rect_size[1] + 0.02)
                    print(f"矩形大小: {self.effect.rect_size[0]:.2f}x{self.effect.rect_size[1]:.2f}")
            elif key == glfw.KEY_DOWN:
                if self.current_shape == 'circle':
                    self.effect.radius = max(0.05, self.effect.radius - 0.02)
                    print(f"圆形半径: {self.effect.radius:.2f}")
                else:
                    self.effect.rect_size[0] = max(0.05, self.effect.rect_size[0] - 0.02)
                    self.effect.rect_size[1] = max(0.05, self.effect.rect_size[1] - 0.02)
                    print(f"矩形大小: {self.effect.rect_size[0]:.2f}x{self.effect.rect_size[1]:.2f}")
            elif key == glfw.KEY_RIGHT:
                self.effect.refraction_radius = min(0.2, self.effect.refraction_radius + 0.01)
                print(f"折射半径: {self.effect.refraction_radius:.2f}")
            elif key == glfw.KEY_LEFT:
                self.effect.refraction_radius = max(0.01, self.effect.refraction_radius - 0.01)
                print(f"折射半径: {self.effect.refraction_radius:.2f}")
            elif key == glfw.KEY_EQUAL or key == glfw.KEY_KP_ADD:  # +键
                self.effect.blur_amount = min(5.0, self.effect.blur_amount + 0.5)
                print(f"模糊强度: {self.effect.blur_amount:.1f}")
            elif key == glfw.KEY_MINUS or key == glfw.KEY_KP_SUBTRACT:  # -键
                self.effect.blur_amount = max(0.0, self.effect.blur_amount - 0.5)
                print(f"模糊强度: {self.effect.blur_amount:.1f}")
            elif key == glfw.KEY_C:
                # 随机颜色
                color = np.random.uniform(0.7, 1.0, 3)
                self.effect.set_color(color)
                print(f"玻璃颜色: R={color[0]:.2f}, G={color[1]:.2f}, B={color[2]:.2f}")
            elif key == glfw.KEY_R:
                # 重置参数
                self.reset_parameters()
            elif key == glfw.KEY_3:
                self.effect.refraction_strength = min(0.2, self.effect.refraction_strength + 0.01)
                print(f"折射强度: {self.effect.refraction_strength:.2f}")
            elif key == glfw.KEY_4:
                self.effect.refraction_strength = max(0.0, self.effect.refraction_strength - 0.01)
                print(f"折射强度: {self.effect.refraction_strength:.2f}")
            elif key == glfw.KEY_5:
                self.effect.noise_strength = min(0.1, self.effect.noise_strength + 0.005)
                print(f"噪声强度: {self.effect.noise_strength:.3f}")
            elif key == glfw.KEY_6:
                self.effect.noise_strength = max(0.0, self.effect.noise_strength - 0.005)
                print(f"噪声强度: {self.effect.noise_strength:.3f}")
            elif key == glfw.KEY_7:
                self.effect.edge_opacity = min(1.0, self.effect.edge_opacity + 0.05)
                print(f"边缘不透明度: {self.effect.edge_opacity:.2f}")
            elif key == glfw.KEY_8:
                self.effect.edge_opacity = max(0.0, self.effect.edge_opacity - 0.05)
                print(f"边缘不透明度: {self.effect.edge_opacity:.2f}")
            elif key == glfw.KEY_9:
                self.effect.max_transparency = min(1.0, self.effect.max_transparency + 0.05)
                print(f"透明度: {self.effect.max_transparency:.2f}")
            elif key == glfw.KEY_0:
                self.effect.max_transparency = max(0.0, self.effect.max_transparency - 0.05)
                print(f"透明度: {self.effect.max_transparency:.2f}")
    
    def reset_parameters(self):
        """重置参数"""
        if self.current_shape == 'circle':
            self.effect.set_shape('circle', radius=0.15)
        else:
            self.effect.set_shape('rectangle', rect_size=(0.2, 0.3), corner_radius=0.05)
        self.effect.set_refraction(0.03)
        self.effect.set_blur(0.0)
        self.effect.set_color((0.9, 0.95, 1.0))
        self.effect.set_transparency(1.0)
        self.effect.set_refraction_strength(0.03)
        self.effect.set_noise_strength(0.01)
        self.effect.set_edge_opacity(0.8)
        print("参数已重置")
    
    def mouse_callback(self, window, xpos, ypos):
        """鼠标回调函数"""
        self.effect.update_mouse_position(xpos, ypos)
    
    def window_size_callback(self, window, width, height):
        """窗口大小回调函数"""
        self.effect.update_window_size(width, height)
    
    def run(self):
        """运行演示"""
        self.init()
        
        print("\n液态玻璃演示启动...")
        print("移动鼠标控制玻璃位置")
        
        while not glfw.window_should_close(self.window):
            # 渲染
            current_time = glfw.get_time()
            self.effect.render(current_time)
            
            # 更新FPS显示
            self.effect.update_fps()
            
            # 交换缓冲区和处理事件
            glfw.swap_buffers(self.window)
            glfw.poll_events()
        
        # 清理
        glfw.terminate()

if __name__ == "__main__":
    try:
        demo = LiquidGlassDemo()
        demo.run()
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()