"""Qwen Session Manager - Manages conversation history for Qwen bot"""
import sqlite3
import json
import time
import os
from typing import List, Optional
from utils.logger import get_logger


class QwenSessionManager:
    """Qwen 会话历史管理"""

    def __init__(self, db_path: str = "database/qwen_sessions.db"):
        self.logger = get_logger("QwenSessionManager")
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self._init_table()

    def _init_table(self):
        """初始化会话表"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                user_id TEXT PRIMARY KEY,
                messages TEXT,  -- JSON 数组
                updated_at INTEGER
            )
        """)
        self.db.commit()

    def get_messages(self, user_id: str) -> List[dict]:
        """获取用户历史消息，最多保留 10 轮"""
        try:
            cursor = self.db.execute(
                "SELECT messages FROM sessions WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                messages = json.loads(row[0])
                # 保留最近 10 轮 (20 条消息)
                return messages[-20:] if len(messages) > 20 else messages
            return []
        except Exception as e:
            self.logger.error(f"获取会话历史失败: {e}")
            return []

    def save_messages(self, user_id: str, messages: List[dict]):
        """保存用户消息历史"""
        try:
            self.db.execute(
                """INSERT OR REPLACE INTO sessions (user_id, messages, updated_at)
                   VALUES (?, ?, ?)""",
                (user_id, json.dumps(messages, ensure_ascii=False), int(time.time()))
            )
            self.db.commit()
        except Exception as e:
            self.logger.error(f"保存会话历史失败: {e}")

    def clear_session(self, user_id: str):
        """清除指定用户的会话历史"""
        try:
            self.db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            self.db.commit()
        except Exception as e:
            self.logger.error(f"清除会话历史失败: {e}")

    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
