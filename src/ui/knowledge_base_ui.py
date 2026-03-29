"""知识库管理界面"""
import os
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFrame, QHBoxLayout, QVBoxLayout, QWidget, QLabel,
                            QFileDialog, QTreeWidget, QTreeWidgetItem, QHeaderView,
                            QAbstractItemView, QTextEdit, QMenu, QSplitter)
from PyQt6.QtGui import QFont
from qfluentwidgets import (CardWidget, SubtitleLabel, CaptionLabel, StrongBodyLabel,
                           PrimaryPushButton, PushButton, LineEdit, ComboBox,
                           ScrollArea, FluentIcon as FIF, InfoBar, InfoBarPosition,
                           TextEdit, SwitchButton, MessageBoxBase, RadioButton)
from services.knowledge.vector_store import VectorStoreManager
from services.knowledge.document_processor import DocumentProcessor
from services.knowledge.rag_retriever import RAGRetriever
from config import config
from utils.logger import get_logger


class KnowledgeBaseUI(QFrame):
    """知识库管理界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger("KnowledgeBaseUI")
        self.vector_store = VectorStoreManager()
        self.doc_processor = DocumentProcessor()
        self.setupUI()
        self.loadRootDocuments()
        self.setObjectName("知识库")

    def setupUI(self):
        """设置主界面UI"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 左侧: 控制面板
        self.control_panel = self._create_control_panel()
        main_layout.addWidget(self.control_panel, 0)

        # 中间: 文档树列表
        self.doc_tree = self._create_doc_tree()
        main_layout.addWidget(self.doc_tree, 1)

        # 右侧: 预览区域
        self.preview_panel = self._create_preview_panel()
        main_layout.addWidget(self.preview_panel, 1)

    def _create_control_panel(self):
        """创建控制面板"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # 标题
        title_label = StrongBodyLabel("知识库管理")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 统计信息
        self.stats_label = CaptionLabel("文档数量: 0")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

        # RAG 开关
        rag_layout = QHBoxLayout()
        rag_layout.addWidget(QLabel("启用 RAG:"))
        self.rag_switch = SwitchButton()
        self.rag_switch.setChecked(config.get("enable_rag", False))
        self.rag_switch.checkedChanged.connect(self.onRAGToggled)
        rag_layout.addWidget(self.rag_switch)
        rag_layout.addStretch()
        layout.addLayout(rag_layout)

        # Web 搜索回退开关
        web_layout = QHBoxLayout()
        web_layout.addWidget(QLabel("智能搜索:"))
        self.web_switch = SwitchButton()
        self.web_switch.setChecked(config.get("enable_web_search_fallback", True))
        self.web_switch.checkedChanged.connect(self.onWebSearchToggled)
        web_layout.addWidget(self.web_switch)
        web_layout.addStretch()
        layout.addLayout(web_layout)

        # 搜索配置按钮
        self.search_config_btn = PushButton("搜索配置")
        self.search_config_btn.setIcon(FIF.SEARCH)
        self.search_config_btn.clicked.connect(self.onSearchConfig)
        layout.addWidget(self.search_config_btn)

        # 添加文档按钮
        self.add_btn = PrimaryPushButton("添加文档")
        self.add_btn.setIcon(FIF.ADD)
        self.add_btn.clicked.connect(self.onAddDocument)
        layout.addWidget(self.add_btn)

        # 添加文本按钮
        self.add_text_btn = PushButton("添加文本")
        self.add_text_btn.setIcon(FIF.EDIT)
        self.add_text_btn.clicked.connect(self.onAddText)
        layout.addWidget(self.add_text_btn)

        # 删除选中按钮
        self.delete_btn = PushButton("删除选中")
        self.delete_btn.setIcon(FIF.DELETE)
        self.delete_btn.clicked.connect(self.onDeleteSelected)
        layout.addWidget(self.delete_btn)

        # 刷新按钮
        self.refresh_btn = PushButton("刷新列表")
        self.refresh_btn.setIcon(FIF.UPDATE)
        self.refresh_btn.clicked.connect(self.loadRootDocuments)
        layout.addWidget(self.refresh_btn)

        # 清空知识库按钮
        self.clear_btn = PushButton("清空知识库")
        self.clear_btn.setIcon(FIF.REMOVE)
        self.clear_btn.clicked.connect(self.onClearAll)
        layout.addWidget(self.clear_btn)

        # 拆分模式配置
        layout.addSpacing(20)
        split_title = StrongBodyLabel("文档拆分模式")
        layout.addWidget(split_title)

        self.split_mode_combo = ComboBox()
        self.split_mode_combo.addItems(["AI 智能拆分", "简单拆分", "不拆分"])
        self.split_mode_combo.setCurrentIndex(0)
        self.split_mode_combo.currentIndexChanged.connect(self.onSplitModeChanged)
        layout.addWidget(self.split_mode_combo)

        split_hint = CaptionLabel("AI 拆分：按语义主题智能拆分\n简单拆分：按段落/长度拆分\n不拆分：整文档作为一个块")
        split_hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(split_hint)

        layout.addStretch()

        return panel

    def _create_doc_tree(self):
        """创建文档树列表（按根文档分组）"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title_label = StrongBodyLabel("文档列表")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 说明
        hint_label = CaptionLabel("右键点击根文档或子块可删除")
        hint_label.setStyleSheet("color: #666;")
        layout.addWidget(hint_label)

        # 树形列表
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "类型", "大小", "添加时间"])
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 60)
        self.tree.setColumnWidth(3, 140)

        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.itemSelectionChanged.connect(self.onTreeSelectionChanged)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.onTreeContextMenu)

        layout.addWidget(self.tree)

        return panel

    def _create_preview_panel(self):
        """创建预览面板"""
        panel = CardWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 标题
        title_label = StrongBodyLabel("内容预览")
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        # 预览文本
        self.preview_text = TextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("选择文档查看内容")
        layout.addWidget(self.preview_text)

        return panel

    def loadRootDocuments(self):
        """加载根文档列表（按根文档分组）"""
        try:
            root_docs = self.vector_store.get_root_documents()

            # 清空树
            self.tree.clear()

            # 统计总块数
            total_chunks = 0

            for root_doc in root_docs:
                root_item = QTreeWidgetItem(self.tree)
                root_item.setText(0, root_doc['root_doc_name'])
                root_item.setText(1, "根文档")
                root_item.setText(2, str(root_doc['chunk_count']))
                root_item.setText(3, self._format_time(root_doc['added_at']))

                # 存储数据
                root_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'root',
                    'root_doc_id': root_doc['root_doc_id'],
                    'root_doc_name': root_doc['root_doc_name']
                })

                # 添加子块
                for chunk in root_doc['chunks']:
                    chunk_item = QTreeWidgetItem(root_item)
                    metadata = chunk.get('metadata', {})
                    chunk_title = metadata.get('chunk_title', chunk.get('id', '未知'))

                    chunk_item.setText(0, chunk_title)
                    chunk_item.setText(1, "子块")
                    content_len = len(chunk.get('content', ''))
                    chunk_item.setText(2, f"{content_len}字")
                    chunk_item.setText(3, self._format_time(metadata.get('added_at', '')))

                    # 存储数据
                    chunk_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'chunk',
                        'doc_id': chunk.get('id'),
                        'root_doc_id': root_doc['root_doc_id'],
                        'content': chunk.get('content', '')
                    })

                total_chunks += root_doc['chunk_count']

            # 展开所有根文档
            self.tree.expandAll()

            # 更新统计
            self.stats_label.setText(f"根文档: {len(root_docs)} | 总块数: {total_chunks}")

            self.logger.info(f"加载了 {len(root_docs)} 个根文档，共 {total_chunks} 个块")

        except Exception as e:
            self.logger.error(f"加载文档失败: {e}")
            InfoBar.error(
                title="加载失败",
                content=f"无法加载文档列表: {str(e)}",
                parent=self
            )

    def _format_time(self, time_str: str) -> str:
        """格式化时间字符串"""
        if not time_str:
            return ""
        try:
            # 尝试解析 ISO 格式
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime("%m-%d %H:%M")
        except:
            return time_str[:16] if len(time_str) > 16 else time_str

    def onAddDocument(self):
        """添加文档"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择文档",
            "",
            "支持的文件 (*.txt *.pdf *.docx *.doc *.md);;所有文件 (*.*)"
        )

        if not file_path:
            return

        # 显示拆分模式选择对话框
        dialog = ImportModeDialog(self)
        if not dialog.exec():
            return

        split_mode = dialog.getSplitMode()

        try:
            # 处理文档
            documents = self.doc_processor.process_file(file_path, split_mode=split_mode)

            if not documents:
                InfoBar.warning(
                    title="添加失败",
                    content="无法解析文档内容",
                    parent=self
                )
                return

            # 添加到向量库
            success = self.vector_store.add_documents(documents)

            if success:
                mode_name = {"ai": "AI 智能", "simple": "简单", "none": "无"}[split_mode]
                InfoBar.success(
                    title="添加成功",
                    content=f"成功添加 {len(documents)} 个文档块 (模式: {mode_name}拆分)",
                    parent=self
                )
                self.loadRootDocuments()
            else:
                InfoBar.error(
                    title="添加失败",
                    content="无法保存到知识库",
                    parent=self
                )

        except Exception as e:
            self.logger.error(f"添加文档失败: {e}")
            InfoBar.error(
                title="添加失败",
                content=f"错误: {str(e)}",
                parent=self
            )

    def onAddText(self):
        """添加文本"""
        dialog = AddTextDialog(self)
        if not dialog.exec():
            return

        text = dialog.getText()
        title = dialog.getTitle()
        split_mode = dialog.getSplitMode()

        if not text.strip():
            return

        try:
            # 处理文本
            documents = self.doc_processor.process_text(
                text,
                doc_id=title,
                metadata={'title': title, 'source': 'manual'},
                split_mode=split_mode
            )

            # 添加到向量库
            success = self.vector_store.add_documents(documents)

            if success:
                mode_name = {"ai": "AI 智能", "simple": "简单", "none": "无"}[split_mode]
                InfoBar.success(
                    title="添加成功",
                    content=f"成功添加 {len(documents)} 个文档块 (模式: {mode_name}拆分)",
                    parent=self
                )
                self.loadRootDocuments()
            else:
                InfoBar.error(
                    title="添加失败",
                    content="无法保存到知识库",
                    parent=self
                )

        except Exception as e:
            self.logger.error(f"添加文本失败: {e}")
            InfoBar.error(
                title="添加失败",
                content=f"错误: {str(e)}",
                parent=self
            )

    def onDeleteSelected(self):
        """删除选中项"""
        selected = self.tree.selectedItems()
        if not selected:
            InfoBar.warning(
                title="未选择",
                content="请先选择要删除的文档",
                parent=self
            )
            return

        item = selected[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if not data:
            return

        if data.get('type') == 'root':
            # 删除根文档
            self._deleteRootDocument(data.get('root_doc_id'), data.get('root_doc_name'))
        else:
            # 删除单个子块
            self._deleteChunk(data.get('doc_id'))

    def onClearAll(self):
        """清空知识库"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.warning(
            self,
            "危险操作",
            "确定要清空所有知识库文档吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.vector_store.reset()
                if success:
                    InfoBar.success(
                        title="清空完成",
                        content="知识库已重置",
                        parent=self
                    )
                    self.loadRootDocuments()
                else:
                    InfoBar.error(
                        title="操作失败",
                        content="无法清空知识库",
                        parent=self
                    )
            except Exception as e:
                self.logger.error(f"清空知识库失败: {e}")
                InfoBar.error(
                    title="操作失败",
                    content=f"错误: {str(e)}",
                    parent=self
                )

    def onTreeSelectionChanged(self):
        """树选择改变时更新预览"""
        selected = self.tree.selectedItems()
        if selected:
            item = selected[0]
            data = item.data(0, Qt.ItemDataRole.UserRole)

            if data:
                if data.get('type') == 'chunk':
                    # 显示子块内容
                    self.preview_text.setPlainText(data.get('content', ''))
                    return
                elif data.get('type') == 'root':
                    # 显示根文档信息
                    root_doc_id = data.get('root_doc_id', '')
                    root_doc_name = data.get('root_doc_name', '')
                    info = f"根文档: {root_doc_name}\nID: {root_doc_id}\n\n"

                    # 获取所有子块内容
                    root_docs = self.vector_store.get_root_documents()
                    for root_doc in root_docs:
                        if root_doc['root_doc_id'] == root_doc_id:
                            info += f"子块数量: {root_doc['chunk_count']}\n\n"
                            info += "--- 子块内容 ---\n\n"
                            for chunk in root_doc['chunks']:
                                metadata = chunk.get('metadata', {})
                                title = metadata.get('chunk_title', '未知')
                                info += f"【{title}】\n{chunk.get('content', '')}\n\n"
                            break

                    self.preview_text.setPlainText(info)
                    return

        self.preview_text.clear()

    def onTreeContextMenu(self, position):
        """树形列表右键菜单"""
        item = self.tree.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        menu = QMenu(self)

        if data.get('type') == 'root':
            # 根文档菜单
            rename_action = menu.addAction("重命名")
            rename_action.triggered.connect(lambda: self._renameRootDocument(
                data.get('root_doc_id'),
                data.get('root_doc_name')
            ))

            menu.addSeparator()

            add_sub_action = menu.addAction("添加子文档")
            add_sub_action.triggered.connect(lambda: self._addSubDocument(
                data.get('root_doc_id'),
                data.get('root_doc_name')
            ))

            menu.addSeparator()

            delete_action = menu.addAction("删除根文档及所有子块")
            delete_action.triggered.connect(lambda: self._deleteRootDocument(
                data.get('root_doc_id'),
                data.get('root_doc_name')
            ))
        else:
            # 子块菜单
            edit_action = menu.addAction("编辑子文档")
            edit_action.triggered.connect(lambda: self._editSubDocument(
                data.get('doc_id'),
                data.get('content', '')
            ))

            menu.addSeparator()

            delete_action = menu.addAction("删除此子块")
            delete_action.triggered.connect(lambda: self._deleteChunk(data.get('doc_id')))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _deleteRootDocument(self, root_doc_id: str, root_doc_name: str):
        """删除根文档"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除根文档 '{root_doc_name}' 及其所有子块吗？\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.vector_store.delete_root_document(root_doc_id, root_doc_name)
                if success:
                    InfoBar.success(
                        title="删除成功",
                        content=f"根文档 '{root_doc_name}' 及其子块已删除",
                        parent=self
                    )
                    self.loadRootDocuments()
                else:
                    InfoBar.error(
                        title="删除失败",
                        content="无法删除根文档",
                        parent=self
                    )
            except Exception as e:
                self.logger.error(f"删除根文档失败: {e}")
                InfoBar.error(
                    title="删除失败",
                    content=f"错误: {str(e)}",
                    parent=self
                )

    def _deleteChunk(self, chunk_id: str):
        """删除单个子块"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除此子块吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.vector_store.delete_chunk(chunk_id)
                if success:
                    InfoBar.success(
                        title="删除成功",
                        content="子块已删除",
                        parent=self
                    )
                    self.loadRootDocuments()
                else:
                    InfoBar.error(
                        title="删除失败",
                        content="无法删除子块",
                        parent=self
                    )
            except Exception as e:
                self.logger.error(f"删除子块失败: {e}")
                InfoBar.error(
                    title="删除失败",
                    content=f"错误: {str(e)}",
                    parent=self
                )

    def _renameRootDocument(self, root_doc_id: str, current_name: str):
        """重命名根文档"""
        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(
            self,
            "重命名根文档",
            "请输入新的文档名称:",
            text=current_name
        )

        if not ok or not new_name.strip() or new_name.strip() == current_name:
            return

        new_name = new_name.strip()
        self.logger.info(f"开始重命名: {root_doc_id} -> {new_name}")

        try:
            success = self.vector_store.rename_root_document(root_doc_id, new_name)
            self.logger.info(f"重命名结果: {success}")

            if success:
                InfoBar.success(
                    title="重命名成功",
                    content=f"文档已重命名为 '{new_name}'",
                    parent=self
                )
                # 强制刷新
                self.tree.clear()
                self.loadRootDocuments()
                self.logger.info("列表已刷新")
            else:
                InfoBar.error(
                    title="重命名失败",
                    content="无法重命名文档",
                    parent=self
                )

        except Exception as e:
            self.logger.error(f"重命名根文档失败: {e}")
            InfoBar.error(
                title="重命名失败",
                content=f"错误: {str(e)}",
                parent=self
            )

    def _addSubDocument(self, root_doc_id: str, root_doc_name: str):
        """在根文档下添加子文档"""
        dialog = AddSubDocumentDialog(root_doc_name, self)
        if not dialog.exec():
            return

        title = dialog.getTitle()
        content = dialog.getContent()

        if not content.strip():
            InfoBar.warning(
                title="内容为空",
                content="请输入子文档内容",
                parent=self
            )
            return

        try:
            success = self.vector_store.add_sub_document(
                root_doc_id=root_doc_id,
                root_doc_name=root_doc_name,
                content=content,
                chunk_title=title
            )

            if success:
                InfoBar.success(
                    title="添加成功",
                    content=f"子文档 '{title}' 已添加到 '{root_doc_name}'",
                    parent=self
                )
                self.loadRootDocuments()
            else:
                InfoBar.error(
                    title="添加失败",
                    content="无法保存子文档",
                    parent=self
                )

        except Exception as e:
            self.logger.error(f"添加子文档失败: {e}")
            InfoBar.error(
                title="添加失败",
                content=f"错误: {str(e)}",
                parent=self
            )

    def _editSubDocument(self, doc_id: str, current_content: str):
        """编辑子文档"""
        # 获取当前文档的完整信息
        try:
            doc_info = self.vector_store.collection.get(ids=[doc_id])
            if doc_info and doc_info['metadatas']:
                metadata = doc_info['metadatas'][0]
                current_title = metadata.get('chunk_title', '未知')
            else:
                current_title = ''
        except:
            current_title = ''

        dialog = EditSubDocumentDialog(current_title, current_content, self)
        if not dialog.exec():
            return

        new_title = dialog.getTitle()
        new_content = dialog.getContent()

        if not new_content.strip():
            InfoBar.warning(
                title="内容为空",
                content="请输入子文档内容",
                parent=self
            )
            return

        try:
            success = self.vector_store.update_document(
                doc_id=doc_id,
                new_content=new_content,
                new_title=new_title
            )

            if success:
                InfoBar.success(
                    title="更新成功",
                    content=f"子文档 '{new_title}' 已更新",
                    parent=self
                )
                self.loadRootDocuments()
            else:
                InfoBar.error(
                    title="更新失败",
                    content="无法更新子文档",
                    parent=self
                )

        except Exception as e:
            self.logger.error(f"更新子文档失败: {e}")
            InfoBar.error(
                title="更新失败",
                content=f"错误: {str(e)}",
                parent=self
            )

    def onSplitModeChanged(self, index: int):
        """拆分模式改变"""
        modes = ["ai", "simple", "none"]
        mode = modes[index] if index < len(modes) else "ai"
        config.set("kb_split_mode", mode, save=True)
        self.logger.info(f"拆分模式已更改为: {mode}")

    def onRAGToggled(self, enabled: bool):
        """RAG 开关切换"""
        config.set("enable_rag", enabled, save=True)

        status = "启用" if enabled else "禁用"
        InfoBar.success(
            title=f"RAG {status}",
            content=f"知识库功能已{status}，重启后生效" if enabled else f"知识库功能已{status}",
            parent=self
        )

    def onWebSearchToggled(self, enabled: bool):
        """Web 搜索开关切换"""
        config.set("enable_web_search_fallback", enabled, save=True)

        status = "启用" if enabled else "禁用"
        InfoBar.success(
            title=f"智能搜索 {status}",
            content=f"本地知识缺失时自动搜索网络: {status}",
            parent=self
        )

    def onSearchConfig(self):
        """打开搜索配置对话框"""
        dialog = SearchConfigDialog(self)
        if dialog.exec():
            # 保存配置
            config.update({
                "serpapi_key": dialog.getSerpAPIKey(),
                "web_search_min_confidence": dialog.getMinConfidence(),
                "web_search_auto_sink": dialog.getAutoSink()
            }, save=True)

            InfoBar.success(
                title="配置已保存",
                content="搜索配置已更新",
                parent=self
            )


