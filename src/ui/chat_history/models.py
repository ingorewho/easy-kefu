"""聊天历史模块 - 数据模型"""
from datetime import datetime, date
from typing import Optional, List
from enum import IntEnum
from pydantic import BaseModel, Field


class MessageStatus(IntEnum):
    """消息状态"""
    PENDING = 0      # 未回复
    REPLIED = 1      # 已回复
    TRANSFERRED = 2  # 转人工
    FAILED = 3       # 失败


class ChatMessageModel(BaseModel):
    """聊天消息模型"""
    id: int
    account_id: int
    shop_id: str
    from_uid: str
    nickname: str
    message_type: str
    user_content: Optional[str] = None
    ai_reply: Optional[str] = None
    conversation_id: Optional[str] = None
    created_at: datetime
    replied_at: Optional[datetime] = None
    status: MessageStatus = MessageStatus.PENDING

    class Config:
        from_attributes = True

    def get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            MessageStatus.PENDING: "未回复",
            MessageStatus.REPLIED: "已回复",
            MessageStatus.TRANSFERRED: "转人工",
            MessageStatus.FAILED: "失败"
        }
        return status_map.get(self.status, "未知")


class FilterParams(BaseModel):
    """筛选参数"""
    account_id: Optional[int] = None
    start_time: Optional[date] = None
    end_time: Optional[date] = None
    user_search: Optional[str] = None
    keyword: Optional[str] = None
    status: Optional[MessageStatus] = None
    page: int = 1
    page_size: int = 100


class QueryResult(BaseModel):
    """查询结果"""
    total: int
    messages: List[ChatMessageModel]
    page: int
    page_size: int
    total_pages: int


class ExportConfig(BaseModel):
    """导出配置"""
    format: str = "excel"
    filename: Optional[str] = None
    include_columns: List[str] = Field(default_factory=lambda: [
        "id", "created_at", "shop_id", "from_uid", "nickname",
        "message_type", "user_content", "ai_reply", "status"
    ])


class AccountInfo(BaseModel):
    """账号信息"""
    id: int
    username: str
    user_id: str
    shop_name: str
    channel_name: str
