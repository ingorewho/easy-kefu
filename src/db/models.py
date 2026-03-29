from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Index, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Channel(Base):
    """渠道表，存储电商渠道基本信息"""
    __tablename__ = 'channels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_name = Column(String(50), unique=True, nullable=False, comment='渠道名称')
    description = Column(String(255), comment='渠道描述')

    # 关联关系 - 一个渠道可以有多个店铺
    shops = relationship('Shop', back_populates='channel', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Channel(channel_name='{self.channel_name}')>"


class Shop(Base):
    """店铺表，存储店铺基本信息"""
    __tablename__ = 'shops'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(Integer, ForeignKey('channels.id'), nullable=False)
    shop_id = Column(String(100), nullable=False, comment='店铺ID')
    shop_name = Column(String(100), nullable=False, comment='店铺名称')
    shop_logo = Column(String(255), nullable=True, comment='店铺logo')
    description = Column(String(255), comment='店铺描述')
    
    # 关联关系 - 多个店铺属于一个渠道，一个店铺可以有多个账号
    channel = relationship('Channel', back_populates='shops')
    accounts = relationship('Account', back_populates='shop', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Shop(shop_id='{self.shop_id}', shop_name='{self.shop_name}', channel='{self.channel.channel_name if self.channel else None}')>" 


class Account(Base):
    """账号表，存储店铺账号信息"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False)
    user_id = Column(String(100), nullable=False, comment='用户ID')
    username = Column(String(100), nullable=False, comment='登录用户名')
    password = Column(String(255), nullable=False, comment='登录密码')
    cookies = Column(Text, comment='存储登录cookies信息的JSON字符串')
    status = Column(Integer, default=None, comment='账号状态: None-未验证, 0-休息,1-在线, 3-离线')
    
    # 关联关系 - 多个账号属于一个店铺
    shop = relationship('Shop', back_populates='accounts')
    # 关联聊天消息
    chat_messages = relationship('ChatMessage', back_populates='account', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Account(username='{self.username}', password='{self.password}', shop='{self.shop.shop_name if self.shop else None}')>"

    
class Keyword(Base):
    """关键词表，存储关键词信息"""
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(100), nullable=False, comment='关键词')

    def __repr__(self):
        return f"<Keyword(keyword='{self.keyword}')>"


class ChatMessage(Base):
    """聊天消息表，存储历史消息记录"""
    __tablename__ = 'chat_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, index=True)
    shop_id = Column(String(50), nullable=False, index=True)

    # 用户标识
    from_uid = Column(String(100), nullable=False, index=True)
    nickname = Column(String(100), comment='用户昵称')

    # 消息内容
    message_type = Column(String(50), nullable=False, comment='消息类型: TEXT/IMAGE/GOODS_INQUIRY/ORDER_INFO等')
    user_content = Column(Text, comment='用户消息内容')
    ai_reply = Column(Text, comment='AI 回复内容')

    # 会话信息
    conversation_id = Column(String(100), comment='会话ID')

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)
    replied_at = Column(DateTime, comment='AI回复时间')

    # 状态: 0-未回复, 1-已回复, 2-转人工, 3-失败
    status = Column(Integer, default=0, comment='消息状态')

    # === AI 学习优化相关字段 ===
    # 人工修正内容
    human_edited_reply = Column(Text, comment='人工修改后的回复内容')
    edit_diff = Column(Text, comment='AI 回复与人工回复的差异记录 JSON')

    # 优化标记
    is_optimization_sample = Column(Integer, default=0, comment='是否作为优化样本：0-否，1-是')
    optimization_type = Column(String(50), comment='优化类型：human_edit/negative_feedback/high_score')

    # 置信度与质量
    ai_confidence = Column(Float, comment='AI 回复置信度 0-1')
    quality_score = Column(Float, comment='回复质量评分 -1.0~1.0')

    # 关联账号 (不使用 backref 避免循环引用问题)
    account = relationship("Account", back_populates="chat_messages")

    def __repr__(self):
        return f"<ChatMessage(from_uid='{self.from_uid}', type='{self.message_type}', status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'shop_id': self.shop_id,
            'from_uid': self.from_uid,
            'nickname': self.nickname,
            'message_type': self.message_type,
            'user_content': self.user_content,
            'ai_reply': self.ai_reply,
            'conversation_id': self.conversation_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'replied_at': self.replied_at.strftime('%Y-%m-%d %H:%M:%S') if self.replied_at else None,
            'status': self.status,
            # AI 学习相关字段
            'human_edited_reply': self.human_edited_reply,
            'edit_diff': self.edit_diff,
            'is_optimization_sample': self.is_optimization_sample,
            'optimization_type': self.optimization_type,
            'ai_confidence': self.ai_confidence,
            'quality_score': self.quality_score
        }


class FeedbackStats(Base):
    """AI 回复效果统计表"""
    __tablename__ = 'ai_feedback_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, index=True)
    from_uid = Column(String(100), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey('chat_messages.id'), unique=True)

    # 评价维度
    satisfaction_score = Column(Integer, comment='满意度 1-5 星')
    is_resolved = Column(Integer, comment='问题是否解决：0-否，1-是')
    is_transferred = Column(Integer, comment='是否转人工：0-否，1-是')

    # 自动评估
    response_time_sec = Column(Float, comment='AI 响应时间（秒）')
    conversation_turns = Column(Integer, comment='会话轮数')
    has_followup = Column(Integer, comment='是否有追问：0-否，1-是')

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True)

    def __repr__(self):
        return f"<FeedbackStats(message_id={self.message_id}, satisfaction={self.satisfaction_score})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'from_uid': self.from_uid,
            'message_id': self.message_id,
            'satisfaction_score': self.satisfaction_score,
            'is_resolved': self.is_resolved,
            'is_transferred': self.is_transferred,
            'response_time_sec': self.response_time_sec,
            'conversation_turns': self.conversation_turns,
            'has_followup': self.has_followup,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class SimilarCase(Base):
    """相似案例库 - 存储人工修正后的高质量回复"""
    __tablename__ = 'ai_similar_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)

    # 案例内容
    user_question = Column(Text, nullable=False, comment='用户问题')
    ai_original_reply = Column(Text, comment='AI 原始回复')
    human_optimized_reply = Column(Text, nullable=False, comment='人工优化回复')

    # 向量化
    question_embedding = Column(Text, comment='问题向量 JSON')

    # 质量指标
    usage_count = Column(Integer, default=0, comment='被引用次数')
    avg_effectiveness = Column(Float, comment='平均有效性评分')

    # 分类
    category = Column(String(50), index=True, comment='问题分类')
    tags = Column(String(500), comment='标签，逗号分隔')

    # 状态
    status = Column(Integer, default=0, comment='0-待审核，1-已启用，2-已禁用')
    reviewed_by = Column(String(100), comment='审核人')

    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<SimilarCase(id={self.id}, category='{self.category}', status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'user_question': self.user_question,
            'ai_original_reply': self.ai_original_reply,
            'human_optimized_reply': self.human_optimized_reply,
            'question_embedding': self.question_embedding,
            'usage_count': self.usage_count,
            'avg_effectiveness': self.avg_effectiveness,
            'category': self.category,
            'tags': self.tags,
            'status': self.status,
            'reviewed_by': self.reviewed_by,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None
        }


class AlertLog(Base):
    """告警日志表，存储情绪告警等告警记录"""
    __tablename__ = 'alert_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 告警类型
    alert_type = Column(String(50), nullable=False, comment='告警类型：emotion/keywor d/system')

    # 情绪相关信息
    emotion_score = Column(Float, comment='情绪分数 (-1.0 ~ 1.0)')
    emotion_level = Column(String(20), comment='情绪等级：positive/neutral/negative/very_negative')
    emotion_keywords = Column(String(500), comment='情绪关键词，逗号分隔')

    # 用户和消息信息
    user_message = Column(Text, comment='用户消息内容')
    from_uid = Column(String(100), index=True, comment='用户 ID')
    nickname = Column(String(100), comment='用户昵称')
    shop_id = Column(String(50), index=True, comment='店铺 ID')
    account_id = Column(Integer, comment='账号 ID')

    # 通知状态
    notified = Column(Integer, default=0, comment='是否已通知：0-未通知，1-已通知')
    notified_at = Column(DateTime, comment='通知时间')
    telegram_message_id = Column(String(100), comment='Telegram 消息 ID')

    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment='告警创建时间')

    def __repr__(self):
        return f"<AlertLog(type='{self.alert_type}', score={self.emotion_score}, from_uid='{self.from_uid}')>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'alert_type': self.alert_type,
            'emotion_score': self.emotion_score,
            'emotion_level': self.emotion_level,
            'emotion_keywords': self.emotion_keywords,
            'user_message': self.user_message,
            'from_uid': self.from_uid,
            'nickname': self.nickname,
            'shop_id': self.shop_id,
            'account_id': self.account_id,
            'notified': self.notified,
            'notified_at': self.notified_at.strftime('%Y-%m-%d %H:%M:%S') if self.notified_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }


class LicenseRecord(Base):
    """License 记录表，存储 License 导入和使用历史"""
    __tablename__ = 'license_records'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # License 信息
    license_id = Column(String(100), nullable=False, index=True, comment='License ID')
    customer_name = Column(String(200), comment='客户名称')
    expire_date = Column(String(20), nullable=False, comment='到期日期 YYYY-MM-DD')
    max_accounts = Column(Integer, default=1, comment='最大账号数')
    features = Column(String(500), comment='功能列表，JSON 格式')

    # 导入信息
    imported_at = Column(DateTime, default=datetime.now, comment='导入时间')
    imported_by = Column(String(100), comment='导入用户/来源')

    # 状态
    status = Column(Integer, default=1, comment='状态：0-无效，1-有效，2-已过期')
    activated_at = Column(DateTime, comment='激活时间')

    # License 文件签名（用于验证）
    signature = Column(String(500), comment='签名')

    def __repr__(self):
        return f"<LicenseRecord(id='{self.license_id}', expire='{self.expire_date}', status={self.status})>"

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'id': self.id,
            'license_id': self.license_id,
            'customer_name': self.customer_name,
            'expire_date': self.expire_date,
            'max_accounts': self.max_accounts,
            'features': self.features,
            'imported_at': self.imported_at.strftime('%Y-%m-%d %H:%M:%S') if self.imported_at else None,
            'imported_by': self.imported_by,
            'status': self.status,
            'activated_at': self.activated_at.strftime('%Y-%m-%d %H:%M:%S') if self.activated_at else None,
            'signature': self.signature
        }