"""知识沉淀器 - 将提取的知识存入 RAG 向量库"""
from typing import List, Optional
from datetime import datetime

from services.knowledge.vector_store import VectorStoreManager
from services.knowledge.knowledge_extractor import ExtractedKnowledge
from utils.logger import get_logger


class KnowledgeSink:
    """知识沉淀器 - 管理知识的持久化存储"""

    def __init__(self):
        self.logger = get_logger("KnowledgeSink")
        self.vector_store = VectorStoreManager()
        self._duplicate_threshold = 0.95  # 重复检测相似度阈值

    def sink(
        self,
        knowledge_list: List[ExtractedKnowledge],
        min_confidence: float = 0.6
    ) -> int:
        """
        将知识沉淀到向量库

        Args:
            knowledge_list: 要沉淀的知识列表
            min_confidence: 最小置信度阈值

        Returns:
            int: 成功沉淀的知识数量
        """
        if not knowledge_list:
            return 0

        success_count = 0

        for knowledge in knowledge_list:
            # 跳过低置信度知识
            if knowledge.confidence < min_confidence:
                self.logger.debug(f"跳过低置信度知识: {knowledge.knowledge[:50]}...")
                continue

            # 跳过不需要沉淀的知识
            if not knowledge.should_sink:
                self.logger.debug(f"跳过非沉淀知识: {knowledge.knowledge[:50]}...")
                continue

            # 检查重复
            if self._is_duplicate(knowledge.knowledge):
                self.logger.debug(f"跳过重复知识: {knowledge.knowledge[:50]}...")
                continue

            # 沉淀到向量库
            if self._store_knowledge(knowledge):
                success_count += 1

        self.logger.info(f"成功沉淀 {success_count}/{len(knowledge_list)} 条知识")
        return success_count

    def _is_duplicate(self, knowledge_text: str) -> bool:
        """
        检查知识是否已存在

        Args:
            knowledge_text: 知识文本

        Returns:
            bool: 是否重复
        """
        try:
            # 搜索相似内容
            results = self.vector_store.search(
                query=knowledge_text,
                top_k=1
            )

            if results:
                # 检查相似度
                distance = results[0].get("distance", 1.0)
                if distance < self._duplicate_threshold:
                    return True

            return False

        except Exception as e:
            self.logger.error(f"重复检测失败: {e}")
            return False

    def _store_knowledge(self, knowledge: ExtractedKnowledge) -> bool:
        """
        存储单条知识

        Args:
            knowledge: 知识对象

        Returns:
            bool: 是否成功
        """
        try:
            # 构建文档结构
            document = {
                "id": f"web_knowledge_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                "content": knowledge.knowledge,
                "metadata": {
                    "source": "web_search",
                    "category": knowledge.category,
                    "confidence": knowledge.confidence,
                    "source_query": knowledge.source_query,
                    "source_url": knowledge.source_url,
                    "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "filename": f"[{knowledge.category}] 网络知识"
                }
            }

            # 添加到向量库
            success = self.vector_store.add_documents([document])

            if success:
                self.logger.info(f"知识已沉淀: {knowledge.knowledge[:80]}...")

            return success

        except Exception as e:
            self.logger.error(f"存储知识失败: {e}")
            return False

    def get_sink_stats(self) -> dict:
        """获取沉淀统计"""
        try:
            all_docs = self.vector_store.get_all_documents()
            web_knowledge = [
                doc for doc in all_docs
                if doc.get("metadata", {}).get("source") == "web_search"
            ]

            categories = {}
            for doc in web_knowledge:
                cat = doc.get("metadata", {}).get("category", "未知")
                categories[cat] = categories.get(cat, 0) + 1

            return {
                "total_web_knowledge": len(web_knowledge),
                "categories": categories
            }

        except Exception as e:
            self.logger.error(f"获取统计失败: {e}")
            return {"total_web_knowledge": 0, "categories": {}}
