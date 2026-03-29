"""
AI 学习优化面板 UI
提供学习信号统计、案例审核、相似案例检索等功能
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QSplitter,
    QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit,
    QComboBox, QHeaderView, QCheckBox, QGroupBox, QMessageBox
)
from PyQt6.QtGui import QFont, QIcon
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, InfoBar, InfoBarPosition,
    TitleLabel, SubtitleLabel, BodyLabel, StrongBodyLabel,
    IndeterminateProgressBar, SpinBox, SearchLineEdit,
    TeachingTip, TeachingTipTailPosition
)
from utils.logger import get_logger
from services.learning.similar_case_manager import SimilarCaseManager
from db.db_manager import db_manager
from datetime import datetime


class StatCard(CardWidget):
    """统计卡片组件"""

    def __init__(self, title: str, value: str = "0", color: str = "#0078D4", parent=None):
        super().__init__(parent)
        self.title_label = BodyLabel(title, self)
        self.value_label = TitleLabel(value, self)
        self.setup_ui(color)

    def setup_ui(self, color: str):
        """设置 UI 样式"""
        self.setFixedHeight(120)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {color}10;
                border: 1px solid {color}30;
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(8)

        self.value_label.setStyleSheet(f"""
            font-size: 36px;
            font-weight: bold;
            color: {color};
        """)

        self.title_label.setStyleSheet("""
            font-size: 14px;
            color: #666666;
        """)

        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str):
        """更新数值"""
        self.value_label.setText(str(value))


class PendingCaseItem(CardWidget):
    """待审核案例项组件"""

    review_requested = pyqtSignal(int)  # case_id
    approve_requested = pyqtSignal(int)  # case_id
    reject_requested = pyqtSignal(int)  # case_id

    def __init__(self, case_data: dict, parent=None):
        super().__init__(parent)
        self.case_id = case_data.get('id')
        self.case_data = case_data
        self.setup_ui()

    def setup_ui(self):
        """设置 UI"""
        self.setFixedHeight(180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # 标题栏
        title_layout = QHBoxLayout()
        category = self.case_data.get('category', 'general')
        title_label = StrongBodyLabel(f"[{category}] 待审核案例")
        time_label = BodyLabel(self.case_data.get('created_at', '')[:16])
        time_label.setStyleSheet("color: #999;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(time_label)
        layout.addLayout(title_layout)

        # 用户问题
        q_group = QGroupBox("用户问题")
        q_layout = QVBoxLayout(q_group)
        q_label = BodyLabel(self.case_data.get('user_question', ''))
        q_label.setWordWrap(True)
        q_layout.addWidget(q_label)
        layout.addWidget(q_group)

        # 回复对比
        reply_layout = QHBoxLayout()
        reply_layout.setSpacing(12)

        # AI 原始回复
        ai_group = QGroupBox("AI 回复")
        ai_layout = QVBoxLayout(ai_group)
        ai_label = BodyLabel(self.case_data.get('ai_original_reply', ''))
        ai_label.setWordWrap(True)
        ai_label.setStyleSheet("color: #666;")
        ai_layout.addWidget(ai_label)
        reply_layout.addWidget(ai_group, 1)

        # 人工优化回复
        human_group = QGroupBox("人工优化回复")
        human_layout = QVBoxLayout(human_group)
        human_label = BodyLabel(self.case_data.get('human_optimized_reply', ''))
        human_label.setWordWrap(True)
        human_label.setStyleSheet("color: #28a745;")
        human_layout.addWidget(human_label)
        reply_layout.addWidget(human_group, 1)

        layout.addLayout(reply_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.view_btn = PrimaryPushButton("查看", self)
        self.approve_btn = PrimaryPushButton("通过", self)
        self.reject_btn = QPushButton("拒绝", self)

        for btn in [self.view_btn, self.approve_btn, self.reject_btn]:
            btn.setFixedHeight(32)

        self.view_btn.clicked.connect(self._on_view)
        self.approve_btn.clicked.connect(self._on_approve)
        self.reject_btn.clicked.connect(self._on_reject)

        btn_layout.addWidget(self.view_btn)
        btn_layout.addWidget(self.approve_btn)
        btn_layout.addWidget(self.reject_btn)
        layout.addLayout(btn_layout)

    def _on_view(self):
        """查看详情"""
        self.review_requested.emit(self.case_id)

    def _on_approve(self):
        """通过案例"""
        self.approve_requested.emit(self.case_id)

    def _on_reject(self):
        """拒绝案例"""
        self.reject_requested.emit(self.case_id)


class AITestSearchWidget(CardWidget):
    """相似案例检索测试组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.case_manager = SimilarCaseManager()
        self.setup_ui()

    def setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        TitleLabel("相似案例检索测试", self).setStyleSheet("font-size: 18px;")

        # 输入框
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入问题:"))
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("请输入要测试的问题...")
        self.search_input.setFixedWidth(400)
        input_layout.addWidget(self.search_input)

        self.search_btn = PrimaryPushButton("测试检索", self)
        self.search_btn.clicked.connect(self._on_search)
        input_layout.addWidget(self.search_btn)
        input_layout.addStretch()
        layout.addLayout(input_layout)

        # 结果展示
        self.result_text = QTextEdit(self)
        self.result_text.setReadOnly(True)
        self.result_text.setMinimumHeight(200)
        self.result_text.setPlaceholderText("检索结果将显示在这里...")
        layout.addWidget(self.result_text)

    def _on_search(self):
        """执行检索"""
        question = self.search_input.text().strip()
        if not question:
            InfoBar.warning(
                title="提示",
                content="请输入问题内容",
                parent=self.window(),
                duration=2000
            )
            return

        self.result_text.setPlainText("正在检索...")

        # 执行检索
        results = self.case_manager.search_similar(question, top_k=5)

        if not results:
            self.result_text.setPlainText("未找到相似案例")
            return

        # 格式化输出
        output = f"找到 {len(results)} 个相似案例:\n\n"
        for i, r in enumerate(results, 1):
            case = r['case']
            similarity = r['similarity']
            output += f"{i}. [相似度 {similarity:.2f}] {case.user_question[:50]}...\n"
            output += f"   回复：{case.human_optimized_reply[:80]}...\n\n"

        self.result_text.setPlainText(output)


