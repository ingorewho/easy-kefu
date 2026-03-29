#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram 通知模块 - 通过 Telegram Bot 发送告警消息

功能：
1. 发送文本消息
2. 支持异步发送
3. 支持消息模板
4. 超时和重试机制
"""

import asyncio
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import requests

from utils.logger import get_logger
from utils.emotion_analyzer import EmotionResult

logger = get_logger("TelegramNotifier")


@dataclass
class AlertMessage:
    """告警消息"""
    emotion_score: float
    user_message: str
    user_info: Dict[str, str]  # {from_uid, nickname, shop_id}
    timestamp: datetime
    threshold: float


class TelegramNotifier:
    """Telegram 通知器"""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        timeout: int = 10,
        max_retries: int = 2
    ):
        """
        初始化 Telegram 通知器

        Args:
            bot_token: Telegram Bot Token
            chat_id: 接收消息的 Chat ID
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.max_retries = max_retries

        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self.logger = get_logger("TelegramNotifier")

        # 发送统计
        self._sent_count = 0
        self._failed_count = 0

    def send_alert(
        self,
        emotion_result: EmotionResult,
        user_info: Dict[str, str],
        message_preview: str,
        shop_name: str = ""
    ) -> bool:
        """
        发送情绪告警消息

        Args:
            emotion_result: 情绪分析结果
            user_info: 用户信息 {from_uid, nickname, shop_id}
            message_preview: 用户消息预览
            shop_name: 店铺名称

        Returns:
            bool: 是否发送成功
        """
        # 构建告警消息
        text = self._build_alert_text(
            emotion_result, user_info, message_preview, shop_name
        )

        return self._send_message(text, parse_mode="HTML")

    def _build_alert_text(
        self,
        emotion_result: EmotionResult,
        user_info: Dict[str, str],
        message_preview: str,
        shop_name: str
    ) -> str:
        """构建告警消息文本"""
        # 情绪等级图标
        level_icons = {
            "very_negative": "🔴",
            "negative": "🟠",
            "neutral": "🟡",
            "positive": "🟢"
        }
        level_icon = level_icons.get(emotion_result.level, "⚪")

        # 情绪分数显示（转换为百分比）
        score_percent = int((emotion_result.score + 1) * 50)  # -1~1 -> 0~100
        score_bar = self._progress_bar(score_percent)

        # 截取消息预览（最多 100 字）
        if len(message_preview) > 100:
            message_preview = message_preview[:97] + "..."

        # 脱敏用户 ID
        from_uid = user_info.get("from_uid", "未知")
        masked_uid = self._mask_string(from_uid)

        text = f"""{level_icon} <b>客服情绪告警</b> {level_icon}

<b>情绪等级：</b>{emotion_result.level.upper()}
<b>情绪分数：</b>{emotion_result.score:.2f} {score_bar}
<b>告警阈值：</b>{emotion_result.should_alert}

<b>店铺：</b>{shop_name or user_info.get("shop_id", "未知")}
<b>用户：</b>{user_info.get("nickname", "未知")} ({masked_uid})
<b>时间：</b>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

<b>用户消息：</b>
<code>{message_preview}</code>

<b>情绪关键词：</b>
<code>{", ".join(emotion_result.keywords) if emotion_result.keywords else "无"}</code>

━━━━━━━━━━━━━━━━━━━━
⚠️ 请及时关注并介入处理"""

        return text

    def _progress_bar(self, percent: int, length: int = 10) -> str:
        """生成进度条"""
        filled = int(length * percent / 100)
        empty = length - filled
        return "█" * filled + "░" * empty

    def _mask_string(self, s: str, keep_first: int = 3, keep_last: int = 4) -> str:
        """脱敏字符串"""
        if len(s) <= keep_first + keep_last:
            return "***"
        return s[:keep_first] + "***" + s[-keep_last:]

    def _send_message(
        self,
        text: str,
        parse_mode: str = "HTML",
        disable_notification: bool = False
    ) -> bool:
        """
        发送 Telegram 消息

        Args:
            text: 消息文本
            parse_mode: 解析模式 (HTML/Markdown)
            disable_notification: 是否静默发送

        Returns:
            bool: 是否发送成功
        """
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }

        # 重试逻辑
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout
                )

                result = response.json()

                if result.get("ok"):
                    self._sent_count += 1
                    self.logger.info(f"Telegram 告警发送成功 | chat_id={self.chat_id}")
                    return True
                else:
                    error = result.get("description", "Unknown error")
                    self.logger.error(f"Telegram API 错误：{error}")
                    self._failed_count += 1
                    return False

            except requests.exceptions.Timeout:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries + 1})")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"连接失败 (尝试 {attempt + 1}/{self.max_retries + 1})")
            except Exception as e:
                self.logger.error(f"发送失败：{e}")

            if attempt < self.max_retries:
                # 指数退避
                import time
                time.sleep(0.5 * (2 ** attempt))

        self._failed_count += 1
        self.logger.error(f"Telegram 告警发送失败，已重试{self.max_retries}次")
        return False

    def send_test_message(self) -> bool:
        """发送测试消息"""
        text = """✅ <b>Telegram 告警测试</b>

如果您收到此消息，说明 Telegram 告警配置正确。

测试时间：{time}

━━━━━━━━━━━━━━━━━━━━
🤖 智能客服系统""".format(
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        return self._send_message(text)

    def get_stats(self) -> Dict[str, int]:
        """获取发送统计"""
        return {
            "sent": self._sent_count,
            "failed": self._failed_count,
            "total": self._sent_count + self._failed_count
        }


# ==================== 异步发送支持 ====================

class AsyncTelegramNotifier:
    """异步 Telegram 通知器（非阻塞）"""

    def __init__(self, bot_token: str, chat_id: str):
        self.notifier = TelegramNotifier(bot_token, chat_id)
        self.logger = get_logger("AsyncTelegramNotifier")

    def send_alert(
        self,
        emotion_result: EmotionResult,
        user_info: Dict[str, str],
        message_preview: str,
        shop_name: str = ""
    ):
        """异步发送告警（不阻塞主线程）"""
        thread = threading.Thread(
            target=self._send_in_thread,
            args=(emotion_result, user_info, message_preview, shop_name),
            daemon=True
        )
        thread.start()

    def _send_in_thread(
        self,
        emotion_result: EmotionResult,
        user_info: Dict[str, str],
        message_preview: str,
        shop_name: str
    ):
        """在线程中发送"""
        try:
            success = self.notifier.send_alert(
                emotion_result, user_info, message_preview, shop_name
            )
            if success:
                self.logger.debug("异步告警发送成功")
            else:
                self.logger.warning("异步告警发送失败")
        except Exception as e:
            self.logger.error(f"异步告警异常：{e}")

    def send_test_message(self) -> bool:
        """发送测试消息（同步）"""
        return self.notifier.send_test_message()


# ==================== 便捷函数 ====================

_notifier_instance: Optional[AsyncTelegramNotifier] = None


def init_notifier(bot_token: str, chat_id: str):
    """初始化通知器"""
    global _notifier_instance
    _notifier_instance = AsyncTelegramNotifier(bot_token, chat_id)
    logger.info("Telegram 通知器已初始化")


def get_notifier() -> Optional[AsyncTelegramNotifier]:
    """获取通知器实例"""
    return _notifier_instance


def send_emotion_alert(
    emotion_result: EmotionResult,
    user_info: Dict[str, str],
    message_preview: str,
    shop_name: str = ""
):
    """便捷函数：发送情绪告警"""
    if _notifier_instance:
        _notifier_instance.send_alert(
            emotion_result, user_info, message_preview, shop_name
        )
    else:
        logger.warning("Telegram 通知器未初始化，跳过告警")


def send_test_alert() -> bool:
    """便捷函数：发送测试告警"""
    if _notifier_instance:
        return _notifier_instance.send_test_message()
    logger.warning("Telegram 通知器未初始化")
    return False
