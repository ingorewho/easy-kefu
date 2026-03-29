import os
import json
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Dict, Any, Optional, Union
from utils.logger import get_logger
from utils.resource_manager import ThreadResourceManager
from db.models import Base, Channel, Shop, Account, Keyword, ChatMessage, AlertLog, FeedbackStats, SimilarCase
from datetime import datetime, timedelta

class DatabaseManager:
    """数据库管理类，提供数据库操作的封装 - 优化版本支持连接池"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = 'database/channel_shop.db', pool_size: int = 10, max_overflow: int = 20):
        """初始化数据库连接 - 优化版本支持连接池

        Args:
            db_path: 数据库文件路径
            pool_size: 连接池大小
            max_overflow: 连接池溢出大小
        """
        if self._initialized:
            return

        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 创建数据库引擎 - 配置连接池
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,  # 连接健康检查
            pool_recycle=3600,   # 连接回收时间（秒）
            echo=False  # 生产环境关闭SQL日志
        )

        # 使用scoped_session确保线程安全
        self.Session = scoped_session(sessionmaker(bind=self.engine))

        # 先初始化logger以便记录后续错误
        self.logger = get_logger()

        # 创建表结构
        try:
            Base.metadata.create_all(self.engine)
            self.logger.debug("数据库表结构已创建/更新")
        except Exception as e:
            self.logger.error(f"创建数据库表结构失败: {e}")
            raise

        # 数据库迁移：添加缺失的列
        self._migrate_database()

        self._initialized = True

        # 资源管理
        self.resource_manager = ThreadResourceManager()
        self.resource_manager.register_thread_pool(
            self.engine.pool,
            f"数据库连接池(size={pool_size}, overflow={max_overflow})"
        )

        # 初始化数据库
        self.init_db()

        self.logger.info(f"数据库连接池已初始化: pool_size={pool_size}, max_overflow={max_overflow}")

    def __del__(self):
        """析构函数，确保连接池被正确关闭"""
        try:
            if hasattr(self, 'Session'):
                self.Session.remove()
            if hasattr(self, 'resource_manager'):
                asyncio.create_task(self.resource_manager.cleanup_all())
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"清理数据库资源失败: {e}")

    def _migrate_database(self):
        """数据库迁移：添加缺失的列"""
        from sqlalchemy import text
        try:
            with self.engine.connect() as conn:
                # 检查 chat_messages 表的列
                result = conn.execute(text("PRAGMA table_info(chat_messages)"))
                existing_columns = {row[1] for row in result}
                
                # 需要添加的列（字段名, SQL类型, 默认值）
                columns_to_add = [
                    ('human_edited_reply', 'TEXT', None),
                    ('edit_diff', 'TEXT', None),
                    ('is_optimization_sample', 'INTEGER', '0'),
                    ('optimization_type', 'VARCHAR(50)', None),
                    ('ai_confidence', 'FLOAT', None),
                    ('quality_score', 'FLOAT', None),
                ]
                
                for col_name, col_type, default in columns_to_add:
                    if col_name not in existing_columns:
                        sql = f"ALTER TABLE chat_messages ADD COLUMN {col_name} {col_type}"
                        if default is not None:
                            sql += f" DEFAULT {default}"
                        conn.execute(text(sql))
                        self.logger.info(f"数据库迁移：添加列 {col_name}")
                
                # 检查 ai_feedback_stats 表
                result = conn.execute(text("PRAGMA table_info(ai_feedback_stats)"))
                existing_columns = {row[1] for row in result}
                
                feedback_columns = [
                    ('satisfaction_score', 'INTEGER', None),
                    ('is_resolved', 'INTEGER', None),
                    ('is_transferred', 'INTEGER', None),
                    ('response_time_sec', 'FLOAT', None),
                    ('conversation_turns', 'INTEGER', None),
                    ('has_followup', 'INTEGER', None),
                ]
                
                for col_name, col_type, default in feedback_columns:
                    if col_name not in existing_columns:
                        sql = f"ALTER TABLE ai_feedback_stats ADD COLUMN {col_name} {col_type}"
                        if default is not None:
                            sql += f" DEFAULT {default}"
                        conn.execute(text(sql))
                        self.logger.info(f"数据库迁移：添加列 {col_name}")
                
                # 检查 ai_similar_cases 表
                result = conn.execute(text("PRAGMA table_info(ai_similar_cases)"))
                existing_columns = {row[1] for row in result}
                
                case_columns = [
                    ('question_embedding', 'TEXT', None),
                    ('usage_count', 'INTEGER', '0'),
                    ('avg_effectiveness', 'FLOAT', None),
                    ('category', 'VARCHAR(50)', None),
                    ('tags', 'VARCHAR(500)', None),
                    ('status', 'INTEGER', '0'),
                    ('reviewed_by', 'VARCHAR(100)', None),
                ]
                
                for col_name, col_type, default in case_columns:
                    if col_name not in existing_columns:
                        sql = f"ALTER TABLE ai_similar_cases ADD COLUMN {col_name} {col_type}"
                        if default is not None:
                            sql += f" DEFAULT {default}"
                        conn.execute(text(sql))
                        self.logger.info(f"数据库迁移：添加列 {col_name}")
                
                conn.commit()
                self.logger.debug("数据库迁移完成")
        except Exception as e:
            self.logger.error(f"数据库迁移失败: {e}")
            # 迁移失败不阻止应用启动

    def init_db(self):
        """初始化渠道信息"""
        channel_name = "pinduoduo"
        description = "拼多多"
        self.add_channel(channel_name, description)


    def get_session(self):
        """获取数据库会话 - 线程安全版本"""
        return self.Session()

    def get_connection_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        if hasattr(self.engine.pool, 'status'):
            return {
                'pool_size': self.engine.pool.size(),
                'checked_in': self.engine.pool.checkedin(),
                'checked_out': self.engine.pool.checkedout(),
                'overflow': self.engine.pool.overflow(),
                'invalid': self.engine.pool.invalid()
            }
        return {}

    async def close_all_connections(self):
        """关闭所有数据库连接"""
        try:
            self.Session.remove()
            self.engine.dispose()
            self.logger.info("所有数据库连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭数据库连接失败: {e}")
    
    # 渠道相关操作
    def add_channel(self, channel_name: str, description: str = None) -> bool:
        """添加渠道
        
        Args:
            channel_name: 渠道名称
            description: 渠道描述
            
        Returns:
            bool: 是否添加成功
        """
        session = self.get_session()
        try:
            # 检查渠道是否已存在
            existing = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if existing:
                return True
                
            # 创建新渠道
            channel = Channel(channel_name=channel_name, description=description)
            session.add(channel)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加渠道失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_channel(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """获取渠道信息
        
        Args:
            channel_name: 渠道名称
            
        Returns:
            Optional[Dict]: 渠道信息或None
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return None
                
            return {
                'id': channel.id,
                'channel_name': channel.channel_name,
                'description': channel.description
            }
        except SQLAlchemyError as e:
            self.logger.error(f"获取渠道失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_all_channels(self) -> List[Dict[str, Any]]:
        """获取所有渠道
        
        Returns:
            List[Dict]: 渠道列表
        """
        session = self.get_session()
        try:
            channels = session.query(Channel).all()
            return [
                {
                    'id': channel.id,
                    'channel_name': channel.channel_name,
                    'description': channel.description
                }
                for channel in channels
            ]
        except SQLAlchemyError as e:
            self.logger.error(f"获取渠道列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def delete_channel(self, channel_name: str) -> bool:
        """删除渠道
        
        Args:
            channel_name: 渠道名称
            
        Returns:
            bool: 是否删除成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                self.logger.warning(f"渠道 {channel_name} 不存在")
                return False
                
            session.delete(channel)
            session.commit()
            self.logger.info(f"成功删除渠道: {channel_name}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"删除渠道失败: {str(e)}")
            return False
        finally:
            session.close()
    
    # 店铺相关操作
    def add_shop(self, channel_name: str, shop_id: str, shop_name: str, shop_logo: str, description: str = None) -> bool:
        """添加店铺
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            shop_name: 店铺名称
            shop_logo: 店铺logo
            description: 店铺描述
            
        Returns:
            bool: 是否添加成功
        """
        session = self.get_session()
        try:
            # 获取对应渠道
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                self.logger.error(f"添加店铺失败: 渠道 {channel_name} 不存在")
                return False
            
            # 检查店铺是否已存在
            existing = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if existing:
                self.logger.warning(f"店铺 {shop_id} 已存在于渠道 {channel_name}")
                return False
            
            # 创建新店铺
            shop = Shop(
                channel_id=channel.id,
                shop_id=shop_id,
                shop_name=shop_name,
                shop_logo=shop_logo,
                description=description
            )
            
            session.add(shop)
            session.commit()
            self.logger.info(f"成功添加店铺: {shop_name}({shop_id}) 到渠道 {channel_name}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加店铺失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_shop(self, channel_name: str, shop_id: str) -> Optional[Dict[str, Any]]:
        """获取店铺信息
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            
        Returns:
            Optional[Dict]: 店铺信息或None
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return None
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return None
                
            return {
                'id': shop.id,
                'channel_id': shop.channel_id,
                'channel_name': channel_name,
                'shop_id': shop.shop_id,
                'shop_name': shop.shop_name,
                'shop_logo': shop.shop_logo,
                'description': shop.description,
            }
        except SQLAlchemyError as e:
            self.logger.error(f"获取店铺失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_shops_by_channel(self, channel_name: str) -> List[Dict[str, Any]]:
        """获取指定渠道下的所有店铺
        
        Args:
            channel_name: 渠道名称
            
        Returns:
            List[Dict]: 店铺列表
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return []
                
            shops = session.query(Shop).filter(Shop.channel_id == channel.id).all()
            return [
                {
                    'id': shop.id,
                    'channel_id': shop.channel_id,
                    'channel_name': channel_name,
                    'shop_id': shop.shop_id,
                    'shop_name': shop.shop_name,
                    'shop_logo': shop.shop_logo,
                    'description': shop.description
                }
                for shop in shops
            ]
        except SQLAlchemyError as e:
            self.logger.error(f"获取店铺列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_shop_info(self, channel_name: str, shop_id: str, shop_name: str = None, shop_logo: str = None, description: str = None) -> bool:
        """更新店铺信息
        
        Args:
            channel_name: 渠道名称
            shop_id: 新的店铺ID
            shop_name: 新的店铺名称
            shop_logo: 新的店铺logo
            description: 新的店铺描述
            
        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return False
            
            if shop_id is not None:
                shop.shop_id = shop_id
            if shop_name is not None:
                shop.shop_name = shop_name
            if shop_logo is not None:
                shop.shop_logo = shop_logo
            if description is not None:
                shop.description = description
                
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新店铺信息失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def delete_shop(self, channel_name: str, shop_id: str) -> bool:
        """删除店铺
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
        Returns:
            bool: 是否删除成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return False
                
            session.delete(shop)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"删除店铺失败: {str(e)}")
            return False
        finally:
            session.close()

    # 账号相关操作
    def add_account(self, channel_name: str, shop_id: str, user_id: str, username: str, password: str, cookies: str = None) -> bool:
        """添加账号
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            user_id: 用户ID
            username: 登录用户名
            password: 登录密码
            cookies: cookies JSON字符串
            
        Returns:
            bool: 是否添加成功
        """
        session = self.get_session()
        try:
            # 获取对应店铺
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                self.logger.error(f"添加账号失败: 渠道 {channel_name} 不存在")
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                self.logger.error(f"添加账号失败: 店铺 {shop_id} 不存在")
                return False
            
            # 检查账号是否已存在
            existing = session.query(Account).filter(
                Account.shop_id == shop.id,
                Account.username == username
            ).first()
            
            if existing:
                self.logger.warning(f"账号 {username} 已存在于店铺 {shop_id}")
                return False
            
            # 创建新账号
            account = Account(
                shop_id=shop.id,
                user_id=user_id,
                username=username,
                password=password,
                cookies=cookies,
                status=None
            )
            
            session.add(account)
            session.commit()
            self.logger.info(f"成功添加账号: {username} 到店铺 {shop_id}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加账号失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_account(self, channel_name: str, shop_id: str,user_id: str) -> Optional[Dict[str, Any]]:
        """获取账号信息
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            user_id: 用户ID
        Returns:
            Optional[Dict]: 账号信息或None
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                self.logger.warning(f"未找到渠道: {channel_name}")
                return None
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                self.logger.warning(f"未找到店铺: {shop_id} (渠道: {channel_name})")
                return None
                
            account = session.query(Account).filter(
                Account.shop_id == shop.id,
                Account.user_id == user_id
            ).first()
            
            if not account:
                self.logger.warning(f"未找到账户: {user_id} (店铺 ID: {shop_id})")
                return None
                
            return {
                'id': account.id,
                'shop_id': account.shop_id,
                'user_id': account.user_id,
                'username': account.username,
                'password': account.password,
                'cookies': account.cookies,
                'status': account.status
            }
        except SQLAlchemyError as e:
            self.logger.error(f"获取账号失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def update_account_info(self, channel_name: str, shop_id: str, user_id: str, username: Optional[str] = None, password: Optional[str] = None, cookies: Optional[str] = None, status: Optional[int] = None) -> bool:
        """更新账号信息
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            user_id: 用户ID
            username: 登录用户名
            password: 登录密码
            cookies: cookies JSON字符串
            status: 账号状态
        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                self.logger.error(f"更新账号失败: 渠道 {channel_name} 不存在")
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                self.logger.error(f"更新账号失败: 店铺 {shop_id} 不存在于渠道 {channel_name}")
                return False
                
            account = session.query(Account).filter(
                Account.shop_id == shop.id,
                Account.user_id == user_id
            ).first()
            
            if not account:
                self.logger.error(f"更新账号失败: 账号 {user_id} 不存在于店铺 {shop_id}")
                return False
                
            # 更新账号信息
            if username is not None:
                account.username = username
            if password is not None:
                account.password = password
            if cookies is not None:
                account.cookies = cookies
            if status is not None:
                account.status = status

            session.commit()
            self.logger.info(f"成功更新账号信息: {username} (用户ID: {user_id})")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新账号信息失败: {str(e)}")
            return False
        finally:
            session.close()
                

    def get_accounts_by_shop(self, channel_name: str, shop_id: str) -> List[Dict[str, Any]]:
        """获取指定店铺下的所有账号
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            
        Returns:
            List[Dict]: 账号列表
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return []
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return []
                
            accounts = session.query(Account).filter(Account.shop_id == shop.id).all()
            return [
                {
                    'id': account.id,
                    'shop_id': account.shop_id,
                    'user_id': account.user_id,
                    'username': account.username,
                    'password': account.password,
                    'cookies': account.cookies,
                    'status': account.status
                }
                for account in accounts
            ]
        except SQLAlchemyError as e:
            self.logger.error(f"获取账号列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_account_status(self, channel_name: str, shop_id: str, user_id: str, status: int) -> bool:
        """更新账号状态
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            user_id: 用户ID
            status: 状态值 (0-未验证, 1-正常, 2-异常)
            
        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return False
                
            account = session.query(Account).filter(
                Account.shop_id == shop.id,
                Account.user_id == user_id
            ).first()
            
            if not account:
                return False
                
            account.status = status
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新账号状态失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def update_account_cookies(self, channel_name: str, shop_id: str, user_id: str, cookies: str) -> bool:
        """更新账号cookies
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            user_id: 用户ID
            cookies: cookies JSON字符串
            
        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return False
                
            account = session.query(Account).filter(
                Account.shop_id == shop.id,
                Account.user_id == user_id
            ).first()
            
            if not account:
                return False
                
            account.cookies = cookies
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新账号cookies失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def delete_account(self, channel_name: str, shop_id: str, user_id: str) -> bool:
        """删除账号
        
        Args:
            channel_name: 渠道名称
            shop_id: 店铺ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        session = self.get_session()
        try:
            channel = session.query(Channel).filter(Channel.channel_name == channel_name).first()
            if not channel:
                return False
                
            shop = session.query(Shop).filter(
                Shop.channel_id == channel.id,
                Shop.shop_id == shop_id
            ).first()
            
            if not shop:
                return False
                
            account = session.query(Account).filter(
                Account.shop_id == shop.id,
                Account.user_id == user_id
            ).first()
            
            if not account:
                return False
                
            session.delete(account)
            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"删除账号失败: {str(e)}")
            return False
        finally:
            session.close()

    # 关键词相关操作
    def add_keyword(self, keyword: str) -> bool:
        """添加关键词
        
        Args:
            keyword: 关键词
            
        Returns:
            bool: 是否添加成功
        """
        session = self.get_session()
        try:
            # 检查关键词是否已存在
            existing = session.query(Keyword).filter(Keyword.keyword == keyword).first()
            if existing:
                self.logger.warning(f"关键词 {keyword} 已存在")
                return False
                
            # 创建新关键词
            keyword_obj = Keyword(keyword=keyword)
            session.add(keyword_obj)
            session.commit()
            self.logger.info(f"成功添加关键词: {keyword}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加关键词失败: {str(e)}")
            return False
        finally:
            session.close()
    
    def get_keyword(self, keyword: str) -> Optional[Dict[str, Any]]:
        """获取关键词信息
        
        Args:
            keyword: 关键词
            
        Returns:
            Optional[Dict]: 关键词信息或None
        """
        session = self.get_session()
        try:
            keyword_obj = session.query(Keyword).filter(Keyword.keyword == keyword).first()
            if not keyword_obj:
                return None
                
            return {
                'id': keyword_obj.id,
                'keyword': keyword_obj.keyword
            }
        except SQLAlchemyError as e:
            self.logger.error(f"获取关键词失败: {str(e)}")
            return None
        finally:
            session.close()
    
    def get_all_keywords(self) -> List[Dict[str, Any]]:
        """获取所有关键词
        
        Returns:
            List[Dict]: 关键词列表
        """
        session = self.get_session()
        try:
            keywords = session.query(Keyword).all()
            return [
                {
                    'id': keyword.id,
                    'keyword': keyword.keyword
                }
                for keyword in keywords
            ]
        except SQLAlchemyError as e:
            self.logger.error(f"获取关键词列表失败: {str(e)}")
            return []
        finally:
            session.close()
    
    def update_keyword(self, old_keyword: str, new_keyword: str) -> bool:
        """更新关键词
        
        Args:
            old_keyword: 原关键词
            new_keyword: 新关键词
            
        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            # 检查原关键词是否存在
            keyword_obj = session.query(Keyword).filter(Keyword.keyword == old_keyword).first()
            if not keyword_obj:
                self.logger.warning(f"关键词 {old_keyword} 不存在")
                return False
            
            # 检查新关键词是否已存在（如果不是同一个关键词）
            if old_keyword != new_keyword:
                existing = session.query(Keyword).filter(Keyword.keyword == new_keyword).first()
                if existing:
                    self.logger.warning(f"关键词 {new_keyword} 已存在")
                    return False
                    
            # 更新关键词
            keyword_obj.keyword = new_keyword
            session.commit()
            self.logger.info(f"成功更新关键词: {old_keyword} -> {new_keyword}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新关键词失败: {str(e)}")
            return False
        finally:
            session.close()

    def delete_keyword(self, keyword: str) -> bool:
        """删除关键词
        
        Args:
            keyword: 关键词
            
        Returns:
            bool: 是否删除成功
        """
        session = self.get_session()
        try:
            keyword_obj = session.query(Keyword).filter(Keyword.keyword == keyword).first()
            if not keyword_obj:
                self.logger.warning(f"关键词 {keyword} 不存在")
                return False
                
            session.delete(keyword_obj)
            session.commit()
            self.logger.info(f"成功删除关键词: {keyword}")
            return True
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"删除关键词失败: {str(e)}")
            return False
        finally:
            session.close()

    # ==================== ChatMessage CRUD ====================

    def add_chat_message(self, account_id: int, shop_id: str,
                         from_uid: str, nickname: str,
                         message_type: str, user_content: str,
                         conversation_id: str = None) -> int:
        """添加用户消息记录

        Args:
            account_id: 账号ID
            shop_id: 店铺ID
            from_uid: 用户ID
            nickname: 用户昵称
            message_type: 消息类型
            user_content: 用户消息内容
            conversation_id: 会话ID

        Returns:
            int: 消息记录ID
        """
        session = self.get_session()
        try:
            msg = ChatMessage(
                account_id=account_id,
                shop_id=shop_id,
                from_uid=from_uid,
                nickname=nickname,
                message_type=message_type,
                user_content=user_content,
                conversation_id=conversation_id,
                status=0
            )
            session.add(msg)
            session.commit()
            return msg.id
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加聊天消息失败: {str(e)}")
            return -1
        finally:
            session.close()

    def update_ai_reply(self, message_id: int, ai_reply: str, status: int = 1):
        """更新 AI 回复

        Args:
            message_id: 消息ID
            ai_reply: AI回复内容
            status: 状态(1-已回复, 2-转人工, 3-失败)
        """
        session = self.get_session()
        try:
            msg = session.query(ChatMessage).filter_by(id=message_id).first()
            if msg:
                msg.ai_reply = ai_reply
                msg.status = status
                msg.replied_at = datetime.now()
                session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新AI回复失败: {str(e)}")
        finally:
            session.close()

    def get_conversation_history(self, account_id: int, from_uid: str,
                                  conversation_id: str = None, limit: int = 30) -> List[Dict[str, Any]]:
        """获取与特定用户的对话历史（当前会话）

        Args:
            account_id: 账号ID
            from_uid: 用户ID
            conversation_id: 会话ID，为None时返回最近消息
            limit: 最多返回多少条记录

        Returns:
            List[Dict]: 消息记录列表，按时间正序排列（最早的在前）
        """
        session = self.get_session()
        try:
            query = session.query(ChatMessage).filter_by(
                account_id=account_id,
                from_uid=from_uid
            )

            # 如果指定了会话ID，只查询该会话
            if conversation_id:
                query = query.filter_by(conversation_id=conversation_id)

            messages = query.order_by(ChatMessage.created_at.asc()) \
                           .limit(limit) \
                           .all()

            return [msg.to_dict() for msg in messages]
        except SQLAlchemyError as e:
            self.logger.error(f"获取对话历史失败: {str(e)}")
            return []
        finally:
            session.close()

    def get_chat_message(self, message_id: int) -> Optional[Dict[str, Any]]:
        """获取单条消息记录

        Args:
            message_id: 消息ID

        Returns:
            Optional[Dict]: 消息记录或None
        """
        session = self.get_session()
        try:
            msg = session.query(ChatMessage).filter_by(id=message_id).first()
            return msg.to_dict() if msg else None
        except SQLAlchemyError as e:
            self.logger.error(f"获取聊天消息失败: {str(e)}")
            return None
        finally:
            session.close()

    def query_chat_messages(self,
                          account_id: int = None,
                          shop_id: str = None,
                          from_uid: str = None,
                          start_time: datetime = None,
                          end_time: datetime = None,
                          status: int = None,
                          keyword: str = None,
                          page: int = 1,
                          page_size: int = 50) -> tuple:
        """多维度查询聊天记录

        Args:
            account_id: 账号ID筛选
            shop_id: 店铺ID筛选
            from_uid: 用户ID筛选
            start_time: 开始时间筛选
            end_time: 结束时间筛选
            status: 状态筛选
            keyword: 关键词搜索(搜索用户内容和AI回复)
            page: 页码
            page_size: 每页条数

        Returns:
            tuple: (total_count, messages_list)
        """
        session = self.get_session()
        try:
            query = session.query(ChatMessage)

            # 筛选条件
            if account_id:
                query = query.filter_by(account_id=account_id)
            if shop_id:
                query = query.filter_by(shop_id=shop_id)
            if from_uid:
                query = query.filter_by(from_uid=from_uid)
            if start_time:
                query = query.filter(ChatMessage.created_at >= start_time)
            if end_time:
                query = query.filter(ChatMessage.created_at <= end_time)
            if status is not None:
                query = query.filter_by(status=status)
            if keyword:
                query = query.filter(
                    (ChatMessage.user_content.contains(keyword)) |
                    (ChatMessage.ai_reply.contains(keyword))
                )

            # 排序和分页
            total = query.count()
            messages = query.order_by(ChatMessage.created_at.desc()) \
                          .offset((page - 1) * page_size) \
                          .limit(page_size) \
                          .all()

            return total, [msg.to_dict() for msg in messages]
        except SQLAlchemyError as e:
            self.logger.error(f"查询聊天消息失败: {str(e)}")
            return 0, []
        finally:
            session.close()

    def get_conversation_history(self, account_id: int, from_uid: str,
                                 limit: int = 100) -> list:
        """获取与特定用户的完整对话历史

        Args:
            account_id: 账号ID
            from_uid: 用户ID
            limit: 最大条数

        Returns:
            list: 消息列表
        """
        session = self.get_session()
        try:
            messages = session.query(ChatMessage) \
                .filter_by(account_id=account_id, from_uid=from_uid) \
                .order_by(ChatMessage.created_at.asc()) \
                .limit(limit) \
                .all()
            return [msg.to_dict() for msg in messages]
        except SQLAlchemyError as e:
            self.logger.error(f"获取会话历史失败: {str(e)}")
            return []
        finally:
            session.close()

    def get_unique_users(self, account_id: int = None, shop_id: str = None,
                        days: int = 30) -> list:
        """获取去重后的用户列表

        Args:
            account_id: 账号ID筛选
            shop_id: 店铺ID筛选
            days: 最近几天

        Returns:
            list: 用户列表
        """
        session = self.get_session()
        try:
            start_date = datetime.now() - timedelta(days=days)
            query = session.query(ChatMessage).filter(ChatMessage.created_at >= start_date)

            if account_id:
                query = query.filter_by(account_id=account_id)
            if shop_id:
                query = query.filter_by(shop_id=shop_id)

            # 按用户分组，获取最新消息
            from sqlalchemy import func
            subquery = query \
                .with_entities(
                    ChatMessage.from_uid,
                    ChatMessage.nickname,
                    func.max(ChatMessage.created_at).label('last_time')
                ) \
                .group_by(ChatMessage.from_uid, ChatMessage.nickname) \
                .subquery()

            results = session.query(subquery).order_by(subquery.c.last_time.desc()).all()

            return [
                {
                    'from_uid': r.from_uid,
                    'nickname': r.nickname,
                    'last_time': r.last_time.strftime('%Y-%m-%d %H:%M:%S')
                }
                for r in results
            ]
        except SQLAlchemyError as e:
            self.logger.error(f"获取用户列表失败: {str(e)}")
            return []
        finally:
            session.close()

    def delete_chat_messages(self, days: int = 90) -> int:
        """删除指定天数之前的消息记录

        Args:
            days: 保留最近几天的记录

        Returns:
            int: 删除的记录数
        """
        session = self.get_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = session.query(ChatMessage) \
                .filter(ChatMessage.created_at < cutoff_date) \
                .delete(synchronize_session=False)
            session.commit()
            self.logger.info(f"已删除 {result} 条过期消息记录")
            return result
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"删除消息记录失败: {str(e)}")
            return 0
        finally:
            session.close()


    # ==================== AlertLog CRUD ====================

    def add_alert_log(self, alert_type: str, emotion_score: float,
                      user_message: str, from_uid: str, nickname: str,
                      shop_id: str, account_id: int = None,
                      emotion_level: str = None, emotion_keywords: str = None) -> int:
        """添加告警记录

        Args:
            alert_type: 告警类型 (emotion/keyword/system)
            emotion_score: 情绪分数
            user_message: 用户消息内容
            from_uid: 用户 ID
            nickname: 用户昵称
            shop_id: 店铺 ID
            account_id: 账号 ID
            emotion_level: 情绪等级
            emotion_keywords: 情绪关键词

        Returns:
            int: 告警记录 ID
        """
        session = self.get_session()
        try:
            alert = AlertLog(
                alert_type=alert_type,
                emotion_score=emotion_score,
                emotion_level=emotion_level,
                emotion_keywords=emotion_keywords,
                user_message=user_message,
                from_uid=from_uid,
                nickname=nickname,
                shop_id=shop_id,
                account_id=account_id,
                notified=0
            )
            session.add(alert)
            session.commit()
            return alert.id
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加告警记录失败：{str(e)}")
            return -1
        finally:
            session.close()

    def update_alert_notified(self, alert_id: int, telegram_message_id: str = None) -> bool:
        """更新告警为已通知状态

        Args:
            alert_id: 告警记录 ID
            telegram_message_id: Telegram 消息 ID

        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            alert = session.query(AlertLog).filter_by(id=alert_id).first()
            if alert:
                alert.notified = 1
                alert.notified_at = datetime.now()
                if telegram_message_id:
                    alert.telegram_message_id = telegram_message_id
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新告警状态失败：{str(e)}")
            return False
        finally:
            session.close()

    def get_alert_logs(self, alert_type: str = None, shop_id: str = None,
                       from_uid: str = None, start_time: datetime = None,
                       end_time: datetime = None, page: int = 1,
                       page_size: int = 50) -> tuple:
        """多维度查询告警记录

        Args:
            alert_type: 告警类型筛选
            shop_id: 店铺 ID 筛选
            from_uid: 用户 ID 筛选
            start_time: 开始时间筛选
            end_time: 结束时间筛选
            page: 页码
            page_size: 每页条数

        Returns:
            tuple: (total_count, alerts_list)
        """
        session = self.get_session()
        try:
            query = session.query(AlertLog)

            # 筛选条件
            if alert_type:
                query = query.filter_by(alert_type=alert_type)
            if shop_id:
                query = query.filter_by(shop_id=shop_id)
            if from_uid:
                query = query.filter_by(from_uid=from_uid)
            if start_time:
                query = query.filter(AlertLog.created_at >= start_time)
            if end_time:
                query = query.filter(AlertLog.created_at <= end_time)

            # 排序和分页
            total = query.count()
            alerts = query.order_by(AlertLog.created_at.desc()) \
                          .offset((page - 1) * page_size) \
                          .limit(page_size) \
                          .all()

            return total, [alert.to_dict() for alert in alerts]
        except SQLAlchemyError as e:
            self.logger.error(f"查询告警记录失败：{str(e)}")
            return 0, []
        finally:
            session.close()

    def get_alert_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取告警统计信息

        Args:
            days: 统计最近几天的数据

        Returns:
            Dict: 统计信息
        """
        session = self.get_session()
        try:
            start_date = datetime.now() - timedelta(days=days)

            # 总告警数
            total = session.query(AlertLog).filter(
                AlertLog.created_at >= start_date
            ).count()

            # 按类型分组
            type_stats = session.query(
                AlertLog.alert_type,
                session.query(AlertLog).filter(
                    AlertLog.created_at >= start_date
                ).filter(AlertLog.alert_type == AlertLog.alert_type).count()
            ).group_by(AlertLog.alert_type).all()

            # 已通知数
            notified = session.query(AlertLog).filter(
                AlertLog.created_at >= start_date,
                AlertLog.notified == 1
            ).count()

            return {
                'total': total,
                'notified': notified,
                'pending': total - notified,
                'by_type': {t[0]: t[1] for t in type_stats},
                'period_days': days
            }
        except SQLAlchemyError as e:
            self.logger.error(f"获取告警统计失败：{str(e)}")
            return {}
        finally:
            session.close()

    def delete_alert_logs(self, days: int = 90) -> int:
        """删除指定天数之前的告警记录

        Args:
            days: 保留最近几天的记录

        Returns:
            int: 删除的记录数
        """
        session = self.get_session()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = session.query(AlertLog) \
                .filter(AlertLog.created_at < cutoff_date) \
                .delete(synchronize_session=False)
            session.commit()
            self.logger.info(f"已删除 {result} 条过期告警记录")
            return result
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"删除告警记录失败：{str(e)}")
            return 0
        finally:
            session.close()

    # ==================== AI 学习优化相关 ====================

    def update_message_confidence(self, message_id: int, confidence: float) -> bool:
        """更新 AI 回复置信度

        Args:
            message_id: 消息 ID
            confidence: 置信度 (0-1)

        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            msg = session.query(ChatMessage).filter_by(id=message_id).first()
            if msg:
                msg.ai_confidence = confidence
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新消息置信度失败：{str(e)}")
            return False
        finally:
            session.close()

    def update_message_quality_score(self, message_id: int, quality_score: float) -> bool:
        """更新回复质量评分

        Args:
            message_id: 消息 ID
            quality_score: 质量评分 (-1.0~1.0)

        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            msg = session.query(ChatMessage).filter_by(id=message_id).first()
            if msg:
                msg.quality_score = quality_score
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新消息质量评分失败：{str(e)}")
            return False
        finally:
            session.close()

    def update_message_human_edit(self, message_id: int, human_reply: str,
                                   edit_diff: dict) -> bool:
        """更新人工修正内容

        Args:
            message_id: 消息 ID
            human_reply: 人工修改后的回复
            edit_diff: 差异记录

        Returns:
            bool: 是否更新成功
        """
        import json
        session = self.get_session()
        try:
            msg = session.query(ChatMessage).filter_by(id=message_id).first()
            if msg:
                msg.human_edited_reply = human_reply
                msg.edit_diff = json.dumps(edit_diff, ensure_ascii=False)
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新人工修正内容失败：{str(e)}")
            return False
        finally:
            session.close()

    def update_message_optimization_flag(self, message_id: int,
                                         is_sample: int = 1,
                                         opt_type: str = None) -> bool:
        """更新优化样本标记

        Args:
            message_id: 消息 ID
            is_sample: 是否作为优化样本 (0-否，1-是)
            opt_type: 优化类型

        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            msg = session.query(ChatMessage).filter_by(id=message_id).first()
            if msg:
                msg.is_optimization_sample = is_sample
                if opt_type:
                    msg.optimization_type = opt_type
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新优化样本标记失败：{str(e)}")
            return False
        finally:
            session.close()

    def add_feedback_stats(self, account_id: int, from_uid: str,
                           message_id: int, satisfaction_score: int = None,
                           is_resolved: int = None, is_transferred: int = None,
                           response_time_sec: float = None,
                           conversation_turns: int = None,
                           has_followup: int = None) -> int:
        """添加反馈统计记录

        Args:
            account_id: 账号 ID
            from_uid: 用户 ID
            message_id: 消息 ID
            satisfaction_score: 满意度评分 (1-5)
            is_resolved: 是否解决 (0-否，1-是)
            is_transferred: 是否转人工 (0-否，1-是)
            response_time_sec: 响应时间（秒）
            conversation_turns: 会话轮数
            has_followup: 是否有追问 (0-否，1-是)

        Returns:
            int: 记录 ID，失败返回 -1
        """
        session = self.get_session()
        try:
            feedback = FeedbackStats(
                account_id=account_id,
                from_uid=from_uid,
                message_id=message_id,
                satisfaction_score=satisfaction_score,
                is_resolved=is_resolved,
                is_transferred=is_transferred,
                response_time_sec=response_time_sec,
                conversation_turns=conversation_turns,
                has_followup=has_followup
            )
            session.add(feedback)
            session.commit()
            return feedback.id
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"添加反馈统计失败：{str(e)}")
            return -1
        finally:
            session.close()

    def get_feedback_stats(self, message_id: int) -> Optional[Dict]:
        """获取消息的反馈统计

        Args:
            message_id: 消息 ID

        Returns:
            Optional[Dict]: 反馈统计或 None
        """
        session = self.get_session()
        try:
            feedback = session.query(FeedbackStats).filter_by(
                message_id=message_id
            ).first()
            return feedback.to_dict() if feedback else None
        except SQLAlchemyError as e:
            self.logger.error(f"获取反馈统计失败：{str(e)}")
            return None
        finally:
            session.close()

    def get_feedback_stats_by_account(self, account_id: int,
                                      days: int = 7) -> List[Dict]:
        """获取账号的反馈统计

        Args:
            account_id: 账号 ID
            days: 最近几天

        Returns:
            List[Dict]: 反馈统计列表
        """
        session = self.get_session()
        try:
            start_date = datetime.now() - timedelta(days=days)
            feedbacks = session.query(FeedbackStats).filter(
                FeedbackStats.account_id == account_id,
                FeedbackStats.created_at >= start_date
            ).all()
            return [f.to_dict() for f in feedbacks]
        except SQLAlchemyError as e:
            self.logger.error(f"获取反馈统计列表失败：{str(e)}")
            return []
        finally:
            session.close()

    # SimilarCase 相关操作
    def get_similar_case(self, case_id: int) -> Optional[Dict]:
        """获取相似案例

        Args:
            case_id: 案例 ID

        Returns:
            Optional[Dict]: 案例或 None
        """
        session = self.get_session()
        try:
            case = session.query(SimilarCase).filter_by(id=case_id).first()
            return case.to_dict() if case else None
        except SQLAlchemyError as e:
            self.logger.error(f"获取相似案例失败：{str(e)}")
            return None
        finally:
            session.close()

    def get_pending_similar_cases(self, account_id: int = None,
                                  limit: int = 50) -> List[Dict]:
        """获取待审核案例

        Args:
            account_id: 账号 ID
            limit: 数量限制

        Returns:
            List[Dict]: 案例列表
        """
        session = self.get_session()
        try:
            query = session.query(SimilarCase).filter_by(status=0)
            if account_id:
                query = query.filter_by(account_id=account_id)
            cases = query.order_by(
                SimilarCase.created_at.desc()
            ).limit(limit).all()
            return [c.to_dict() for c in cases]
        except SQLAlchemyError as e:
            self.logger.error(f"获取待审核案例失败：{str(e)}")
            return []
        finally:
            session.close()

    def update_similar_case_status(self, case_id: int, status: int,
                                   reviewed_by: str = None) -> bool:
        """更新案例状态

        Args:
            case_id: 案例 ID
            status: 状态 (0-待审核，1-已启用，2-已禁用)
            reviewed_by: 审核人

        Returns:
            bool: 是否更新成功
        """
        session = self.get_session()
        try:
            case = session.query(SimilarCase).filter_by(id=case_id).first()
            if case:
                case.status = status
                if reviewed_by:
                    case.reviewed_by = reviewed_by
                session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            self.logger.error(f"更新案例状态失败：{str(e)}")
            return False
        finally:
            session.close()

    def get_similar_case_statistics(self, account_id: int = None) -> Dict:
        """获取案例统计信息

        Args:
            account_id: 账号 ID

        Returns:
            Dict: 统计信息
        """
        session = self.get_session()
        try:
            query = session.query(SimilarCase)
            if account_id:
                query = query.filter_by(account_id=account_id)

            total = query.count()
            pending = query.filter_by(status=0).count()
            enabled = query.filter_by(status=1).count()
            disabled = query.filter_by(status=2).count()

            return {
                "total": total,
                "pending": pending,
                "enabled": enabled,
                "disabled": disabled
            }
        except SQLAlchemyError as e:
            self.logger.error(f"获取案例统计失败：{str(e)}")
            return {"total": 0, "pending": 0, "enabled": 0, "disabled": 0}
        finally:
            session.close()


# 创建全局数据库管理器实例（路径由调用方传入）
# 注意：这里的默认路径仅作为后备，实际使用时应通过 database/__init__.py 导入 db_manager
default_db_path = os.environ.get('DB_PATH', 'database/channel_shop.db')
db_manager = DatabaseManager(db_path=default_db_path) 