"""
AI 学习优化模块
提供学习信号收集、优化引擎、相似案例管理等功能
"""

from .signal_collector import LearningSignalCollector, SignalType, LearningSignal
from .optimization_engine import OptimizationEngine, OptimizationTask
from .similar_case_manager import SimilarCaseManager

__all__ = [
    'LearningSignalCollector',
    'SignalType',
    'LearningSignal',
    'OptimizationEngine',
    'OptimizationTask',
    'SimilarCaseManager'
]
