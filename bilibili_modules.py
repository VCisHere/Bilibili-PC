import requests


class BilibiliRecommendItem:
    def __init__(self):
        self.title = ""
        self.cover_url = ""
        self.url = ""
        self.description = []


class BilibiliUser:
    app_key = "bca7e84c2d947ac6"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {'User-Agent': "Mozilla/5.0 BiliDroid/6.4.0 (bbcallen@gmail.com) os/android model/M1903F11I mobi_app/android build/6040500 channel/bili innerVer/6040500 osVer/9.0.0 network/2"})
        self.get_cookies = lambda: self.session.cookies.get_dict(
            domain=".bilibili.com")
        self.get_csrf = lambda: self.get_cookies().get("bili_jct", "")
        self.get_sid = lambda: self.get_cookies().get("sid", "")
        self.get_uid = lambda: self.get_cookies().get("DedeUserID", "")
        self.get_sessdata = lambda: self.get_cookies().get("SESSDATA", "")
        self.access_token = ""
        self.refresh_token = ""
        self.username = ""
        self.password = ""
        self.info = {
            'coins': 0,
            'experience': {
                'current': 0,
                'next': 0,
            },
            'face': "",
            'level': 0,
            'nickname': "",
        }
        self.isLogin = False
