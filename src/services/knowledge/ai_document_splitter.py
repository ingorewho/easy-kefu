"""AI 智能文档拆分器 - 按语义主题拆分"""
import json
import re
from typing import List, Dict, Optional
from pathlib import Path

from utils.logger import get_logger
from config import config


class AIDocumentSplitter:
    """AI 智能文档拆分器 - 按语义主题拆分"""

    def __init__(self):
        self.logger = get_logger("AIDocumentSplitter")
        self.max_chunk_size = config.get("kb_ai_split_max_chunk_size", 800)

    def split(self, content: str, doc_name: str) -> List[Dict]:
        """
        使用 AI 智能拆分文档

        策略：
        1. 如果文档较短（< 300 字），不拆分
        2. 如果文档较长，调用 AI 分析主题边界
        3. 返回带语义标签的块

        Args:
            content: 文档内容
            doc_name: 文档名称

        Returns:
            List[Dict]: 文档块列表
        """
        try:
            # 清理内容
            content = content.strip()
            if not content:
                return []

            # 短文档不拆分
            if len(content) < 300:
                self.logger.info(f"文档 {doc_name} 较短 ({len(content)} 字)，不拆分")
                return [{
                    'title': doc_name,
                    'content': content,
                    'is_ai_split': False
                }]

            # 调用 AI 分析拆分
            self.logger.info(f"开始使用 AI 拆分文档: {doc_name} ({len(content)} 字)")
            chunks = self._call_ai_to_split(content, doc_name)

            if chunks:
                self.logger.info(f"AI 拆分完成: {doc_name} -> {len(chunks)} 个主题块")
                return chunks

            # AI 拆分失败，回退到简单拆分
            self.logger.warning(f"AI 拆分失败，使用简单拆分: {doc_name}")
            return self._fallback_split(content, doc_name)

        except Exception as e:
            self.logger.error(f"AI 拆分失败: {e}")
            return self._fallback_split(content, doc_name)

    def _call_ai_to_split(self, content: str, doc_name: str) -> Optional[List[Dict]]:
        """
        调用 AI 分析文档结构

        Returns:
            List[Dict]: 拆分后的块列表，每个块包含 title 和 content
        """
        try:
            # 根据配置选择 AI 提供商
            bot_type = config.get("bot_type", "coze")

            if bot_type == "qwen":
                return self._call_qwen_split(content, doc_name)
            elif bot_type == "kimi":
                return self._call_kimi_split(content, doc_name)
            else:
                return self._call_coze_split(content, doc_name)

        except Exception as e:
            self.logger.error(f"调用 AI 拆分失败: {e}")
            return None

    def _call_qwen_split(self, content: str, doc_name: str) -> Optional[List[Dict]]:
        """调用 Qwen AI 进行文档拆分"""
        try:
            import requests

            api_key = config.get("qwen_api_key", "")
            if not api_key:
                self.logger.error("Qwen API Key 未配置")
                return None

            prompt = self._build_split_prompt(content, doc_name)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": config.get("qwen_model", "qwen-turbo"),
                "messages": [
                    {
                        "role": "system",
                        "content": "你是文档分析助手，专门分析客服知识文档并按主题拆分。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3
            }

            response = requests.post(
                f"{config.get('qwen_api_base', 'https://dashscope.aliyuncs.com/api/v1')}/services/aigc/text-generation/generation",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("output", {}).get("text", "")
                return self._parse_split_result(text)
            else:
                self.logger.error(f"Qwen API 错误: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Qwen 拆分失败: {e}")
            return None

    def _call_kimi_split(self, content: str, doc_name: str) -> Optional[List[Dict]]:
        """调用 Kimi AI 进行文档拆分"""
        try:
            import requests

            api_key = config.get("kimi_api_key", "")
            if not api_key:
                self.logger.error("Kimi API Key 未配置")
                return None

            prompt = self._build_split_prompt(content, doc_name)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": config.get("kimi_model", "kimi-k2.5"),
                "messages": [
                    {
                        "role": "system",
                        "content": "你是文档分析助手，专门分析客服知识文档并按主题拆分。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3
            }

            response = requests.post(
                f"{config.get('kimi_api_base', 'https://api.moonshot.cn/v1')}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return self._parse_split_result(text)
            else:
                self.logger.error(f"Kimi API 错误: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Kimi 拆分失败: {e}")
            return None

    def _call_coze_split(self, content: str, doc_name: str) -> Optional[List[Dict]]:
        """调用 Coze AI 进行文档拆分"""
        try:
            import requests

            token = config.get("coze_token", "")
            bot_id = config.get("coze_bot_id", "")

            if not token or not bot_id:
                self.logger.error("Coze Token 或 Bot ID 未配置")
                return None

            prompt = self._build_split_prompt(content, doc_name)

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            data = {
                "bot_id": bot_id,
                "query": prompt,
                "stream": False
            }

            response = requests.post(
                f"{config.get('coze_api_base', 'https://api.coze.cn')}/open_api/v2/chat",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])
                for msg in messages:
                    if msg.get("type") == "answer":
                        return self._parse_split_result(msg.get("content", ""))
                return None
            else:
                self.logger.error(f"Coze API 错误: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Coze 拆分失败: {e}")
            return None

    def _build_split_prompt(self, content: str, doc_name: str) -> str:
        """构建拆分提示词"""
        return f"""请分析以下客服知识文档，按主题拆分成独立的知识点。

文档名称：{doc_name}

文档内容：
{content}

请按以下要求拆分：
1. 识别文档中的不同主题（如发货、退换货、售后等）
2. 每个主题应该是一个完整的知识点或问答
3. 每个块的内容不要超过 {self.max_chunk_size} 字
4. 为每个块起一个简洁的标题（5-15字）

必须返回以下 JSON 格式，不要添加其他说明：
{{
    "chunks": [
        {{"title": "主题标题1", "content": "具体内容1"}},
        {{"title": "主题标题2", "content": "具体内容2"}}
    ]
}}

注意：
- 确保 JSON 格式正确
- 每个 chunk 的 content 要完整保留原文
- 如果内容较少（少于2个主题），可以只返回1个 chunk"""

    def _parse_split_result(self, text: str) -> Optional[List[Dict]]:
        """解析 AI 返回的拆分结果"""
        try:
            # 尝试提取 JSON
            # 先找 JSON 代码块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                text = json_match.group(1)
            else:
                # 找花括号包裹的内容
                json_match = re.search(r'(\{[\s\S]*\})', text)
                if json_match:
                    text = json_match.group(1)

            result = json.loads(text)
            chunks = result.get("chunks", [])

            if not chunks:
                self.logger.warning("AI 返回的 chunks 为空")
                return None

            # 验证并清理结果
            valid_chunks = []
            for chunk in chunks:
                title = chunk.get("title", "").strip()
                content = chunk.get("content", "").strip()

                if title and content:
                    valid_chunks.append({
                        "title": title,
                        "content": content,
                        "is_ai_split": True
                    })

            return valid_chunks if valid_chunks else None

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"解析拆分结果失败: {e}")
            return None

    def _fallback_split(self, content: str, doc_name: str) -> List[Dict]:
        """
        回退拆分策略 - 按段落和长度拆分

        Args:
            content: 文档内容
            doc_name: 文档名称

        Returns:
            List[Dict]: 文档块列表
        """
        chunks = []

        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]

        current_chunk = []
        current_size = 0
        chunk_index = 0

        for para in paragraphs:
            para_size = len(para)

            if current_size + para_size > self.max_chunk_size and current_chunk:
                # 保存当前块
                chunk_content = '\n\n'.join(current_chunk)
                chunks.append({
                    'title': f'{doc_name}_{chunk_index}',
                    'content': chunk_content,
                    'is_ai_split': False
                })
                chunk_index += 1

                # 新块保留一些上下文
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # 添加最后一个块
        if current_chunk:
            chunk_content = '\n\n'.join(current_chunk)
            chunks.append({
                'title': f'{doc_name}_{chunk_index}' if chunk_index > 0 else doc_name,
                'content': chunk_content,
                'is_ai_split': False
            })

        return chunks

    def split_simple(self, content: str, doc_name: str, chunk_size: int = 500) -> List[Dict]:
        """
        简单拆分 - 按固定长度拆分（保留原功能）

        Args:
            content: 文档内容
            doc_name: 文档名称
            chunk_size: 每块大小

        Returns:
            List[Dict]: 文档块列表
        """
        chunks = []
        content_len = len(content)

        if content_len <= chunk_size:
            return [{
                'title': doc_name,
                'content': content,
                'is_ai_split': False
            }]

        # 按长度分割
        start = 0
        chunk_index = 0

        while start < content_len:
            end = min(start + chunk_size, content_len)

            # 尽量在句子边界分割
            if end < content_len:
                # 找最近的句号、问号、感叹号
                for sep in ['。', '？', '?', '!', '！', '\n']:
                    pos = content.rfind(sep, start, end)
                    if pos > start + chunk_size // 2:
                        end = pos + 1
                        break

            chunk_content = content[start:end].strip()
            if chunk_content:
                chunks.append({
                    'title': f'{doc_name}_{chunk_index}',
                    'content': chunk_content,
                    'is_ai_split': False
                })
                chunk_index += 1

            start = end

        return chunks
