"""筛选面板组件"""
from datetime import datetime, timedelta
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QHBoxLayout
from qfluentwidgets import (
    CardWidget, ComboBox, DateEdit, LineEdit,
    PrimaryPushButton, PushButton, FluentIcon as FIF,
    SegmentedWidget
)

from .service import ChatHistoryService
from .models import FilterParams, MessageStatus
from utils.logger import get_logger


class FilterPanel(CardWidget):
    """筛选面板 - 带账号Tab切换"""

    query_requested = pyqtSignal(FilterParams)
    export_requested = pyqtSignal(FilterParams)
    account_changed = pyqtSignal(int)  # 切换账号时发出账号ID，-1表示全部

    def __init__(self, service: ChatHistoryService, parent=None):
        super().__init__(parent)
        self.logger = get_logger('FilterPanel')
        self.service = service
        self._account_map = {}  # tab_id -> account_id
        self._current_account_id = -1  # -1表示全部
        self._setup_ui()
        self._load_accounts()

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # 标题
        from qfluentwidgets import StrongBodyLabel
        from PyQt6.QtGui import QFont
        title = StrongBodyLabel("筛选条件")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title)

        # 账号Tab栏
        layout.addWidget(QLabel("选择账号:"))
        self.account_tabs = SegmentedWidget()
        self.account_tabs.setFixedHeight(36)
        self.account_tabs.currentItemChanged.connect(self._on_tab_changed_by_key)
        layout.addWidget(self.account_tabs)

        # 日期范围
        date_layout = QHBoxLayout()
        self.date_start = DateEdit()
        self.date_start.setDate(datetime.now() - timedelta(days=7))
        self.date_end = DateEdit()
        self.date_end.setDate(datetime.now())
        date_layout.addWidget(QLabel("开始:"))
        date_layout.addWidget(self.date_start)
        date_layout.addWidget(QLabel("结束:"))
        date_layout.addWidget(self.date_end)
        layout.addLayout(date_layout)

        # 关键词搜索
        self.keyword_input = LineEdit()
        self.keyword_input.setPlaceholderText("搜索消息内容...")
        layout.addWidget(self.keyword_input)

        # 状态筛选
        self.status_combo = ComboBox()
        self.status_combo.addItem("全部", None)
        self.status_combo.addItem("未回复", MessageStatus.PENDING)
        self.status_combo.addItem("已回复", MessageStatus.REPLIED)
        self.status_combo.addItem("转人工", MessageStatus.TRANSFERRED)
        self.status_combo.addItem("失败", MessageStatus.FAILED)
        layout.addWidget(QLabel("状态:"))
        layout.addWidget(self.status_combo)

        # 查询和导出按钮
        btn_layout = QHBoxLayout()
        self.query_btn = PrimaryPushButton("查询")
        self.query_btn.setIcon(FIF.SEARCH)
        self.query_btn.clicked.connect(self._on_query)
        btn_layout.addWidget(self.query_btn)

        self.export_btn = PushButton("导出")
        self.export_btn.setIcon(FIF.SAVE)
        self.export_btn.clicked.connect(self._on_export)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _load_accounts(self):
        """加载账号到Tab栏"""
        # 添加"全部"Tab
        self.account_tabs.addItem("all", "全部")
        self._account_map["all"] = -1

        try:
            accounts = self.service.get_accounts()
            self.logger.info(f'加载到 {len(accounts)} 个账号')
            for i, acc in enumerate(accounts):
                tab_id = f"acc_{acc.id}"
                # 显示用户名+店铺名，如果太长截断
                text = f"{acc.username}"
                if len(text) > 8:
                    text = text[:7] + "..."

                self.logger.info(f'创建Tab: tab_id={tab_id}, text={text}, account_id={acc.id}')
                self.account_tabs.addItem(tab_id, text)
                self._account_map[tab_id] = acc.id

                # 设置tooltip显示完整信息
                self.account_tabs.setToolTip(f"{acc.username} | {acc.shop_name}")

        except Exception as e:
            self.logger.error(f'加载账号失败: {e}', exc_info=True)

        # 默认选中"全部"
        self.account_tabs.setCurrentItem("all")

    def _on_tab_changed_by_key(self, tab_key: str):
        """Tab切换信号回调 - 通过tab key查找account_id"""
        account_id = self._account_map.get(tab_key, -1)
        self.logger.info(f'Tab切换: tab_key={tab_key}, account_id={account_id}')
        self._current_account_id = account_id
        self.account_changed.emit(account_id)
        # 自动触发查询
        self._on_query()

    def _on_tab_changed(self, account_id: int):
        """Tab切换回调（兼容旧代码）"""
        self.logger.info(f'Tab切换: account_id={account_id}')
        self._current_account_id = account_id
        self.account_changed.emit(account_id)
        # 自动触发查询
        self._on_query()

    def _on_query(self):
        """查询按钮点击"""
        filters = self._build_filters()
        self.query_requested.emit(filters)

    def _on_export(self):
        """导出按钮点击"""
        filters = self._build_filters()
        self.export_requested.emit(filters)

    def _build_filters(self) -> FilterParams:
        """构建筛选参数"""
        status_data = self.status_combo.currentData()
        account_id = self._current_account_id if self._current_account_id != -1 else None

        return FilterParams(
            account_id=account_id,
            start_time=self.date_start.date().toPyDate(),
            end_time=self.date_end.date().toPyDate(),
            keyword=self.keyword_input.text() or None,
            status=status_data,
            page=1,
            page_size=100
        )

    def get_filters(self) -> FilterParams:
        """获取当前筛选条件"""
        return self._build_filters()

    def get_current_account_id(self) -> int:
        """获取当前选中的账号ID"""
        return self._current_account_id
