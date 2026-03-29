"""文档处理器 - 支持多种格式的文档解析和分割"""
import os
import re
import hashlib
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

from utils.logger import get_logger
from config import config
from services.knowledge.ai_document_splitter import AIDocumentSplitter


class DocumentProcessor:
    """文档处理器 - 解析和分割文档"""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = 50):
        self.logger = get_logger("DocumentProcessor")
        self.chunk_size = chunk_size or config.get("kb_simple_chunk_size", 500)
        self.chunk_overlap = chunk_overlap
        self.ai_splitter = AIDocumentSplitter()

    def process_file(self, file_path: str, metadata: Optional[Dict] = None, split_mode: str = None) -> List[Dict]:
        """
        处理文件，返回文档块列表

        Args:
            file_path: 文件路径
            metadata: 额外元数据
            split_mode: 拆分模式 (ai | simple | none)，默认从配置读取

        Returns:
            List[Dict]: 文档块列表
        """
        try:
            path = Path(file_path)
            suffix = path.suffix.lower()

            # 根据文件类型选择解析方法
            if suffix == '.txt':
                content = self._read_txt(file_path)
            elif suffix == '.pdf':
                content = self._read_pdf(file_path)
            elif suffix in ['.docx', '.doc']:
                content = self._read_word(file_path)
            elif suffix in ['.md', '.markdown']:
                content = self._read_txt(file_path)
            else:
                self.logger.warning(f"不支持的文件格式: {suffix}")
                return []

            if not content.strip():
                return []

            # 生成根文档ID
            root_doc_id = self._generate_root_doc_id(path.name)

            # 获取拆分模式
            if split_mode is None:
                split_mode = config.get("kb_split_mode", "ai")

            # 根据模式拆分文档
            if split_mode == "ai":
                chunks = self.ai_splitter.split(content, path.name)
            elif split_mode == "simple":
                chunks = self.ai_splitter.split_simple(content, path.name, self.chunk_size)
            else:  # none - 不拆分
                chunks = [{'title': path.name, 'content': content, 'is_ai_split': False}]

            # 构建文档块
            documents = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{root_doc_id}_chunk_{i}"
                doc = {
                    'id': chunk_id,
                    'content': chunk['content'],
                    'metadata': {
                        'root_doc_id': root_doc_id,
                        'root_doc_name': path.name,
                        'chunk_title': chunk.get('title', f'块_{i}'),
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'is_chunk': True,
                        'is_ai_split': chunk.get('is_ai_split', False),
                        'split_method': split_mode,
                        'source': file_path,
                        'filename': path.name,
                        'added_at': datetime.now().isoformat(),
                        **(metadata or {})
                    }
                }
                documents.append(doc)

            self.logger.info(f"成功处理文件 {path.name}，生成 {len(documents)} 个文档块 (模式: {split_mode})")
            return documents

        except Exception as e:
            self.logger.error(f"处理文件失败 {file_path}: {e}")
            return []

    def process_text(self, text: str, doc_id: str = None, metadata: Optional[Dict] = None, split_mode: str = None) -> List[Dict]:
        """
        处理纯文本

        Args:
            text: 文本内容
            doc_id: 文档ID
            metadata: 元数据
            split_mode: 拆分模式 (ai | simple | none)

        Returns:
            List[Dict]: 文档块列表
        """
        try:
            if not text.strip():
                return []

            # 生成根文档ID
            title = doc_id or 'manual_text'
            root_doc_id = self._generate_root_doc_id(title)

            # 获取拆分模式
            if split_mode is None:
                split_mode = config.get("kb_split_mode", "ai")

            # 根据模式拆分文档
            if split_mode == "ai":
                chunks = self.ai_splitter.split(text, title)
            elif split_mode == "simple":
                chunks = self.ai_splitter.split_simple(text, title, self.chunk_size)
            else:  # none - 不拆分
                chunks = [{'title': title, 'content': text, 'is_ai_split': False}]

            documents = []
            for i, chunk in enumerate(chunks):
                chunk_id = f"{root_doc_id}_chunk_{i}"
                doc = {
                    'id': chunk_id,
                    'content': chunk['content'],
                    'metadata': {
                        'root_doc_id': root_doc_id,
                        'root_doc_name': title,
                        'chunk_title': chunk.get('title', f'块_{i}'),
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'is_chunk': True,
                        'is_ai_split': chunk.get('is_ai_split', False),
                        'split_method': split_mode,
                        'added_at': datetime.now().isoformat(),
                        **(metadata or {})
                    }
                }
                documents.append(doc)

            return documents

        except Exception as e:
            self.logger.error(f"处理文本失败: {e}")
            return []

    def _read_txt(self, file_path: str) -> str:
        """读取文本文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _read_pdf(self, file_path: str) -> str:
        """读取 PDF 文件"""
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            text_parts = []

            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

            return '\n\n'.join(text_parts)

        except ImportError:
            self.logger.error("pypdf 未安装，请运行: pip install pypdf")
            raise

    def _read_word(self, file_path: str) -> str:
        """读取 Word 文件"""
        try:
            from docx import Document

            doc = Document(file_path)
            text_parts = []

            for para in doc.paragraphs:
                if para.text.strip():
                    text_parts.append(para.text)

            return '\n\n'.join(text_parts)

        except ImportError:
            self.logger.error("python-docx 未安装，请运行: pip install python-docx")
            raise

    def _split_text(self, text: str) -> List[str]:
        """
        分割文本为块

        策略：
        1. 优先按段落分割
        2. 长段落再按句子分割
        3. 确保每个块不超过 chunk_size
        """
        # 清理文本
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)

        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_size = len(para)

            # 如果当前段落本身超过 chunk_size，需要进一步分割
            if para_size > self.chunk_size:
                # 先保存当前累积的内容
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    # 保留重叠部分
                    overlap_text = ' '.join(current_chunk)[-self.chunk_overlap:]
                    current_chunk = [overlap_text] if overlap_text else []
                    current_size = len(overlap_text)

                # 按句子分割长段落
                sentences = re.split(r'([。！？.!?])', para)
                for i in range(0, len(sentences) - 1, 2):
                    sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else '')
                    sentence = sentence.strip()

                    if not sentence:
                        continue

                    if current_size + len(sentence) > self.chunk_size:
                        if current_chunk:
                            chunks.append(' '.join(current_chunk))
                            overlap_text = ' '.join(current_chunk)[-self.chunk_overlap:]
                            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                            current_size = sum(len(s) for s in current_chunk)
                    else:
                        current_chunk.append(sentence)
                        current_size += len(sentence)

            else:
                # 正常段落处理
                if current_size + para_size > self.chunk_size:
                    chunks.append(' '.join(current_chunk))
                    overlap_text = ' '.join(current_chunk)[-self.chunk_overlap:]
                    current_chunk = [overlap_text, para] if overlap_text else [para]
                    current_size = sum(len(s) for s in current_chunk)
                else:
                    current_chunk.append(para)
                    current_size += para_size

        # 添加最后一个块
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text]

    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return ['.txt', '.pdf', '.docx', '.doc', '.md', '.markdown']

    def _generate_root_doc_id(self, filename: str) -> str:
        """生成根文档唯一ID"""
        # 使用文件名 + 时间戳哈希
        import time
        timestamp = str(int(time.time()))
        hash_input = f"{filename}_{timestamp}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        # 清理文件名，移除扩展名和特殊字符
        clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', Path(filename).stem)
        return f"root_{clean_name}_{hash_value}"
