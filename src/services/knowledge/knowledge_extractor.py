"""知识提取器 - 使用 Qwen 从搜索结果提取结构化知识"""
import json
from typing import List, Dict, Optional
import dashscope
from dashscope import Generation
from config import config
from utils.logger import get_logger


class ExtractedKnowledge:
    """提取的知识数据结构"""

    def __init__(
        self,
        knowledge: str,
        confidence: float,
        category: str,
        should_sink: bool,
        source_query: str = "",
        source_url: str = ""
    ):
        self.knowledge = knowledge
        self.confidence = confidence
        self.category = category
        self.should_sink = should_sink
        self.source_query = source_query
        self.source_url = source_url

    def to_dict(self) -> Dict:
        return {
            "knowledge": self.knowledge,
            "confidence": self.confidence,
            "category": self.category,
            "should_sink": self.should_sink,
            "source_query": self.source_query,
            "source_url": self.source_url
        }


class KnowledgeExtractor:
    """知识提取器 - 使用 Qwen 模型提取结构化知识"""

    def __init__(self):
        self.logger = get_logger("KnowledgeExtractor")
        self.api_key = config.get("qwen_api_key", "")
        self.model = config.get("qwen_model", "qwen-turbo")

        if self.api_key:
            dashscope.api_key = self.api_key

    def extract(
        self,
        search_results: List[Dict],
        original_query: str,
        min_confidence: float = 0.6
    ) -> List[ExtractedKnowledge]:
        """
        从搜索结果提取结构化知识

        Args:
            search_results: 搜索结果列表
            original_query: 原始查询
            min_confidence: 最小置信度阈值

        Returns:
            List[ExtractedKnowledge]: 提取的知识列表
        """
        if not self.api_key:
            self.logger.warning("未配置 Qwen API Key，跳过知识提取")
            return []

        if not search_results:
            return []

        try:
            # 构建提示词
            search_content = self._format_search_results(search_results)

            prompt = f"""基于以下搜索结果，提取与用户问题相关的结构化知识。

用户问题: {original_query}

搜索结果:
{search_content}

请提取知识并以 JSON 格式返回:
{{
    "knowledge_list": [
        {{
            "knowledge": "提取的知识点（简洁准确）",
            "confidence": 0.85,
            "category": "分类（如：产品信息/售后政策/使用方法等）",
            "should_sink": true
        }}
    ]
}}

注意:
- confidence: 0-1 之间的置信度，表示知识可靠程度
- should_sink: 是否值得沉淀到知识库（true/false）
- 只提取与用户问题直接相关的高质量知识
- 如果搜索结果不包含有效信息，返回空列表"""

            # 调用 Qwen API
            response = Generation.call(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是专业的知识提取助手，擅长从搜索结果中提取结构化知识。"},
                    {"role": "user", "content": prompt}
                ],
                result_format="message"
            )

            if response.status_code != 200:
                self.logger.error(f"Qwen API 调用失败: {response.message}")
                return []

            # 解析响应
            content = response.output.choices[0].message.content
            return self._parse_extraction(content, original_query, search_results)

        except Exception as e:
            self.logger.error(f"知识提取失败: {e}")
            return []

    def _format_search_results(self, results: List[Dict]) -> str:
        """格式化搜索结果"""
        formatted = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if title or snippet:
                formatted.append(f"[{i}] {title}\n{snippet}")
        return "\n\n".join(formatted)

    def _parse_extraction(
        self,
        content: str,
        original_query: str,
        search_results: List[Dict]
    ) -> List[ExtractedKnowledge]:
        """解析提取结果"""
        try:
            # 提取 JSON
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            knowledge_list = []
            items = data.get("knowledge_list", [])

            for item in items:
                knowledge = ExtractedKnowledge(
                    knowledge=item.get("knowledge", ""),
                    confidence=item.get("confidence", 0.0),
                    category=item.get("category", "通用"),
                    should_sink=item.get("should_sink", False),
                    source_query=original_query,
                    source_url=search_results[0].get("link", "") if search_results else ""
                )
                knowledge_list.append(knowledge)

            self.logger.info(f"成功提取 {len(knowledge_list)} 条知识")
            return knowledge_list

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
            return []
        except Exception as e:
            self.logger.error(f"解析提取结果失败: {e}")
            return []

    def _extract_json(self, content: str) -> str:
        """从文本中提取 JSON"""
        # 尝试找到 JSON 块
        start = content.find("{")
        end = content.rfind("}")

        if start != -1 and end != -1 and end > start:
            return content[start:end + 1]

        return content

    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key)
