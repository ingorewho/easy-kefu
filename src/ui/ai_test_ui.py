"""AI 测试界面 - 模拟与 AI 对话"""
import threading
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QThreadPool, QRunnable, QObject
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget,
                            QLabel, QTextEdit, QScrollArea, QWidgetAction)
from PyQt6.QtGui import QFont
from qfluentwidgets import (CardWidget, SubtitleLabel, CaptionLabel, StrongBodyLabel,
                           PrimaryPushButton, PushButton, LineEdit, ComboBox,
                           ScrollArea, FluentIcon as FIF, InfoBar, InfoBarPosition,
                           TextEdit, Dialog)
from config import config
from core.bridge.context import Context, ContextType, ChannelType
from core.bridge.reply import Reply, ReplyType
from utils.logger import get_logger


class AIWorkerSignals(QObject):
    """AI Worker 信号"""
    result = pyqtSignal(object, object)  # status, result


class AIWorker(QRunnable):
    """AI 调用工作线程"""

    def __init__(self, bot, context):
        super().__init__()
        self.bot = bot
        self.context = context
        self.signals = AIWorkerSignals()

    def run(self):
        try:
            if not self.bot:
                self.signals.result.emit("error", "Bot 未初始化，请检查配置")
                return

            # 直接调用同步的 bot.reply 方法
            reply = self.bot.reply(self.context)
            self.signals.result.emit("success", reply)
        except Exception as e:
            self.signals.result.emit("error", str(e))


