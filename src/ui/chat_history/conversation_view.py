"""对话详情视图组件"""
from PyQt6.QtWidgets import QVBoxLayout, QTextEdit
from PyQt6.QtGui import QFont
from qfluentwidgets import CardWidget, StrongBodyLabel, CaptionLabel

from .service import ChatHistoryService
from .models import ChatMessageModel


class ConversationViewWidget(CardWidget):
    """对话详情视图"""

    def __init__(self, service: ChatHistoryService, parent=None):
        super().__init__(parent)
        self.service = service
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = StrongBodyLabel("对话详情")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 用户信息
        self.user_info_label = CaptionLabel("选择消息查看完整对话")
        self.user_info_label.setStyleSheet("color: #666;")
        layout.addWidget(self.user_info_label)

        # 对话内容
        self.conversation_text = QTextEdit()
        self.conversation_text.setReadOnly(True)
        layout.addWidget(self.conversation_text)

    def show_conversation(self, message: ChatMessageModel):
        """显示对话详情"""
        # 显示用户信息
        user_info = (
            f"用户: {message.nickname} ({message.from_uid})\n"
            f"时间: {message.created_at.strftime('%Y-%m-%d %H:%M:%S') if message.created_at else ''}\n"
            f"店铺: {message.shop_id}\n"
            f"类型: {message.message_type}"
        )
        self.user_info_label.setText(user_info)

        # 尝试获取完整对话历史
        messages = self.service.get_conversation(message.account_id, message.from_uid)

        if len(messages) <= 1:
            # 单条消息显示
            self._show_single_message(message)
        else:
            # 显示完整对话
            self._show_conversation_history(messages)

    def _show_single_message(self, message: ChatMessageModel):
        """显示单条消息"""
        html = f"""
        <style>
            .user-msg {{ background-color: #e3f2fd; padding: 10px; border-radius: 8px; margin: 5px 0; }}
            .ai-msg {{ background-color: #f5f5f5; padding: 10px; border-radius: 8px; margin: 5px 0; }}
            .label {{ color: #666; font-size: 12px; margin-bottom: 5px; }}
        </style>
        <div class="label">用户消息:</div>
        <div class="user-msg">{message.user_content or ''}</div>
        <br>
        <div class="label">AI 回复:</div>
        <div class="ai-msg">{message.ai_reply or '(暂无回复)'}</div>
        """
        self.conversation_text.setHtml(html)

    def _show_conversation_history(self, messages):
        """显示对话历史"""
        html_parts = ['<style>']
        html_parts.append('.user-msg { background-color: #95EC69; padding: 10px; border-radius: 8px; margin: 5px 0; max-width: 80%; }')
        html_parts.append('.ai-msg { background-color: #FFFFFF; border: 1px solid #E0E0E0; padding: 10px; border-radius: 8px; margin: 5px 0; max-width: 80%; }')
        html_parts.append('.time { color: #999; font-size: 11px; }')
        html_parts.append('.user-container { text-align: right; }')
        html_parts.append('.ai-container { text-align: left; }')
        html_parts.append('</style>')

        for msg in messages:
            time_str = msg.created_at.strftime('%H:%M') if msg.created_at else ''

            # 用户消息
            html_parts.append(f'<div class="user-container">')
            html_parts.append(f'<div class="user-msg">')
            html_parts.append(f'<div class="time">{time_str}</div>')
            html_parts.append(f'<div>{msg.user_content or ""}</div>')
            html_parts.append(f'</div></div>')

            # AI 回复
            if msg.ai_reply:
                html_parts.append(f'<div class="ai-container">')
                html_parts.append(f'<div class="ai-msg">')
                html_parts.append(f'<div class="time">AI</div>')
                html_parts.append(f'<div>{msg.ai_reply}</div>')
                html_parts.append(f'</div></div>')

        self.conversation_text.setHtml(''.join(html_parts))
