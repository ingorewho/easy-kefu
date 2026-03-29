"""Kimi Bot Implementation - Using Moonshot AI API"""
import json
from typing import Optional

from core.agents.bot import Bot
from core.bridge.reply import Reply, ReplyType
from core.bridge.context import Context, ContextType
from config import config
from utils.logger import get_logger
from core.agents.KimiAgent.session_manager import KimiSessionManager


class KimiBot(Bot):
    """Kimi Bot 实现 - 使用 Moonshot AI API (OpenAI兼容接口)"""

    def __init__(self):
        super().__init__()
        self.logger = get_logger("KimiBot")
        self.api_key = config.get("kimi_api_key")
        self.api_base = config.get("kimi_api_base", "https://api.moonshot.cn/v1")
        self.model = config.get("kimi_model", "kimi-k2.5")
        self.system_prompt = config.get("kimi_system_prompt", "你是 Kimi，是一个 helpful AI 助手。")

        # 调试日志：显示实际使用的配置（隐藏部分 API Key）
        key_preview = self.api_key[:10] + "..." + self.api_key[-4:] if self.api_key and len(self.api_key) > 14 else "未设置"
        self.logger.info(f"KimiBot 配置: base_url={self.api_base}, model={self.model}, api_key={key_preview}")

        # 初始化 OpenAI 客户端
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            self.logger.info(f"KimiBot 初始化完成，使用模型: {self.model}")
        except ImportError:
            self.logger.error("openai 模块未安装，请安装: pip install openai")
            self.client = None
        except Exception as e:
            self.logger.error(f"KimiBot 初始化失败: {e}")
            self.client = None

        # 初始化会话管理器
        self.session_manager = KimiSessionManager()

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return self.system_prompt

    def _preprocess_content(self, context: Context) -> str:
        """预处理消息内容"""
        if context.type == ContextType.TEXT:
            try:
                # 尝试解析 JSON 格式（Coze 格式的预处理消息）
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
            if not self.client:
                return Reply(ReplyType.ERROR, "Kimi Bot 未正确初始化，请检查 API 配置")

            if not self.api_key:
                return Reply(ReplyType.ERROR, "Kimi API Key 未配置")

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

            # 调用 Kimi API
            self.logger.debug(f"调用 Kimi API，用户: {user_id}, 模型: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048
            )

            # 获取 AI 回复
            reply_content = response.choices[0].message.content

            # 保存助手回复到历史
            messages.append({"role": "assistant", "content": reply_content})
            self.session_manager.save_messages(user_id, messages)

            self.logger.debug(f"Kimi 回复: {reply_content[:100]}...")
            return Reply(ReplyType.TEXT, reply_content)

        except Exception as e:
            self.logger.error(f"Kimi 处理消息异常: {str(e)}", exc_info=True)
            return Reply(ReplyType.TEXT, f"AI 服务暂时不可用: {str(e)}")
