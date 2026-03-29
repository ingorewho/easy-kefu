import sys
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel
from PyQt6.QtGui import QFont, QIcon, QPixmap
from qfluentwidgets import FluentWindow,qrouter, NavigationItemPosition, setTheme, Theme
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import SubtitleLabel
from ui.user_ui import UserManagerWidget
from ui.keyword_ui import KeywordManagerWidget
from ui.auto_reply_ui import AutoReplyUI, auto_reply_manager
from ui.log_ui import LogUI
from ui.setting_ui import SettingUI
from ui.chat_history import ChatHistoryUI
from ui.ai_test_ui import AITestUI
from ui.knowledge_base_ui import KnowledgeBaseUI
from ui.ai_learning_ui import AITestUI as AILearningUI
from utils.logger import get_logger

def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class Widget(QFrame):

    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        # 创建标题标签
        self.label = SubtitleLabel(text, self)
        # 创建水平布局
        self.hBoxLayout = QHBoxLayout(self)
        # 设置标签文本居中对齐
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 将标签添加到布局中,设置居中对齐和拉伸因子1
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignmentFlag.AlignCenter)

        # 必须给子界面设置全局唯一的对象名
        self.setObjectName(text.replace(' ', '-'))

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('智能客服')
        # 使用资源路径加载图标
        icon_path = get_resource_path("resources/icons/icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            # 降级方案：使用 icns 或默认图标
            self.setWindowIcon(QIcon())
        self.logger = get_logger("MainWindow")

        # 创建主要视图
        self.monitor_view = AutoReplyUI(self)
        self.keyword_manager_view = KeywordManagerWidget(self)
        self.user_manager_view = UserManagerWidget(self)
        self.log_view = LogUI(self)
        self.chat_history_view = ChatHistoryUI(self)
        self.ai_test_view = AITestUI(self)
        self.knowledge_base_view = KnowledgeBaseUI(self)
        self.ai_learning_view = AILearningUI(self)
        self.settingInterface = SettingUI(self)

        # 初始化界面
        self.initNavigation()
        self.initWindow()

    # 初始化导航栏
    def initNavigation(self):
        self.navigationInterface.setExpandWidth(200)
        self.navigationInterface.setMinimumWidth(200)
        self.addSubInterface(self.monitor_view, FIF.CHAT, '自动回复')
        self.addSubInterface(self.keyword_manager_view, FIF.EDIT, '关键词管理')
        self.addSubInterface(self.user_manager_view, FIF.PEOPLE, '账号管理')
        self.addSubInterface(self.chat_history_view, FIF.MUSIC, '聊天历史')
        self.addSubInterface(self.ai_test_view, FIF.ROBOT, 'AI 测试')
        self.addSubInterface(self.knowledge_base_view, FIF.BOOK_SHELF, '知识库')
        self.addSubInterface(self.ai_learning_view, FIF.LEAF, 'AI 学习')
        self.addSubInterface(self.log_view, FIF.HISTORY, '日志管理')
        self.addSubInterface(self.settingInterface, FIF.SETTING, '设置', NavigationItemPosition.BOTTOM)
        
        
        # 设置默认选中的界面为设置页
        qrouter.setDefaultRouteKey(self.navigationInterface, self.settingInterface.objectName())

    def toggleTheme(self):
        """切换夜间/日间模式"""
        from qfluentwidgets import setTheme, Theme
        current_theme = self.themeController.actualTheme
        if current_theme == Theme.DARK:
            setTheme(Theme.LIGHT)
        else:
            setTheme(Theme.DARK)

    # 初始化窗口
    def initWindow(self):
        self.resize(1000, 800)
        self.setMinimumWidth(1280)
        self.setMinimumHeight(720)
        self.center()
        # 启动后默认切换到设置页
        self.switchTo(self.settingInterface)

    # 将窗口移动到屏幕中央
    def center(self):
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def closeEvent(self, event):
        """ 重写窗口关闭事件，确保后台线程安全退出 """
       
        # 停止所有自动回复线程
        auto_reply_manager.stop_all()
        
        super().closeEvent(event) 