"""Qwen Bot Implementation - Using DashScope (Alibaba Cloud) API"""
import json
from typing import Optional

from core.agents.bot import Bot
from core.bridge.reply import Reply, ReplyType
from core.bridge.context import Context, ContextType
from config import config
from utils.logger import get_logger
from core.agents.QwenAgent.session_manager import QwenSessionManager


class QwenBot(Bot):
    """Qwen Bot 实现 - 使用阿里云百炼 (DashScope) API"""

    def __init__(self):
        super().__init__()
        self.logger = get_logger("QwenBot")
        self.api_key = config.get("qwen_api_key")
        self.model = config.get("qwen_model", "qwen-turbo")
        self.system_prompt = config.get("qwen_system_prompt", "你是通义千问，是一个 helpful AI 助手。")

        # 初始化 DashScope
        try:
            import dashscope
            dashscope.api_key = self.api_key
            self.dashscope = dashscope
            self.logger.info(f"QwenBot 初始化完成，使用模型: {self.model}")
        except ImportError:
            self.logger.error("dashscope 模块未安装，请安装: pip install dashscope")
            self.dashscope = None
        except Exception as e:
            self.logger.error(f"QwenBot 初始化失败: {e}")
            self.dashscope = None

        # 初始化会话管理器
        self.session_manager = QwenSessionManager()

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return self.system_prompt

    def _preprocess_content(self, context: Context) -> str:
        """预处理消息内容"""
        if context.type == ContextType.TEXT:
            try:
                content_obj = json.loads(context.content)
                if isinstance(content_obj, list) and len(content_obj) > 0:
                    text_parts = []
                    for item in content_obj:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    return " ".join(text_parts) if text_parts else context.content
            except (json.JSONDecodeError, TypeError):
                pass
            return str(context.content)
        elif context.type in [ContextType.GOODS_INQUIRY, ContextType.GOODS_SPEC]:
            try:
                goods_info = context.content if isinstance(context.content, dict) else json.loads(context.content)
                return f"商品：{goods_info.get('goods_name', '未知商品')}，价格：{goods_info.get('goods_price', '未知')}，规格：{goods_info.get('goods_spec', '未指定')}"
            except:
                return str(context.content)
        elif context.type == ContextType.ORDER_INFO:
            try:
                order_info = context.content if isinstance(context.content, dict) else json.loads(context.content)
                return f"订单：{order_info.get('order_id', '未知订单')}，商品：{order_info.get('goods_name', '未知商品')}"
            except:
                return str(context.content)
        else:
            return str(context.content)

    def reply(self, context: Context) -> Reply:
        """
        处理用户消息并返回 AI 回复

        Args:
            context: 消息上下文

        Returns:
            Reply 对象
        """
        try:
            if not self.dashscope:
                return Reply(ReplyType.ERROR, "Qwen Bot 未正确初始化，请检查 API 配置")

            if not self.api_key:
                return Reply(ReplyType.ERROR, "Qwen API Key 未配置")

            # 获取用户标识
            from_uid = context.kwargs.get("from_uid")
            shop_id = context.kwargs.get("shop_id")
            user_id = f"{shop_id}_{from_uid}" if shop_id and from_uid else "default_user"

            # 获取会话历史
            messages = self.session_manager.get_messages(user_id)

            # 如果没有历史记录，添加系统提示
            if not messages:
                messages.append({"role": "system", "content": self._build_system_prompt()})

            # 预处理当前消息
            user_content = self._preprocess_content(context)

            # 添加用户消息
            messages.append({"role": "user", "content": user_content})

            # 调用 Qwen API
            self.logger.debug(f"调用 Qwen API，用户: {user_id}, 模型: {self.model}")

            from dashscope import Generation
            response = Generation.call(
                model=self.model,
                messages=messages,
                result_format='message',
                temperature=0.7,
                max_tokens=2048
            )

            if response.status_code == 200:
                reply_content = response.output.choices[0].message.content

                # 保存助手回复到历史
                messages.append({"role": "assistant", "content": reply_content})
                self.session_manager.save_messages(user_id, messages)

                self.logger.debug(f"Qwen 回复: {reply_content[:100]}...")
                return Reply(ReplyType.TEXT, reply_content)
            else:
                error_msg = f"Qwen API 错误: {response.message}"
                self.logger.error(error_msg)
                return Reply(ReplyType.ERROR, error_msg)

        except Exception as e:
            self.logger.error(f"Qwen 处理消息异常: {str(e)}", exc_info=True)
            return Reply(ReplyType.TEXT, f"AI 服务暂时不可用: {str(e)}")
