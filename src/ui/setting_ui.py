# 设置界面

from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel,
                            QFormLayout, QStackedWidget, QMessageBox, QFileDialog)
from PyQt6.QtGui import QFont
from qfluentwidgets import (CardWidget, SubtitleLabel, CaptionLabel, BodyLabel,
                           PrimaryPushButton, PushButton, StrongBodyLabel,
                           LineEdit, ComboBox, ScrollArea, FluentIcon as FIF,
                           InfoBar, InfoBarPosition, PasswordLineEdit,
                           TimePicker, SpinBox, SwitchButton, TextEdit, setTheme, Theme)
from PyQt6.QtCore import QTime
from utils.logger import get_logger
from config import config
from utils.license_manager import get_license_manager


class ModelSelectCard(CardWidget):
    """AI 模型选择卡片"""

    model_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("AI 模型选择")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 模型类型选择
        self.model_type_combo = ComboBox()
        self.model_type_combo.addItems(["Coze", "Kimi (Moonshot)", "Qwen (通义千问)"])
        self.model_type_combo.setFixedWidth(200)
        self.model_type_combo.currentIndexChanged.connect(self.model_changed.emit)
        form_layout.addRow("选择模型:", self.model_type_combo)

        layout.addLayout(form_layout)

        # 说明文本
        self.description_label = CaptionLabel(
            "Coze: 字节跳动扣子平台，支持自定义工作流和插件\n"
            "Kimi: Moonshot AI，长文本处理能力出色\n"
            "Qwen: 阿里云通义千问，中文理解能力强"
        )
        self.description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(self.description_label)

    def getConfig(self) -> dict:
        """获取配置"""
        model_map = {0: "coze", 1: "kimi", 2: "qwen"}
        return {"bot_type": model_map.get(self.model_type_combo.currentIndex(), "coze")}

    def setConfig(self, config_data: dict):
        """设置配置"""
        bot_type = config_data.get("bot_type", "coze")
        model_map = {"coze": 0, "kimi": 1, "qwen": 2}
        index = model_map.get(bot_type, 0)
        self.model_type_combo.setCurrentIndex(index)


