import os
import time

import ffmpeg
import qrcode
import requests as rq
import threading

import wbiSigned as wbi


# user_agent = "LiquidGlassBilibili Client/0.0.1 (intmainreturn@outlook.com)"
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'

# 禁用所有代理相关环境变量
proxy_env_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
for proxy_var in proxy_env_vars:
    os.environ.pop(proxy_var, None)  # 移除环境变量


class GetVideoInfo:
    def __init__(self, id, cid):
        self.id = id
        self.cid = cid
        if id[0:2] == "BV":
            self.url = f"https://api.bilibili.com/x/web-interface/view?bvid={id}"
        else:
            self.url =f"https://api.bilibili.com/x/web-interface/wbi/view?avid={id}"
        
        # 使用Cookie
        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # 解析Cookie文件中的每一行
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]  # 格式：域名、标志、路径等 -> 键值对

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        
        response = rq.get(self.url, headers=headers, cookies=cookies)
        response.raise_for_status()  # 检查HTTP状态码
        self.info = response.json()
    
    # 判断是否获取成功
    def is_success(self):
        return self.info.get("code") == 0

    def get_video_info(self):
        if not self.is_success():
            return None
        
        data = self.info.get("data", {})
        video_info = {
            "title": data.get("title", ""),
            "duration": data.get("duration", 0),
            "thumbnail_path": data.get("pic", ""),
            "upname": data.get("owner", {}).get("name", ""),
            "release_time": data.get("pubdate", 0),
            "bvid": data.get("bvid", ""),
            "avid": data.get("aid", ""),
        }
        return video_info

    def get_video_duration(self):
        """获取视频时长（秒）"""
        if not self.is_success():
            return 0
        return self.info.get("data", {}).get("duration", 0)


    def get_video_streaming_info_dash(self):
        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # 解析Cookie文件中的每一行
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?bvid={self.id}&cid={self.cid}&qn=112&fnval=4048"
        response = rq.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        info = response.json()
        
        # 解析DASH格式数据
        dash_data = info.get("data", {}).get("dash", {})
        if not dash_data:
            raise Exception("无法获取DASH格式视频信息")
        
        video_url = dash_data.get("video", [{}])[0].get("baseUrl", "")
        audio_url = dash_data.get("audio", [{}])[0].get("baseUrl", "")
        if not video_url or not audio_url:
            raise Exception("无法获取视频或音频URL")

        return video_url, audio_url
    
    def get_video_streaming_info_mp4(self):
        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # 解析Cookie文件中的每一行
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
        }

        url = f"https://api.bilibili.com/x/player/wbi/playurl?bvid={self.id}&cid={self.cid}&qn=112&fnval=1"
        response = rq.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        info = response.json()
        # 解析MP4格式数据
        mp4_data = info.get("data", {}).get("durl", [{}])[0]
        if not mp4_data:
            raise Exception("无法获取MP4格式视频信息")
        
        video_url = mp4_data.get("url", "")
        if not video_url:
            raise Exception("无法获取视频URL")

        return video_url


# 获取推荐
class GetRecommendVideos:
    def __init__(self, page=1, pagesize=20):

        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                # 解析Cookie文件中的每一行
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]  # 格式：域名、标志、路径等 -> 键值对

        self.page = page
        self.pagesize = pagesize
        self.url = f"https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd?page={self.page}&pagesize={self.pagesize}"
        
        # 使用Cookie
        with open("Cookie","r") as f:
            self.cookie = f.read()

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com",

        }

        response = rq.get(self.url, headers=headers, cookies=cookies)
        response.raise_for_status()  # 检查HTTP状态码
        self.info = response.json()
        

    def get_recommend_videos(self):
        if not self.info.get("code") == 0:
            return None
        
        return self.info.get("data", {}).get("item", [])