class AddTextDialog(MessageBoxBase):
    """添加文本对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加知识文本")
        self.setupUI()

    def setupUI(self):
        """设置对话框UI"""
        # 标题输入
        self.title_edit = LineEdit()
        self.title_edit.setPlaceholderText("输入标题（如：退换货政策）")
        self.viewLayout.addWidget(QLabel("标题:"))
        self.viewLayout.addWidget(self.title_edit)

        # 内容输入
        self.content_edit = TextEdit()
        self.content_edit.setPlaceholderText("输入知识内容...")
        self.content_edit.setMinimumHeight(200)
        self.viewLayout.addWidget(QLabel("内容:"))
        self.viewLayout.addWidget(self.content_edit)

        # 拆分模式选择
        self.viewLayout.addWidget(QLabel("拆分模式:"))
        split_layout = QVBoxLayout()

        self.ai_radio = RadioButton("AI 智能拆分（推荐）")
        self.ai_radio.setChecked(True)
        split_layout.addWidget(self.ai_radio)

        self.simple_radio = RadioButton("简单拆分（按段落/长度）")
        split_layout.addWidget(self.simple_radio)

        self.none_radio = RadioButton("不拆分（整文档作为一个块）")
        split_layout.addWidget(self.none_radio)

        self.viewLayout.addLayout(split_layout)

        # 设置按钮文本
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")

    def getTitle(self) -> str:
        return self.title_edit.text().strip()

    def getText(self) -> str:
        return self.content_edit.toPlainText().strip()

    def getSplitMode(self) -> str:
        """获取选择的拆分模式"""
        if self.ai_radio.isChecked():
            return "ai"
        elif self.simple_radio.isChecked():
            return "simple"
        else:
            return "none"


class ImportModeDialog(MessageBoxBase):
    """导入模式选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择导入模式")
        self.setupUI()

    def setupUI(self):
        """设置对话框UI"""
        info_label = QLabel("请选择文档拆分方式：")
        info_label.setStyleSheet("font-weight: bold;")
        self.viewLayout.addWidget(info_label)

        # 拆分模式选择
        split_layout = QVBoxLayout()

        self.ai_radio = RadioButton("AI 智能拆分（推荐）")
        self.ai_radio.setChecked(True)
        ai_hint = CaptionLabel("按语义主题智能拆分，生成带标题的知识块")
        ai_hint.setStyleSheet("color: #666; padding-left: 20px;")
        split_layout.addWidget(self.ai_radio)
        split_layout.addWidget(ai_hint)

        self.simple_radio = RadioButton("简单拆分")
        simple_hint = CaptionLabel("按段落和固定长度拆分，适合结构化文档")
        simple_hint.setStyleSheet("color: #666; padding-left: 20px;")
        split_layout.addWidget(self.simple_radio)
        split_layout.addWidget(simple_hint)

        self.none_radio = RadioButton("不拆分")
        none_hint = CaptionLabel("整个文档作为一个知识块，适合短篇文档")
        none_hint.setStyleSheet("color: #666; padding-left: 20px;")
        split_layout.addWidget(self.none_radio)
        split_layout.addWidget(none_hint)

        self.viewLayout.addLayout(split_layout)

        # 设置按钮文本
        self.yesButton.setText("导入")
        self.cancelButton.setText("取消")

    def getSplitMode(self) -> str:
        """获取选择的拆分模式"""
        if self.ai_radio.isChecked():
            return "ai"
        elif self.simple_radio.isChecked():
            return "simple"
        else:
            return "none"