class CozeConfigCard(CardWidget):
    """Coze配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("Coze AI 配置")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # API Base URL
        self.api_base_edit = LineEdit()
        self.api_base_edit.setPlaceholderText("https://api.coze.cn")
        self.api_base_edit.setText("https://api.coze.cn")
        form_layout.addRow("API Base URL:", self.api_base_edit)

        # API Token
        self.api_token_edit = PasswordLineEdit()
        self.api_token_edit.setPlaceholderText("输入您的 Coze API Token")
        form_layout.addRow("API Token:", self.api_token_edit)

        # Bot ID
        self.bot_id_edit = LineEdit()
        self.bot_id_edit.setPlaceholderText("输入您的 Bot ID")
        form_layout.addRow("Bot ID:", self.bot_id_edit)

        layout.addLayout(form_layout)

        # 说明文本
        description_label = CaptionLabel(
            "请在 Coze 平台获取您的 API Token 和 Bot ID。\n"
            "API Token 用于身份验证，Bot ID 用于指定使用的特定机器人。"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def getConfig(self) -> dict:
        """获取配置"""
        return {
            "coze_api_base": self.api_base_edit.text().strip() or "https://api.coze.cn",
            "coze_token": self.api_token_edit.text().strip(),
            "coze_bot_id": self.bot_id_edit.text().strip()
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        self.api_base_edit.setText(config_data.get("coze_api_base", "https://api.coze.cn"))
        self.api_token_edit.setText(config_data.get("coze_token", ""))
        self.bot_id_edit.setText(config_data.get("coze_bot_id", ""))


class KimiConfigCard(CardWidget):
    """Kimi 配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("Kimi (Moonshot) 配置")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # API Base URL
        self.api_base_edit = LineEdit()
        self.api_base_edit.setPlaceholderText("https://api.moonshot.cn/v1")
        self.api_base_edit.setText("https://api.moonshot.cn/v1")
        form_layout.addRow("API Base URL:", self.api_base_edit)

        # API Key
        self.api_key_edit = PasswordLineEdit()
        self.api_key_edit.setPlaceholderText("输入您的 Moonshot API Key")
        form_layout.addRow("API Key:", self.api_key_edit)

        # Model 选择
        self.model_combo = ComboBox()
        self.model_combo.addItems([
            "kimi-k2.5",          # 最新 k2.5 系列（推荐）
            "kimi-k2.5-long",     # k2.5 长上下文版本
            "moonshot-v1-8k",
            "moonshot-v1-32k",
            "moonshot-v1-128k",
            "moonshot-v1-auto"
        ])
        self.model_combo.setFixedWidth(200)
        form_layout.addRow("模型:", self.model_combo)

        layout.addLayout(form_layout)

        # 说明文本
        description_label = CaptionLabel(
            "请在 Moonshot AI 开放平台获取您的 API Key。\n"
            "推荐：kimi-k2.5 系列具有更强的推理能力和代码能力\n"
            "v1 系列：8k(8K)/32k(32K)/128k(128K)/auto(自动选择)"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def getConfig(self) -> dict:
        """获取配置"""
        return {
            "kimi_api_base": self.api_base_edit.text().strip() or "https://api.moonshot.cn/v1",
            "kimi_api_key": self.api_key_edit.text().strip(),
            "kimi_model": self.model_combo.currentText()
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        self.api_base_edit.setText(config_data.get("kimi_api_base", "https://api.moonshot.cn/v1"))
        self.api_key_edit.setText(config_data.get("kimi_api_key", ""))

        model = config_data.get("kimi_model", "kimi-k2.5")
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        else:
            # 如果找不到对应模型，添加并选择它（支持自定义模型）
            self.model_combo.addItem(model)
            self.model_combo.setCurrentIndex(self.model_combo.count() - 1)


class QwenConfigCard(CardWidget):
    """Qwen 配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("Qwen (通义千问) 配置")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # API Base URL
        self.api_base_edit = LineEdit()
        self.api_base_edit.setPlaceholderText("https://dashscope.aliyuncs.com/api/v1")
        self.api_base_edit.setText("https://dashscope.aliyuncs.com/api/v1")
        form_layout.addRow("API Base URL:", self.api_base_edit)

        # API Key
        self.api_key_edit = PasswordLineEdit()
        self.api_key_edit.setPlaceholderText("输入您的 DashScope API Key")
        form_layout.addRow("API Key:", self.api_key_edit)

        # Model 选择
        self.model_combo = ComboBox()
        self.model_combo.addItems([
            "qwen-turbo",
            "qwen-plus",
            "qwen-max",
            "qwen-max-longcontext"
        ])
        self.model_combo.setFixedWidth(200)
        form_layout.addRow("模型:", self.model_combo)

        layout.addLayout(form_layout)

        # 说明文本
        description_label = CaptionLabel(
            "请在阿里云百炼平台获取您的 DashScope API Key。\n"
            "模型说明：turbo(快速)/plus(均衡)/max(最强)/max-longcontext(超长上下文)"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def getConfig(self) -> dict:
        """获取配置"""
        return {
            "qwen_api_base": self.api_base_edit.text().strip() or "https://dashscope.aliyuncs.com/api/v1",
            "qwen_api_key": self.api_key_edit.text().strip(),
            "qwen_model": self.model_combo.currentText()
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        self.api_base_edit.setText(config_data.get("qwen_api_base", "https://dashscope.aliyuncs.com/api/v1"))
        self.api_key_edit.setText(config_data.get("qwen_api_key", ""))

        model = config_data.get("qwen_model", "qwen-turbo")
        index = self.model_combo.findText(model)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)


class BusinessHoursCard(CardWidget):
    """业务时间配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("业务时间设置")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 开始时间
        self.start_time_picker = TimePicker()
        self.start_time_picker.setTime(QTime(8, 0))  # 默认8:00
        form_layout.addRow("开始时间:", self.start_time_picker)

        # 结束时间
        self.end_time_picker = TimePicker()
        self.end_time_picker.setTime(QTime(23, 0))  # 默认23:00
        form_layout.addRow("结束时间:", self.end_time_picker)

        layout.addLayout(form_layout)

        # 说明文本
        description_label = CaptionLabel(
            "设置AI客服的工作时间。在工作时间内，系统将自动响应客户消息。\n"
            "在非工作时间，系统将不会自动回复。"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def getConfig(self) -> dict:
        """获取配置"""
        return {
            "businessHours": {
                "start": self.start_time_picker.getTime().toString("HH:mm"),
                "end": self.end_time_picker.getTime().toString("HH:mm")
            }
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        business_hours = config_data.get("businessHours", {})

        # 解析开始时间
        start_time_str = business_hours.get("start", "08:00")
        start_time = QTime.fromString(start_time_str, "HH:mm")
        if start_time.isValid():
            self.start_time_picker.setTime(start_time)

        # 解析结束时间
        end_time_str = business_hours.get("end", "23:00")
        end_time = QTime.fromString(end_time_str, "HH:mm")
        if end_time.isValid():
            self.end_time_picker.setTime(end_time)


class AIReplyConfigCard(CardWidget):
    """AI 回复风格配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("AI 回复风格配置")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 系统提示词
        self.system_prompt_edit = TextEdit()
        self.system_prompt_edit.setPlaceholderText("你是电商客服，回复要简短口语化，不超过20字")
        self.system_prompt_edit.setMaximumHeight(80)
        form_layout.addRow("系统提示词:", self.system_prompt_edit)

        # 最大字数
        self.max_length_spin = SpinBox()
        self.max_length_spin.setRange(5, 200)
        self.max_length_spin.setValue(20)
        self.max_length_spin.setSuffix(" 字")
        form_layout.addRow("最大字数:", self.max_length_spin)

        # 回复风格
        self.style_combo = ComboBox()
        self.style_combo.addItems(["口语化", "正式"])
        self.style_combo.setFixedWidth(150)
        form_layout.addRow("回复风格:", self.style_combo)

        # 不带标点符号
        self.no_punctuation_switch = SwitchButton()
        self.no_punctuation_switch.setChecked(True)
        form_layout.addRow("不带标点符号:", self.no_punctuation_switch)

        # 回复延迟范围
        delay_layout = QHBoxLayout()
        self.delay_min_spin = SpinBox()
        self.delay_min_spin.setRange(0, 30)
        self.delay_min_spin.setValue(2)
        self.delay_min_spin.setSuffix(" 秒")
        self.delay_max_spin = SpinBox()
        self.delay_max_spin.setRange(0, 60)
        self.delay_max_spin.setValue(10)
        self.delay_max_spin.setSuffix(" 秒")
        delay_layout.addWidget(self.delay_min_spin)
        delay_layout.addWidget(QLabel("-"))
        delay_layout.addWidget(self.delay_max_spin)
        delay_layout.addStretch()
        form_layout.addRow("回复延迟:", delay_layout)

        layout.addLayout(form_layout)

        # 说明文本
        description_label = CaptionLabel(
            "设置AI客服回复的风格和限制条件。\n"
            "系统提示词：定义AI的角色和回复要求\n"
            "回复延迟：模拟人工回复的思考时间"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def getConfig(self) -> dict:
        """获取配置"""
        style_map = {0: "casual", 1: "formal"}
        return {
            "ai_system_prompt": self.system_prompt_edit.toPlainText().strip() or "你是电商客服，回复要简短口语化，不超过20字",
            "ai_reply_max_length": self.max_length_spin.value(),
            "ai_reply_style": style_map.get(self.style_combo.currentIndex(), "casual"),
            "ai_reply_no_punctuation": self.no_punctuation_switch.isChecked(),
            "ai_reply_delay_min": self.delay_min_spin.value(),
            "ai_reply_delay_max": self.delay_max_spin.value()
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        self.system_prompt_edit.setPlainText(config_data.get("ai_system_prompt", "你是电商客服，回复要简短口语化，不超过20字"))
        self.max_length_spin.setValue(config_data.get("ai_reply_max_length", 20))

        style = config_data.get("ai_reply_style", "casual")
        style_map = {"casual": 0, "formal": 1}
        self.style_combo.setCurrentIndex(style_map.get(style, 0))

        self.no_punctuation_switch.setChecked(config_data.get("ai_reply_no_punctuation", True))
        self.delay_min_spin.setValue(config_data.get("ai_reply_delay_min", 2))
        self.delay_max_spin.setValue(config_data.get("ai_reply_delay_max", 10))


class EmotionAlertCard(CardWidget):
    """情绪告警配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("情绪告警设置")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 启用情绪告警
        self.enable_alert_switch = SwitchButton()
        self.enable_alert_switch.setChecked(False)
        form_layout.addRow("启用情绪告警:", self.enable_alert_switch)

        # 告警阈值
        self.threshold_spin = SpinBox()
        self.threshold_spin.setRange(-10, 0)
        self.threshold_spin.setValue(-6)
        self._update_threshold_suffix()
        self.threshold_spin.valueChanged.connect(self._update_threshold_suffix)
        form_layout.addRow("告警阈值:", self.threshold_spin)

        # 冷却时间
        self.cooldown_spin = SpinBox()
        self.cooldown_spin.setRange(60, 3600)
        self.cooldown_spin.setValue(300)
        self.cooldown_spin.setSuffix(" 秒")
        form_layout.addRow("冷却时间:", self.cooldown_spin)

        # Telegram Bot Token
        self.bot_token_edit = PasswordLineEdit()
        self.bot_token_edit.setPlaceholderText("输入您的 Telegram Bot Token")
        form_layout.addRow("Telegram Bot Token:", self.bot_token_edit)

        # Telegram Chat ID
        self.chat_id_edit = LineEdit()
        self.chat_id_edit.setPlaceholderText("输入接收告警的 Chat ID")
        form_layout.addRow("Telegram Chat ID:", self.chat_id_edit)

        layout.addLayout(form_layout)

        # 测试按钮
        test_btn_layout = QHBoxLayout()
        test_btn_layout.addStretch()
        self.test_alert_btn = PushButton("发送测试消息")
        self.test_alert_btn.setIcon(FIF.SEND)
        self.test_alert_btn.setFixedWidth(150)
        self.test_alert_btn.clicked.connect(self._on_test_alert)
        test_btn_layout.addWidget(self.test_alert_btn)
        layout.addLayout(test_btn_layout)

        # 说明文本
        description_label = CaptionLabel(
            "当检测到用户消息的负面情绪超过阈值时，系统将通过 Telegram 发送告警通知。\n"
            "告警阈值：情绪分数低于此值时触发告警（范围：-1.0 ~ 0，推荐 -0.6）\n"
            "冷却时间：同一用户的告警间隔时间，避免短时间内重复告警\n"
            "Bot Token 和 Chat ID 用于指定接收告警的 Telegram 机器人和聊天对象。"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def _update_threshold_suffix(self, value=None):
        """更新阈值后缀显示"""
        actual_value = self.threshold_spin.value() / 10
        self.threshold_spin.setSuffix(f"  (实际：{actual_value:.1f})")

    def _on_test_alert(self):
        """测试告警按钮点击事件"""
        from utils.telegram_notifier import init_notifier, send_test_alert

        bot_token = self.bot_token_edit.text().strip()
        chat_id = self.chat_id_edit.text().strip()

        if not bot_token or not chat_id:
            InfoBar.warning(
                title="配置不完整",
                content="请先填写 Telegram Bot Token 和 Chat ID",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return

        # 初始化通知器
        init_notifier(bot_token, chat_id)

        # 发送测试消息
        success = send_test_alert()

        if success:
            InfoBar.success(
                title="发送成功",
                content="测试消息已发送，请查收！",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.error(
                title="发送失败",
                content="请检查 Bot Token 和 Chat ID 是否正确，以及网络连接是否正常",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )

    def getConfig(self) -> dict:
        """获取配置"""
        # 阈值转换为实际值（-10 ~ 0 -> -1.0 ~ 0）
        threshold_value = self.threshold_spin.value() / 10
        return {
            "enable_telegram_alert": self.enable_alert_switch.isChecked(),
            "emotion_alert_threshold": threshold_value,
            "emotion_alert_cooldown": self.cooldown_spin.value(),
            "telegram_bot_token": self.bot_token_edit.text().strip(),
            "telegram_chat_id": self.chat_id_edit.text().strip()
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        self.enable_alert_switch.setChecked(config_data.get("enable_telegram_alert", False))

        # 阈值转换（-1.0 ~ 0 -> -10 ~ 0）
        threshold = config_data.get("emotion_alert_threshold", -0.6)
        self.threshold_spin.setValue(int(threshold * 10))

        self.cooldown_spin.setValue(config_data.get("emotion_alert_cooldown", 300))
        self.bot_token_edit.setText(config_data.get("telegram_bot_token", ""))
        self.chat_id_edit.setText(config_data.get("telegram_chat_id", ""))


class SettingUI(QFrame):
    """设置界面"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.logger = get_logger("SettingUI")
        self.setupUI()
        self.loadConfig()

        # 设置对象名
        self.setObjectName("设置")

    def setupUI(self):
        """设置主界面UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # 创建头部区域
        header_widget = self.createHeaderWidget()

        # 创建内容区域
        content_widget = self.createContentWidget()

        # 连接按钮信号
        self.save_btn.clicked.connect(self.onSaveConfig)
        self.reset_btn.clicked.connect(self.onResetConfig)

        # 添加到主布局
        main_layout.addWidget(header_widget)
        main_layout.addWidget(content_widget, 1)

    def createHeaderWidget(self):
        """创建头部区域"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(20)

        # 标题
        title_label = SubtitleLabel("系统设置")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))

        # 描述
        description_label = CaptionLabel("配置AI客服的基本参数和工作时间")
        description_label.setStyleSheet("color: #666;")

        # 左侧标题区域
        title_area = QWidget()
        title_layout = QVBoxLayout(title_area)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)
        title_layout.addWidget(title_label)
        title_layout.addWidget(description_label)

        # 按钮区域
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        # 夜间模式切换按钮
        self.theme_btn = PushButton("夜间模式")
        self.theme_btn.setIcon(FIF.CONSTRACT)
        self.theme_btn.setFixedSize(100, 40)
        self.theme_btn.clicked.connect(self.toggleTheme)

        # 重置按钮
        self.reset_btn = PushButton("重置")
        self.reset_btn.setIcon(FIF.UPDATE)
        self.reset_btn.setFixedSize(80, 40)

        # 保存按钮
        self.save_btn = PrimaryPushButton("保存")
        self.save_btn.setIcon(FIF.SAVE)
        self.save_btn.setFixedSize(100, 40)

        buttons_layout.addWidget(self.theme_btn)
        buttons_layout.addWidget(self.reset_btn)
        buttons_layout.addWidget(self.save_btn)

        # 添加到头部布局
        header_layout.addWidget(title_area)
        header_layout.addStretch()
        header_layout.addWidget(buttons_widget)

        return header_widget

    def createContentWidget(self):
        """创建内容区域"""
        # 滚动区域
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # 去除边框
        scroll_area.setStyleSheet("""
            ScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # 内容容器
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 模型选择卡片
        self.model_select_card = ModelSelectCard()
        self.model_select_card.model_changed.connect(self.onModelChanged)
        content_layout.addWidget(self.model_select_card)

        # 创建堆叠配置卡片
        self.stacked_config = QStackedWidget()
        self.coze_config_card = CozeConfigCard()
        self.kimi_config_card = KimiConfigCard()
        self.qwen_config_card = QwenConfigCard()

        self.stacked_config.addWidget(self.coze_config_card)
        self.stacked_config.addWidget(self.kimi_config_card)
        self.stacked_config.addWidget(self.qwen_config_card)

        content_layout.addWidget(self.stacked_config)

        # 业务时间卡片
        self.business_hours_card = BusinessHoursCard()
        content_layout.addWidget(self.business_hours_card)

        # AI 回复配置卡片
        self.ai_reply_config_card = AIReplyConfigCard()
        content_layout.addWidget(self.ai_reply_config_card)

        # 情绪告警配置卡片
        self.emotion_alert_card = EmotionAlertCard()
        content_layout.addWidget(self.emotion_alert_card)

        # AI 学习优化配置卡片
        self.ai_learning_card = AILearningConfigCard()
        content_layout.addWidget(self.ai_learning_card)

        # License 管理配置卡片
        self.license_card = LicenseConfigCard()
        content_layout.addWidget(self.license_card)

        content_layout.addStretch()

        # 设置容器样式
        content_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)

        scroll_area.setWidget(content_container)

        return scroll_area

    def onModelChanged(self, index: int):
        """模型选择改变时切换配置卡片"""
        self.stacked_config.setCurrentIndex(index)

    def toggleTheme(self):
        """切换夜间/日间模式"""
        from config import config
        from qfluentwidgets import isDarkTheme, setTheme, Theme
        # 切换主题
        if isDarkTheme():
            setTheme(Theme.LIGHT)
            self.theme_btn.setText("夜间模式")
            config.set("theme", "light", save=True)
        else:
            setTheme(Theme.DARK)
            self.theme_btn.setText("日间模式")
            config.set("theme", "dark", save=True)

    def loadConfig(self):
        """从config模块加载配置"""
        try:
            loaded_config = {
                # 模型选择
                "bot_type": config.get("bot_type", "coze"),

                # Coze 配置
                "coze_api_base": config.get("coze_api_base", "https://api.coze.cn"),
                "coze_token": config.get("coze_token", ""),
                "coze_bot_id": config.get("coze_bot_id", ""),

                # Kimi 配置
                "kimi_api_base": config.get("kimi_api_base", "https://api.moonshot.cn/v1"),
                "kimi_api_key": config.get("kimi_api_key", ""),
                "kimi_model": config.get("kimi_model", "moonshot-v1-8k"),

                # Qwen 配置
                "qwen_api_base": config.get("qwen_api_base", "https://dashscope.aliyuncs.com/api/v1"),
                "qwen_api_key": config.get("qwen_api_key", ""),
                "qwen_model": config.get("qwen_model", "qwen-turbo"),

                # 业务时间
                "businessHours": config.get("businessHours", {"start": "08:00", "end": "23:00"}),

                # AI 回复配置
                "ai_system_prompt": config.get("ai_system_prompt", "你是电商客服，回复要简短口语化，不超过20字"),
                "ai_reply_max_length": config.get("ai_reply_max_length", 20),
                "ai_reply_style": config.get("ai_reply_style", "casual"),
                "ai_reply_no_punctuation": config.get("ai_reply_no_punctuation", True),
                "ai_reply_delay_min": config.get("ai_reply_delay_min", 2),
                "ai_reply_delay_max": config.get("ai_reply_delay_max", 10),

                # 情绪告警配置
                "enable_telegram_alert": config.get("enable_telegram_alert", False),
                "emotion_alert_threshold": config.get("emotion_alert_threshold", -0.6),
                "emotion_alert_cooldown": config.get("emotion_alert_cooldown", 300),
                "telegram_bot_token": config.get("telegram_bot_token", ""),
                "telegram_chat_id": config.get("telegram_chat_id", "")
            }

            # 验证并设置配置
            self._validateAndSetConfig(loaded_config)
            self.logger.info("配置加载成功")

        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            QMessageBox.warning(self, "加载失败", f"加载配置失败：{str(e)}")
            self._loadDefaultConfig()

    def _loadDefaultConfig(self):
        """加载默认配置"""
        default_config = {
            "bot_type": "coze",
            "coze_api_base": "https://api.coze.cn",
            "coze_token": "",
            "coze_bot_id": "",
            "kimi_api_base": "https://api.moonshot.cn/v1",
            "kimi_api_key": "",
            "kimi_model": "moonshot-v1-8k",
            "qwen_api_base": "https://dashscope.aliyuncs.com/api/v1",
            "qwen_api_key": "",
            "qwen_model": "qwen-turbo",
            "businessHours": {
                "start": "08:00",
                "end": "23:00"
            },
            "ai_system_prompt": "你是电商客服，回复要简短口语化，不超过20字",
            "ai_reply_max_length": 20,
            "ai_reply_style": "casual",
            "ai_reply_no_punctuation": True,
            "ai_reply_delay_min": 2,
            "ai_reply_delay_max": 10,
            "enable_telegram_alert": False,
            "emotion_alert_threshold": -0.6,
            "emotion_alert_cooldown": 300,
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        }

        self.model_select_card.setConfig(default_config)
        self.coze_config_card.setConfig(default_config)
        self.kimi_config_card.setConfig(default_config)
        self.qwen_config_card.setConfig(default_config)
        self.business_hours_card.setConfig(default_config)
        self.ai_reply_config_card.setConfig(default_config)
        self.emotion_alert_card.setConfig(default_config)
        self.ai_learning_card.setConfig(default_config)
        self.logger.info("已加载默认配置")

    def _validateAndSetConfig(self, config_data):
        """验证并设置配置"""
        # 设置模型选择
        self.model_select_card.setConfig(config_data)

        # 设置各模型配置
        self.coze_config_card.setConfig(config_data)
        self.kimi_config_card.setConfig(config_data)
        self.qwen_config_card.setConfig(config_data)

        # 设置业务时间
        self.business_hours_card.setConfig(config_data)

        # 设置AI回复配置
        self.ai_reply_config_card.setConfig(config_data)

        # 设置情绪告警配置
        self.emotion_alert_card.setConfig(config_data)

        # 设置 AI 学习配置
        self.ai_learning_card.setConfig(config_data)

        # 根据当前选择的模型切换显示
        model_map = {"coze": 0, "kimi": 1, "qwen": 2}
        current_model = config_data.get("bot_type", "coze")
        self.stacked_config.setCurrentIndex(model_map.get(current_model, 0))

    def onSaveConfig(self):
        """保存配置到config模块"""
        try:
            # 获取所有配置
            model_config = self.model_select_card.getConfig()
            current_index = self.stacked_config.currentIndex()

            # 根据当前选择的模型获取对应配置
            if current_index == 0:  # Coze
                ai_config = self.coze_config_card.getConfig()
            elif current_index == 1:  # Kimi
                ai_config = self.kimi_config_card.getConfig()
            else:  # Qwen
                ai_config = self.qwen_config_card.getConfig()

            business_config = self.business_hours_card.getConfig()

            # 获取AI回复配置
            ai_reply_config = self.ai_reply_config_card.getConfig()

            # 获取情绪告警配置
            emotion_alert_config = self.emotion_alert_card.getConfig()

            # 获取 AI 学习配置
            ai_learning_config = self.ai_learning_card.getConfig()

            # 验证延迟设置
            if ai_reply_config["ai_reply_delay_min"] >= ai_reply_config["ai_reply_delay_max"]:
                QMessageBox.warning(self, "配置错误", "最小延迟必须小于最大延迟！")
                return

            # 合并配置
            new_config = {**model_config, **ai_config, **business_config, **ai_reply_config, **emotion_alert_config, **ai_learning_config}

            # 验证必填项（根据选择的模型）
            bot_type = model_config.get("bot_type", "coze")
            if bot_type == "coze":
                if not ai_config.get("coze_token"):
                    QMessageBox.warning(self, "配置错误", "请输入 Coze API Token！")
                    return
                if not ai_config.get("coze_bot_id"):
                    QMessageBox.warning(self, "配置错误", "请输入 Bot ID！")
                    return
            elif bot_type == "kimi":
                if not ai_config.get("kimi_api_key"):
                    QMessageBox.warning(self, "配置错误", "请输入 Kimi API Key！")
                    return
            elif bot_type == "qwen":
                if not ai_config.get("qwen_api_key"):
                    QMessageBox.warning(self, "配置错误", "请输入 Qwen API Key！")
                    return

            # 验证时间设置
            start_time = self.business_hours_card.start_time_picker.getTime()
            end_time = self.business_hours_card.end_time_picker.getTime()

            if start_time >= end_time:
                QMessageBox.warning(self, "时间设置错误", "开始时间必须早于结束时间！")
                return

            # 使用config模块保存配置
            config.update(new_config, save=True)

            self.logger.info("配置保存成功")

            # 显示成功消息
            InfoBar.success(
                title="保存成功",
                content=f"配置已保存！当前使用模型: {bot_type.upper()}",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self
            )

        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误：{str(e)}")

    def onResetConfig(self):
        """重置配置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有配置吗？\n这将重新加载配置文件中的原始设置。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 使用config模块重新加载配置文件
                config.reload()
                self.loadConfig()
                self.logger.info("配置已重置")

                InfoBar.success(
                    title="重置成功",
                    content="配置已重置为配置文件中的设置！",
                    orient=Qt.Orientation.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=2000,
                    parent=self
                )
            except Exception as e:
                self.logger.error(f"重置配置失败: {e}")
                QMessageBox.critical(self, "重置失败", f"重置配置失败：{str(e)}")


class AILearningConfigCard(CardWidget):
    """AI 学习优化配置卡片"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("AI 学习优化")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)

        # 启用自动学习
        self.enable_auto_learn_switch = SwitchButton()
        self.enable_auto_learn_switch.setChecked(True)
        form_layout.addRow("启用自动学习:", self.enable_auto_learn_switch)

        # 自动沉淀网络知识
        self.enable_web_sink_switch = SwitchButton()
        self.enable_web_sink_switch.setChecked(True)
        form_layout.addRow("自动沉淀网络知识:", self.enable_web_sink_switch)

        # 低置信度阈值
        self.low_confidence_spin = SpinBox()
        self.low_confidence_spin.setRange(1, 9)
        self.low_confidence_spin.setValue(6)
        self.low_confidence_spin.setPrefix("0.")
        self._update_confidence_suffix()
        self.low_confidence_spin.valueChanged.connect(self._update_confidence_suffix)
        form_layout.addRow("低置信度阈值:", self.low_confidence_spin)

        layout.addLayout(form_layout)

        # 说明文本
        description_label = CaptionLabel(
            "启用自动学习后，系统会根据人工修正、负反馈等信号自动优化 AI 回复质量。\n"
            "低置信度阈值：当 AI 回复置信度低于此值时，将触发优化流程。"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def _update_confidence_suffix(self, value=None):
        """更新置信度后缀显示"""
        actual_value = self.low_confidence_spin.value() / 10
        self.low_confidence_spin.setSuffix(f" (实际：{actual_value:.1f})")

    def getConfig(self) -> dict:
        """获取配置"""
        low_confidence = self.low_confidence_spin.value() / 10
        return {
            "enable_auto_learn": self.enable_auto_learn_switch.isChecked(),
            "enable_web_search_auto_sink": self.enable_web_sink_switch.isChecked(),
            "low_confidence_threshold": low_confidence
        }

    def setConfig(self, config_data: dict):
        """设置配置"""
        self.enable_auto_learn_switch.setChecked(
            config_data.get("enable_auto_learn", True)
        )
        self.enable_web_sink_switch.setChecked(
            config_data.get("enable_web_search_auto_sink",
                           config_data.get("web_search_auto_sink", True))
        )
        low_confidence = config_data.get("low_confidence_threshold", 0.6)
        self.low_confidence_spin.setValue(int(low_confidence * 10))


class LicenseConfigCard(CardWidget):
    """License 管理配置卡片"""

    def __init__(self, parent=None):
        self.license_manager = get_license_manager()
        super().__init__(parent)
        self.setupUI()
        self.refreshStatus()

    def setupUI(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 卡片标题
        title_label = StrongBodyLabel("软件授权管理")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 状态显示区域（使用 QWidget 而不是 CardWidget 避免嵌套问题）
        self.status_widget = QWidget()
        self.status_widget.setObjectName("statusWidget")
        self.status_widget.setStyleSheet("""
            #statusWidget {
                background-color: #f5f5f5;
                border-radius: 8px;
            }
        """)
        status_layout = QVBoxLayout(self.status_widget)
        status_layout.setContentsMargins(16, 12, 16, 12)

        # 状态标题
        self.status_title = BodyLabel("授权状态")
        self.status_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        status_layout.addWidget(self.status_title)

        # 状态详情
        self.status_detail = CaptionLabel("正在检查授权...")
        self.status_detail.setStyleSheet("color: #666;")
        self.status_detail.setWordWrap(True)
        status_layout.addWidget(self.status_detail)

        layout.addWidget(self.status_widget)

        # License 详情区域
        self.details_widget = QWidget()
        details_layout = QFormLayout(self.details_widget)
        details_layout.setSpacing(10)
        details_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        # License ID
        self.license_id_label = BodyLabel("-")
        details_layout.addRow("License ID:", self.license_id_label)

        # 客户名称
        self.customer_label = BodyLabel("-")
        details_layout.addRow("授权对象:", self.customer_label)

        # 到期日期
        self.expire_label = BodyLabel("-")
        details_layout.addRow("到期日期:", self.expire_label)

        # 账号限制
        self.max_accounts_label = BodyLabel("-")
        details_layout.addRow("账号限额:", self.max_accounts_label)

        # 功能列表
        self.features_label = BodyLabel("-")
        self.features_label.setWordWrap(True)
        details_layout.addRow("授权功能:", self.features_label)

        layout.addWidget(self.details_widget)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()

        # 导入按钮
        self.import_btn = PrimaryPushButton("导入 License")
        self.import_btn.setIcon(FIF.FOLDER_ADD)
        self.import_btn.setFixedWidth(140)
        self.import_btn.clicked.connect(self.onImportLicense)
        button_layout.addWidget(self.import_btn)

        # 刷新按钮
        self.refresh_btn = PushButton("刷新状态")
        self.refresh_btn.setIcon(FIF.SYNC)
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self.refreshStatus)
        button_layout.addWidget(self.refresh_btn)

        layout.addLayout(button_layout)
        
        # 添加弹性空间，使说明文本位于底部
        layout.addStretch()

        # 说明文本
        description_label = CaptionLabel(
            "请导入有效的 License 文件以激活软件。"
            "License 文件可通过联系管理员获取。导入后请重启软件使部分设置生效。"
        )
        description_label.setStyleSheet("color: #666; padding: 8px 0;")
        layout.addWidget(description_label)

    def refreshStatus(self):
        """刷新 License 状态显示"""
        try:
            # 重新加载 License
            self.license_manager.load_and_verify()

            is_valid = self.license_manager.is_valid()
            license_info = self.license_manager.get_license_info()

            if is_valid and license_info:
                # 有效状态 - 绿色背景
                self.status_widget.setStyleSheet("""
                    #statusWidget {
                        background-color: #f6ffed;
                        border: 1px solid #b7eb8f;
                        border-radius: 8px;
                    }
                """)
                self.status_title.setText("✅ 已授权")
                self.status_title.setStyleSheet("color: #52c41a; font-weight: bold;")

                # 计算剩余天数
                try:
                    expire_date = datetime.strptime(license_info.expire_date, "%Y-%m-%d")
                    days_left = (expire_date - datetime.now()).days + 1
                    if days_left < 0:
                        days_left = 0
                except (ValueError, TypeError):
                    days_left = 0

                self.status_detail.setText(
                    f"您的软件已授权，有效期至 {license_info.expire_date}，"
                    f"剩余 {days_left} 天。"
                )
                self.status_detail.setStyleSheet("color: #666;")

                # 显示详细信息
                self.license_id_label.setText(str(license_info.license_id) if license_info.license_id else "-")
                self.customer_label.setText(str(license_info.customer_name) if license_info.customer_name else "未知")
                self.expire_label.setText(f"{license_info.expire_date}（剩余 {days_left} 天）")
                self.max_accounts_label.setText(f"{license_info.max_accounts} 个")
                features_text = ", ".join(license_info.features) if license_info.features else "基础功能"
                self.features_label.setText(features_text)
                self.details_widget.setVisible(True)
            else:
                # 无效状态 - 红色背景
                self.status_widget.setStyleSheet("""
                    #statusWidget {
                        background-color: #fff2f0;
                        border: 1px solid #ffccc7;
                        border-radius: 8px;
                    }
                """)
                self.status_title.setText("❌ 未授权")
                self.status_title.setStyleSheet("color: #f5222d; font-weight: bold;")

                error_msg = self.license_manager.get_error_message()
                if error_msg:
                    self.status_detail.setText(
                        f"软件未授权或授权已失效。{error_msg}"
                    )
                else:
                    self.status_detail.setText("软件未授权，请导入有效的 License 文件。")
                self.status_detail.setStyleSheet("color: #666;")

                # 清空详细信息
                self.license_id_label.setText("-")
                self.customer_label.setText("-")
                self.expire_label.setText("-")
                self.max_accounts_label.setText("-")
                self.features_label.setText("-")
                self.details_widget.setVisible(True)
                
        except Exception as e:
            # 异常情况
            self.status_title.setText("⚠️ 检查失败")
            self.status_title.setStyleSheet("color: #faad14; font-weight: bold;")
            self.status_detail.setText(f"检查 License 状态时出错：{str(e)}")
            self.status_detail.setStyleSheet("color: #666;")

    def onImportLicense(self):
        """导入 License 文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 License 文件",
            "",
            "License 文件 (*.key *.lic *.json);;所有文件 (*.*)"
        )

        if not file_path:
            return

        # 导入 License
        success, message = self.license_manager.import_license(file_path)

        if success:
            InfoBar.success(
                title="导入成功",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            self.refreshStatus()
        else:
            InfoBar.error(
                title="导入失败",
                content=message,
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
