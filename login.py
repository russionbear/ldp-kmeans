import base64
import ctypes
import inspect
import sys
import os
import json
import encipher
import re
import random
import string
import shutil
from threading import Thread
import pandas
import functools
from myCpu import previousHandle
from typing import Dict, List
from datetime import datetime
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSize, Qt, QRegExp, QEvent, QCoreApplication
from PyQt5.QtGui import QIcon, QPixmap, QRegExpValidator, QCursor
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton \
    , QCheckBox, QLabel, QStyle, QComboBox, QScrollArea, QListWidgetItem, QMainWindow, QTableWidget \
    , QMenu, QAction, QToolBar, QListWidget, QStackedLayout, QSpinBox, QFormLayout, QMessageBox, \
    QTableWidgetItem, QAbstractItemView

from qt_material import apply_stylesheet, list_themes
from source.images import BIcon

App = QtWidgets.QApplication(sys.argv)

EMAIL_RE = r'^[A-Za-z0-9\u4e00-\u9fa5]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$'  # 邮箱正则
USERNAME_RE = r'^([a-zA-Z0-9_\u4e00-\u9fa5]{4,16})$'  # 用户名正则
PASSWORD_RE = r'^([a-zA-Z0-9_\.\-]{4,16})$'  # 密码正则
WEB_URL = 'https://www.baidu.com/'  # 网址，暂时无效
PROGRAM_ROOT = os.getcwd() + '/localstorageKeams/'  # 数据集存放位置
PROGRAM_CACHE_ROOT = os.getcwd() + '/cache/'  # 缓存文件存放位置


def addInfoToLog(path, tag, value):
    """
    保存错误信息
    :param path: 错误信息文件路径
    :param tag: 错误信息的标记
    :param value: 错误内容
    :return: 
    """
    if os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            pass
    with open(path, 'w+', encoding='utf-8') as f:
        f.write(f"{str(datetime.now())} {tag}:{value}")


class _SocketHelper:
    """
    与服务进行数据交互，暂时废弃
    """

    def __init__(self):
        pass

    def userRegister(self):
        pass

    def getMailCode(self):
        pass

    def updateToken(self, **kwargs):
        pass

    def resetPassword(self):
        pass

    def getUserInfo(self, token):
        pass

    def modifyUserInfo(self):
        pass

    def checkToken(self, token):
        pass


SocketHelper = _SocketHelper()  # 与服务进行数据交互


class ServerEvent(QEvent):
    """
    与算法程序进行通讯
    """
    idType = QEvent.registerEventType()

    def __init__(self, data):
        super(ServerEvent, self).__init__(ServerEvent.idType)
        self.data = data


