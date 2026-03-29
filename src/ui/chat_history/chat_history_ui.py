"""聊天历史查看界面 - 重构版"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout
from qfluentwidgets import InfoBar, InfoBarPosition

from .filter_panel import FilterPanel
from .message_list import MessageListWidget
from .conversation_view import ConversationViewWidget
from .service import ChatHistoryService
from .models import FilterParams, ExportConfig
from utils.logger import get_logger


class ChatHistoryUI(QFrame):
    """聊天历史查看界面 - 重构版"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('ChatHistoryUI')
        self.service = ChatHistoryService()
        self._setup_ui()
        self._connect_signals()
        self.setObjectName("聊天历史")

    def _setup_ui(self):
        """设置界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 筛选面板
        self.filter_panel = FilterPanel(self.service)
        layout.addWidget(self.filter_panel, 0)

        # 消息列表
        self.message_list = MessageListWidget()
        layout.addWidget(self.message_list, 1)

        # 对话详情
        self.conversation_view = ConversationViewWidget(self.service)
        layout.addWidget(self.conversation_view, 1)

    def _connect_signals(self):
        """连接信号"""
        self.filter_panel.query_requested.connect(self._on_query)
        self.filter_panel.export_requested.connect(self._on_export)
        self.message_list.message_selected.connect(self._on_message_selected)

    def _on_query(self, filters: FilterParams):
        """执行查询"""
        try:
            self.logger.info(f"开始查询: account_id={filters.account_id}, start={filters.start_time}, end={filters.end_time}")
            result = self.service.query_messages(filters)
            self.logger.info(f"查询完成: total={result.total}, messages={len(result.messages)}")
            self.message_list.update_messages(result)
        except Exception as e:
            self.logger.error(f"查询失败: {e}", exc_info=True)
            InfoBar.error(
                title="查询失败",
                content=str(e),
                parent=self
            )

    def _on_export(self, filters: FilterParams):
        """执行导出"""
        try:
            config = ExportConfig()
            filename = self.service.export_to_excel(filters, config)
            InfoBar.success(
                title="导出成功",
                content=f"已保存到: {filename}",
                parent=self
            )
        except Exception as e:
            InfoBar.error(
                title="导出失败",
                content=str(e),
                parent=self
            )

    def _on_message_selected(self, message):
        """消息被选中"""
        self.conversation_view.show_conversation(message)
