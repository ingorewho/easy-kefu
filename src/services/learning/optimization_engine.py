"""
优化引擎
负责处理和执行优化任务，将学习信号转化为实际的优化行动
"""

import uuid
import threading
import queue
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from db.db_manager import db_manager
from db.models import ChatMessage
from utils.logger import get_logger


@dataclass
class OptimizationTask:
    """优化任务"""
    task_id: str
    signal_type: str
    message_id: int
    priority: float
    status: str = "pending"  # pending/processing/completed/failed
    result: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None

    def __repr__(self):
        return f"<OptimizationTask(id={self.task_id}, type={self.signal_type}, status={self.status})>"


class OptimizationEngine:
    """优化引擎 - 负责处理和执行优化任务"""

    def __init__(self, auto_process: bool = False):
        self.logger = get_logger("OptimizationEngine")
        self.task_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.processed_ids: set = set()  # 避免重复处理
        self.auto_process = auto_process
        self._processing = False
        self._worker_thread: Optional[threading.Thread] = None

        # 问题分类关键词
        self.category_keywords = {
            "price": ["价格", "多少钱", "优惠", "折扣", "便宜", "贵", "费用", "价位"],
            "shipping": ["发货", "快递", "物流", "配送", "邮费", "运费", "几天到"],
            "product_effect": ["功效", "作用", "效果", "怎么用", "使用方法", "成分"],
            "after_sales": ["售后", "退换", "保修", "维修", "客服", "投诉"],
            "product_info": ["规格", "容量", "重量", "尺寸", "颜色", "款式", "型号"]
        }

        if auto_process:
            self.start_background_processor()

    def start_background_processor(self, batch_size: int = 10):
        """启动后台处理线程"""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._processing = True
            self._worker_thread = threading.Thread(
                target=self._process_loop,
                args=(batch_size,),
                daemon=True
            )
            self._worker_thread.start()
            self.logger.info("优化引擎后台处理线程已启动")

    def stop_background_processor(self):
        """停止后台处理线程"""
        self._processing = False
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            self.logger.info("优化引擎后台处理线程已停止")

    def _process_loop(self, batch_size: int):
        """后台处理循环"""
        while self._processing:
            try:
                # 从优先级队列获取任务
                priority, task = self.task_queue.get(timeout=1)
                if task.message_id in self.processed_ids:
                    continue
                self._execute_task(task)
                self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"处理任务失败：{e}")

    def add_task(
        self,
        signal_type: str,
        message_id: int,
        priority: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OptimizationTask:
        """
        添加优化任务到队列

        Args:
            signal_type: 信号类型
            message_id: 消息 ID
            priority: 优先级 (0-1，越高越优先)
            metadata: 附加元数据

        Returns:
            OptimizationTask 对象
        """
        # 检查是否已处理过
        if message_id in self.processed_ids:
            self.logger.debug(f"消息 {message_id} 已处理过，跳过")
            return None

        task = OptimizationTask(
            task_id=str(uuid.uuid4()),
            signal_type=signal_type,
            message_id=message_id,
            priority=priority,
            metadata=metadata or {}
        )

        # 使用负优先级实现高优先级先处理（优先队列是最小堆）
        self.task_queue.put((-priority, task))
        self.logger.info(
            f"添加优化任务：task_id={task.task_id}, "
            f"type={signal_type}, priority={priority}"
        )

        return task

    def process_task(self, task: OptimizationTask) -> bool:
        """处理单个任务"""
        if task.message_id in self.processed_ids:
            return False

        try:
            task.status = "processing"
            self._execute_task(task)
            task.status = "completed"
            self.processed_ids.add(task.message_id)
            task.processed_at = datetime.now()
            return True
        except Exception as e:
            task.status = "failed"
            task.result = str(e)
            self.logger.error(f"处理任务失败：{e}")
            return False

    def process_queue(self, batch_size: int = 10):
        """批量处理优化任务"""
        tasks_processed = 0
        temp_tasks = []

        # 从队列取出任务
        while not self.task_queue.empty() and tasks_processed < batch_size:
            try:
                priority, task = self.task_queue.get_nowait()
                temp_tasks.append((priority, task))
            except queue.Empty:
                break

        # 处理任务
        for priority, task in temp_tasks:
            if task.message_id in self.processed_ids:
                continue

            success = self.process_task(task)
            if success:
                tasks_processed += 1
            else:
                # 处理失败的任务放回队列
                self.task_queue.put((priority, task))

        self.logger.info(f"批量处理完成：处理 {tasks_processed} 个任务")

    def _execute_task(self, task: OptimizationTask):
        """执行单个优化任务"""
        if task.signal_type == "human_edit":
            self._process_human_edit(task)
        elif task.signal_type == "negative_feedback":
            self._process_negative_feedback(task)
        elif task.signal_type == "positive_feedback":
            self._process_positive_feedback(task)
        elif task.signal_type == "low_confidence":
            self._process_low_confidence(task)
        else:
            self.logger.warning(f"未知任务类型：{task.signal_type}")

    def _process_human_edit(self, task: OptimizationTask):
        """处理人工修正任务"""
        from .similar_case_manager import SimilarCaseManager

        # 获取消息记录
        msg_data = db_manager.get_chat_message(task.message_id)
        if not msg_data:
            raise ValueError(f"Message {task.message_id} not found")

        # 提取人工优化内容
        human_edited_reply = msg_data.get("human_edited_reply")
        if not human_edited_reply:
            raise ValueError("No human edited reply found")

        user_question = msg_data.get("user_content", "")
        ai_reply = msg_data.get("ai_reply", "")
        account_id = msg_data.get("account_id")

        # 添加到相似案例库
        case_manager = SimilarCaseManager()
        category = self._auto_classify(user_question)
        case_id = case_manager.add_case(
            account_id=account_id,
            user_question=user_question,
            ai_reply=ai_reply,
            human_reply=human_edited_reply,
            category=category
        )

        if case_id > 0:
            task.result = f"Added to similar cases: {case_id}"
            self.logger.info(f"人工修正已沉淀为案例：case_id={case_id}")

            # 更新消息标记为优化样本
            db_manager.update_message_optimization_flag(
                task.message_id,
                is_sample=1,
                opt_type="human_edit"
            )
        else:
            raise ValueError("Failed to add case")

    def _process_negative_feedback(self, task: OptimizationTask):
        """处理负反馈任务"""
        # 获取消息记录
        msg_data = db_manager.get_chat_message(task.message_id)
        if not msg_data:
            raise ValueError(f"Message {task.message_id} not found")

        reason = task.metadata.get("reason", "unknown")
        self.logger.warning(
            f"负反馈记录：message_id={task.message_id}, "
            f"reason={reason}, user_question={msg_data.get('user_content', '')}"
        )

        # 标记为优化样本
        db_manager.update_message_optimization_flag(
            task.message_id,
            is_sample=1,
            opt_type="negative_feedback"
        )

        task.result = f"Negative feedback logged: {reason}"

    def _process_positive_feedback(self, task: OptimizationTask):
        """处理正面评价任务"""
        msg_data = db_manager.get_chat_message(task.message_id)
        if not msg_data:
            raise ValueError(f"Message {task.message_id} not found")

        satisfaction = task.metadata.get("satisfaction_score", 5)
        self.logger.info(
            f"正面评价：message_id={task.message_id}, "
            f"satisfaction={satisfaction}"
        )

        # 标记为优化样本
        db_manager.update_message_optimization_flag(
            task.message_id,
            is_sample=1,
            opt_type="high_score"
        )

        task.result = f"Positive feedback logged: {satisfaction} stars"

    def _process_low_confidence(self, task: OptimizationTask):
        """处理低置信度任务"""
        msg_data = db_manager.get_chat_message(task.message_id)
        if not msg_data:
            raise ValueError(f"Message {task.message_id} not found")

        confidence = task.metadata.get("confidence", 0)
        self.logger.warning(
            f"低置信度回复：message_id={task.message_id}, "
            f"confidence={confidence}"
        )

        # 标记为需要优化
        db_manager.update_message_optimization_flag(
            task.message_id,
            is_sample=1,
            opt_type="low_confidence"
        )

        task.result = f"Low confidence logged: {confidence}"

    def _auto_classify(self, question: str) -> str:
        """
        自动分类问题

        Args:
            question: 用户问题

        Returns:
            分类名称
        """
        if not question:
            return "general"

        question_lower = question.lower()

        for category, keywords in self.category_keywords.items():
            if any(kw in question for kw in keywords):
                return category

        return "general"

    def get_task_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        return {
            "queue_size": self.task_queue.qsize(),
            "processed_count": len(self.processed_ids),
            "is_processing": self._processing
        }
