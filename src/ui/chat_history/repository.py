"""聊天历史模块 - 数据访问层"""
from typing import Optional, List, Tuple
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models import ChatMessage, Account, Shop, Channel
from db.db_manager import DatabaseManager
from .models import ChatMessageModel, FilterParams, QueryResult, AccountInfo
from utils.logger import get_logger

logger = get_logger('ChatHistoryRepository')


class ChatHistoryRepository:
    """聊天历史数据仓库 - 统一数据库访问"""

    _instance = None
    _db_manager: Optional[DatabaseManager] = None

    def __new__(cls):
        """单例模式，确保只有一个 Repository 实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def db(self) -> DatabaseManager:
        """获取数据库管理器（延迟初始化）"""
        if self._db_manager is None:
            self._db_manager = DatabaseManager()
        return self._db_manager

    def query_messages(self, filters: FilterParams) -> QueryResult:
        """查询消息列表"""
        logger.info(f'查询消息: account_id={filters.account_id}, start={filters.start_time}, end={filters.end_time}')
        session = self.db.get_session()
        try:
            query = session.query(ChatMessage)

            # 应用筛选条件
            if filters.account_id is not None:
                query = query.filter(ChatMessage.account_id == filters.account_id)
            if filters.start_time:
                # 将 date 转换为 datetime 进行比较
                start_datetime = datetime.combine(filters.start_time, datetime.min.time())
                query = query.filter(ChatMessage.created_at >= start_datetime)
            if filters.end_time:
                # 将 date 转换为 datetime，并设置为当天的最后一刻
                end_datetime = datetime.combine(filters.end_time, datetime.max.time().replace(microsecond=0))
                query = query.filter(ChatMessage.created_at <= end_datetime)
            if filters.status is not None:
                query = query.filter(ChatMessage.status == filters.status)
            if filters.keyword:
                query = query.filter(
                    (ChatMessage.user_content.contains(filters.keyword)) |
                    (ChatMessage.ai_reply.contains(filters.keyword))
                )

            # 获取总数
            total = query.count()
            logger.info(f'查询结果: total={total}')

            # 分页
            offset = (filters.page - 1) * filters.page_size
            messages = query.order_by(ChatMessage.created_at.desc()) \
                          .offset(offset) \
                          .limit(filters.page_size) \
                          .all()

            # 转换为模型
            message_models = [ChatMessageModel.model_validate(m) for m in messages]

            total_pages = (total + filters.page_size - 1) // filters.page_size

            return QueryResult(
                total=total,
                messages=message_models,
                page=filters.page,
                page_size=filters.page_size,
                total_pages=total_pages
            )
        finally:
            session.close()

    def get_conversation_history(self, account_id: int, from_uid: str,
                                  limit: int = 100) -> List[ChatMessageModel]:
        """获取与特定用户的对话历史"""
        session = self.db.get_session()
        try:
            messages = session.query(ChatMessage) \
                .filter_by(account_id=account_id, from_uid=from_uid) \
                .order_by(ChatMessage.created_at.asc()) \
                .limit(limit) \
                .all()
            return [ChatMessageModel.model_validate(m) for m in messages]
        finally:
            session.close()

    def get_all_accounts(self) -> List[AccountInfo]:
        """获取所有账号列表"""
        session = self.db.get_session()
        try:
            accounts = session.query(Account, Shop, Channel) \
                .join(Shop, Account.shop_id == Shop.id) \
                .join(Channel, Shop.channel_id == Channel.id) \
                .all()

            logger.info(f'数据库查询到 {len(accounts)} 个账号')
            result = []
            for acc, shop, channel in accounts:
                logger.info(f'  账号: id={acc.id}, user_id={acc.user_id}, shop_id={shop.shop_id}, username={acc.username}')
                result.append(AccountInfo(
                    id=acc.id,
                    username=acc.username,
                    user_id=acc.user_id,
                    shop_name=shop.shop_name,
                    channel_name=channel.channel_name
                ))
            return result
        finally:
            session.close()