class MainWidget(QMainWindow):
    """
    主界面
    """

    def __init__(self):
        super(MainWidget, self).__init__()
        self.dataHandleMethod = ["默认填充", "删除数据", "中位数", "平均数", "众数", "丢弃该列"]
        self.dataExportType = ["导出簇中心", "导出离群点", "导出非离群点", "导出分类列"]
        self.serverPayType = {"年": "350", "月": "30"}
        self.defaultResultExport = []
        self.setCentralWidget(QWidget(self))

        # 存放当前任务的菜单
        self.taskMenu: [QMenu, None] = None
        self.datasetBar = QToolBar('side')
        self.datasetView = QListWidget()
        self.datasetViewSortMethod = "名称"
        self.datasetViewSortMethodR = False
        self.datasetRightMenu: [QMenu, None] = None

        self.mainLayout = QStackedLayout()
        self.currentMainLayer = 'none'
        # 保存界面中的主要控件
        self.mainViews: Dict[str, Dict[str, QWidget, None, dict, int]] = {
            'primData': {
                'table': QTableWidget(),
                "nowPage": QSpinBox(),
                "pages": QLabel("0"),
                "maxRow": QComboBox(),
                "maxRowBak": 0,
                "pdForm": None
            },
            "taskSet": {
                'table': QTableWidget(),
                'dCenters': QSpinBox(),
                'checkCol': QSpinBox(),
                'tip': QLabel("tip"),
                "skipHeader": QCheckBox("跳过首行"),
                'status': QLabel("status"),
                'up': QPushButton('启动'),
                'down': QPushButton('停止')
            },
            "resultShow": {
                'table': QTableWidget(),
                "image": QLabel(),
                "acc": QLabel(),
                "nmi": QLabel(),
                "exportSet": QComboBox(),
                "export": QPushButton('导出'),
            },
            "layer": {}  # 此处不能赋值
        }
        # 保存对话框控件
        self.dialogViews: Dict[str, Dict[str, QWidget, None, Dict[List, str], int]] = {
            "userInfo": {},
            "userRegister": {},
            "findPassword": {},
            "userPay": {},
            "userLogin": {},
            "setDefaultTask": {},
            "renameDataset": {
                "targetItem": None
            },
            'layer': {},
            "data": {
                "userInfo": {},
                "defaultSet": {
                    "centers": 8,
                    "checkCol": 0,
                    "handleLoss": "删除数据"
                },
                "datasets": {},
                # 界面样式
                "appStyle": 'dark_teal.xml',
                "webUrl": WEB_URL
            }
        }

        self.mainViews['layer']['primData'] = self.initUiPrimData()
        self.mainViews['layer']['taskSet'] = self.initUiTaskSet()
        self.mainViews['layer']['resultShow'] = self.initUiResultShow()
        self.mainViews['layer']['none'] = QLabel('未选择数据集', self.centralWidget())
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.datasetView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.datasetView.customContextMenuRequested.connect(self.initDatasetRightMenu)

        self.initEnv()

        self.dialogUserInfo()
        self.dialogUserPay()
        self.dialogUserLogin()
        self.dialogSetDefaultTask()
        self.dialogFindPassword()
        self.dialogRegister()
        self.dialogRenameDataset()

        self.initUI()
        Service.sub = self
        self.mainLayout.setCurrentWidget(self.mainViews['layer']['none'])

        # self.centralWidget().setEnabled(True)
        # self.dialogUserPay()

    def initUI(self):
        """
        ui
        :return:
        """
        self.resize(1200, 800)
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        self.setWindowIcon(QIcon(pm))
        self.setWindowTitle("筛问卷")
        for k, v in self.mainViews['layer'].items():
            self.mainLayout.addWidget(v)
        self.centralWidget().setLayout(self.mainLayout)
        topMenuBar = self.menuBar()
        fileMenu = topMenuBar.addMenu('数据')
        fileMenu.addAction('导入').triggered.connect(self.inputFile)

        fileSortMenu = fileMenu.addMenu('排序方式')
        fileSortMenu.addAction('名称')
        fileSortMenu.addAction('时间')
        fileSortMenu.addAction('最近')
        fileSortMenu.addAction('大小')
        fileSortMenu.addAction("逆序").setCheckable(True)
        fileSortMenu.triggered.connect(self.handleDatasetSort)

        self.taskMenu = topMenuBar.addMenu('任务')
        self.taskMenu.triggered.connect(self.controlShowTask)

        userMenu = topMenuBar.addMenu('用户')
        userMenu.addAction('信息').triggered.connect(self.showUserInfo)
        userMenu.addAction("支付").triggered.connect(self.showUserPay)
        userMenu.addAction("登录/出").triggered.connect(self.topMLoginAction)
        userMenu.addAction("注册").triggered.connect(self.showUserRegister)
        userMenu.addAction("重置密码").triggered.connect(self.dialogViews['layer']['findPassword'].show)

        setMenu = topMenuBar.addMenu("设置")
        setMenu.addAction("默认参数").triggered.connect(self.showSetDefaultTask)
        styleMenu = setMenu.addMenu('样式')
        for i in list_themes():
            action = styleMenu.addAction(i.split('.')[0])
            action.setData(i)
        styleMenu.triggered.connect(self.swapStyle)

        toolbar = self.addToolBar("toolbar")
        toolbar.setMovable(False)
        toolbar.addAction('数据集')
        toolbar.addAction('原始数据')
        toolbar.addAction('新建任务')
        toolbar.addAction('结果')
        toolbar.actionTriggered.connect(self.handleTopToolBar)

        self.addToolBar(Qt.LeftToolBarArea, self.datasetBar)
        self.datasetBar.addWidget(self.datasetView)
        self.datasetBar.setMovable(False)

    def initEnv(self):
        """
        创建程序运行时需要的文件，读取用户信息
        :return:
        """
        if not os.path.exists(PROGRAM_ROOT):
            os.mkdir(PROGRAM_ROOT)

        # 读取用户信息
        if not os.path.exists(PROGRAM_ROOT + 'user'):
            with open(PROGRAM_ROOT + 'user', 'w', encoding='utf-8') as f:
                tmp = encipher.encrypt(json.dumps(self.dialogViews['data']))
                f.write(tmp)
        else:
            with open(PROGRAM_ROOT + 'user', 'r', encoding='utf-8') as f:
                try:
                    self.dialogViews['data'] = json.loads(encipher.decrypt(f.read()))
                except:
                    addInfoToLog(PROGRAM_ROOT + 'log', 'error', 'user 文件格式错误, 请重新登录')

        # 读取数据集信息
        dataset = {}
        for i in os.listdir(PROGRAM_ROOT):
            if not os.path.exists(PROGRAM_ROOT + i + '/state.txt'):
                continue
            with open(PROGRAM_ROOT + i + '/state.txt', 'r', encoding='utf-8') as f:
                try:
                    tmp = json.load(f)
                except:
                    continue
                dataset[i] = tmp
        self.dialogViews['data']['datasets'] = dataset

        self.centralWidget().setEnabled(False)
        if self.dialogViews['data']['userInfo']:
            if not self.dialogViews['data']["userInfo"]['remember']:
                return
            SocketHelper.checkToken(self.dialogViews['data']["userInfo"]['token'])
            response = {'status': 0, "info": "fff"}
            #### check
            self.centralWidget().setEnabled(True)

        # 切换界面风格
        apply_stylesheet(App, theme=self.dialogViews['data']['appStyle'])
        self.datasetView.addItems(list(self.dialogViews['data']['datasets'].keys()))
        self.datasetView.currentRowChanged.connect(self.handleTopToolBar)
        if self.datasetView.count():
            self.datasetView.setCurrentRow(0)

    def initUiPrimData(self):
        """
        管理原始数据的ui
        :return:
        """
        self.mainViews['primData']['table'].setRowCount(7)
        self.mainViews['primData']['table'].setColumnCount(7)
        for i in range(7):
            for j in range(7):
                self.mainViews['primData']['table'].setItem(i, j, QTableWidgetItem(''))
        self.mainViews['primData']['table'].setEditTriggers(QAbstractItemView.NoEditTriggers)
        view = QWidget(self.centralWidget())
        layout1 = QHBoxLayout()
        layout1.setAlignment(Qt.AlignRight)
        layout1.addWidget(QLabel("浏览数据"))
        layout1.addStretch(1)

        layout2 = QHBoxLayout()
        layout2.setAlignment(Qt.AlignRight)
        layout2.addWidget(QLabel("当前页"))
        layout2.addWidget(self.mainViews['primData']["nowPage"])
        layout2.addWidget(self.mainViews['primData']['pages'])
        layout2.addSpacing(20)
        layout2.addWidget(QLabel("最大行数"))
        layout2.addWidget(self.mainViews['primData']['maxRow'])
        layout = QVBoxLayout()
        layout.addLayout(layout1)
        layout.addWidget(self.mainViews['primData']['table'])
        layout.addLayout(layout2)
        view.setLayout(layout)

        self.mainViews['primData']['maxRow'].addItems([str(i * 10) for i in range(1, 11)])
        self.mainViews['primData']['maxRow'].currentTextChanged.connect(self.handlePrimChgRow)
        self.mainViews['primData']['nowPage'].valueChanged.connect(self.handlePrimChgPage)
        self.mainViews['primData']['nowPage'].setMinimum(1)

        return view

    def initUiTaskSet(self):
        """
        数据预处理页面
        :return:
        """
        self.mainViews['taskSet']["dCenters"].setValue(8)
        self.mainViews['taskSet']["dCenters"].setMinimum(2)
        self.mainViews['taskSet']['table'].setRowCount(4)
        self.mainViews['taskSet']['table'].setColumnCount(7)
        self.mainViews['taskSet']['table'].setVerticalHeaderItem(0, QTableWidgetItem('首行'))
        self.mainViews['taskSet']['table'].setVerticalHeaderItem(1, QTableWidgetItem('数据类型'))
        self.mainViews['taskSet']['table'].setVerticalHeaderItem(2, QTableWidgetItem('缺失值处理'))
        self.mainViews['taskSet']['table'].setVerticalHeaderItem(3, QTableWidgetItem('默认填充'))
        self.mainViews['taskSet']['checkCol'].setMinimum(-10000)
        self.mainViews['taskSet']['checkCol'].setMaximum(10000)
        self.mainViews['taskSet']['status'].setText("未处理")
        self.mainViews['taskSet']['up'].clicked.connect(functools.partial(self.controlTask, "up"))
        self.mainViews['taskSet']['down'].clicked.connect(functools.partial(self.controlTask, "down"))
        self.mainViews['taskSet']['tip'].setText(
            "tip:\n对于非数值类型，缺失值的处理方式为默认填充，其他方式无效\n验证列为0则不进行验证，如果为负值则从右边数起,设置验证列成功会使 簇中心 失效\n只有二维数据才会有图片、"
            "处理时间太长则意味着处理失败")
        layout = QVBoxLayout()
        layout0 = QHBoxLayout()
        layout0.addWidget(QLabel('数据预处理方案'), 1)
        layout0.addWidget(self.mainViews['taskSet']["skipHeader"])
        layout.addLayout(layout0)
        layout.addWidget(self.mainViews['taskSet']['table'])
        layout1 = QHBoxLayout()
        layout1.addWidget(QLabel('簇中心个数'))
        layout1.addWidget(self.mainViews['taskSet']['dCenters'])
        layout1.addSpacing(10)
        layout1.addWidget(QLabel('第'))
        layout1.addWidget(self.mainViews['taskSet']['checkCol'])
        layout1.addWidget(QLabel('列为验证列'))
        layout1.addStretch(1)

        layout2 = QHBoxLayout()
        layout2.addWidget(self.mainViews['taskSet']['status'])
        layout2.addStretch(1)
        layout2.addWidget(self.mainViews['taskSet']['up'])
        layout2.addWidget(self.mainViews['taskSet']['down'])

        layout.addWidget(self.mainViews['taskSet']['tip'])
        layout.addLayout(layout1)
        layout.addLayout(layout2)

        view = QWidget()
        view.setLayout(layout)

        return view

    def initUiResultShow(self):
        """
        显示处理结果的页面
        :return:
        """
        layout1 = QVBoxLayout()
        layout1.addWidget(self.mainViews['resultShow']['table'])
        layout1.addWidget(self.mainViews['resultShow']['image'])
        layout1_1 = QHBoxLayout()
        layout1_1.addWidget(QLabel('ACC:'))
        layout1_1.addWidget(self.mainViews['resultShow']['acc'])
        layout1_1.addSpacing(15)
        layout1_1.addWidget(QLabel('NMI:'))
        layout1_1.addWidget(self.mainViews['resultShow']['nmi'])
        layout1_1.addStretch(1)
        layout1.addLayout(layout1_1)

        layout2 = QHBoxLayout()
        layout2.setAlignment(Qt.AlignBottom)
        layout2.addWidget(self.mainViews['resultShow']['exportSet'])
        layout2.addWidget(self.mainViews['resultShow']['export'])

        layout0 = QHBoxLayout()
        layout0.addLayout(layout1)
        layout0.addLayout(layout2)
        view = QWidget()
        view.setLayout(layout0)
        self.mainViews['resultShow']['exportSet'].addItems(self.dataExportType)
        self.mainViews['resultShow']['export'].clicked.connect(self.outputFile)
        self.mainViews['resultShow']['image'].setScaledContents(True)
        self.mainViews['resultShow']['image'].setFixedSize(200, 200)
        return view

    def initDatasetRightMenu(self, pos):
        """
        右键点击数据集时的菜单
        :param pos:
        :return:
        """
        self.datasetRightMenu = QMenu(self)
        self.datasetRightMenu.addAction("删除")
        self.datasetRightMenu.addAction("explorer")
        self.datasetRightMenu.addAction("重命名")
        self.datasetRightMenu.triggered.connect(self.handleDatasetRightMenu)
        self.datasetRightMenu.popup(QCursor.pos())

    def dialogUserInfo(self):
        """
        显示用户信息的对话框
        :return:
        """
        self.dialogViews['userInfo'].update({
            "email": QLabel("@"),
            'username': QLineEdit(),
            "reset": QPushButton('重置'),
            'submit': QPushButton("提交")
        })
        view = QWidget()
        view.setWindowTitle("user info")
        view.setWindowModality(Qt.ApplicationModal)
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.setContentsMargins(30, 30, 30, 30)
        self.dialogViews['layer']['userInfo'] = view
        layout = QFormLayout()
        layout.addRow('email', self.dialogViews['userInfo']['email'])
        layout.addRow('用户名', self.dialogViews['userInfo']['username'])
        layout1 = QHBoxLayout()
        layout1.addWidget(self.dialogViews['userInfo']['reset'])
        layout1.addWidget(self.dialogViews['userInfo']['submit'])
        layout.addRow('操作', layout1)
        view.setLayout(layout)
        return view

    def dialogUserPay(self):
        """
        与支付有关的对话框
        :return:
        """
        self.dialogViews['userPay'].update({
            "restMoney": QLabel("0"),
            "serverType": QLabel("a year"),
            "payType": QComboBox(),
            "payMonth": QSpinBox(),
            "payMoney": QLabel("0"),
            "payButton": QPushButton("充值"),
            "label": QLabel()
        })
        view = QWidget()
        view.setWindowTitle("pay")
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.setWindowModality(Qt.ApplicationModal)
        view.setContentsMargins(50, 50, 50, 50)
        self.dialogViews['layer']['userPay'] = view
        layout1 = QFormLayout()
        layout1.addRow('余额', self.dialogViews['userPay']['restMoney'])
        layout1.addRow('服务类型', self.dialogViews['userPay']['serverType'])

        layout2 = QHBoxLayout()
        layout2.addWidget(self.dialogViews['userPay']['payType'])
        layout2.addWidget(self.dialogViews['userPay']['payMoney'])
        layout2.addWidget(self.dialogViews['userPay']['payMoney'])
        layout2.addWidget(self.dialogViews['userPay']['payButton'])

        layout = QVBoxLayout()
        layout.addLayout(layout1)
        layout.addLayout(layout2)
        layout.addWidget(self.dialogViews['userPay']['label'])
        view.setLayout(layout)
        self.dialogViews['userPay']['payType'].addItems(list(self.serverPayType.keys()))
        self.dialogViews['userPay']['payType'].currentTextChanged.connect( \
            lambda arg: self.dialogViews['userPay']['payMoney'].setText(self.serverPayType[arg]))
        self.dialogViews['userPay']['payType'].setCurrentText(list(self.serverPayType.keys())[0])
        self.dialogViews['userPay']['payMoney'].setText(list(self.serverPayType.values())[0])
        return view

    def dialogUserLogin(self):
        """
        用户登入对话框
        :return:
        """
        self.dialogViews['userLogin'].update({
            "email": QLineEdit(),
            "password": QLineEdit(),
            "remember": QCheckBox('临时登录'),
            # "webUrl": QPushButton("url"),
            "forgetP": QPushButton("忘记密码"),
            'submit': QPushButton('登录')
        })
        view = QWidget()
        view.setWindowTitle("login")
        # view.setWindowIcon(self.windowIcon())

        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.resize(400, 300)
        view.setWindowModality(Qt.ApplicationModal)
        view.setContentsMargins(50, 50, 50, 50)
        self.dialogViews['layer']['userLogin'] = view
        layout1 = QFormLayout()
        layout1.addRow('注册邮箱', self.dialogViews['userLogin']['email'])
        layout1.addRow('密码', self.dialogViews['userLogin']['password'])

        layout1_1 = QHBoxLayout()
        layout1_1.addWidget(self.dialogViews['userLogin']['remember'])
        layout1_1.addStretch(1)
        layout1_1.addWidget(self.dialogViews['userLogin']['forgetP'])
        # layout1.addChildLayout(layout1_1)
        layout1.addItem(layout1_1)

        layout1.addWidget(self.dialogViews['userLogin']['submit'])
        # layout1.addWidget(self.dialogViews['userLogin']['webUrl'])

        # layout0 = QVBoxLayout()
        # layout0.addLayout(layout1)
        view.setLayout(layout1)
        self.dialogViews['userLogin']['submit'].clicked.connect(self.handleLogin)
        # self.dialogViews['userLogin']['webUrl'].clicked.connect(lambda arg: webbrowser.open(WEB_URL))
        self.dialogViews['userLogin']['forgetP'].clicked.connect(self.showFindPassword)
        self.dialogViews['userLogin']['email'].setValidator(QRegExpValidator(QRegExp(EMAIL_RE)))
        # self.dialogViews['userLogin']['username'].setValidator(QRegExpValidator(QRegExp(r'^([a-zA-Z0-9_\u4e00-\u9fa5]{4,16})$')))
        self.dialogViews['userLogin']['password'].setValidator(QRegExpValidator(QRegExp(PASSWORD_RE)))
        self.dialogViews['userLogin']['password'].setEchoMode(QLineEdit.Password)
        self.dialogViews['userLogin']['password'].setMaxLength(16)
        self.dialogViews['userLogin']['email'].setMaxLength(32)
        return view

    def dialogFindPassword(self):
        """
        找回密码对话框
        :return:
        """
        self.dialogViews['findPassword'].update({
            "email": QLineEdit(),
            "newPassword": QLineEdit(),
            "newPassword2": QLineEdit(),
            "code": QLineEdit(),
            "getCode": QPushButton("发送邮箱验证码"),
            "status": QLabel("fff"),
            "submit": QPushButton("提交")
        })
        view = QWidget()
        view.setWindowTitle("reset password")
        # view.setWindowIcon(self.windowIcon())
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.setWindowModality(Qt.ApplicationModal)
        view.setContentsMargins(30, 30, 30, 30)
        self.dialogViews['layer']['findPassword'] = view
        layout = QFormLayout()
        layout.addRow('email', self.dialogViews['findPassword']['email'])
        layout.addRow('设置密码', self.dialogViews['findPassword']['newPassword'])
        layout.addRow('确认密码', self.dialogViews['findPassword']['newPassword2'])
        layout1 = QHBoxLayout()
        layout1.addWidget(self.dialogViews['findPassword']['code'])
        layout1.addWidget(self.dialogViews['findPassword']['getCode'])
        layout.addItem(layout1)

        layout.addWidget(self.dialogViews['findPassword']['status'])
        layout.addWidget(self.dialogViews['findPassword']['submit'])
        view.setLayout(layout)
        self.dialogViews['findPassword']['email'].setValidator(QRegExpValidator(QRegExp(EMAIL_RE)))
        self.dialogViews['findPassword']['newPassword'].setEchoMode(QLineEdit.Password)
        self.dialogViews['findPassword']['newPassword'].setValidator(QRegExpValidator(QRegExp(PASSWORD_RE)))
        self.dialogViews['findPassword']['newPassword2'].setEchoMode(QLineEdit.Password)
        self.dialogViews['findPassword']['newPassword2'].setValidator(QRegExpValidator(QRegExp(PASSWORD_RE)))
        self.dialogViews['findPassword']['code'].setValidator(QRegExpValidator(QRegExp(r'[0-9]*')))
        return view

    def dialogRegister(self):
        """
        注册用户对话框
        :return:
        """
        self.dialogViews['userRegister'].update({
            "username": QLineEdit(),
            "email": QLineEdit(),
            "newPassword": QLineEdit(),
            "newPassword2": QLineEdit(),
            "code": QLineEdit(),
            "getCode": QPushButton("发送邮箱验证码"),
            "status": QLabel("fff"),
            "submit": QPushButton("提交")
        })
        view = QWidget()
        view.setWindowTitle("register")
        # view.setWindowIcon(self.windowIcon())
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.setWindowModality(Qt.ApplicationModal)
        view.setContentsMargins(30, 30, 30, 30)
        self.dialogViews['layer']['userRegister'] = view
        layout = QFormLayout()
        layout.addRow('用户名', self.dialogViews['userRegister']['username'])
        layout.addRow('设置密码', self.dialogViews['userRegister']['newPassword'])
        layout.addRow('确认密码', self.dialogViews['userRegister']['newPassword2'])
        # layout.addRow('email', self.dialogViews['userRegister']['email'])
        layout1 = QHBoxLayout()
        layout1.addWidget(self.dialogViews['userRegister']['code'])
        layout1.addWidget(self.dialogViews['userRegister']['getCode'])
        layout.addItem(layout1)

        layout.addWidget(self.dialogViews['userRegister']['status'])
        layout.addWidget(self.dialogViews['userRegister']['submit'])
        view.setLayout(layout)

        self.dialogViews['userRegister']['email'].setValidator(QRegExpValidator(QRegExp(EMAIL_RE)))
        self.dialogViews['userRegister']['username'].setValidator(QRegExpValidator(QRegExp(USERNAME_RE)))
        self.dialogViews['userRegister']['newPassword'].setEchoMode(QLineEdit.Password)
        self.dialogViews['userRegister']['newPassword'].setValidator(QRegExpValidator(QRegExp(PASSWORD_RE)))
        self.dialogViews['userRegister']['newPassword2'].setEchoMode(QLineEdit.Password)
        self.dialogViews['userRegister']['newPassword2'].setValidator(QRegExpValidator(QRegExp(PASSWORD_RE)))
        self.dialogViews['userRegister']['code'].setValidator(QRegExpValidator(QRegExp(r'[0-9]*')))
        return view

    def dialogSetDefaultTask(self):
        """
        设置默认的数据预处理的对话框
        :return:
        """
        self.dialogViews['setDefaultTask'].update({
            'centers': QSpinBox(),
            "checkCol": QSpinBox(),
            'handleLoss': QComboBox(),
            'saveBtn': QPushButton('保存')
        })
        view = QWidget()
        view.setWindowTitle("default set")
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.setWindowModality(Qt.ApplicationModal)
        view.setContentsMargins(30, 30, 30, 30)
        self.dialogViews['layer']['setDefaultTask'] = view
        layout = QFormLayout()
        layout.addRow("簇个数", self.dialogViews['setDefaultTask']['centers'])
        layout.addRow("验证列", self.dialogViews['setDefaultTask']['checkCol'])
        layout.addRow("缺失值处理", self.dialogViews['setDefaultTask']['handleLoss'])
        layout.addWidget(self.dialogViews['setDefaultTask']['saveBtn'])
        view.setLayout(layout)
        self.dialogViews['setDefaultTask']['handleLoss'].addItems(self.dataHandleMethod)
        self.dialogViews['setDefaultTask']['saveBtn'].clicked.connect(self.handleDefaultSet)
        return view

    def dialogRenameDataset(self):
        """
        重命名数据集对话框
        :return:
        """
        self.dialogViews['renameDataset'].update({
            'input': QLineEdit(),
            'saveBtn': QPushButton('确定')
        })
        view = QWidget()
        view.setWindowTitle("rename")
        # view.setWindowIcon(self.windowIcon())
        pm = QPixmap()
        pm.loadFromData(base64.b64decode(BIcon))
        view.setWindowIcon(QIcon(pm))
        view.setWindowModality(Qt.ApplicationModal)
        view.setContentsMargins(30, 30, 30, 30)
        self.dialogViews['layer']['renameDataset'] = view
        layout = QHBoxLayout()
        layout.addWidget(self.dialogViews['renameDataset']['input'])
        layout.addWidget(self.dialogViews['renameDataset']['saveBtn'])
        view.setLayout(layout)

        def handleSaveBtn():
            new_name = self.dialogViews['renameDataset']['input'].text()
            old_name = self.dialogViews['renameDataset']['oldName']
            self.dialogViews['renameDataset']['itemTarget'].setText(new_name)
            os.rename(PROGRAM_ROOT + old_name, PROGRAM_ROOT + new_name)
            self.dialogViews['data']['datasets'][new_name] = self.dialogViews['data']['datasets'][old_name]
            del self.dialogViews['data']['datasets'][old_name]
            self.dialogViews['layer']['renameDataset'].hide()

        self.dialogViews['renameDataset']['saveBtn'].clicked.connect(handleSaveBtn)
        return view

    def handleTopToolBar(self, action: [QAction, str] = None):
        """
        工具栏
        :param action:
        :return:
        """
        if not self.centralWidget().isEnabled():
            return
        current = self.datasetView.currentItem()
        if not current:
            self.currentMainLayer = 'none'
            self.mainLayout.setCurrentWidget(self.mainViews['layer']['none'])
            return

        # 相同dataset
        if type(action) != int:
            actionText = action.text()
            # if self.currentMainLayer == action.text() or \
            #         self.mainViews['primData']['pdForm'] is None:
            if self.currentMainLayer == action.text():
                return
            if self.mainViews['primData']['pdForm'] is None:
                # try:
                #     data = pandas.read_csv(PROGRAM_ROOT + current.text() + '/from.xls', header=None)
                # except:
                #     addInfoToLog(PROGRAM_ROOT + 'log', 'read csv error', PROGRAM_ROOT + current.text() + '/from.xls')
                #     return
                msg_box = QMessageBox(QMessageBox.Warning, 'error', '打开文件失败,如果导入的是xls文件，请确保导入的文件名（无后缀）与第一个表名相同')
                msg_box.setWindowIcon(self.windowIcon())
                msg_box.exec_()
                return
        else:
            # print(action, 'chagne')
            actionText = self.currentMainLayer

            try:
                data = pandas.read_csv(PROGRAM_ROOT + current.text() + '/from.csv', header=None)
                # data.apply(str)
                # data = pandas.read_csv(PROGRAM_ROOT + current.text() + '/from.xls', header=None, encoding='utf-8')
            except:
                addInfoToLog(PROGRAM_ROOT + 'log', 'read csv error', PROGRAM_ROOT + current.text() + '/from.xls')
                return
            # print(data, actionText)
            data.drop(columns=[0], inplace=True)
            data.fillna(12, inplace=True)
            data = data.astype(str)
            # print(data, 'data')
            self.mainViews['primData']['pdForm'] = data

        # if not self.centralWidget().isEnabled():
        #     self.centralWidget().setEnabled(True)

        if actionText == "数据集":
            if self.datasetBar.isHidden():
                self.datasetBar.setHidden(False)
            else:
                self.datasetBar.setHidden(True)
            return
        # print('skip', actionText)
        if actionText in ["原始数据", 'primData']:
            # print('primData')
            self.mainLayout.setCurrentWidget(self.mainViews['layer']['primData'])
            self.currentMainLayer = 'primData'
            self.readToPrimData(current.text())
        elif actionText in ["新建任务", "taskSet"]:
            self.mainLayout.setCurrentWidget(self.mainViews['layer']['taskSet'])
            self.currentMainLayer = 'taskSet'
            self.readToTaskSet(current.text())
        elif actionText in ["结果", "resultShow"]:
            self.mainLayout.setCurrentWidget(self.mainViews['layer']['resultShow'])
            self.currentMainLayer = 'resultShow'
            # self.mainViews['resultShow']["acc"].setText(self.dialogViews['data']['datasets'][current.text()]['acc'])
            # self.mainViews['resultShow']["nmi"].setText(self.dialogViews['data']['datasets'][current.text()]['nmi'])
            # if os.path.exists(PROGRAM_ROOT + current.text() + '/rlt.png'):
            #     # pass
            #     self.mainViews['resultShow']['image'].setPixmap(QPixmap(PROGRAM_ROOT + current.text() + '/rlt.png'))
            # else:
            #     self.mainViews['resultShow']['image'].clear()
            self.showResultXls(current.text())

    def setDatasetBarHidden(self):
        """
        显示或隐藏数据集列表
        :return:
        """
        if self.datasetBar.isHidden():
            self.datasetBar.setHidden(False)
        else:
            self.datasetBar.setHidden(True)

    def saveLocalInfo(self):
        """
        保存用户信息
        :return:
        """
        keys = ['userInfo', 'defaultSet', "appStyle"]
        tmp_data = {}
        for k in keys:
            tmp_data[k] = self.dialogViews['data'][k]
        with open(PROGRAM_ROOT + 'user', 'w', encoding='utf-8') as f:
            tmp = encipher.encrypt(json.dumps(tmp_data))
            f.write(tmp)

    def handleLogin(self):
        """
        响应用户登录
        :return:
        """
        data = {
            'email': self.dialogViews['userLogin']['email'].text(),
            'password': self.dialogViews['userLogin']['password'].text()
        }
        if re.match(EMAIL_RE, data['email']) is None or re.match(PASSWORD_RE, data['password']) is None:
            # print('password, or email error')
            msg_box = QMessageBox(QMessageBox.Warning, '格式错误', 'password or email error')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        SocketHelper.updateToken(email=data['email'], password=data['password'])
        response = {'status': 0, 'token': "token"}
        if response['status'] != 0:
            msg_box = QMessageBox(QMessageBox.Warning, '信息错误', '')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()

        SocketHelper.checkToken(response['token'])
        response1 = {'status': 0, "info": '7777'}
        if response1['status'] != 0:
            msg_box = QMessageBox(QMessageBox.Warning, '无效信息', '错误码:' + str(response1['status']))
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        ### check

        SocketHelper.getUserInfo(response['token'])
        response2 = {'status': 0, 'info': {
            'email': 'test@mail',
            'username': 'username',
            'restMoney': "restMoney",
            'typeName': "typeName",
            "serverType": 'none'
        }}
        if response2['status'] != 0:
            msg_box = QMessageBox(QMessageBox.Warning, str(response2['status']), '获取用户信息失败')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return

        self.dialogViews['data']['userInfo'].update(response2['info'])
        self.dialogViews['data']['userInfo']['token'] = response['token']
        self.dialogViews['data']['userInfo']['remember'] = not self.dialogViews['userLogin']['remember'].isChecked()
        self.saveLocalInfo()
        self.centralWidget().setEnabled(True)
        self.dialogViews['layer']['userLogin'].hide()

    def showFindPassword(self):
        """
        打开找回密码对话框
        :return:
        """
        for k, v in self.dialogViews['layer'].items():
            if not v.isHidden():
                v.hide()
                break
        self.dialogViews['layer']['findPassword'].show()

    def showUserInfo(self):
        """
        打开显示用户信息对话框
        :return:
        """
        if not self.dialogViews['data']['userInfo']:
            msg_box = QMessageBox(QMessageBox.Warning, "warning", '先登录')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        self.dialogViews['userInfo']['email'].setText(self.dialogViews['data']['userInfo']['email'])
        self.dialogViews['userInfo']['username'].setText(self.dialogViews['data']['userInfo']['username'])
        self.dialogViews['layer']['userInfo'].show()

    def showUserPay(self):
        """
        打开支付对话框
        :return:
        """
        if not self.dialogViews['data']['userInfo']:
            msg_box = QMessageBox(QMessageBox.Warning, "warning", '先登录')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        self.dialogViews['userPay']['restMoney'].setText(self.dialogViews['data']['userInfo']['restMoney'])
        self.dialogViews['userPay']['serverType'].setText(self.dialogViews['data']['userInfo']['serverType'])
        self.dialogViews['layer']['userPay'].show()

    def showUserRegister(self):
        """
        打开用户登录对话框
        :return:
        """
        if self.dialogViews['data']['userInfo']:
            msg_box = QMessageBox(QMessageBox.Information, "warning", '先登出')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        self.dialogViews['userRegister']['username'].setText('')
        self.dialogViews['userRegister']['newPassword'].setText('')
        self.dialogViews['userRegister']['newPassword2'].setText('')
        self.dialogViews['layer']['userRegister'].show()

    def showSetDefaultTask(self):
        """
        打开设置默认配置对话框
        :return:
        """
        self.dialogViews['setDefaultTask']['centers'].setValue(self.dialogViews['data']['defaultSet']['centers'])
        self.dialogViews['setDefaultTask']['checkCol'].setValue(self.dialogViews['data']['defaultSet']['checkCol'])
        self.dialogViews['setDefaultTask']['handleLoss']. \
            setCurrentText(self.dialogViews['data']['defaultSet']['handleLoss'])
        self.dialogViews['layer']['setDefaultTask'].show()

    def topMLoginAction(self):
        """
        响应用户登录、登出
        :return:
        """
        if self.centralWidget().isEnabled():
            self.centralWidget().setEnabled(False)
            self.dialogViews['data']['userInfo'] = {}
            self.saveLocalInfo()
        else:
            self.dialogViews['layer']['userLogin'].show()

    def swapStyle(self, action: QAction):
        """
        切换界面风格
        :param action:
        :return:
        """
        apply_stylesheet(App, action.data())
        self.dialogViews['data']['appStyle'] = action.data()
        self.saveLocalInfo()

    def inputFile(self):
        """
        导入文件
        :return:
        """
        fileName, fileType = QtWidgets.QFileDialog.getOpenFileName(self, "选取文件", os.getcwd(),
                                                                   "data (*.csv *.xls *.txt)")
        if fileName == "":
            return

        # 防止有相同的文件名
        rlt_name0 = os.path.split(fileName)[1]
        rlt_name = rlt_name0.split('.')
        rlt_name.pop()
        rlt_name = '.'.join(rlt_name)
        rlt_name_ = rlt_name

        while os.path.exists(PROGRAM_ROOT + rlt_name_):
            rlt_name_ = rlt_name + '.' + ''.join(random.sample(string.ascii_letters + string.digits, 4))
        os.mkdir(PROGRAM_ROOT + rlt_name_)

        try:
            if rlt_name0.split('.')[-1] == 'xls':
                tmp_data = pandas.read_excel(fileName, header=None)
            else:
                tmp_data = pandas.read_csv(fileName, header=None)
        except:
            msg_box = QMessageBox(QMessageBox.Warning, 'error', '数据格式错误')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        tmp_data.to_csv(PROGRAM_ROOT + rlt_name_ + '/from.csv', header=None)
        state_file = {
            'name': rlt_name_, 'createTime': str(datetime.now()), 'modifyTime': 'null',
            'state': '未处理', "acc": "", "nmi": "", "size": str(tmp_data.size // 1024),
            "skipHeader": False, 'dCenters': []
        }
        with open(PROGRAM_ROOT + rlt_name_ + '/state.txt', 'w', encoding='utf-8') as f:
            json.dump(state_file, f)
        #
        self.datasetView.insertItem(0, rlt_name_)
        self.dialogViews['data']['datasets'][rlt_name_] = state_file

    def handleDefaultSet(self):
        """
        保存默认配置
        :return:
        """
        self.dialogViews['data']['centers'] = self.dialogViews['setDefaultTask']['centers'].value()
        self.dialogViews['data']['checkCol'] = self.dialogViews['setDefaultTask']['checkCol'].value()
        self.dialogViews['data']['handleLoss'] = self.dialogViews['setDefaultTask']['handleLoss'].currentText()

    def handleDatasetRightMenu(self, action: QAction = None):
        """
        响应数据集右键菜单
        :param action:
        :return:
        """
        current = self.datasetView.currentItem()
        if not current:
            return
        if action.text() == "删除":
            shutil.rmtree(PROGRAM_ROOT + current.text())
            del self.dialogViews['data']['datasets'][current.text()]
            # self.datasetView.removeItemWidget(self.datasetView.currentItem())
            self.datasetView.takeItem(self.datasetView.currentRow())
            self.mainLayout.setCurrentWidget(self.mainViews['layer']['none'])
        elif action.text() == "重命名":
            self.dialogViews['renameDataset']['input'].setText(current.text())
            self.dialogViews['renameDataset']['oldName'] = current.text()
            self.dialogViews['renameDataset']['itemTarget'] = current
            self.dialogViews["layer"]['renameDataset'].show()
        elif action.text() == "explorer":
            os.startfile(PROGRAM_ROOT + current.text())

    def handleDatasetSort(self, action: QAction):
        """
        对数据集排序
        :param action:
        :return:
        """
        keys = list(self.dialogViews['data']['datasets'].keys())
        data = self.dialogViews['data']['datasets']
        currentTag = action.text()
        if currentTag == "逆序":
            currentTag = self.datasetViewSortMethod
            self.datasetViewSortMethodR = action.isChecked()
        if currentTag == "名称":
            keys.sort(key=lambda arg: data[arg]['name'], reverse=self.datasetViewSortMethodR)
            self.datasetViewSortMethod = currentTag
        elif currentTag == "时间":
            keys.sort(key=lambda arg: data[arg]['createTime'], reverse=self.datasetViewSortMethodR)
            self.datasetViewSortMethod = currentTag
        elif currentTag == "最近":
            keys.sort(key=lambda arg: data[arg]['modifyTime'], reverse=self.datasetViewSortMethodR)
            self.datasetViewSortMethod = currentTag
        elif currentTag == "大小":
            keys.sort(key=lambda arg: data[arg]['size'], reverse=self.datasetViewSortMethodR)
            self.datasetViewSortMethod = currentTag

        self.datasetView.clear()
        self.datasetView.addItems(keys)

    def readToPrimData(self, current):
        """
        读取原始数据
        :param current:
        :return:
        """
        self.centralWidget().setEnabled(True)
        data = self.mainViews['primData']['pdForm']
        self.mainViews['primData']['table'].clear()
        self.mainViews['primData']['table'].setRowCount(int(self.mainViews['primData']['maxRow'].currentText()))
        self.mainViews['primData']['table'].setColumnCount(len(data.columns))
        self.handlePrimChgRow(self)

    def handlePrimModify(self, action):
        pass

    def handlePrimChgRow(self, action):
        """
        处理原始数据页面的单个页面最大数据量的改变
        :param action:
        :return:
        """
        pdForm = self.mainViews['primData']['pdForm']
        if action == '0':
            return
        if type(action) != str:
            action = self.mainViews['primData']['maxRow'].currentText()
        self.mainViews['primData']['table'].setRowCount(int(action))
        self.mainViews['primData']['table'].clear()
        for i in range(int(action)):
            for j1, j in enumerate(pdForm.columns):
                try:
                    self.mainViews['primData']['table'].setItem(i, j1, QTableWidgetItem(str(pdForm.loc[i, j])))
                except:
                    pass
        if self.mainViews['primData']['nowPage'].value() != 1:
            self.mainViews['primData']['nowPage'].setValue(1)
        self.mainViews['primData']['nowPage'].setMaximum(int(len(pdForm.index) // int(action) + 1))
        self.mainViews['primData']['pages'].setText(str(len(pdForm.index) // int(action) + 1))

    def handlePrimChgPage(self, nowId):
        """
        原始数页面的页面切换
        :param nowId:
        :return:
        """
        pdForm = self.mainViews['primData']['pdForm']
        if pdForm is None:
            return
        maxRow = int(self.mainViews['primData']['maxRow'].currentText())
        self.mainViews['primData']['table'].clear()
        for i1, i in enumerate(range((nowId - 1) * maxRow, nowId * maxRow)):
            for j1, j in enumerate(pdForm.columns):
                try:
                    self.mainViews['primData']['table'].setItem(i1, j1, QTableWidgetItem(pdForm.loc[i, j]))
                except:
                    pass

    def readToTaskSet(self, currentText):
        """
        读取数据预处理配置
        :param currentText:
        :return:
        """
        pdForm = self.mainViews['primData']['pdForm']
        state_file = self.dialogViews['data']['datasets'][currentText]
        self.mainViews['taskSet']['status'].setText(state_file['state'])
        self.mainViews['taskSet']['table'].setColumnCount(len(pdForm.columns))
        for i1, i in enumerate(pdForm.columns):
            self.mainViews['taskSet']['table'].setCellWidget(0, i1, QLabel(pdForm.iloc[0, i1]))
            tmp = QCheckBox("数值")
            tmp.setChecked(True)
            self.mainViews['taskSet']['table'].setCellWidget(1, i1, tmp)
            tmp = QComboBox()
            tmp.addItems(self.dataHandleMethod)
            tmp.setCurrentText(self.dialogViews['data']['defaultSet']['handleLoss'])
            self.mainViews['taskSet']['table'].setCellWidget(2, i1, tmp)
            self.mainViews['taskSet']['table'].setItem(3, i1, QTableWidgetItem("0"))

        self.mainViews['taskSet']["dCenters"].setValue(self.dialogViews['data']['defaultSet']['centers'])
        self.mainViews['taskSet']["checkCol"].setValue(self.dialogViews['data']['defaultSet']['checkCol'])

    def controlTask(self, action):
        current = self.datasetView.currentItem()
        if not current:
            msg_box = QMessageBox(QMessageBox.Warning, 'error', '未选择数据集')
            msg_box.setWindowIcon(self.windowIcon())
            msg_box.exec_()
            return
        currentText = current.text()

        names = [i.text() for i in self.taskMenu.actions()]
        if action == 'up':
            if currentText in names:
                return
            preHandle = self.gatherPreHandle()
            self.taskMenu.addAction(currentText).setData(preHandle)
            Service.startTask(currentText, self.mainViews['primData']["pdForm"].copy(), preHandle)
            self.mainViews['taskSet']['status'].setText("正在处理")
            self.dialogViews['data']['datasets'][currentText]['state'] = "正在处理"
            self.dialogViews['data']['datasets'][currentText]['skipHeader'] = preHandle['skipHeader']
        elif action == 'down':
            if currentText not in names:
                return

            for i1, i in enumerate(self.taskMenu.actions()):
                if i.text() == currentText:
                    self.taskMenu.removeAction(i)
                    break
            Service.stopTask(currentText)
            self.mainViews['taskSet']['status'].setText("未处理")
            self.dialogViews['data']['datasets'][currentText]['state'] = "未处理"

    def controlShowTask(self, action: QAction):
        currentText = action.text()
        for i in range(self.datasetView.count()):
            if self.datasetView.item(i) == currentText:
                currentItem = self.datasetView.item(i)
                break
        else:
            for i1, i in enumerate(self.taskMenu.actions()):
                if i.text() == currentText:
                    self.taskMenu.removeAction(i)
                    break
            Service.stopTask(currentText)
            return
        self.datasetView.setCurrentItem(currentItem)
        self.handleTopToolBar("taskSet")
        self.showPreHandle(action.data())

    def gatherPreHandle(self):
        """
        收集用户的数据与处理配置
        :return:
        """
        rlt = {
            "skipHeader": self.mainViews['taskSet']['skipHeader'].isChecked(),
            "colType": [],
            "handleLoss": [],
            "defaultFill": [],
            "dCenters": self.mainViews['taskSet']['dCenters'].value(),
            "checkCol": self.mainViews['taskSet']['checkCol'].value()
        }
        cols = self.mainViews['taskSet']['table'].columnCount()
        for i in range(cols):
            rlt["colType"].append(self.mainViews['taskSet']['table'].cellWidget(1, i).isChecked())
            rlt["handleLoss"].append(self.mainViews['taskSet']['table'].cellWidget(2, i).currentText())
            rlt["defaultFill"].append(self.mainViews['taskSet']['table'].item(3, i).text())

        return rlt

    def showPreHandle(self, rlt):
        """
        显示用户的数据预处理配置
        :param rlt:
        :return:
        """
        self.mainViews['taskSet']['skipHeader'].setChecked(rlt["skipHeader"])
        self.mainViews['taskSet']['dCenters'].setValue(rlt["dCenters"])
        self.mainViews['taskSet']['checkCol'].setValue(rlt["checkCol"])
        cols = self.mainViews['taskSet']['table'].columnCount()
        for i in range(cols):
            self.mainViews['taskSet']['table'].cellWidget(1, i).setChecked(rlt["colType"][i])
            self.mainViews['taskSet']['table'].cellWidget(2, i).setCurrentText(rlt["handleLoss"][i])
            self.mainViews['taskSet']['table'].cellWidget(3, i).setText(rlt["defaultFill"][i])

    def customEvent(self, a0: 'QEvent') -> None:
        """
        自定义事件，与算法程序进行通讯
        :param a0:
        :return:
        """
        if a0.type() == ServerEvent.idType:
            if a0.data['name'] in self.dialogViews['data']['datasets']:
                # print('========POST================')
                if 'acc' not in a0.data:
                    if self.datasetView.currentItem().text() == a0.data['name'] and self.currentMainLayer == 'primData':
                        self.dialogViews['data']['datasets'][a0.data['name']]['state'] = '处理失败'
                else:
                    self.dialogViews['data']['datasets'][a0.data['name']]['acc'] = a0.data['acc']
                    self.dialogViews['data']['datasets'][a0.data['name']]['nmi'] = a0.data['nmi']
                    self.dialogViews['data']['datasets'][a0.data['name']]['state'] = '已完成'
                    self.dialogViews['data']['datasets'][a0.data['name']]['dCenters'] = a0.data['dCenters']
                    with open(PROGRAM_ROOT + a0.data['name'] + '/state.txt', 'w') as f:
                        json.dump(self.dialogViews['data']['datasets'][a0.data['name']], f)

                    if self.datasetView.currentItem().text() == a0.data['name']:
                        self.mainViews['taskSet']['status'].setText('已完成')
                        self.mainViews['resultShow']['acc'].setText(a0.data['acc'])
                        self.mainViews['resultShow']['nmi'].setText(a0.data['nmi'])
                        if self.currentMainLayer == 'resultShow':
                            self.showResultXls(a0.data['name'])

    def handleServerCb(self, a0):
        """
        响应算法程序返回的结果
        :param a0:
        :return:
        """
        if a0.type() == ServerEvent.idType:
            if a0.data['name'] in self.dialogViews['data']['datasets']:
                if 'acc' not in a0.data:
                    self.dialogViews['data']['datasets'][a0.data['name']]['state'] = '已完成'
                    if self.datasetView.currentItem().text() == a0.data['name'] and self.currentMainLayer == 'primData':
                        self.dialogViews['data']['datasets'][a0.data['name']]['state'] = '处理失败'
                else:
                    self.dialogViews['data']['datasets'][a0.data['name']]['acc'] = a0.data['name']['acc']
                    self.dialogViews['data']['datasets'][a0.data['name']]['nmi'] = a0.data['name']['nmi']
                    self.dialogViews['data']['datasets'][a0.data['name']]['state'] = '已完成'
                    self.dialogViews['data']['datasets'][a0.data['name']]['dCenters'] = [a0.data['dCenters']]
                    with open(PROGRAM_ROOT + a0.data['name'], 'w') as f:
                        json.dump(self.dialogViews['data']['datasets'][a0.data['name']], f)
                    if self.datasetView.currentItem().text() == a0.data['name']:
                        self.handleTopToolBar(QAction("none"))
                        self.handleTopToolBar(QAction("primData"))
                    else:
                        for i in range(self.datasetView.count()):
                            if self.datasetView.item(i).text() == a0.data['name']:
                                self.datasetView.setCurrentItem(self.datasetView.item(i))
                                self.handleTopToolBar(QAction("primData"))

    def outputFile(self):
        """
        导出分析结果
        :return:
        """
        current = self.datasetView.currentItem()
        if not current:
            return
        if current.text() not in self.dialogViews['data']['datasets']:
            return

        if not os.path.exists(PROGRAM_ROOT + current.text() + '/to.csv'):
            return

        fileName, fileType = QtWidgets.QFileDialog.getSaveFileName(self, "文件保存", os.getcwd())
        if fileName == "":
            return
        # pdForm = pandas.DataFrame()
        type_ = self.mainViews['resultShow']['exportSet'].currentText()
        dCenters = list(self.dialogViews['data']['datasets'][current.text()]['dCenters'].keys())
        skipHeader = self.dialogViews['data']['datasets'][current.text()]['skipHeader']
        if type_ == "导出簇中心":
            if skipHeader:
                for i1, i in enumerate(dCenters):
                    dCenters[i1] += 1

            tmp_pd = self.mainViews['primData']['pdForm'].iloc[dCenters]
            tmp_pd.to_csv(fileName, header=None if not skipHeader else 0, index=None)
        elif type_ == "导出离群点":
            tmp_class = pandas.read_csv(PROGRAM_ROOT + current.text() + '/to.csv', header=None)
            cols = []
            # enDict2 = tmp_class.iloc[:, 0].idxmin()
            enDict2 = 0
            enDict3 = -1
            tmp_endDict1 = dict(tmp_class.iloc[:].value_counts())
            for k, v in tmp_endDict1.items():
                if v < enDict3 or enDict3 == -1:
                    enDict3 = v
                    enDict2 = k[0]
            for i in range(len(tmp_class.index)):
                if tmp_class.iloc[i, 0] == enDict2:
                    cols.append(i + 1 if skipHeader else 0)

            self.mainViews['primData']['pdForm'].iloc[cols].to_csv(fileName, header=None, index=None)

        elif type_ == "导出非离群点":
            tmp_class = pandas.read_csv(PROGRAM_ROOT + current.text() + '/to.csv', header=None)
            cols = []
            # enDict2 = tmp_class.iloc[:, 0].idxmin()
            enDict2 = 0
            enDict3 = -1
            tmp_endDict1 = dict(tmp_class.iloc[:].value_counts())
            for k, v in tmp_endDict1.items():
                if v < enDict3 or enDict3 == -1:
                    enDict3 = v
                    enDict2 = k[0]
            for i in range(len(tmp_class.index)):
                if tmp_class.iloc[i, 0] != enDict2:
                    cols.append(i + 1 if skipHeader else 0)

            self.mainViews['primData']['pdForm'].iloc[cols].to_csv(fileName, header=None, index=None)
        elif type_ == "导出分类列":
            shutil.copyfile(PROGRAM_ROOT + current.text() + '/to.csv', fileName)

    def showResultXls(self, currentText):
        """
        显示数据分析后的结果
        :param currentText:
        :return:
        """
        if os.path.exists(PROGRAM_ROOT + currentText + '/rlt.png'):
            self.mainViews['resultShow']['image'].setPixmap(QPixmap(PROGRAM_ROOT + currentText + '/rlt.png'))
        else:
            self.mainViews['resultShow']['image'].clear()
        self.mainViews['resultShow']['acc'].setText(self.dialogViews['data']['datasets'][currentText]['acc'])
        self.mainViews['resultShow']['nmi'].setText(self.dialogViews['data']['datasets'][currentText]['nmi'])
        if os.path.exists(PROGRAM_ROOT + currentText + '/to.csv'):
            tmp_dict = self.dialogViews['data']['datasets'][currentText]['dCenters']
            dCenters = list(tmp_dict.keys())
            dCenters = [int(i) for i in dCenters]
            dCenters_value = list(tmp_dict.values())

            if self.dialogViews['data']['datasets'][currentText]['skipHeader']:
                for i1, i in enumerate(dCenters):
                    dCenters[i1] += 1

            tmp_pd = self.mainViews['primData']['pdForm'].iloc[[int(i) for i in dCenters]]

            self.mainViews['resultShow']['table'].clear()
            self.mainViews['resultShow']['table'].setColumnCount(len(tmp_pd.columns) + 1)
            self.mainViews['resultShow']['table'].setRowCount(len(tmp_pd.index))
            self.mainViews['resultShow']['table'].setHorizontalHeaderItem(len(tmp_pd.columns), QTableWidgetItem("数量"))
            for i1, i in enumerate(tmp_pd.index):
                for j1, j in enumerate(tmp_pd.columns):
                    self.mainViews['resultShow']['table'].setItem(i1, j1, QTableWidgetItem(str(tmp_pd.iloc[i1, j1])))
                self.mainViews['resultShow']['table'].setItem(i1, len(tmp_pd.columns),
                                                              QTableWidgetItem(str(dCenters_value[i1])))

        else:
            self.mainViews['resultShow']['table'].setColumnCount(0)

    def close(self) -> bool:
        """
        界面关闭
        :return:
        """
        Service.stopAll()
        return super(MainWidget, self).close()


class MyThread(Thread):
    """
    继承线程类，添加强制终止线程的功能，用来运行算法程序
    """

    def __init__(self, name, callback, **kwargs):
        super(MyThread, self).__init__()
        self.name = name
        self.kwargs = kwargs
        self.callback = callback
        self.stopped = False

    def run(self) -> None:
        rlt = previousHandle(**self.kwargs)

        if not self.stopped:
            rlt['name'] = self.name
            self.callback(rlt)

    def stop(self):
        """raises the exception, performs cleanup if needed"""
        tid = self.ident
        exctype = SystemExit
        try:
            tid = ctypes.c_long(tid)
            if not inspect.isclass(exctype):
                exctype = type(exctype)
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
            if res == 0:
                # pass
                raise ValueError("invalid thread id")
            elif res != 1:
                # """if it returns a number greater than one, you're in trouble,
                # and you should call it again with exc=NULL to revert the effect"""
                ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
                raise SystemError("PyThreadState_SetAsyncExc failed")
        except Exception as err:
            print(err)


class _Service:
    """
    后台，管理算法程序
    """

    def __init__(self):
        # 保存线程
        self.pools = {}
        # 事件接收者，即主界面程序
        self.sub = None

    def stopAll(self):
        """
        停止所有任务
        :return:
        """
        for i in list(self.pools.keys()):
            self.stopTask(i)

    def setSub(self, sub):
        self.sub = sub

    def startTask(self, name, pd, handle):
        """
        启动任务
        :param name:
        :param pd:
        :param handle:
        :return:
        """
        self.stopTask(name)
        self.pools[name] = MyThread(
            name,
            self.handleCallback,
            arg=handle, pdForm=pd,
            cacheFile=PROGRAM_CACHE_ROOT + name,
            rltPath=PROGRAM_ROOT + name + '/to.csv',
            imgPath=PROGRAM_ROOT + name + '/rlt.png')
        self.pools[name].start()

    def stopTask(self, name):
        """
        停止任务
        :param name:
        :return:
        """
        if name in self.pools:
            tmp = self.pools[name]
            del self.pools[name]
            if tmp.is_alive():
                tmp.stop()

    def handleCallback(self, rlt):
        """
        发送事件给界面程序
        :param rlt:
        :return:
        """
        if self.sub is not None:
            QCoreApplication.sendEvent(self.sub, ServerEvent(rlt))
        self.stopTask(rlt['name'])


Service = _Service()

if __name__ == "__main__":
    myWindow = MainWidget()
    myWindow.show()
    sys.exit(App.exec_())
