import base64
import hashlib
from typing import List
import requests
import rsa
import time
from urllib import parse
from bilibili_modules import BilibiliRecommendItem, BilibiliUser
import logging


class Bilibili:

    @staticmethod
    def calc_sign(param):
        salt = "60698ba2f68e01ce44738920a0ffe768"
        sign_hash = hashlib.md5()
        sign_hash.update(f"{param}{salt}".encode())
        return sign_hash.hexdigest()

    def login_prepare(self, user: BilibiliUser):
        url = "https://passport.bilibili.com/api/oauth2/getKey"
        payload = {
            'appkey': user.app_key,
            'sign': self.calc_sign(f"appkey={user.app_key}")
        }
        try:
            response = user.session.post(url, data=payload)
            if response.ok:
                response_json = response.json()
            return {
                'key_hash': response_json['data']['hash'],
                'pub_key': rsa.PublicKey.load_pkcs1_openssl_pem(response_json['data']['key'].encode()),
            }
        except:
            logging.getLogger("bili_str").info("网络错误")
            return None

    def login_token(self, user: BilibiliUser):
        param = f"access_key={user.access_token}&appkey={user.app_key}&ts={int(time.time())}"
        url = f"https://passport.bilibili.com/api/v2/oauth2/info?{param}&sign={self.calc_sign(param)}"
        try:
            response = user.session.get(url)
            if (response.ok):
                response_json = response.json()
            if ('code' in response_json):
                if (response_json['code'] == 0):
                    user.session.cookies.set('DedeUserID', str(
                        response_json['data']['mid']), domain=".bilibili.com")
                    logging.getLogger("bili_str").info(
                        f"Token仍有效, 有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + int(response_json['data']['expires_in'])))}")
                    param = f"access_key={user.access_token}&appkey={user.app_key}&gourl=http%3A%2F%2Faccount.bilibili.com%2Faccount%2Fhome&ts={int(time.time())}"
                    url = f"https://passport.bilibili.com/api/login/sso?{param}&sign={self.calc_sign(param)}"
                    user.session.get(url)
                    if all(key in user.get_cookies() for key in ["bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "SESSDATA"]):
                        logging.getLogger("bili_str").info("Cookie获取成功")
                        logging.getLogger("bili_str").info("登录成功")
                        user.isLogin = True
                        return True
                    else:
                        logging.getLogger("bili_str").info("Cookie获取失败")
                else:
                    logging.getLogger("bili_str").info("Token无效或无Token，请先登录")
        except:
            logging.getLogger("bili_str").info("网络错误")
        return False

    def refresh_user_token(self, user: BilibiliUser):
        url = "https://passport.bilibili.com/api/v2/oauth2/refresh_token"
        param = f"access_key={user.access_token}&appkey={user.app_key}&refresh_token={user.refresh_token}&ts={int(time.time())}"
        payload = f"{param}&sign={self.calc_sign(param)}"
        headers = {'Content-type': "application/x-www-form-urlencoded"}
        try:
            response = user.session.post(url, data=payload, headers=headers)
            if (response.ok):
                response_json = response.json()
                if ('code' in response_json):
                    if (response_json['code'] == 0):
                        for cookie in response_json['data']['cookie_info']['cookies']:
                            user.session.cookies.set(
                                cookie['name'], cookie['value'], domain=".bilibili.com")
                            user.access_token = response_json['data']['token_info']['access_token']
                            user.refresh_token = response_json['data']['token_info']['refresh_token']
                            logging.getLogger("bili_str").info(
                                f"Token刷新成功, 有效期至{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + int(response_json['data']['token_info']['expires_in'])))}")
                            return True
            logging.getLogger("bili_str").info("Token刷新失败")
        except:
            logging.getLogger("bili_str").info("网络错误")
        return False

    def captcha_test(self, user: BilibiliUser):
        captchaUrl = "https://passport.bilibili.com/captcha"
        headers = {'Host': "passport.bilibili.com"}
        response = user.session.get(
            captchaUrl, headers=headers)
        logging.getLogger("bili_pic").info(
            base64.b64encode(response.content).decode("utf-8"))

    def login_password(self, user: BilibiliUser, version="v2", captcha=None):
        key = self.login_prepare(user)
        if key == None:
            logging.getLogger("bili_str").info("登录失败")
            return
        key_hash, pub_key = key['key_hash'], key['pub_key']
        url = f"https://passport.bilibili.com/api/{version}/oauth2/login"
        if captcha == None:
            param = f"appkey={user.app_key}&password={parse.quote_plus(base64.b64encode(rsa.encrypt(f'{key_hash}{user.password}'.encode(), pub_key)))}&username={parse.quote_plus(user.username)}"
        else:
            param = f"appkey={user.app_key}&captcha={captcha}&password={parse.quote_plus(base64.b64encode(rsa.encrypt(f'{key_hash}{user.password}'.encode(), pub_key)))}&username={parse.quote_plus(user.username)}"
        payload = f"{param}&sign={self.calc_sign(param)}"
        headers = {'Content-type': "application/x-www-form-urlencoded"}
        try:
            response = user.session.post(url, data=payload, headers=headers)
            if response.ok:
                response_json = response.json()
                if ('code' in response_json):
                    if (response_json['code'] == -449):
                        logging.getLogger("bili_str").info(
                            "服务器繁忙，尝试使用v3接口登录...")
                        self.login_password(user, "v3", captcha)
                        return

                    elif response_json['code'] == -105 or response_json['code'] == 0 and response_json['data']['status'] == 2:
                        captchaUrl = "https://passport.bilibili.com/captcha"
                        headers = {'Host': "passport.bilibili.com"}
                        captchaResponse = user.session.get(
                            captchaUrl, headers=headers)
                        logging.getLogger("bili_pic").info(
                            base64.b64encode(captchaResponse.content).decode("utf-8"))
                        return

                    elif response_json['code'] == 0 and response_json['data']['status'] == 0:
                        for cookie in response_json['data']['cookie_info']['cookies']:
                            user.session.cookies.set(
                                cookie['name'], cookie['value'], domain=".bilibili.com")
                        user.access_token = response_json['data']['token_info']['access_token']
                        user.refresh_token = response_json['data']['token_info']['refresh_token']
                        user.isLogin = True
                        logging.getLogger("bili_str").info("登录成功")
                    else:
                        logging.getLogger("bili_str").info("登录失败")
        except:
            logging.getLogger("bili_str").info("网络错误")

    def get_user_info(self, user: BilibiliUser):
        url = "https://api.bilibili.com/x/space/myinfo"
        payload = {
            'SESSDATA': user.get_sessdata()
        }
        headers = {
            'Host': "api.bilibili.com",
            'Referer': f"https://space.bilibili.com/{user.get_uid()}/",
        }
        try:
            response = user.session.get(url, data=payload, headers=headers)
            if response.ok:
                response_json = response.json()
                if "code" in response_json:
                    if response_json['code'] == 0:
                        user.info['coins'] = response_json['data']['coins']
                        user.info['experience']['current'] = response_json['data']['level_exp']['current_exp']
                        user.info['experience']['next'] = response_json['data']['level_exp']['next_exp']
                        user.info['face'] = response_json['data']['face']
                        user.info['level'] = response_json['data']['level']
                        user.info['nickname'] = response_json['data']['name']
                        return user

                    elif response_json['code'] == -101:
                        logging.getLogger("bili_str").info("账号未登录")
                        return None
            else:
                logging.getLogger("bili_str").info("获取用户信息失败")
                return None
        except:
            logging.getLogger("bili_str").info("网络错误")

    def get_recommend(self, user: BilibiliUser) -> (List[BilibiliRecommendItem]):
        url = "https://app.bilibili.com/x/v2/feed/index"
        payload = f"access_key={user.access_token}"
        recommend_list = []
        try:
            response = user.session.get(url, params=payload)
            if response.ok:
                response_json = response.json()
                for item in response_json['data']['items']:
                    recommend_item = BilibiliRecommendItem()
                    recommend_item.title = item['title']
                    recommend_item.url = f"https://www.bilibili.com/video/{item['goto']}{item['param']}"
                    recommend_item.cover_url = item['cover']
                    if 'args' in item:
                        if ('up_name' in item['args']):
                            recommend_item.description.append(
                                f"UP:{item['args']['up_name']}")
                    if ('cover_left_1_content_description' in item):
                        recommend_item.description.append(
                            item['cover_left_1_content_description'])
                    if ('cover_left_2_content_description' in item):
                        recommend_item.description.append(
                            item['cover_left_2_content_description'])
                    if ('cover_right_content_description' in item):
                        recommend_item.description.append(
                            item['cover_right_content_description'])
                    recommend_list.append(recommend_item)
            if len(recommend_list) != 0:
                logging.getLogger("bili_str").info(
                    f"获取{len(recommend_list)}条新推荐")
            else:
                logging.getLogger("bili_str").info(f"获取推荐失败")
        except:
            logging.getLogger("bili_str").info("网络错误")
        return recommend_list
