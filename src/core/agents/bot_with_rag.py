"""支持 RAG 的 Bot 包装器"""
from typing import Optional

from core.agents.bot import Bot
from core.bridge.context import Context
from core.bridge.reply import Reply
from services.knowledge.rag_retriever import HybridRAGRetriever
from config import config
from utils.logger import get_logger


class BotWithRAG(Bot):
    """为 Bot 添加 RAG 知识库支持的包装器（支持混合检索）"""

    def __init__(self, base_bot: Bot, enable_rag: bool = True):
        super().__init__()
        self.base_bot = base_bot
        self.enable_rag = enable_rag

        # 使用混合检索器
        if enable_rag:
            self.rag_retriever = HybridRAGRetriever(
                top_k=config.get("rag_top_k", 3),
                score_threshold=config.get("rag_score_threshold", 0.5),
                enable_web_fallback=config.get("enable_web_search_fallback", True),
                min_confidence=config.get("web_search_min_confidence", 0.6)
            )
        else:
            self.rag_retriever = None

        self.logger = get_logger("BotWithRAG")

        # 复制 base_bot 的属性
        self.__class__.__name__ = base_bot.__class__.__name__

    def reply(self, context: Context) -> Reply:
        """
        处理消息，支持 RAG 增强
        """
        try:
            if not self.enable_rag or not self.rag_retriever:
                # RAG 未启用，直接调用基础 Bot
                self.logger.info("RAG 未启用，直接调用基础 Bot")
                return self.base_bot.reply(context)

            # 获取原始内容
            original_content = context.content

            # 如果是 JSON 格式（来自 message_handler 预处理），提取文本
            import json
            try:
                content_obj = json.loads(original_content)
                if isinstance(content_obj, list) and len(content_obj) > 0:
                    text_parts = []
                    for item in content_obj:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                    query = " ".join(text_parts) if text_parts else original_content
                else:
                    query = original_content
            except (json.JSONDecodeError, TypeError):
                query = str(original_content)

            self.logger.info(f"RAG 查询: {query[:50]}...")

            # 从配置读取 prompt 设置
            system_prompt = config.get("ai_system_prompt", "你是电商客服，回复要简短口语化，不超过20字")
            max_length = config.get("ai_reply_max_length", 20)
            style = config.get("ai_reply_style", "casual")
            no_punctuation = config.get("ai_reply_no_punctuation", True)

            self.logger.info(f"AI回复配置: max_length={max_length}, style={style}, no_punctuation={no_punctuation}")

            # 获取对话历史并格式化
            chat_history = context.kwargs.get("chat_history", [])
            chat_context = self._format_chat_history(chat_history)
            self.logger.info(f"对话历史: {len(chat_history)} 条记录")

            # 使用 RAG 增强查询
            enhanced_prompt = self.rag_retriever.enhance_prompt(
                query=query,
                original_prompt=system_prompt
            )

            # 在提示词中插入对话上下文（放在知识之后，当前问题之前）
            if chat_context:
                enhanced_prompt = enhanced_prompt.replace(
                    "=== 用户问题 ===",
                    f"{chat_context}\n\n=== 当前问题 ==="
                )

            self.logger.info(f"RAG 增强后提示词:\n{enhanced_prompt[:500]}...")

            # 添加风格限制
            style_hint = "口语化" if style == "casual" else "正式"
            enhanced_prompt += f"\n\n注意：请用{style_hint}口吻直接回答，不超过{max_length}字，不要解释知识来源，回复要基于对话上下文"
            if no_punctuation:
                enhanced_prompt += "，结尾不要带标点符号"
            enhanced_prompt += "。"

            # 创建新的 context 传递给基础 Bot
            enhanced_context = Context(
                type=context.type,
                content=json.dumps([{"type": "text", "text": enhanced_prompt}], ensure_ascii=False),
                kwargs=context.kwargs,
                channel_type=context.channel_type
            )

            self.logger.info(f"RAG 增强后的提示词长度: {len(enhanced_prompt)}")

            # 调用基础 Bot
            return self.base_bot.reply(enhanced_context)

        except Exception as e:
            self.logger.error(f"RAG 处理失败: {e}，回退到基础 Bot")
            # RAG 失败时回退到基础 Bot
            return self.base_bot.reply(context)

    def _format_chat_history(self, chat_history: list) -> str:
        """格式化对话历史为上下文字符串

        Args:
            chat_history: 消息记录列表

        Returns:
            str: 格式化后的对话上下文
        """
        if not chat_history:
            return ""

        context_parts = ["\n【对话上下文】"]

        for msg in chat_history:
            user_content = msg.get('user_content', '')
            ai_reply = msg.get('ai_reply', '')
            created_at = msg.get('created_at', '')

            # 只显示有内容的记录
            if user_content:
                # 截断过长的内容
                if len(user_content) > 50:
                    user_content = user_content[:47] + "..."
                context_parts.append(f"用户：{user_content}")

            if ai_reply:
                # 截断过长的回复
                if len(ai_reply) > 50:
                    ai_reply = ai_reply[:47] + "..."
                context_parts.append(f"客服：{ai_reply}")

        return "\n".join(context_parts)

    def get_knowledge_stats(self) -> dict:
        """获取知识库统计"""
        if self.rag_retriever:
            return self.rag_retriever.get_knowledge_stats()
        return {'enabled': False}
