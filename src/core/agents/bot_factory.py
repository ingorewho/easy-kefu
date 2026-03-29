"""
channel factory
"""
from config import config


def create_bot(bot_type: str = None, enable_rag: bool = None):
    """
    创建一个bot实例

    Args:
        bot_type: bot类型，如果不指定则从配置中读取
        enable_rag: 是否启用 RAG 知识库，None 则从配置读取

    :return: bot实例
    """
    bot_type = bot_type or config.get("bot_type", "coze")

    # RAG 配置
    if enable_rag is None:
        enable_rag = config.get("enable_rag", False)

    # 创建基础 Bot
    if bot_type == "coze":
        from core.agents.CozeAgent.bot import CozeBot
        base_bot = CozeBot()
    elif bot_type == "kimi":
        from core.agents.KimiAgent.bot import KimiBot
        base_bot = KimiBot()
    elif bot_type == "qwen":
        from core.agents.QwenAgent.bot import QwenBot
        base_bot = QwenBot()
    else:
        raise RuntimeError(f"Invalid bot type: {bot_type}")

    # 如果需要 RAG，包装基础 Bot
    if enable_rag:
        from core.agents.bot_with_rag import BotWithRAG
        return BotWithRAG(base_bot, enable_rag=True)

    return base_bot