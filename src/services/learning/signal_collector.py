"""
学习信号收集器
负责收集各类 AI 回复质量相关的学习信号，包括人工修正、负反馈、正面评价等
"""

from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime
from utils.logger import get_logger


class SignalType(Enum):
    """学习信号类型"""
    HUMAN_EDIT = "human_edit"           # 人工修正
    NEGATIVE_FEEDBACK = "negative"      # 负反馈（转人工/投诉）
    POSITIVE_FEEDBACK = "positive"      # 正面评价（4-5 星）
    LOW_CONFIDENCE = "low_confidence"   # 低置信度回复
    TIMEOUT = "timeout"                 # 回复超时


class LearningSignal:
    """学习信号数据类"""

    def __init__(
        self,
        signal_type: SignalType,
        message_id: int,
        priority: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.signal_type = signal_type
        self.message_id = message_id
        self.priority = priority  # 优化优先级 0-1
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    def __repr__(self):
        return f"<LearningSignal(type={self.signal_type.value}, message_id={self.message_id}, priority={self.priority})>"


class LearningSignalCollector:
    """学习信号收集器"""

    def __init__(self):
        self.logger = get_logger("LearningSignalCollector")
        # 信号处理优先级配置
        self.priority_config = {
            SignalType.NEGATIVE_FEEDBACK: 0.9,   # 负反馈最高优先级
            SignalType.HUMAN_EDIT: 0.8,          # 人工修正高优先级
            SignalType.POSITIVE_FEEDBACK: 0.5,   # 正面评价用于强化
            SignalType.LOW_CONFIDENCE: 0.6,      # 低置信度需要优化
            SignalType.TIMEOUT: 0.4              # 超时优化响应速度
        }

    def collect(
        self,
        signal_type: SignalType,
        message_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LearningSignal:
        """
        收集学习信号

        Args:
            signal_type: 信号类型
            message_id: 消息 ID
            metadata: 附加元数据

        Returns:
            LearningSignal 对象
        """
        signal = LearningSignal(
            signal_type=signal_type,
            message_id=message_id,
            priority=self.priority_config.get(signal_type, 0.5),
            metadata=metadata
        )

        self.logger.info(
            f"收集学习信号：type={signal_type.value}, "
            f"message_id={message_id}, priority={signal.priority}"
        )

        return signal

    def collect_human_edit(
        self,
        message_id: int,
        original: str,
        edited: str
    ) -> LearningSignal:
        """收集人工修正信号"""
        diff = self._compute_diff(original, edited)

        return self.collect(
            signal_type=SignalType.HUMAN_EDIT,
            message_id=message_id,
            metadata={
                "original": original,
                "edited": edited,
                "diff": diff,
                "edit_length": len(edited) - len(original)
            }
        )

    def collect_negative_feedback(
        self,
        message_id: int,
        reason: str
    ) -> LearningSignal:
        """收集负反馈信号（转人工/投诉）"""
        return self.collect(
            signal_type=SignalType.NEGATIVE_FEEDBACK,
            message_id=message_id,
            metadata={"reason": reason}
        )

    def collect_positive_feedback(
        self,
        message_id: int,
        satisfaction_score: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LearningSignal:
        """收集正面评价信号"""
        meta = metadata or {}
        meta["satisfaction_score"] = satisfaction_score
        return self.collect(
            signal_type=SignalType.POSITIVE_FEEDBACK,
            message_id=message_id,
            metadata=meta
        )

    def collect_low_confidence(
        self,
        message_id: int,
        confidence: float
    ) -> LearningSignal:
        """收集低置信度信号"""
        return self.collect(
            signal_type=SignalType.LOW_CONFIDENCE,
            message_id=message_id,
            metadata={"confidence": confidence}
        )

    def collect_timeout(
        self,
        message_id: int,
        timeout_seconds: float
    ) -> LearningSignal:
        """收集超时信号"""
        return self.collect(
            signal_type=SignalType.TIMEOUT,
            message_id=message_id,
            metadata={"timeout_seconds": timeout_seconds}
        )

    def _compute_diff(self, original: str, edited: str) -> Dict[str, Any]:
        """计算文本差异"""
        # 使用 difflib 计算详细差异
        import difflib

        original_lines = original.splitlines(keepends=True)
        edited_lines = edited.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            original_lines,
            edited_lines,
            lineterm='',
            n=0
        ))

        return {
            "original_len": len(original),
            "edited_len": len(edited),
            "is_shorter": len(edited) < len(original),
            "diff_lines": len(diff),
            "diff_preview": ''.join(diff[:10])  # 前 10 行差异预览
        }
