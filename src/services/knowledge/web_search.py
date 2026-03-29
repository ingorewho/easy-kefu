"""Web 搜索模块 - 支持多种搜索提供商"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
import time
from utils.logger import get_logger


class WebSearchProvider(ABC):
    """Web 搜索提供商抽象基类"""

    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        执行搜索

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            List[Dict]: 搜索结果列表，每个结果包含 title, link, snippet
        """
        pass


class SerpAPIProvider(WebSearchProvider):
    """SerpAPI Google 搜索实现"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
        self.logger = get_logger("SerpAPIProvider")

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """使用 SerpAPI 执行 Google 搜索"""
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "num": num_results,
                "hl": "zh-CN",
                "gl": "cn"
            }

            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = []

            # 提取有机搜索结果
            organic_results = data.get("organic_results", [])
            for result in organic_results[:num_results]:
                results.append({
                    "title": result.get("title", ""),
                    "link": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "source": "google"
                })

            # 提取知识图谱信息（如果有）
            knowledge_graph = data.get("knowledge_graph", {})
            if knowledge_graph:
                description = knowledge_graph.get("description", "")
                if description:
                    results.insert(0, {
                        "title": knowledge_graph.get("title", query),
                        "link": knowledge_graph.get("website", ""),
                        "snippet": description,
                        "source": "knowledge_graph"
                    })

            self.logger.info(f"搜索 '{query}' 获取 {len(results)} 条结果")
            return results

        except requests.exceptions.RequestException as e:
            self.logger.error(f"搜索请求失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"搜索处理失败: {e}")
            return []


class BaiduSearchProvider(WebSearchProvider):
    """百度搜索实现（需要百度 API Key）"""

    def __init__(self, api_key: str, secret_key: Optional[str] = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = "https://www.baidu.com/s"
        self.logger = get_logger("BaiduSearchProvider")

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """百度搜索（简化实现）"""
        self.logger.warning("百度搜索需要额外的 API 接入，当前返回空结果")
        # 实际实现需要使用百度统计 API 或百度搜索资源平台 API
        return []


class WebSearchManager:
    """Web 搜索管理器"""

    def __init__(self, provider: str = "serpapi", api_key: str = ""):
        self.logger = get_logger("WebSearchManager")
        self.provider = self._create_provider(provider, api_key)
        self._last_search_time = 0
        self._min_interval = 1.0  # 最小请求间隔（秒）

    def _create_provider(self, provider: str, api_key: str) -> Optional[WebSearchProvider]:
        """创建搜索提供商"""
        if not api_key:
            self.logger.warning("未配置搜索 API Key")
            return None

        if provider == "serpapi":
            return SerpAPIProvider(api_key)
        else:
            self.logger.error(f"不支持的搜索提供商: {provider}")
            return None

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        执行搜索，带速率限制

        Args:
            query: 搜索查询
            num_results: 返回结果数量

        Returns:
            List[Dict]: 搜索结果
        """
        if not self.provider:
            self.logger.warning("搜索提供商未配置")
            return []

        # 速率限制
        elapsed = time.time() - self._last_search_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        results = self.provider.search(query, num_results)
        self._last_search_time = time.time()

        return results

    def format_results(self, results: List[Dict]) -> str:
        """
        将搜索结果格式化为文本

        Args:
            results: 搜索结果列表

        Returns:
            str: 格式化后的文本
        """
        if not results:
            return ""

        formatted = ["=== 网络搜索结果 ==="]

        for i, result in enumerate(results, 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")

            if title or snippet:
                formatted.append(f"\n[{i}] {title}")
                if snippet:
                    formatted.append(f"内容: {snippet}")
                if link:
                    formatted.append(f"来源: {link}")

        return "\n".join(formatted)

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return self.provider is not None
