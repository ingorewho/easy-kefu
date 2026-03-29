#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
情绪分析模块 - 混合方案：本地规则初筛 + AI 深度分析

功能：
1. 基于中文情绪词库的快速筛选
2. 可选 AI 深度分析（复用现有 Bot 接口）
3. 返回情绪分数 (-1.0 到 1.0)

情绪分数说明：
- > 0.3: 正面情绪
- -0.3 ~ 0.3: 中性
- < -0.3: 负面情绪（需要关注）
- < -0.6: 强烈负面情绪（触发告警）
"""

import re
from typing import NamedTuple
from dataclasses import dataclass
from utils.logger import get_logger

logger = get_logger("EmotionAnalyzer")


@dataclass
class EmotionResult:
    """情绪分析结果"""
    score: float           # 情绪分数 (-1.0 ~ 1.0)
    level: str            # 情绪等级 (positive/neutral/negative/very_negative)
    keywords: list        # 检测到的情绪关键词
    is_negative: bool     # 是否为负面情绪
    should_alert: bool    # 是否应该触发告警

    @staticmethod
    def from_score(score: float, keywords: list = None, threshold: float = -0.6) -> 'EmotionResult':
        """根据分数创建结果"""
        if score > 0.3:
            level = "positive"
        elif score >= -0.3:
            level = "neutral"
        elif score >= threshold:
            level = "negative"
        else:
            level = "very_negative"

        return EmotionResult(
            score=score,
            level=level,
            keywords=keywords or [],
            is_negative=score < -0.3,
            should_alert=score < threshold
        )


# ==================== 情绪词库 ====================

# 负面情绪词库（愤怒、失望、投诉、辱骂等）
NEGATIVE_WORDS = {
    # 愤怒类
    '生气', '愤怒', '火大', '气死', '恼火', '发火', '恼怒', '愤恨',
    '混蛋', '垃圾', '废物', '骗局', '骗子', '坑人', '黑店', '破店',

    # 失望类
    '失望', '无语', '呵呵', '算了', '无语', '无奈', '心累', '崩溃',
    '差劲', '不好', '不行', '太差', '极差', '垃圾', '烂', '破',

    # 投诉类
    '投诉', '举报', '曝光', '维权', '315', '消协', '平台投诉',
    '差评', '给差评', '必须差评', '一星', '0 星',

    # 不满类
    '不满', '生气', '气愤', '恼火', '不爽', '恶心', '恶心人',
    '忽悠', '欺诈', '虚假', '骗人', '假一赔十', '假货', '伪劣',

    # 催促类
    '太慢了', '慢死了', '还没到', '什么时候到', '到底多久', '等的着急',

    # 威胁类
    '等着', '你们等着', '给我等着', '不会放过', '没完', '走着瞧',

    # 否定类
    '再也不', '不会再', '永久拉黑', '永不', '别想', '休想',
}

# 程度副词（增强情绪强度）
DEGREE_ADVERBS = {
    '非常': 1.5, '特别': 1.5, '极其': 1.8, '太': 1.3,
    '很': 1.2, '十分': 1.3, '格外': 1.4, '分外': 1.3,
    '超级': 1.6, '巨': 1.4, '死': 1.5, '要命': 1.5,
    '真的': 1.2, '确实': 1.2, '简直': 1.4,
}

# 否定词（反转情绪）
NEGATION_WORDS = {'不', '没', '别', '不要', '没有', '未', '勿', '非'}


class EmotionAnalyzer:
    """情绪分析器"""

    _instance = None
    _ai_bot = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.logger = get_logger("EmotionAnalyzer")
        self._ai_bot = None
        self._ai_threshold = -0.4  # 使用 AI 分析的阈值（初步检测为负面的再调用 AI）

    def analyze(self, text: str, use_ai: bool = True, threshold: float = -0.6) -> EmotionResult:
        """
        分析文本情绪

        Args:
            text: 待分析的文本
            use_ai: 是否使用 AI 深度分析（当初步检测为负面时）
            threshold: 告警阈值

        Returns:
            EmotionResult: 情绪分析结果
        """
        if not text or not text.strip():
            return EmotionResult.from_score(0.0, [], threshold)

        # Step 1: 本地规则分析
        score, keywords = self._analyze_local(text)

        self.logger.debug(f"本地分析结果：score={score}, keywords={keywords}")

        # Step 2: 如果初步检测为负面且启用 AI，进行深度分析
        if use_ai and score < self._ai_threshold and self._ai_bot:
            try:
                ai_score = self._analyze_ai(text)
                self.logger.debug(f"AI 分析结果：score={ai_score}")
                # 综合本地和 AI 结果（AI 权重更高）
                score = 0.3 * score + 0.7 * ai_score
            except Exception as e:
                self.logger.warning(f"AI 情绪分析失败，使用本地结果：{e}")

        return EmotionResult.from_score(score, keywords, threshold)

    def _analyze_local(self, text: str) -> tuple:
        """
        本地规则分析

        Returns:
            (score, keywords): 情绪分数和关键词列表
        """
        score = 0.0
        keywords = []

        # 检测负面情绪词
        for word in NEGATIVE_WORDS:
            if word in text:
                keywords.append(word)
                score -= 0.15  # 基础负面分数

        if not keywords:
            return 0.0, []

        # 去重
        keywords = list(set(keywords))

        # 程度副词增强
        for adverb, multiplier in DEGREE_ADVERBS.items():
            if adverb in text:
                score *= multiplier
                if adverb not in keywords:
                    keywords.append(adverb)

        # 否定词处理（简化版：如果有否定词，减少负面程度）
        has_negation = any(neg in text for neg in NEGATION_WORDS)
        if has_negation:
            # 否定词可能反转语义，但在这里我们保守处理
            # 因为 "不生气" 这种表达在客服场景中较少，更多是 "不解决" 这类负面表达
            score *= 0.8

        # 限制分数范围
        score = max(-1.0, min(1.0, score))

        # 多个负面词叠加
        if len(keywords) > 1:
            score *= (1 + 0.2 * (len(keywords) - 1))
            score = max(-1.0, min(1.0, score))

        return score, keywords

    def _analyze_ai(self, text: str) -> float:
        """
        AI 深度分析情绪

        Returns:
            float: 情绪分数 (-1.0 ~ 1.0)
        """
        if not self._ai_bot:
            return -0.5  # 默认负面

        try:
            # 构建情绪分析提示词
            prompt = f"""请分析以下用户消息的情绪，返回 -1.0 到 1.0 之间的情绪分数：
