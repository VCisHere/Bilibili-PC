from typing import List
from bilibili_methods import Bilibili
from bilibili_modules import BilibiliRecommendItem, BilibiliUser
import config


class Cmd:
    def __init__(self):
        self.cfg = config.Config("config.toml")
        self.cfg.load_config()

        self.user = BilibiliUser()

        self.cmd_login_password = []
        self.cmd_login_token = []
        self.cmd_refresh_token = []
        self.cmd_recommend = []
        self.cmd_get_user_info = []
        self.cmd_help = []
        self.cmd_clear = []
        self.cmd_exit = []

        self.display_help = False

        self.bilibili = Bilibili()
        self.load_config_to_user()
        self.load_config_cmd()
        self.load_config_misc()

    def load_config_cmd(self):

        self.cmd_login_password = self.cfg.config['command']['login_password']
        self.cmd_login_token = self.cfg.config['command']['login_token']
        self.cmd_refresh_token = self.cfg.config['command']['refresh_token']
        self.cmd_recommend = self.cfg.config['command']['recommend']
        self.cmd_get_user_info = self.cfg.config['command']['get_user_info']
        self.cmd_help = self.cfg.config['command']['help']
        self.cmd_clear = self.cfg.config['command']['clear']
        self.cmd_exit = self.cfg.config['command']['exit']

    def load_config_misc(self):
        self.display_help = self.cfg.config['misc']['display_help']

    def load_config_to_user(self):
        self.user.access_token = self.cfg.config['user']['access_token']
        self.user.refresh_token = self.cfg.config['user']['refresh_token']

    def save_token_to_config(self):
        self.cfg.config['user']['access_token'] = self.user.access_token
        self.cfg.config['user']['refresh_token'] = self.user.refresh_token
        self.cfg.save_config()

    def login_password(self, username, password):
        self.user.username = username
        self.user.password = password
        self.bilibili.login_password(self.user)
        self.save_token_to_config()

    def login_token(self):
        self.bilibili.login_token(self.user)

    def refresh_token(self):
        self.bilibili.refresh_user_token(self.user)
        self.save_token_to_config()

    def get_recommend(self):
        return self.bilibili.get_recommend(self.user)

    def get_user_info(self):
        return self.bilibili.get_user_info(self.user)

    def login_captcha(self, captchaStr):
        self.bilibili.login_password(self.user, captcha=captchaStr)
        self.save_token_to_config()