class Download:
    def download_thumbnail(self, thumbnail_url, save_path, max_retries=3):
        """下载视频缩略图到指定路径"""
        for attempt in range(max_retries):
            try:
                response = rq.get(thumbnail_url, timeout=10)
                response.raise_for_status()
                with open(save_path, "wb") as f:
                    f.write(response.content)
                return True
            except Exception as e:
                print(f"下载失败 ({attempt+1}/{max_retries}): {str(e)}")
        return False
    
    def download_video(self, video_bvid, video_cid, save_path, callback=None):
        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        # 获取视频流信息
        url = f"https://api.bilibili.com/x/player/wbi/playurl?bvid={video_bvid}&cid={video_cid}&qn=112&fnval=4048"
        response = rq.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        info = response.json()
        
        # 解析DASH格式数据
        dash_data = info.get("data", {}).get("dash", {})
        if not dash_data:
            raise Exception("无法获取DASH格式视频信息")

        video_url = dash_data.get("video", [{}])[0].get("baseUrl", "")
        audio_url = dash_data.get("audio", [{}])[0].get("baseUrl", "")

        # 临时文件路径
        video_save_path = f"./temp/{video_bvid}-video.m4s"
        audio_save_path = f"./temp/{video_bvid}-audio.m4s"

        # 创建下载线程
        video_thread = threading.Thread(
            target=self._download_task,
            args=(video_url, video_save_path, "视频流", headers, cookies)
        )
        audio_thread = threading.Thread(
            target=self._download_task,
            args=(audio_url, audio_save_path, "音频流", headers, cookies)
        )

        # 启动线程
        video_thread.start()
        audio_thread.start()

        # 等待线程完成
        video_thread.join()
        audio_thread.join()

        # 检查下载结果
        if not all([os.path.exists(video_save_path), os.path.exists(audio_save_path)]):
            raise Exception("视频或音频流下载失败")

        # 混流处理
        try:
            video_input = ffmpeg.input(video_save_path)
            audio_input = ffmpeg.input(audio_save_path)
            ffmpeg.output(
                video_input, 
                audio_input, 
                save_path, 
                vcodec='copy', 
                acodec='copy', 
                loglevel='error'
            ).run(overwrite_output=True)
        except ffmpeg.Error as e:
            raise Exception(f"混流失败: {e.stderr.decode()}")
        finally:
            # 清理临时文件
            os.remove(video_save_path)
            os.remove(audio_save_path)

        print(f"视频合成完成: {save_path}")

        if callback:
            callback()

    def _download_task(self, url, save_path, task_name, headers, cookies):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with rq.get(url, headers=headers, cookies=cookies, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(save_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                progress = downloaded / total_size * 100
                                print(f"[{task_name}] 进度: {progress:.1f}%", end='\r')
                    print(f"\n[{task_name}] 下载完成")
                    return True
            except Exception as e:
                print(f"[{task_name}] 第 {attempt+1} 次尝试失败: {str(e)}")
                time.sleep(2)
        raise Exception(f"[{task_name}] 下载失败，已达最大重试次数")
    
    def download_user_face(self, save_path):

        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        user_data = GetUserInfo().get_user_info()
        url = user_data["face"]

        response = rq.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        

class QrLogin:
    def __init__(self):
        # 修复Cookie读取方式
        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        # 使用cookies参数代替header中的Cookie
        self.info = rq.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
            headers=headers,
            cookies=cookies
        )
        self.url = self.info.json().get("data", {}).get("url", "")
        self.qrcode_key = self.info.json().get("data", {}).get("qrcode_key", "")
    
    def get_qrcode(self):
        qrcode.make(self.url).save("./temp/qrcode.png")
        return "./temp/qrcode.png"
    
    def get_info(self):
        return self.qrcode_key
    
    # 确认是否登录
    def check_login(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }
        
        try:
            # 使用requests发送请求
            response = rq.get(
                "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
                params={"qrcode_key": self.qrcode_key},
                headers=headers
            )
            response.raise_for_status()

            # 保存Cookie（使用Netscape格式）
            with open("Cookie", "w") as f:
                for cookie in response.cookies:
                    # 生成符合Netscape格式的Cookie行
                    cookie_line = f".bilibili.com\tTRUE\t/\t{'TRUE' if cookie.secure else 'FALSE'}\t{cookie.expires or '0'}\t{cookie.name}\t{cookie.value}\n"
                    f.write(cookie_line)

            # 返回登录状态码
            return response.json().get("data", {}).get("code", 0)
            
        except Exception as e:
            print(f"登录验证失败: {str(e)}")
            return -1  # 返回错误状态码

class GetUserInfo:
    def __init__(self):
        self.url = "https://api.bilibili.com/x/web-interface/nav"

        cookies = {}
        with open("Cookie", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }
        self.info = rq.get(self.url, headers=self.headers,cookies=cookies)
        self.info = self.info.json()
    
    def get_user_info(self):
        info = self.info.get("data", {})
        user_info = {
            "name": info.get("uname", ""),
            "mid": info.get("mid", 0),
            "vip": info.get("vipStatus", 0),
            "vip_type": info.get("vipType", 0),
            "vip_pay_type": info.get("vip_pay_type", 0),
            "vip_label": info.get("vip_label", 0),
            "vip_nickname_color": info.get("vip_nickname_color", ""),
            "vip_due_date": info.get("vipDueDate", 0),
            "current_level":info.get("level_info", {}).get("current_level", 0),
            "current_exp":info.get("level_info", {}).get("current_exp", 0),
            "current_min":info.get("level_info", {}).get("current_min", 0),
            "next_exp":info.get("level_info", {}).get("next_exp", 0),
            "face":info.get("face", ""),
            "is_login":info.get("isLogin", 0),
            "money":info.get("money", 0),
        }
        if self.info.get("code", 0) != 0:
            return None
        
        return user_info


if __name__ == "__main__":
    # video_id = "BV1xV411d7b2"  # Example video ID
    # video_info = GetVideoInfo(video_id)
    # print(video_info.get_video_info())
    # recommend = GetRecommendVideos()
    # print(recommend.get_recommend_videos())
    # user_info = GetUserInfo()
    # user_data = user_info.get_user_info()
    # print(user_data)
    # Download().download_user_face(user_data["face"], "./temp/face.jpg")
    # Download().download_video("BV1aAhPzdEJ8","31374511005","./temp/demo.mp4")
    # a = QrLogin()
    # a.get_qrcode()
    # a.check_login()
    # print(GetRecommendVideos(page=1, pagesize=12).get_recommend_videos())
    # print(GetVideoInfo("BV1aAhPzdEJ8","31374511005").get_video_duration())
    # print(GetVideoInfo("BV1aAhPzdEJ8","31374511005").get_video_streaming_info_mp4())
    Download().download_user_face("./temp/face.jpg")
    pass