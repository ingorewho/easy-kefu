"""
非工作时间消息队列管理器
用于在非工作时间缓存消息，工作时间恢复后逐一处理
"""
import asyncio
from datetime import datetime, time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

from utils.logger import get_logger
from config import config


@dataclass
class QueuedMessage:
  """队列中的消息"""
  msg_id: str
  context: Any  # Context 对象
  queue_name: str
  shop_id: str
  user_id: str
  username: str
  from_uid: str
  nickname: str
  timestamp: float
  added_at: datetime = field(default_factory=datetime.now)


class BusinessHoursQueueManager:
  """
  非工作时间消息队列管理器

  功能：
  1. 在非工作时间缓存消息（不处理、不回复、不打开会话）
  2. 定时检查工作时间状态
  3. 进入工作时间后，逐一处理队列中的消息
  """

  _instance = None

  def __new__(cls, *args, **kwargs):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance._initialized = False
    return cls._instance

  def __init__(self, check_interval: int = 60):
    if self._initialized:
      return

    self.logger = get_logger("BusinessHoursQueue")
    self.message_queue: List[QueuedMessage] = []
    self.check_interval = check_interval  # 检查间隔（秒）
    self._running = False
    self._task: Optional[asyncio.Task] = None
    self._lock = asyncio.Lock()

    # 处理回调函数
    self._processor_callback: Optional[Callable] = None

    self._initialized = True
    self.logger.info("非工作时间消息队列管理器已初始化")

  def register_processor(self, callback: Callable):
    """
    注册消息处理器回调

    Args:
      callback: 处理函数，接收 QueuedMessage 参数
    """
    self._processor_callback = callback
    self.logger.info("已注册消息处理器回调")

  def _is_business_hours(self) -> bool:
    """检查当前是否在工作时间"""
    try:
      business_hours = config.get("businessHours", {"start": "08:00", "end": "23:00"})
      start_time_str = business_hours.get("start", "08:00")
      end_time_str = business_hours.get("end", "23:00")

      now = datetime.now().time()
      start_time = datetime.strptime(start_time_str, "%H:%M").time()
      end_time = datetime.strptime(end_time_str, "%H:%M").time()

      return start_time <= now <= end_time
    except Exception as e:
      self.logger.error(f"检查工作时间失败: {e}")
      return True  # 出错时默认在工作时间

  async def add_message(self, msg: QueuedMessage) -> bool:
    """
    添加消息到队列

    Args:
      msg: 要缓存的消息

    Returns:
      bool: 是否添加成功
    """
    async with self._lock:
      self.message_queue.append(msg)
      self.logger.info(
        f"消息已加入非工作时间队列: "
        f"msg_id={msg.msg_id}, user={msg.nickname}, "
        f"queue_size={len(self.message_queue)}"
      )
      return True

  async def get_queue_size(self) -> int:
    """获取队列大小"""
    async with self._lock:
      return len(self.message_queue)

  async def clear_queue(self):
    """清空队列"""
    async with self._lock:
      count = len(self.message_queue)
      self.message_queue.clear()
      self.logger.info(f"已清空非工作时间队列，共 {count} 条消息")

  async def start(self):
    """启动队列管理器"""
    if self._running:
      self.logger.warning("队列管理器已在运行")
      return

    self._running = True
    self._task = asyncio.create_task(self._monitor_loop())
    self.logger.info("非工作时间队列管理器已启动")

  async def stop(self):
    """停止队列管理器"""
    self._running = False

    if self._task and not self._task.done():
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass

    self.logger.info("非工作时间队列管理器已停止")

  async def _monitor_loop(self):
    """监控循环 - 检查工作时间并处理队列"""
    self.logger.info("开始监控工作时间状态")

    last_state = None  # None=未知, True=工作时间, False=非工作时间

    try:
      while self._running:
        current_state = self._is_business_hours()

        # 状态变化时记录日志
        if current_state != last_state:
          if current_state:
            self.logger.info("⏰ 进入工作时间，开始处理队列消息")
            await self._process_queue()
          else:
            self.logger.info("⏰ 进入非工作时间，新消息将被缓存")
          last_state = current_state
        elif current_state and self.message_queue:
          # 工作时间且队列中有消息，继续处理
          await self._process_queue()

        await asyncio.sleep(self.check_interval)

    except asyncio.CancelledError:
      self.logger.info("监控循环已取消")
    except Exception as e:
      self.logger.error(f"监控循环异常: {e}")

  async def _process_queue(self):
    """处理队列中的消息"""
    if not self._processor_callback:
      self.logger.warning("未注册消息处理器，无法处理队列消息")
      return

    processed = 0
    failed = 0

    while True:
      async with self._lock:
        if not self.message_queue:
          break
        msg = self.message_queue.pop(0)

      try:
        self.logger.info(
          f"处理队列消息: msg_id={msg.msg_id}, "
          f"user={msg.nickname}, "
          f"queued_at={msg.added_at.strftime('%H:%M:%S')}"
        )

        await self._processor_callback(msg)
        processed += 1

        # 每条消息处理后短暂延迟，避免过快
        await asyncio.sleep(0.5)

      except Exception as e:
        self.logger.error(f"处理队列消息失败: {e}")
        failed += 1

        # 失败的消息放回队列末尾，稍后重试
        async with self._lock:
          self.message_queue.append(msg)

        # 避免连续失败，暂停一下
        await asyncio.sleep(1)

    if processed > 0 or failed > 0:
      self.logger.info(f"队列处理完成: 成功={processed}, 失败={failed}, 剩余={len(self.message_queue)}")


# 全局队列管理器实例
business_hours_queue = BusinessHoursQueueManager()


def is_business_hours() -> bool:
  """检查当前是否在工作时间的便捷函数"""
  return business_hours_queue._is_business_hours()