- 1.0 表示非常开心/满意
- 0 表示中性
- -1.0 表示非常愤怒/失望

用户消息：{text}

只返回一个数字，不要解释。"""

            from core.bridge.context import Context, ContextType, ChannelType

            context = Context(
                type=ContextType.TEXT,
                content=prompt,
                kwargs={},
                channel_type=ChannelType.PINDUODUO
            )

            reply = self._ai_bot.reply(context)

            # 解析 AI 返回的分数
            if reply and reply.content:
                # 提取数字
                import re
                match = re.search(r'-?[\d.]+', str(reply.content))
                if match:
                    score = float(match.group())
                    return max(-1.0, min(1.0, score))

            return -0.5

        except Exception as e:
            self.logger.error(f"AI 情绪分析异常：{e}")
            return -0.5

    def set_ai_bot(self, bot):
        """设置 AI Bot 用于深度分析"""
        self._ai_bot = bot
        self.logger.info(f"已设置 AI Bot: {bot.__class__.__name__ if bot else 'None'}")

    @staticmethod
    def quick_check(text: str) -> bool:
        """
        快速检查是否包含负面情绪词

        Returns:
            bool: 是否包含负面情绪
        """
        if not text:
            return False
        return any(word in text for word in NEGATIVE_WORDS)


# 全局分析器实例
_analyzer = None

def get_analyzer() -> EmotionAnalyzer:
    """获取情绪分析器单例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = EmotionAnalyzer()
    return _analyzer


def analyze_emotion(text: str, use_ai: bool = True, threshold: float = -0.6) -> EmotionResult:
    """便捷函数：分析文本情绪"""
    return get_analyzer().analyze(text, use_ai, threshold)


def quick_negative_check(text: str) -> bool:
    """便捷函数：快速检查负面情绪"""
    return EmotionAnalyzer.quick_check(text)
