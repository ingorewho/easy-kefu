"""混合 RAG 检索器 - 本地知识库 + Web 搜索"""
from typing import List, Dict, Optional
from config import config
from services.knowledge.vector_store import VectorStoreManager
from services.knowledge.web_search import WebSearchManager
from services.knowledge.knowledge_extractor import KnowledgeExtractor
from services.knowledge.knowledge_sink import KnowledgeSink
from utils.logger import get_logger


class HybridRAGRetriever:
    """混合 RAG 检索器 - 优先本地知识库，缺失时自动 Web 搜索"""

    def __init__(
        self,
        top_k: int = 3,
        score_threshold: float = 0.5,
        enable_web_fallback: Optional[bool] = None,
        min_confidence: Optional[float] = None
    ):
        self.logger = get_logger("HybridRAGRetriever")
        self.vector_store = VectorStoreManager()
        self.top_k = top_k
        self.score_threshold = score_threshold

        # Web 搜索相关组件
        self.enable_web_fallback = enable_web_fallback if enable_web_fallback is not None else config.get("enable_web_search_fallback", True)
        self.web_search = WebSearchManager(
            provider=config.get("web_search_provider", "serpapi"),
            api_key=config.get("serpapi_key", "")
        )

        # 知识提取和沉淀
        self.knowledge_extractor = KnowledgeExtractor()
        self.knowledge_sink = KnowledgeSink()
        self.min_confidence = min_confidence if min_confidence is not None else config.get("web_search_min_confidence", 0.6)
        self.auto_sink = config.get("web_search_auto_sink", True)

        self.logger.info(f"混合检索器初始化完成，Web 回退: {self.enable_web_fallback}")

    def retrieve(self, query: str, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        检索相关知识（本地 + Web）

        Args:
            query: 用户查询
            filter_dict: 过滤条件

        Returns:
            List[Dict]: 相关文档列表
        """
        # 1. 先查询本地知识库
        local_results = self._retrieve_local(query, filter_dict)

        if local_results:
            self.logger.info(f"本地知识库返回 {len(local_results)} 条结果")
            return local_results

        # 2. 本地无结果，触发 Web 搜索
        if not self.enable_web_fallback or not self.web_search.is_configured():
            self.logger.info("本地无结果，Web 搜索未启用或未配置")
            return []

        self.logger.info("本地无结果，触发 Web 搜索...")
        return self._retrieve_web(query)

    def _retrieve_local(self, query: str, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """检索本地知识库"""
        try:
            results = self.vector_store.search(
                query=query,
                top_k=self.top_k,
                filter_dict=filter_dict
            )

            # 过滤低质量结果
            # ChromaDB 使用 L2 距离，值越小越相似
            # 如果 threshold 较小（<=1），假设是 cosine 相似度，不过滤
            # 如果 threshold 较大（>1），假设是 L2 距离，进行过滤
            if self.score_threshold <= 1.0:
                # Cosine 相似度阈值，或者不过滤
                filtered = results
            else:
                # L2 距离阈值过滤
                filtered = [
                    doc for doc in results
                    if doc.get("distance", 999) < self.score_threshold
                ]

            self.logger.info(f"本地检索: 原始 {len(results)} 条, 过滤后 {len(filtered)} 条, threshold={self.score_threshold}")
            return filtered

        except Exception as e:
            self.logger.error(f"本地检索失败: {e}")
            return []

    def _retrieve_web(self, query: str) -> List[Dict]:
        """检索 Web 并提取知识"""
        try:
            # 执行 Web 搜索
            search_results = self.web_search.search(query, num_results=5)

            if not search_results:
                self.logger.warning("Web 搜索无结果")
                return []

            self.logger.info(f"Web 搜索获取 {len(search_results)} 条结果")

            # 提取结构化知识
            if not self.knowledge_extractor.is_configured():
                # 未配置提取器，直接使用原始搜索结果
                return self._format_search_as_docs(search_results)

            extracted = self.knowledge_extractor.extract(
                search_results=search_results,
                original_query=query,
                min_confidence=self.min_confidence
            )

            if not extracted:
                self.logger.warning("知识提取无结果")
                return self._format_search_as_docs(search_results)

            self.logger.info(f"提取 {len(extracted)} 条结构化知识")

            # 自动沉淀到本地知识库
            if self.auto_sink:
                sink_count = self.knowledge_sink.sink(extracted, self.min_confidence)
                self.logger.info(f"自动沉淀 {sink_count} 条知识到本地库")

            # 转换为文档格式返回
            return self._format_knowledge_as_docs(extracted, search_results)

        except Exception as e:
            self.logger.error(f"Web 检索失败: {e}")
            return []

    def _format_search_as_docs(self, search_results: List[Dict]) -> List[Dict]:
        """将搜索结果格式化为文档"""
        docs = []
        for i, result in enumerate(search_results):
            content = f"{result.get('title', '')}\n{result.get('snippet', '')}".strip()
            if content:
                docs.append({
                    "id": f"web_search_{i}",
                    "content": content,
                    "metadata": {
                        "source": "web_search",
                        "source_url": result.get("link", ""),
                        "filename": "[网络搜索] " + result.get("title", "")[:50]
                    },
                    "distance": 0.5  # 默认中等相似度
                })
        return docs

    def _format_knowledge_as_docs(
        self,
        knowledge_list: List,
        search_results: List[Dict]
    ) -> List[Dict]:
        """将提取的知识格式化为文档"""
        docs = []
        source_url = search_results[0].get("link", "") if search_results else ""

        for item in knowledge_list:
            docs.append({
                "id": f"web_knowledge_{id(item)}",
                "content": item.knowledge,
                "metadata": {
                    "source": "web_search",
                    "category": item.category,
                    "confidence": item.confidence,
                    "source_url": item.source_url or source_url,
                    "filename": f"[网络知识] {item.category}"
                },
                "distance": 1 - item.confidence  # 转换为距离
            })

        return docs

    def build_context(self, query: str, retrieved_docs: List[Dict]) -> str:
        """
        构建 RAG 上下文

        Args:
            query: 用户查询
            retrieved_docs: 检索到的文档

        Returns:
            str: 增强的提示词上下文
        """
        if not retrieved_docs:
            return ""

        context_parts = ["=== 相关知识 ==="]

        for i, doc in enumerate(retrieved_docs, 1):
            source = doc.get("metadata", {}).get("filename", "未知来源")
            content = doc.get("content", "").strip()
            source_type = doc.get("metadata", {}).get("source", "local")

            if content:
                prefix = "[网络]" if source_type == "web_search" else "[本地]"
                context_parts.append(f"\n[{i}] {prefix} 来源: {source}\n{content}")

        context_parts.append(f"\n=== 用户问题 ===\n{query}")
        context_parts.append("\n请基于以上知识回答问题。如果知识库中没有相关信息，请说明。")

        return "\n".join(context_parts)

    def enhance_prompt(self, query: str, original_prompt: str = "") -> str:
        """
        增强用户提示词

        Args:
            query: 用户查询
            original_prompt: 原始系统提示词

        Returns:
            str: 增强后的完整提示词
        """
        self.logger.info(f"开始检索知识库，查询: {query}")

        # 检索相关知识
        docs = self.retrieve(query)

        self.logger.info(f"检索完成，找到 {len(docs)} 条相关知识")
        for i, doc in enumerate(docs):
            source = doc.get('metadata', {}).get('source', 'unknown')
            content_preview = doc.get('content', '')[:50]
            self.logger.info(f"  [{i+1}] source={source}, content={content_preview}...")

        if not docs:
            self.logger.warning("未检索到任何相关知识")
            return query

        # 构建增强提示词
        rag_context = self.build_context(query, docs)

        enhanced = f"""{original_prompt}

{rag_context}
"""
        return enhanced

    def get_knowledge_stats(self) -> Dict:
        """获取知识库统计信息"""
        web_stats = self.knowledge_sink.get_sink_stats()

        return {
            "total_documents": self.vector_store.count(),
            "web_knowledge": web_stats["total_web_knowledge"],
            "web_categories": web_stats["categories"],
            "top_k": self.top_k,
            "score_threshold": self.score_threshold,
            "web_fallback_enabled": self.enable_web_fallback,
            "web_search_configured": self.web_search.is_configured()
        }


# 保持向后兼容
RAGRetriever = HybridRAGRetriever
