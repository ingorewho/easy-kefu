"""消息列表组件"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QFont
from qfluentwidgets import CardWidget, StrongBodyLabel, CaptionLabel

from .models import ChatMessageModel, QueryResult


class MessageListWidget(CardWidget):
    """消息列表组件"""

    message_selected = pyqtSignal(ChatMessageModel)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_result: QueryResult = None
        self._setup_ui()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title = StrongBodyLabel("消息列表")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 状态标签
        self.status_label = CaptionLabel("共 0 条记录")
        self.status_label.setStyleSheet("color: #666;")
        layout.addWidget(self.status_label)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "时间", "用户", "类型", "内容预览", "AI回复预览", "状态"
        ])

        # 列宽设置
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(5, 60)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.table)

    def update_messages(self, result: QueryResult):
        """更新消息列表"""
        self._current_result = result
        messages = result.messages if result else []

        self.table.setRowCount(len(messages))

        for row, msg in enumerate(messages):
            # 时间
            time_str = msg.created_at.strftime('%m-%d %H:%M') if msg.created_at else ''
            self.table.setItem(row, 0, QTableWidgetItem(time_str))

            # 用户
            nickname = msg.nickname[:8] + "..." if len(msg.nickname) > 8 else msg.nickname
            user_item = QTableWidgetItem(nickname)
            user_item.setToolTip(msg.from_uid)
            self.table.setItem(row, 1, user_item)

            # 类型
            self.table.setItem(row, 2, QTableWidgetItem(msg.message_type))

            # 内容预览
            content = msg.user_content or ""
            content = content[:30] + "..." if len(content) > 30 else content
            content_item = QTableWidgetItem(content)
            content_item.setToolTip(msg.user_content or "")
            self.table.setItem(row, 3, content_item)

            # AI回复预览
            reply = msg.ai_reply or ""
            reply = reply[:30] + "..." if len(reply) > 30 else reply
            reply_item = QTableWidgetItem(reply)
            reply_item.setToolTip(msg.ai_reply or "")
            self.table.setItem(row, 4, reply_item)

            # 状态
            self.table.setItem(row, 5, QTableWidgetItem(msg.get_status_text()))

        self.status_label.setText(f"共 {len(messages)} 条记录 / 总计 {result.total if result else 0}")

    def _on_selection_changed(self):
        """选择改变时触发"""
        if not self._current_result:
            return

        selected = self.table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        if 0 <= row < len(self._current_result.messages):
            self.message_selected.emit(self._current_result.messages[row])
