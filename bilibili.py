import sys
from typing import List
import requests
from io import BytesIO
from PIL import Image, ImageQt
from PySide6 import QtCore, QtWidgets, QtGui
from requests.models import Response
from bilibili_modules import BilibiliRecommendItem, BilibiliUser
from bilibili_cmd import Cmd
import logging
import webbrowser
import os


class LabelWidget(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()


class NoHoverLabelWidget(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)


class LabelItemWidget(QtWidgets.QListWidgetItem):
    def __init__(self, text: str):
        super().__init__()
        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QHBoxLayout()

        self.label = LabelWidget()
        self.label.setText(text)
        self.layout.addWidget(self.label)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(self.layout)
        self.setSizeHint(self.widget.sizeHint())


class PictureItemWidget(QtWidgets.QListWidgetItem):
    def __init__(self, img: QtGui.QPixmap):
        super().__init__()
        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QHBoxLayout()

        self.label = LabelWidget()
        self.label.setPixmap(img)
        self.layout.addWidget(self.label)

        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(self.layout)
        self.setSizeHint(self.widget.sizeHint())


class CoverLabelWidget(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(120)
        self.setFixedWidth(190)


class RecommendItemWidget (QtWidgets.QListWidgetItem):

    def __init__(self, item: BilibiliRecommendItem):
        super().__init__()
        self.widget = QtWidgets.QWidget()
        self.layout = QtWidgets.QHBoxLayout()
        # self.layout.setAlignment(QtCore.Qt.AlignLeft)

        self.cover = CoverLabelWidget()
        self.cover.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.detailLayout = QtWidgets.QVBoxLayout()

        self.title = NoHoverLabelWidget()
        self.title.setText(item.title)
        self.url = item.url

        self.detailLayout.addWidget(self.title)

        self.description = []

        for descriptionItem in item.description:
            description = NoHoverLabelWidget()
            description.setText(descriptionItem)
            self.description.append(description)
            self.detailLayout.addWidget(description)

        self.detailLayout.setContentsMargins(5, 5, 5, 5)
        self.detailLayout.setSpacing(0)

        self.layout.addWidget(self.cover)
        self.layout.addLayout(self.detailLayout)
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.widget.setLayout(self.layout)

        self.setSizeHint(self.widget.sizeHint())

    def slot_add(self, pic: QtGui.QPixmap):
        if pic != None:
            self.cover.setPixmap(pic)


class InputStatus:
    Normal = 0
    LoginUsername = 1
    LoginPassword = 2
    LoginCaptcha = 3


class BilibiliWidget(QtWidgets.QWidget):
    biliCmd = Cmd()

    class LoggerWorker(logging.Handler, QtCore.QObject):

        class LogEmitter(QtCore.QObject):
            log = QtCore.Signal(str)

        def __init__(self):
            super().__init__()
            self.emitter = BilibiliWidget.LoggerWorker.LogEmitter()

        def emit(self, record):
            msg = self.format(record)
            self.emitter.log.emit(msg)

    class RecommendWorker(QtCore.QThread):
        sinOut = QtCore.Signal(BilibiliRecommendItem)

        def __init__(self):
            super().__init__()

        def run(self):
            recommendList = BilibiliWidget.biliCmd.get_recommend()
            self.sinOut.emit(recommendList)

    class RecommendCoverWorker(QtCore.QThread):
        sinOut = QtCore.Signal(int)

        def __init__(self, id: int, recommendList: List[BilibiliRecommendItem], recommendItemWidgetList: List[RecommendItemWidget]):
            super().__init__()
            self.id = id
            self.recommendList = recommendList
            self.recommendItemWidgetList = recommendItemWidgetList

        def run(self):
            for index in range(len(self.recommendList)):
                recommend = self.recommendList[index]
                recommendItemWidget = self.recommendItemWidgetList[index]
                pic = self.load_cover(
                    recommend.cover_url, recommendItemWidget.cover.width(), recommendItemWidget.cover.height())
                if pic != None:
                    recommendItemWidget.cover.setPixmap(pic)
            self.sinOut.emit(id)

        def load_cover(self, cover_url, width, height) -> (QtGui.QPixmap):
            try:
                imgData = requests.get(cover_url)
                imgBytes = BytesIO(imgData.content)
                img = Image.open(imgBytes)
                if img == None:
                    return None
                if img.width / img.height > width / height:
                    imgWidth = width * 2
                    imgHeight = int(imgWidth * img.height / img.width)
                else:
                    imgHeight = height * 2
                    imgWidth = int(imgHeight * img.width / img.height)

                img = img.resize((imgWidth, imgHeight), Image.ANTIALIAS)
                pic = QtGui.QPixmap(ImageQt.ImageQt(img))
                pic.setDevicePixelRatio(2.0)
                return pic
            except:
                pass

    class LoginTokenWorker(QtCore.QThread):
        sinOut = QtCore.Signal()

        def __init__(self):
            super().__init__()

        def run(self):
            BilibiliWidget.biliCmd.login_token()
            self.sinOut.emit()

    class LoginPasswordWorker(QtCore.QThread):
        sinOut = QtCore.Signal()

        def __init__(self, username, password):
            super().__init__()
            self.username = username
            self.password = password

        def run(self):
            BilibiliWidget.biliCmd.login_password(self.username, self.password)
            self.sinOut.emit()

    class RefreshTokenWorker(QtCore.QThread):
        sinOut = QtCore.Signal()

        def __init__(self):
            super().__init__()

        def run(self):
            BilibiliWidget.biliCmd.refresh_token()
            self.sinOut.emit()

    class GetUserInfoWorker(QtCore.QThread):
        sinOut = QtCore.Signal(BilibiliUser)

        def __init__(self):
            super().__init__()

        def run(self):
            user = BilibiliWidget.biliCmd.get_user_info()
            self.sinOut.emit(user)

    def __init__(self):
        super().__init__()

        self.inputStatus = InputStatus.Normal
        self.isRunningCmd = False
        self.coverWorkers = []
        self.worker = None

        self.list = QtWidgets.QListWidget()
        self.list.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.list.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.list.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(self.item_click)

        self.inputcmd = QtWidgets.QLineEdit()
        self.inputcmd.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self.inputcmd.returnPressed.connect(self.input_cmd)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.layout.addWidget(self.list)
        self.layout.addWidget(self.inputcmd)

        self.log("哔哩哔哩 (゜-゜)つロ 干杯~")
        if self.biliCmd.display_help == True:
            self.display_help()

    def item_click(self, item):
        if type(item) is RecommendItemWidget:
            webbrowser.open(item.url)

    def start_log(self):
        self.loggerWorker = BilibiliWidget.LoggerWorker()
        self.loggerWorker.setFormatter(logging.Formatter('%(message)s'))
        self.loggerWorker.emitter.log.connect(self.log)

        self.loggerPicWorker = BilibiliWidget.LoggerWorker()
        self.loggerPicWorker.setFormatter(logging.Formatter('%(message)s'))
        self.loggerPicWorker.emitter.log.connect(self.log_picture)

        logging.getLogger("bili_pic").addHandler(self.loggerPicWorker)
        logging.getLogger("bili_pic").setLevel(logging.INFO)

        logging.getLogger("bili_str").addHandler(self.loggerWorker)
        logging.getLogger("bili_str").setLevel(logging.INFO)

    def input_cmd(self):
        if self.isRunningCmd == True:
            return
        cmdStr = self.inputcmd.text()
        self.worker = None
        if self.inputStatus == InputStatus.Normal:
            if cmdStr in self.biliCmd.cmd_login_token:
                self.worker = BilibiliWidget.LoginTokenWorker()

            elif cmdStr in self.biliCmd.cmd_recommend:
                self.worker = BilibiliWidget.RecommendWorker()
                self.worker.sinOut.connect(self.slot_recommend)

            elif cmdStr in self.biliCmd.cmd_clear:
                self.clear_list()

            elif cmdStr in self.biliCmd.cmd_login_password:
                self.log("请输入账号")
                self.inputStatus = InputStatus.LoginUsername

            elif cmdStr in self.biliCmd.cmd_get_user_info:
                self.worker = BilibiliWidget.GetUserInfoWorker()
                self.worker.sinOut.connect(self.slot_get_user_info)

            elif cmdStr in self.biliCmd.cmd_refresh_token:
                self.worker = BilibiliWidget.RefreshTokenWorker()

            elif cmdStr in self.biliCmd.cmd_help:
                self.display_help()

            elif cmdStr in self.biliCmd.cmd_exit:
                QtWidgets.QApplication.quit()

        elif self.inputStatus == InputStatus.LoginUsername:
            self.log("请输入密码")
            self.username = cmdStr
            self.inputcmd.setEchoMode(QtWidgets.QLineEdit.Password)
            self.inputStatus = InputStatus.LoginPassword

        elif self.inputStatus == InputStatus.LoginPassword:
            self.log("登录中...")
            self.inputcmd.setEchoMode(QtWidgets.QLineEdit.Normal)
            self.inputStatus = InputStatus.Normal
            self.worker = BilibiliWidget.LoginPasswordWorker(
                self.username, cmdStr)

        elif self.inputStatus == InputStatus.LoginCaptcha:
            self.biliCmd.login_captcha(cmdStr)
            self.inputStatus = InputStatus.Normal

        if self.worker != None:
            self.isRunningCmd = True
            self.worker.sinOut.connect(self.end_cmd)
            self.worker.start()
        self.inputcmd.clear()

    def clear_list(self):
        for coverWorker in self.coverWorkers:
            coverWorker.terminate()
        self.list.clear()

    def end_cmd(self):
        self.isRunningCmd = False

    def display_help(self):
        self.log("帮助")
        self.log("账号密码登录: login")
        self.log("Token登录: login token")
        self.log("刷新Token: refresh token")
        self.log("推荐页: recommend")
        self.log("用户信息: user info")
        self.log("帮助: help")
        self.log("清屏: clear")
        self.log("退出: exit")

    def slot_recommend(self, items: List[BilibiliRecommendItem]):
        recommendItemWidgetList = []
        for item in items:
            recommend = RecommendItemWidget(item)
            self.list.addItem(recommend)
            self.list.setItemWidget(recommend, recommend.widget)
            recommendItemWidgetList.append(recommend)
        coverWorker = BilibiliWidget.RecommendCoverWorker(
            len(self.coverWorkers), items, recommendItemWidgetList)
        self.coverWorkers.append(coverWorker)
        coverWorker.sinOut.connect(self.slot_covers_load_end)
        coverWorker.start()

    def slot_covers_load_end(self, id: int):
        self.coverWorkers.pop(id)

    def slot_get_user_info(self, user):
        if user == None:
            return
        info = user.info
        logging.getLogger("bili_str").info(
            f"{info['nickname']}(UID={user.get_uid()})")
        logging.getLogger("bili_str").info(
            f"Lv.{info['level']}({info['experience']['current']}/{info['experience']['next']})")
        logging.getLogger("bili_str").info(f"硬币:{info['coins']}")

    def log_picture(self, message: str):
        self.log("请输入验证码")
        image = QtGui.QPixmap()
        image.loadFromData(
            QtCore.QByteArray.fromBase64(str.encode(message)))
        labelWidget = PictureItemWidget(image)
        self.list.addItem(labelWidget)
        self.list.setItemWidget(labelWidget, labelWidget.widget)
        self.inputStatus = InputStatus.LoginCaptcha

    def log(self, message):
        messageLabelItem = LabelItemWidget(message)
        self.list.addItem(messageLabelItem)
        self.list.setItemWidget(messageLabelItem, messageLabelItem.widget)

    def closeEvent(self, event: QtGui.QCloseEvent):
        for coverWorker in self.coverWorkers:
            coverWorker.terminate()
        if self.worker != None and self.worker.isRunning():
            self.worker.terminate()
            self.clear_list()
        return super().closeEvent(event)


app = QtWidgets.QApplication([])
font_path_1 = os.path.join(os.path.dirname(
    __file__), 'font/CascadiaCodePL.ttf')
font_path_2 = os.path.join(os.path.dirname(
    __file__), 'font/SourceHanSansHWSC.otf')
QtGui.QFontDatabase.addApplicationFont(font_path_1)
QtGui.QFontDatabase.addApplicationFont(font_path_2)

css_path = os.path.join(os.path.dirname(
    __file__), 'app.css')

with open(css_path, "r") as fh:
    QtWidgets.QApplication.setStyleSheet(app, fh.read())

widget = BilibiliWidget()
widget.setWindowTitle("哔哩哔哩 (゜-゜)つロ 干杯~")
ico_path = os.path.join(os.path.dirname(__file__), 'bilibili.ico')
app.setWindowIcon(QtGui.QIcon(ico_path))
widget.show()
widget.start_log()

sys.exit(app.exec())
