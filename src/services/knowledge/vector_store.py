"""向量存储管理器 - 使用 ChromaDB"""
import os
import sys
import hashlib
from typing import List, Dict, Optional
from datetime import datetime

from utils.logger import get_logger


def get_resource_path(relative_path):
    """获取资源文件的绝对路径（支持 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


class VectorStoreManager:
    """向量存储管理器 - 管理知识库的向量数据"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # 使用用户目录存储知识库（避免只读文件系统问题）
            if hasattr(sys, '_MEIPASS'):
                db_path = os.path.expanduser("~/Library/Application Support/智能客服/knowledge_base")
            else:
                db_path = get_resource_path("database/knowledge_base")
        os.makedirs(db_path, exist_ok=True)
        self.logger = get_logger("VectorStoreManager")
        self.db_path = db_path
        self.client = None
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        """初始化 ChromaDB"""
        try:
            import chromadb
            from chromadb.config import Settings

            os.makedirs(self.db_path, exist_ok=True)

            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # 获取或创建集合
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base",
                metadata={"description": "客服知识库"}
            )

            self.logger.info(f"ChromaDB 初始化完成: {self.db_path}")

        except ImportError:
            self.logger.error("chromadb 未安装，请运行: pip install chromadb")
            raise
        except Exception as e:
            self.logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def add_documents(self, documents: List[Dict]) -> bool:
        """
        添加文档到向量库

        Args:
            documents: 文档列表，每项包含 {
                'id': 文档ID,
                'content': 文档内容,
                'metadata': 元数据
            }

        Returns:
            bool: 是否添加成功
        """
        try:
            if not documents:
                return True

            ids = []
            texts = []
            metadatas = []

            for doc in documents:
                doc_id = doc.get('id') or self._generate_id(doc['content'])
                ids.append(doc_id)
                texts.append(doc['content'])
                metadatas.append({
                    **doc.get('metadata', {}),
                    'added_at': datetime.now().isoformat()
                })

            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )

            self.logger.info(f"成功添加 {len(documents)} 个文档到向量库")
            return True

        except Exception as e:
            self.logger.error(f"添加文档失败: {e}")
            return False

    def search(self, query: str, top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_dict: 过滤条件

        Returns:
            List[Dict]: 相关文档列表
        """
        try:
            self.logger.info(f"向量库搜索: query='{query}', top_k={top_k}")

            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filter_dict
            )

            documents = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    documents.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0,
                        'id': results['ids'][0][i]
                    })

            self.logger.info(f"向量库搜索完成: 找到 {len(documents)} 条结果")
            for i, doc in enumerate(documents):
                self.logger.info(f"  [{i+1}] id={doc['id']}, distance={doc.get('distance', 'N/A')}")

            return documents

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """删除指定文档"""
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            self.logger.error(f"删除文档失败: {e}")
            return False

    def rename_root_document(self, root_doc_id: str, new_name: str) -> bool:
        """重命名根文档（更新所有子块的 root_doc_name）

        Args:
            root_doc_id: 根文档ID
            new_name: 新名称

        Returns:
            bool: 是否成功
        """
        try:
            from datetime import datetime

            # 获取所有属于该根文档的文档
            all_docs = self.get_all_documents()
            updated_count = 0

            for doc in all_docs:
                metadata = doc.get('metadata', {})
                if metadata.get('root_doc_id') == root_doc_id:
                    doc_id = doc.get('id')
                    # 更新 metadata
                    metadata['root_doc_name'] = new_name
                    metadata['updated_at'] = datetime.now().isoformat()

                    # ChromaDB 需要删除后重新添加才能更新 metadata
                    self.collection.delete(ids=[doc_id])
                    self.collection.add(
                        ids=[doc_id],
                        documents=[doc.get('content', '')],
                        metadatas=[metadata]
                    )
                    updated_count += 1

            self.logger.info(f"成功重命名根文档: {root_doc_id} -> {new_name}, 更新了 {updated_count} 个子块")
            return True

        except Exception as e:
            self.logger.error(f"重命名根文档失败: {e}")
            return False

    def add_sub_document(self, root_doc_id: str, root_doc_name: str,
                          content: str, chunk_title: str = None) -> bool:
        """在指定根文档下添加子文档

        Args:
            root_doc_id: 根文档ID
            root_doc_name: 根文档名称
            content: 子文档内容
            chunk_title: 子文档标题（可选）

        Returns:
            bool: 是否成功
        """
        try:
            from datetime import datetime

            # 获取该根文档下现有的子块数量
            existing_docs = self.get_all_documents()
            chunk_count = 0
            for doc in existing_docs:
                metadata = doc.get('metadata', {})
                if metadata.get('root_doc_id') == root_doc_id:
                    chunk_count += 1

            # 生成新的子文档ID
            new_chunk_id = f"{root_doc_id}_chunk_{chunk_count}"

            # 如果没有提供标题，自动生成
            if not chunk_title:
                chunk_title = f"子文档_{chunk_count}"

            # 构建文档
            doc = {
                'id': new_chunk_id,
                'content': content,
                'metadata': {
                    'root_doc_id': root_doc_id,
                    'root_doc_name': root_doc_name,
                    'chunk_title': chunk_title,
                    'chunk_index': chunk_count,
                    'is_chunk': True,
                    'is_sub_document': True,  # 标记为手动添加的子文档
                    'added_at': datetime.now().isoformat(),
                    'source': 'manual_add'
                }
            }

            # 添加到向量库
            self.collection.add(
                ids=[doc['id']],
                documents=[doc['content']],
                metadatas=[doc['metadata']]
            )

            self.logger.info(f"成功添加子文档: {new_chunk_id} 到根文档 {root_doc_name}")
            return True

        except Exception as e:
            self.logger.error(f"添加子文档失败: {e}")
            return False

    def update_document(self, doc_id: str, new_content: str, new_title: str = None) -> bool:
        """更新指定文档的内容

        Args:
            doc_id: 文档ID
            new_content: 新内容
            new_title: 新标题（可选，仅更新metadata中的chunk_title）

        Returns:
            bool: 是否成功
        """
        try:
            from datetime import datetime

            # 先获取原文档的metadata
            result = self.collection.get(ids=[doc_id])
            if not result or not result['ids']:
                self.logger.error(f"找不到文档: {doc_id}")
                return False

            existing_metadata = result['metadatas'][0] if result['metadatas'] else {}

            # 更新内容
            if new_title:
                existing_metadata['chunk_title'] = new_title
            existing_metadata['updated_at'] = datetime.now().isoformat()

            # 删除旧文档并添加新文档（ChromaDB不支持直接更新）
            self.collection.delete(ids=[doc_id])
            self.collection.add(
                ids=[doc_id],
                documents=[new_content],
                metadatas=[existing_metadata]
            )

            self.logger.info(f"成功更新文档: {doc_id}")
            return True

        except Exception as e:
            self.logger.error(f"更新文档失败: {e}")
            return False

    def get_root_documents(self) -> List[Dict]:
        """
        获取所有根文档（按 root_doc_id 分组）

        Returns:
            [
                {
                    'root_doc_id': 'root_xxx',
                    'root_doc_name': '发货时效.txt',
                    'chunk_count': 3,
                    'added_at': '2024-01-01',
                    'chunks': [...]
                }
            ]
        """
        try:
            documents = self.get_all_documents()

            # 按 root_doc_id 分组
            root_docs = {}

            for doc in documents:
                metadata = doc.get('metadata', {})

                # 获取根文档ID（兼容旧数据）
                root_doc_id = metadata.get('root_doc_id')
                if not root_doc_id:
                    # 旧数据兼容：使用 filename 作为分组键
                    filename = metadata.get('filename', 'unknown')
                    root_doc_id = f"legacy_{filename}"
                    # 更新文档的 metadata，添加 root_doc_id
                    metadata['root_doc_id'] = root_doc_id
                    metadata['root_doc_name'] = filename

                # 获取根文档名称
                root_doc_name = metadata.get('root_doc_name', metadata.get('filename', 'unknown'))

                if root_doc_id not in root_docs:
                    root_docs[root_doc_id] = {
                        'root_doc_id': root_doc_id,
                        'root_doc_name': root_doc_name,
                        'chunks': [],
                        'added_at': metadata.get('added_at', ''),
                        'is_legacy': not metadata.get('root_doc_id')
                    }

                root_docs[root_doc_id]['chunks'].append(doc)

            # 计算每个根文档的统计信息
            result = []
            for root_doc in root_docs.values():
                chunks = root_doc['chunks']
                # 获取最早的添加时间
                added_times = [c.get('metadata', {}).get('added_at', '') for c in chunks]
                added_times = [t for t in added_times if t]
                added_at = min(added_times) if added_times else ''

                # 按 chunk_index 排序
                chunks.sort(key=lambda x: x.get('metadata', {}).get('chunk_index', 0))

                # 从所有子块中找出最新的 root_doc_name（有 updated_at 的优先）
                latest_root_name = root_doc['root_doc_name']
                latest_update_time = ''
                for c in chunks:
                    meta = c.get('metadata', {})
                    name = meta.get('root_doc_name', '')
                    update_time = meta.get('updated_at', '')
                    if name:
                        # 优先选择有 updated_at 的，或者更新时间更新的
                        if update_time:
                            if not latest_update_time or update_time > latest_update_time:
                                latest_root_name = name
                                latest_update_time = update_time
                        elif not latest_update_time:
                            # 如果没有找到过 updated_at，使用任意一个名称
                            latest_root_name = name

                result.append({
                    'root_doc_id': root_doc['root_doc_id'],
                    'root_doc_name': latest_root_name,
                    'chunk_count': len(chunks),
                    'added_at': added_at,
                    'chunks': chunks,
                    'is_legacy': root_doc['is_legacy']
                })

            # 按添加时间倒序
            result.sort(key=lambda x: x['added_at'], reverse=True)

            return result

        except Exception as e:
            self.logger.error(f"获取根文档列表失败: {e}")
            return []

    def delete_root_document(self, root_doc_id: str, root_doc_name: str = None) -> bool:
        """
        删除根文档及其所有子块

        Args:
            root_doc_id: 根文档ID
            root_doc_name: 根文档名称（用于旧数据兼容）

        Returns:
            bool: 是否删除成功
        """
        try:
            doc_ids = []

            # 1. 尝试按 root_doc_id 查询
            results = self.collection.get(
                where={"root_doc_id": root_doc_id}
            )

            if results['ids']:
                doc_ids = results['ids']
            elif root_doc_id.startswith('legacy_') and root_doc_name:
                # 2. 旧数据兼容：按 filename 查询
                self.logger.info(f"尝试按文件名删除旧数据: {root_doc_name}")
                all_docs = self.get_all_documents()
                for doc in all_docs:
                    metadata = doc.get('metadata', {})
                    filename = metadata.get('filename', '')
                    if filename == root_doc_name:
                        doc_ids.append(doc['id'])

            if not doc_ids:
                self.logger.warning(f"未找到根文档: {root_doc_id}")
                return False

            # 3. 批量删除
            self.collection.delete(ids=doc_ids)

            self.logger.info(f"成功删除根文档 {root_doc_id} 及其 {len(doc_ids)} 个子块")
            return True

        except Exception as e:
            self.logger.error(f"删除根文档失败: {e}")
            return False

    def delete_chunk(self, chunk_id: str) -> bool:
        """
        删除单个分块

        Args:
            chunk_id: 分块ID

        Returns:
            bool: 是否删除成功
        """
        return self.delete_document(chunk_id)

    def get_all_documents(self) -> List[Dict]:
        """获取所有文档"""
        try:
            results = self.collection.get()

            documents = []
            if results['ids']:
                for i, doc_id in enumerate(results['ids']):
                    documents.append({
                        'id': doc_id,
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i] if results['metadatas'] else {}
                    })

            return documents

        except Exception as e:
            self.logger.error(f"获取文档列表失败: {e}")
            return []

    def count(self) -> int:
        """获取文档总数"""
        try:
            return self.collection.count()
        except Exception as e:
            self.logger.error(f"获取文档数量失败: {e}")
            return 0

    def reset(self):
        """清空知识库（危险操作）"""
        try:
            self.client.delete_collection("knowledge_base")
            self.collection = self.client.get_or_create_collection(
                name="knowledge_base",
                metadata={"description": "客服知识库"}
            )
            self.logger.info("知识库已清空")
            return True
        except Exception as e:
            self.logger.error(f"清空知识库失败: {e}")
            return False

    def _generate_id(self, content: str) -> str:
        """为内容生成唯一ID"""
        return hashlib.md5(content.encode()).hexdigest()[:16]
