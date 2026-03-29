"""聊天历史模块 - 业务服务层"""
import pandas as pd
from datetime import datetime
from typing import Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from .repository import ChatHistoryRepository
from .models import (
    ChatMessageModel, FilterParams, QueryResult,
    ExportConfig, AccountInfo
)


class ChatHistoryService(QObject):
    """聊天历史业务服务"""

    # 信号定义
    query_completed = pyqtSignal(QueryResult)
    query_error = pyqtSignal(str)
    export_completed = pyqtSignal(str)
    export_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._repository = ChatHistoryRepository()

    def query_messages(self, filters: FilterParams) -> QueryResult:
        """同步查询消息"""
        return self._repository.query_messages(filters)

    def get_accounts(self) -> List[AccountInfo]:
        """获取账号列表"""
        return self._repository.get_all_accounts()

    def get_conversation(self, account_id: int, from_uid: str) -> List[ChatMessageModel]:
        """获取对话历史"""
        return self._repository.get_conversation_history(account_id, from_uid)

    def export_to_excel(self, filters: FilterParams, config: ExportConfig) -> str:
        """导出到 Excel"""
        # 查询所有数据（不分页）
        from copy import copy
        export_filters = copy(filters)
        export_filters.page = 1
        export_filters.page_size = 10000

        result = self._repository.query_messages(export_filters)

        # 转换为 DataFrame
        data = []
        for msg in result.messages:
            row = msg.model_dump(include=set(config.include_columns))
            row['status'] = msg.get_status_text()
            data.append(row)

        df = pd.DataFrame(data)

        # 生成文件名
        if not config.filename:
            config.filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        # 导出
        df.to_excel(config.filename, index=False, engine='openpyxl')
        return config.filename


class AsyncQueryWorker(QThread):
    """异步查询工作线程"""

    completed = pyqtSignal(QueryResult)
    error = pyqtSignal(str)

    def __init__(self, service: ChatHistoryService, filters: FilterParams):
        super().__init__()
        self.service = service
        self.filters = filters

    def run(self):
        """执行查询"""
        try:
            result = self.service.query_messages(self.filters)
            self.completed.emit(result)
        except Exception as e:
            self.error.emit(str(e))
