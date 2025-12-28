import glfw
import numpy as np
import math
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image
import os
import random

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
        enable_second_glass: 是否启用第二个玻璃
        blend_strength: 融合强度，控制两个玻璃靠近时的融合程度
    """
    def __init__(self, width=1200, height=800, shape='circle', radius=0.15, 
                 rect_size=(0.2, 0.3), corner_radius=0.05, refraction_radius=0.05,
                 blur_amount=0.0, glass_color=(0.9, 0.95, 1.0), max_transparency=1.0,
                 refraction_strength=0.03, noise_strength=0.01, edge_opacity=0.8,
                 enable_second_glass=True, blend_strength=0.3):
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
        
        # 双玻璃参数
        self.enable_second_glass = enable_second_glass
        self.blend_strength = blend_strength  # 融合强度
        
        # 鼠标位置（控制第一个玻璃）
        self.mouse_x = 0.5
        self.mouse_y = 0.5
        
        # 第二个玻璃的位置和参数
        self.glass2_x = 0.3
        self.glass2_y = 0.3
        self.glass2_radius = radius * 0.8  # 第二个玻璃稍小一些
        self.glass2_color = np.array([0.95, 0.9, 1.0], dtype=np.float32)  # 淡紫色
        self.glass2_velocity = [0.003, 0.002]  # 自动移动速度
        
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
            print(f"玻璃1半径: {self.radius}")
            if self.enable_second_glass:
                print(f"玻璃2半径: {self.glass2_radius}")
        else:
            print(f"矩形大小: {self.rect_size[0]}x{self.rect_size[1]}")
            print(f"圆角半径: {self.corner_radius}")
        print(f"折射半径: {self.refraction_radius}")
        print(f"折射强度: {self.refraction_strength}")
        print(f"噪声强度: {self.noise_strength}")
        print(f"模糊强度: {self.blur_amount}")
        print(f"边缘不透明度: {self.edge_opacity}")
        if self.enable_second_glass:
            print(f"双玻璃融合: 启用")
            print(f"融合强度: {self.blend_strength}")
    
    def init_glfw(self):
        """初始化GLFW窗口"""
        if not glfw.init():
            raise Exception("GLFW初始化失败")
        
        # 创建窗口
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)
        
        self.window = glfw.create_window(self.width, self.height, "Liquid Glass Effect - Dual Glass with Blending", None, None)
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
        uniform float u_radius2;
        uniform vec2 u_rect_size;
        uniform float u_corner_radius;
        uniform float u_refraction_radius;
        uniform float u_blur_amount;
        uniform float u_time;
        uniform vec2 u_mouse_pos;
        uniform vec2 u_mouse_pos2;
        uniform vec2 u_resolution;
        uniform vec3 u_glass_color;
        uniform vec3 u_glass_color2;
        uniform float u_max_transparency;
        uniform float u_refraction_strength;
        uniform float u_noise_strength;
        uniform float u_edge_opacity;
        uniform bool u_enable_second_glass;
        uniform float u_blend_strength;
        
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
        
        // 平滑最小值函数 (用于融合两个玻璃)
        float smin(float a, float b, float k) {{
            float h = clamp(0.5 + 0.5*(b-a)/k, 0.0, 1.0);
            return mix(b, a, h) - k*h*(1.0-h);
        }}
        
        void main() {{
            vec2 uv = TexCoord;
            vec2 center1 = u_mouse_pos;
            vec2 center2 = u_mouse_pos2;
            
            // 计算两个玻璃的距离
            float dist1 = circleDistance(uv, center1, u_radius, u_resolution);
            float dist2 = 1000.0;  // 初始化为大值
            
            if (u_enable_second_glass) {{
                dist2 = circleDistance(uv, center2, u_radius2, u_resolution);
            }}
            
            // 计算两个玻璃中心的距离
            float glassDistance = length(center1 - center2);
            
            // 计算融合因子 - 当两个玻璃靠近时增加融合
            float blendFactor = 0.0;
            if (u_enable_second_glass) {{
                // 计算两个玻璃的接近程度
                float maxDistance = u_radius + u_radius2 + 0.1;
                blendFactor = 1.0 - smoothstep(0.0, maxDistance, glassDistance);
                blendFactor *= u_blend_strength;
            }}
            
            // 计算融合后的距离
            float dist;
            if (u_enable_second_glass && blendFactor > 0.001) {{
                // 双玻璃融合模式 - 使用平滑最小值
                dist = smin(dist1, dist2, blendFactor * 0.1);
            }} else {{
                // 单玻璃模式或第二个玻璃未启用
                dist = dist1;
            }}
            
            // 判断当前片段是否在任何玻璃的折射半径内
            bool inGlass1 = dist1 <= u_refraction_radius;
            bool inGlass2 = u_enable_second_glass && dist2 <= u_refraction_radius;
            
            // 如果不在任何玻璃的折射半径内，直接显示背景
            if (!inGlass1 && !inGlass2) {{
                FragColor = vec4(texture(backgroundTexture, uv).rgb, 1.0);
                return;
            }}
            
            // 计算当前片段主要受哪个玻璃影响
            float mainDist = dist;
            vec2 mainCenter = center1;
            vec3 mainColor = u_glass_color;
            
            // 如果更靠近第二个玻璃，则使用第二个玻璃的参数
            if (u_enable_second_glass && abs(dist2) < abs(dist1)) {{
                mainDist = dist2;
                mainCenter = center2;
                mainColor = u_glass_color2;
            }}
            
            // 在融合区域，使用融合后的参数
            if (u_enable_second_glass && blendFactor > 0.01) {{
                // 根据距离权重混合中心
                float weight1 = 1.0 - smoothstep(0.0, u_refraction_radius, abs(dist1));
                float weight2 = 1.0 - smoothstep(0.0, u_refraction_radius, abs(dist2));
                float totalWeight = weight1 + weight2;
                if (totalWeight > 0.0) {{
                    mainCenter = (center1 * weight1 + center2 * weight2) / totalWeight;
                    mainColor = (u_glass_color * weight1 + u_glass_color2 * weight2) / totalWeight;
                }}
                
                // 使用融合后的距离
                mainDist = dist;
            }}
            
            // 计算边缘折射因子
            float edgeFactor = 0.0;
            if (mainDist > 0.0) {{
                // 在玻璃外部边缘区域
                edgeFactor = smoothstep(0.0, 1.0, mainDist / u_refraction_radius);
            }} else {{
                // 在玻璃内部，靠近边缘的区域
                edgeFactor = smoothstep(0.0, -1.0, mainDist / u_refraction_radius);
            }}
            
            // 减小中心的折射效果
            float centerFactor = 1.0 - smoothstep(0.0, u_refraction_radius, -mainDist);
            edgeFactor *= centerFactor;
            
            // 折射方向
            vec2 refractDir = normalize(uv - mainCenter);
            
            // 夸张的折射偏移（只在边缘区域）
            vec2 refractOffset = refractDir * edgeFactor * u_refraction_strength;
            
            // 添加噪声扰动
            float noiseStrengthFactor = 1.0 - smoothstep(0.0, u_refraction_radius * 0.5, -mainDist);
            float noise = fractalNoise((uv - mainCenter) * 10.0 + u_time * 0.5);
            refractOffset += refractDir * noise * u_noise_strength * noiseStrengthFactor;
            
            // 在融合区域添加额外的噪声扰动
            if (u_enable_second_glass && blendFactor > 0.01) {{
                float noise2 = fractalNoise((uv - center2) * 12.0 + u_time * 0.7);
                refractOffset += normalize(uv - center2) * noise2 * u_noise_strength * 0.5 * blendFactor;
            }}
            
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
            
            // 计算透明度
            float alpha = u_max_transparency;
            
            // 边缘区域增加不透明度
            if (abs(mainDist) < u_refraction_radius * 0.3) {{
                alpha = mix(alpha, u_edge_opacity, smoothstep(0.0, 1.0, abs(mainDist) / (u_refraction_radius * 0.3)));
            }}
            
            // 在融合区域调整透明度
            if (u_enable_second_glass && blendFactor > 0.01) {{
                // 在融合区域增加透明度变化
                float blendAlpha = u_max_transparency * (1.0 + blendFactor * 0.3);
                alpha = mix(alpha, blendAlpha, blendFactor);
            }}
            
            // 最终颜色
            vec3 finalColor = refractColor * mainColor;
            
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
            'u_radius2': glGetUniformLocation(self.glass_shader, 'u_radius2'),
            'u_rect_size': glGetUniformLocation(self.glass_shader, 'u_rect_size'),
            'u_corner_radius': glGetUniformLocation(self.glass_shader, 'u_corner_radius'),
            'u_refraction_radius': glGetUniformLocation(self.glass_shader, 'u_refraction_radius'),
            'u_blur_amount': glGetUniformLocation(self.glass_shader, 'u_blur_amount'),
            'u_time': glGetUniformLocation(self.glass_shader, 'u_time'),
            'u_mouse_pos': glGetUniformLocation(self.glass_shader, 'u_mouse_pos'),
            'u_mouse_pos2': glGetUniformLocation(self.glass_shader, 'u_mouse_pos2'),
            'u_resolution': glGetUniformLocation(self.glass_shader, 'u_resolution'),
            'u_glass_color': glGetUniformLocation(self.glass_shader, 'u_glass_color'),
            'u_glass_color2': glGetUniformLocation(self.glass_shader, 'u_glass_color2'),
            'u_max_transparency': glGetUniformLocation(self.glass_shader, 'u_max_transparency'),
            'u_refraction_strength': glGetUniformLocation(self.glass_shader, 'u_refraction_strength'),
            'u_noise_strength': glGetUniformLocation(self.glass_shader, 'u_noise_strength'),
            'u_edge_opacity': glGetUniformLocation(self.glass_shader, 'u_edge_opacity'),
            'u_enable_second_glass': glGetUniformLocation(self.glass_shader, 'u_enable_second_glass'),
            'u_blend_strength': glGetUniformLocation(self.glass_shader, 'u_blend_strength'),
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
            self.glass2_radius = radius * 0.8
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
        # 第二个玻璃使用互补色
        self.glass2_color = np.array([1.0 - color[0] * 0.5, 
                                      1.0 - color[1] * 0.5, 
                                      color[2]], dtype=np.float32)
    
    def set_second_glass_color(self, color):
        """设置第二个玻璃颜色"""
        self.glass2_color = np.array(color, dtype=np.float32)
    
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
    
    def set_blend_strength(self, strength):
        """设置融合强度"""
        self.blend_strength = max(0.0, min(1.0, strength))
    
    def set_glass2_position(self, x, y):
        """设置第二个玻璃的位置"""
        self.glass2_x = x
        self.glass2_y = y
    
    def set_glass2_radius(self, radius):
        """设置第二个玻璃的半径"""
        self.glass2_radius = radius
    
    def get_glass2_info(self):
        """获取第二个玻璃的信息"""
        return {
            'x': self.glass2_x,
            'y': self.glass2_y,
            'radius': self.glass2_radius,
            'color': self.glass2_color.tolist(),
            'enabled': self.enable_second_glass
        }
    
    def toggle_second_glass(self):
        """切换第二个玻璃的启用状态"""
        self.enable_second_glass = not self.enable_second_glass
        return self.enable_second_glass
    
    def update_second_glass_position(self):
        """更新第二个玻璃的位置（自动移动）"""
        if not self.enable_second_glass:
            return
        
        # 更新位置
        self.glass2_x += self.glass2_velocity[0]
        self.glass2_y += self.glass2_velocity[1]
        
        # 边界检查，反弹
        if self.glass2_x <= 0.1 or self.glass2_x >= 0.9:
            self.glass2_velocity[0] = -self.glass2_velocity[0]
            self.glass2_x = max(0.1, min(0.9, self.glass2_x))
        if self.glass2_y <= 0.1 or self.glass2_y >= 0.9:
            self.glass2_velocity[1] = -self.glass2_velocity[1]
            self.glass2_y = max(0.1, min(0.9, self.glass2_y))
    
    def update_mouse_position(self, x, y):
        """更新鼠标位置（控制第一个玻璃）"""
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
        glUniform1f(self.glass_uniforms['u_radius2'], self.glass2_radius if self.shape == 'circle' else 0.0)
        glUniform2f(self.glass_uniforms['u_rect_size'], self.rect_size[0], self.rect_size[1])
        glUniform1f(self.glass_uniforms['u_corner_radius'], self.corner_radius)
        glUniform1f(self.glass_uniforms['u_refraction_radius'], self.refraction_radius)
        glUniform1f(self.glass_uniforms['u_blur_amount'], self.blur_amount)
        glUniform1f(self.glass_uniforms['u_time'], time)
        glUniform2f(self.glass_uniforms['u_mouse_pos'], self.mouse_x, self.mouse_y)
        glUniform2f(self.glass_uniforms['u_mouse_pos2'], self.glass2_x, self.glass2_y)
        glUniform2f(self.glass_uniforms['u_resolution'], float(self.width), float(self.height))
        glUniform3f(self.glass_uniforms['u_glass_color'], 
                   self.glass_color[0], self.glass_color[1], self.glass_color[2])
        glUniform3f(self.glass_uniforms['u_glass_color2'], 
                   self.glass2_color[0], self.glass2_color[1], self.glass2_color[2])
        glUniform1f(self.glass_uniforms['u_max_transparency'], self.max_transparency)
        glUniform1f(self.glass_uniforms['u_refraction_strength'], self.refraction_strength)
        glUniform1f(self.glass_uniforms['u_noise_strength'], self.noise_strength)
        glUniform1f(self.glass_uniforms['u_edge_opacity'], self.edge_opacity)
        glUniform1i(self.glass_uniforms['u_enable_second_glass'], self.enable_second_glass)
        glUniform1f(self.glass_uniforms['u_blend_strength'], self.blend_strength)
        
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
            
            # 计算两个玻璃的距离
            dx = self.mouse_x - self.glass2_x
            dy = self.mouse_y - self.glass2_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # 打印FPS和参数
            shape_info = f"半径: {self.radius:.2f}" if self.shape == 'circle' else f"尺寸: {self.rect_size[0]:.2f}x{self.rect_size[1]:.2f}"
            glass2_info = f"玻璃2: ({self.glass2_x:.2f}, {self.glass2_y:.2f})" if self.enable_second_glass else "单玻璃"
            print(f"FPS: {self.fps:.1f} | 形状: {self.shape} | {shape_info} | "
                  f"折射强度: {self.refraction_strength:.2f} | 噪声: {self.noise_strength:.2f} | "
                  f"融合强度: {self.blend_strength:.2f} | {glass2_info} | "
                  f"距离: {distance:.2f}")




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
            edge_opacity=0.8,  # 边缘不透明度
            enable_second_glass=True,  # 启用第二个玻璃
            blend_strength=0.3  # 融合强度
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
            if os.path.exists(f"8{ext}"):
                image_files.append(f"8{ext}")
        
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
        print("  鼠标: 控制第一个玻璃的位置")
        print("  1: 切换为圆形玻璃")
        print("  2: 切换为矩形玻璃")
        print("  上下箭头: 调整玻璃大小")
        print("  左右箭头: 调整折射半径")
        print("  +/-: 调整模糊强度")
        print("  C: 随机改变玻璃颜色")
        print("  V: 随机改变第二个玻璃颜色")
        print("  R: 重置参数")
        print("  B: 切换第二个玻璃的启用状态")
        print("  N/M: 调整融合强度 (N减小, M增加)")
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
        print("\n提示: 让两个玻璃靠近观察融合效果!")
    
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
                    self.effect.glass2_radius = self.effect.radius * 0.8
                    print(f"圆形半径: {self.effect.radius:.2f}")
                else:
                    self.effect.rect_size[0] = min(0.5, self.effect.rect_size[0] + 0.02)
                    self.effect.rect_size[1] = min(0.5, self.effect.rect_size[1] + 0.02)
                    print(f"矩形大小: {self.effect.rect_size[0]:.2f}x{self.effect.rect_size[1]:.2f}")
            elif key == glfw.KEY_DOWN:
                if self.current_shape == 'circle':
                    self.effect.radius = max(0.05, self.effect.radius - 0.02)
                    self.effect.glass2_radius = self.effect.radius * 0.8
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
                print(f"玻璃1颜色: R={color[0]:.2f}, G={color[1]:.2f}, B={color[2]:.2f}")
            elif key == glfw.KEY_V:
                # 随机第二个玻璃颜色
                color = np.random.uniform(0.7, 1.0, 3)
                self.effect.set_second_glass_color(color)
                print(f"玻璃2颜色: R={color[0]:.2f}, G={color[1]:.2f}, B={color[2]:.2f}")
            elif key == glfw.KEY_R:
                # 重置参数
                self.reset_parameters()
            elif key == glfw.KEY_B:
                # 切换第二个玻璃
                enabled = self.effect.toggle_second_glass()
                status = "启用" if enabled else "禁用"
                print(f"第二个玻璃: {status}")
            elif key == glfw.KEY_N:
                self.effect.blend_strength = max(0.0, self.effect.blend_strength - 0.05)
                print(f"融合强度: {self.effect.blend_strength:.2f}")
            elif key == glfw.KEY_M:
                self.effect.blend_strength = min(1.0, self.effect.blend_strength + 0.05)
                print(f"融合强度: {self.effect.blend_strength:.2f}")
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
        self.effect.set_second_glass_color((0.95, 0.9, 1.0))
        self.effect.set_transparency(1.0)
        self.effect.set_refraction_strength(0.03)
        self.effect.set_noise_strength(0.01)
        self.effect.set_edge_opacity(0.8)
        self.effect.set_blend_strength(0.3)
        self.effect.enable_second_glass = True
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
        print("移动鼠标控制第一个玻璃位置")
        print("第二个玻璃会自动移动")
        print("让两个玻璃靠近观察融合效果!")
        
        while not glfw.window_should_close(self.window):
            # 更新第二个玻璃的位置
            self.effect.update_second_glass_position()
            
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