class AITestUI(QFrame):
    """AI 测试界面 - 模拟与 AI 对话"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.bot = None
        self.conversation_history = []  # 当前测试会话历史
        self.system_prompt = "你是智能客服助手，请友好、专业地回答用户问题。"
        self.logger = get_logger("AITestUI")
        self.setupUI()
        self.init_bot()
        self.setObjectName("AI 测试")

    def setupUI(self):
        """设置主界面UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 顶部: 配置和提示词设置
        self.config_panel = self._create_config_panel()
        main_layout.addWidget(self.config_panel)

        # 中间: 聊天记录区域
        self.chat_area = self._create_chat_area()
        main_layout.addWidget(self.chat_area, 1)

        # 底部: 输入区域
        self.input_panel = self._create_input_panel()
        main_layout.addWidget(self.input_panel)

    def _create_config_panel(self):
        """创建配置面板"""
        panel = CardWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)

        # 模型信息显示
        self.model_label = SubtitleLabel("当前模型: 加载中...")
        layout.addWidget(self.model_label)

        layout.addStretch()

        # 系统提示词设置
        self.sys_prompt_btn = PushButton("设置系统提示词")
        self.sys_prompt_btn.setIcon(FIF.EDIT)
        self.sys_prompt_btn.clicked.connect(self.set_system_prompt)
        layout.addWidget(self.sys_prompt_btn)

        # 清空对话
        self.clear_btn = PushButton("清空对话")
        self.clear_btn.setIcon(FIF.DELETE)
        self.clear_btn.clicked.connect(self.clear_conversation)
        layout.addWidget(self.clear_btn)

        return panel

    def _create_chat_area(self):
        """创建聊天显示区域（气泡形式）"""
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(12)
        self.chat_layout.setContentsMargins(12, 12, 12, 12)
        self.chat_layout.addStretch()

        scroll.setWidget(self.chat_container)

        # 添加欢迎消息
        self._add_system_message("欢迎使用 AI 测试功能！在这里您可以模拟用户与 AI 对话，测试不同场景下的回复效果。")

        return scroll

    def _create_input_panel(self):
        """创建输入区域"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 第一行: 消息类型和选项
        top_layout = QHBoxLayout()

        # 消息类型选择
        top_layout.addWidget(QLabel("消息类型:"))
        self.msg_type_combo = ComboBox()
        self.msg_type_combo.addItems([
            "文本消息",
            "商品咨询",
            "订单信息"
        ])
        self.msg_type_combo.setFixedWidth(150)
        top_layout.addWidget(self.msg_type_combo)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # 第二行: 输入框和发送按钮
        bottom_layout = QHBoxLayout()

        # 输入框
        self.input_edit = TextEdit()
        self.input_edit.setPlaceholderText("输入测试消息，按 Enter 发送...")
        self.input_edit.setMaximumHeight(80)
        self.input_edit.installEventFilter(self)
        bottom_layout.addWidget(self.input_edit, 1)

        # 发送按钮
        self.send_btn = PrimaryPushButton("发送")
        self.send_btn.setIcon(FIF.SEND)
        self.send_btn.setFixedSize(100, 40)
        self.send_btn.clicked.connect(self.send_message)
        bottom_layout.addWidget(self.send_btn)

        layout.addLayout(bottom_layout)

        return panel

    def eventFilter(self, obj, event):
        """事件过滤器 - 处理 Enter 发送"""
        if obj == self.input_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return and not event.modifiers():
                self.send_message()
                return True
        return super().eventFilter(obj, event)

    def init_bot(self):
        """初始化 Bot"""
        try:
            from core.agents.bot_factory import create_bot
            # 重新加载配置，确保获取最新的 RAG 设置
            config.reload()
            self.bot = create_bot()
            bot_type = config.get('bot_type', 'coze').upper()
            enable_rag = config.get('enable_rag', False)
            self.model_label.setText(f"当前模型: {bot_type} {'(RAG)' if enable_rag else ''}")
            self.logger.info(f"AI 测试界面初始化 Bot 成功: {bot_type}, RAG={enable_rag}")
        except Exception as e:
            self.model_label.setText(f"模型加载失败: {e}")
            self.logger.error(f"AI 测试界面初始化 Bot 失败: {e}")

    def send_message(self):
        """发送测试消息"""
        content = self.input_edit.toPlainText().strip()
        if not content:
            return

        # 重新加载配置，确保使用最新的 API Key
        config.reload()

        # 每次发送前重新初始化 Bot，确保使用最新配置
        try:
            from core.agents.bot_factory import create_bot
            self.bot = create_bot()
            bot_type = config.get('bot_type', 'coze').upper()
            enable_rag = config.get('enable_rag', False)
            self.model_label.setText(f"当前模型: {bot_type} {'(RAG)' if enable_rag else ''}")
            self.logger.info(f"Bot 已初始化: type={bot_type}, RAG={enable_rag}, bot_class={self.bot.__class__.__name__}")
        except Exception as e:
            self._add_system_message(f"模型初始化失败: {e}")
            return

        # 1. 显示用户消息
        self._add_user_message(content)

        # 2. 清空输入框
        self.input_edit.clear()

        # 3. 构建 Context
        context = self._build_test_context(content)

        # 3. 调用 AI
        self.send_btn.setEnabled(False)
        self.send_btn.setText("思考中...")

        # 在新线程中运行 AI 调用，避免阻塞 UI
        worker = AIWorker(self.bot, context)
        worker.signals.result.connect(self._handle_ai_result)
        QThreadPool.globalInstance().start(worker)

    def _handle_ai_result(self, status, result):
        """处理 AI 回复结果（在主线程中执行），带随机延迟"""
        import random
        import time

        # 从配置读取延迟范围
        config.reload()
        delay_min = config.get("ai_reply_delay_min", 2)
        delay_max = config.get("ai_reply_delay_max", 10)
        delay = random.uniform(delay_min, delay_max)
        self.logger.info(f"AI 回复延迟: {delay:.1f}秒 (范围: {delay_min}-{delay_max})")
        time.sleep(delay)

        if status == "success":
            reply = result
            if reply.type == ReplyType.TEXT:
                self._add_ai_message(reply.content)
            else:
                self._add_ai_message(f"[非文本回复: {reply.type}]")
        else:
            self._add_system_message(f"错误: {result}")

        self.send_btn.setEnabled(True)
        self.send_btn.setText("发送")

    def _build_test_context(self, content: str) -> Context:
        """构建测试用的 Context"""
        msg_type_map = {
            0: ContextType.TEXT,
            1: ContextType.GOODS_INQUIRY,
            2: ContextType.ORDER_INFO
        }

        msg_type_idx = self.msg_type_combo.currentIndex()

        # 如果选择的是商品咨询或订单信息，构造对应格式
        if msg_type_idx == 1:  # 商品咨询
            content = {
                "goods_id": "test_123",
                "goods_name": "测试商品",
                "goods_price": "99.99",
                "goods_spec": content  # 用户输入作为规格咨询
            }
        elif msg_type_idx == 2:  # 订单信息
            content = {
                "order_id": "ORDER_12345",
                "goods_name": "测试商品",
                "order_status": "待发货"
            }

        return Context(
            type=msg_type_map[msg_type_idx],
            content=content,
            kwargs={
                'user_id': 'test_user_001',
                'shop_id': 'test_shop_001',
                'from_uid': 'test_uid_001',
                'username': '测试店铺',
                'nickname': '测试用户',
                'account_id': 1
            },
            channel_type=ChannelType.PINDUODUO
        )

    def _add_user_message(self, content: str):
        """添加用户消息气泡"""
        bubble = self._create_message_bubble("user", content)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        # 保存历史
        self.conversation_history.append({
            'sender': 'user',
            'content': content,
            'time': datetime.now()
        })

    def _add_ai_message(self, content: str):
        """添加 AI 消息气泡"""
        bubble = self._create_message_bubble("ai", content)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

        # 保存历史
        self.conversation_history.append({
            'sender': 'ai',
            'content': content,
            'time': datetime.now()
        })

    def _add_system_message(self, content: str):
        """添加系统消息"""
        bubble = self._create_message_bubble("system", content)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)

    def _create_message_bubble(self, sender: str, content: str) -> QWidget:
        """创建单个消息气泡"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 4)

        # 消息标签
        msg_label = QLabel(content)
        msg_label.setWordWrap(True)
        msg_label.setMaximumWidth(500)
        msg_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # 时间标签
        time_str = datetime.now().strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #999; font-size: 10px;")

        if sender == "user":
            # 用户消息 - 绿色右对齐
            msg_label.setStyleSheet("""
                QLabel {
                    background-color: #95EC69;
                    padding: 10px 12px;
                    border-radius: 8px;
                    color: #000;
                }
            """)

            # 垂直布局：消息在上，时间在下
            v_layout = QVBoxLayout()
            v_layout.setSpacing(2)
            v_layout.addWidget(msg_label)
            v_layout.addWidget(time_label)
            v_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

            layout.addStretch()
            layout.addLayout(v_layout)

        elif sender == "ai":
            # AI 消息 - 白色左对齐
            msg_label.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    padding: 10px 12px;
                    border-radius: 8px;
                    color: #000;
                }
            """)

            # 垂直布局
            v_layout = QVBoxLayout()
            v_layout.setSpacing(2)
            v_layout.addWidget(msg_label)
            v_layout.addWidget(time_label)
            v_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

            layout.addLayout(v_layout)
            layout.addStretch()

        else:
            # 系统消息 - 居中灰色
            msg_label.setStyleSheet("""
                QLabel {
                    color: #999;
                    padding: 8px;
                    font-size: 12px;
                }
            """)
            msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(msg_label)

        return container

    def set_system_prompt(self):
        """设置系统提示词"""
        dialog = Dialog("设置系统提示词", "", self)
        dialog.yesButton.setText("确定")
        dialog.cancelButton.setText("取消")

        # 添加文本编辑框
        text_edit = TextEdit()
        text_edit.setPlainText(self.system_prompt)
        text_edit.setMinimumHeight(100)
        dialog.vBoxLayout.insertWidget(1, text_edit)

        if dialog.exec():
            self.system_prompt = text_edit.toPlainText().strip()
            InfoBar.success(
                title="设置成功",
                content="系统提示词已更新",
                parent=self
            )

    def clear_conversation(self):
        """清空对话"""
        # 清除所有消息气泡（保留 stretch）
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 清空历史
        self.conversation_history.clear()

        # 添加欢迎消息
        self._add_system_message("对话已清空。开始新的测试对话吧！")