class AITestUI(QWidget):
    """AI 学习优化主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('AITestUI')
        self.case_manager = SimilarCaseManager()
        self.setup_ui()
        self.refresh_stats()

    def setup_ui(self):
        """设置 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 标题
        subtitle = SubtitleLabel("AI 学习优化")
        subtitle.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(subtitle)

        # 统计卡片区域
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(16)

        # 创建统计卡片
        self.human_edit_card = StatCard("人工修正", "0", "#0078D4")
        self.negative_card = StatCard("负反馈", "0", "#DC3545")
        self.positive_card = StatCard("好评强化", "0", "#28A745")
        self.cases_card = StatCard("已沉淀案例", "0", "#FFC107")

        for card in [self.human_edit_card, self.negative_card,
                     self.positive_card, self.cases_card]:
            stats_layout.addWidget(card)

        main_layout.addWidget(stats_container)

        # 刷新按钮
        self.refresh_btn = PrimaryPushButton("刷新统计", self)
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self.refresh_stats)
        main_layout.addWidget(self.refresh_btn)

        # 分割器：左侧待审核，右侧测试
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：待审核案例
        pending_group = QGroupBox("待审核案例")
        pending_layout = QVBoxLayout(pending_group)
        pending_layout.setSpacing(10)

        # 待审核案例列表
        self.pending_scroll = QScrollArea()
        self.pending_scroll.setWidgetResizable(True)
        self.pending_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.pending_container = QWidget()
        self.pending_layout = QVBoxLayout(self.pending_container)
        self.pending_layout.setSpacing(8)
        self.pending_layout.addStretch()
        self.pending_scroll.setWidget(self.pending_container)
        pending_layout.addWidget(self.pending_scroll)

        # 批量操作按钮
        bulk_layout = QHBoxLayout()
        bulk_layout.addStretch()
        self.approve_all_btn = PrimaryPushButton("批量通过", self)
        self.approve_all_btn.clicked.connect(self.approve_all_pending)
        bulk_layout.addWidget(self.approve_all_btn)
        pending_layout.addLayout(bulk_layout)

        splitter.addWidget(pending_group)

        # 右侧：检索测试
        test_widget = AITestSearchWidget()
        splitter.addWidget(test_widget)

        splitter.setSizes([400, 400])
        main_layout.addWidget(splitter, 1)

        self.setObjectName("AI 学习")

    def refresh_stats(self):
        """刷新统计数据"""
        try:
            # 获取案例统计
            stats = self.case_manager.get_statistics()

            # 更新卡片
            self.cases_card.set_value(str(stats.get('enabled', 0)))

            # 从数据库获取其他统计
            # 这里可以扩展为查询 FeedbackStats 等表
            self.human_edit_card.set_value(str(stats.get('pending', 0)))
            self.negative_card.set_value("0")
            self.positive_card.set_value("0")

            # 加载待审核案例
            self.load_pending_cases()

            InfoBar.success(
                title="成功",
                content="统计已更新",
                parent=self.window(),
                duration=1500
            )
        except Exception as e:
            self.logger.error(f"刷新统计失败：{e}")
            InfoBar.error(
                title="错误",
                content=f"刷新失败：{e}",
                parent=self.window(),
                duration=3000
            )

    def load_pending_cases(self):
        """加载待审核案例"""
        # 清空现有项
        while self.pending_layout.count() > 1:
            item = self.pending_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取待审核案例
        cases = db_manager.get_pending_similar_cases(limit=10)

        if not cases:
            no_data_label = BodyLabel("暂无待审核案例")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_data_label.setStyleSheet("padding: 40px; color: #999;")
            self.pending_layout.insertWidget(0, no_data_label)
            return

        # 添加案例项
        for case_data in cases:
            case_item = PendingCaseItem(case_data)
            case_item.review_requested.connect(self.show_case_detail)
            case_item.approve_requested.connect(self.approve_case)
            case_item.reject_requested.connect(self.reject_case)
            self.pending_layout.insertWidget(
                self.pending_layout.count() - 1,
                case_item
            )

    def show_case_detail(self, case_id: int):
        """显示案例详情"""
        case = self.case_manager.get_case_by_id(case_id)
        if not case:
            InfoBar.warning("提示", "案例不存在", parent=self.window(), duration=2000)
            return

        # 创建详情对话框
        detail_box = QMessageBox(self.window())
        detail_box.setWindowTitle("案例详情")
        detail_box.setText(f"案例 ID: {case_id}\n\n"
                          f"分类：{case.category}\n"
                          f"用户问题：{case.user_question}\n\n"
                          f"AI 回复：{case.ai_original_reply}\n\n"
                          f"人工优化：{case.human_optimized_reply}")
        detail_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        detail_box.exec()

    def approve_case(self, case_id: int):
        """通过案例"""
        try:
            success = db_manager.update_similar_case_status(
                case_id, status=1, reviewed_by="admin"
            )
            if success:
                InfoBar.success(
                    title="成功",
                    content="案例已通过并启用",
                    parent=self.window(),
                    duration=2000
                )
                self.refresh_stats()
            else:
                InfoBar.error("错误", "操作失败", parent=self.window(), duration=2000)
        except Exception as e:
            self.logger.error(f"通过案例失败：{e}")
            InfoBar.error("错误", str(e), parent=self.window(), duration=3000)

    def reject_case(self, case_id: int):
        """拒绝案例"""
        try:
            success = db_manager.update_similar_case_status(
                case_id, status=2, reviewed_by="admin"
            )
            if success:
                InfoBar.success(
                    title="成功",
                    content="案例已拒绝",
                    parent=self.window(),
                    duration=2000
                )
                self.refresh_stats()
            else:
                InfoBar.error("错误", "操作失败", parent=self.window(), duration=2000)
        except Exception as e:
            self.logger.error(f"拒绝案例失败：{e}")
            InfoBar.error("错误", str(e), parent=self.window(), duration=3000)

    def approve_all_pending(self):
        """批量通过待审核案例"""
        cases = db_manager.get_pending_similar_cases(limit=50)
        if not cases:
            InfoBar.warning("提示", "暂无待审核案例", parent=self.window(), duration=2000)
            return

        count = 0
        for case in cases:
            try:
                db_manager.update_similar_case_status(
                    case['id'], status=1, reviewed_by="admin"
                )
                count += 1
            except Exception as e:
                self.logger.error(f"通过案例 {case['id']} 失败：{e}")

        InfoBar.success(
            title="完成",
            content=f"已通过 {count}/{len(cases)} 个案例",
            parent=self.window(),
            duration=3000
        )
        self.refresh_stats()