class SearchConfigDialog(MessageBoxBase):
    """搜索配置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("智能搜索配置")
        self.setupUI()

    def setupUI(self):
        """设置对话框UI"""
        from qfluentwidgets import SpinBox

        # SerpAPI Key
        self.api_key_edit = LineEdit()
        self.api_key_edit.setPlaceholderText("输入 SerpAPI Key")
        self.api_key_edit.setText(config.get("serpapi_key", ""))
        self.api_key_edit.setEchoMode(LineEdit.EchoMode.Password)
        self.viewLayout.addWidget(QLabel("SerpAPI Key:"))
        self.viewLayout.addWidget(self.api_key_edit)

        # 最小置信度
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("知识沉淀置信度阈值:"))
        self.confidence_spin = SpinBox()
        self.confidence_spin.setRange(1, 10)
        self.confidence_spin.setValue(int(config.get("web_search_min_confidence", 0.6) * 10))
        confidence_layout.addWidget(self.confidence_spin)
        confidence_layout.addWidget(QLabel("(0.1-1.0)"))
        confidence_layout.addStretch()
        self.viewLayout.addLayout(confidence_layout)

        # 自动沉淀开关
        auto_sink_layout = QHBoxLayout()
        auto_sink_layout.addWidget(QLabel("自动沉淀到知识库:"))
        self.auto_sink_switch = SwitchButton()
        self.auto_sink_switch.setChecked(config.get("web_search_auto_sink", True))
        auto_sink_layout.addWidget(self.auto_sink_switch)
        auto_sink_layout.addStretch()
        self.viewLayout.addLayout(auto_sink_layout)

        # 说明文本
        help_text = (
            "说明:\n"
            "• SerpAPI Key 用于 Google 搜索，获取地址: serpapi.com\n"
            "• 置信度阈值: 低于此值的知识不会沉淀到本地库\n"
            "• 自动沉淀: 将网络搜索结果自动保存到本地知识库"
        )
        help_label = QLabel(help_text)
        help_label.setStyleSheet("color: #666; font-size: 12px;")
        self.viewLayout.addWidget(help_label)

        # 设置按钮文本
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

    def getSerpAPIKey(self) -> str:
        return self.api_key_edit.text().strip()

    def getMinConfidence(self) -> float:
        return self.confidence_spin.value() / 10.0

    def getAutoSink(self) -> bool:
        return self.auto_sink_switch.isChecked()


class AddSubDocumentDialog(MessageBoxBase):
    """添加子文档对话框"""

    def __init__(self, root_doc_name: str, parent=None):
        super().__init__(parent)
        self.root_doc_name = root_doc_name
        self.setWindowTitle(f"添加子文档到 '{root_doc_name}'")
        self.setupUI()

    def setupUI(self):
        """设置对话框UI"""
        # 标题输入
        self.title_edit = LineEdit()
        self.title_edit.setPlaceholderText("输入子文档标题（如：产品功效说明）")
        self.viewLayout.addWidget(QLabel("标题:"))
        self.viewLayout.addWidget(self.title_edit)

        # 内容输入
        self.content_edit = TextEdit()
        self.content_edit.setPlaceholderText("输入子文档内容...")
        self.content_edit.setMinimumHeight(250)
        self.viewLayout.addWidget(QLabel("内容:"))
        self.viewLayout.addWidget(self.content_edit)

        # 设置按钮文本
        self.yesButton.setText("添加")
        self.cancelButton.setText("取消")

    def getTitle(self) -> str:
        return self.title_edit.text().strip()

    def getContent(self) -> str:
        return self.content_edit.toPlainText().strip()


class EditSubDocumentDialog(MessageBoxBase):
    """编辑子文档对话框"""

    def __init__(self, current_title: str, current_content: str, parent=None):
        super().__init__(parent)
        self.current_title = current_title
        self.current_content = current_content
        self.setWindowTitle("编辑子文档")
        self.setupUI()

    def setupUI(self):
        """设置对话框UI"""
        # 标题输入
        self.title_edit = LineEdit()
        self.title_edit.setText(self.current_title)
        self.title_edit.setPlaceholderText("输入子文档标题")
        self.viewLayout.addWidget(QLabel("标题:"))
        self.viewLayout.addWidget(self.title_edit)

        # 内容输入
        self.content_edit = TextEdit()
        self.content_edit.setPlainText(self.current_content)
        self.content_edit.setMinimumHeight(300)
        self.viewLayout.addWidget(QLabel("内容:"))
        self.viewLayout.addWidget(self.content_edit)

        # 设置按钮文本
        self.yesButton.setText("保存")
        self.cancelButton.setText("取消")

    def getTitle(self) -> str:
        return self.title_edit.text().strip()

    def getContent(self) -> str:
        return self.content_edit.toPlainText().strip()
