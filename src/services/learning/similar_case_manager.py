"""
相似案例管理器
负责存储和检索人工优化后的高质量回复案例
支持向量检索和关键词匹配两种模式
"""

from typing import List, Dict, Optional
import json
import numpy as np
from db.db_manager import db_manager
from db.models import SimilarCase
from utils.logger import get_logger


class SimilarCaseManager:
    """相似案例管理器 - 存储和检索人工优化后的高质量回复"""

    def __init__(self):
        self.logger = get_logger("SimilarCaseManager")
        self.embedding_model = None
        self.has_embedding = self._try_load_embedding_model()

    def _try_load_embedding_model(self) -> bool:
        """尝试加载向量化模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self.embedding_model = SentenceTransformer(
                'paraphrase-multilingual-MiniLM-L12-v2',
                trust_remote_code=True
            )
            self.logger.info("成功加载向量化模型，启用向量检索")
            return True
        except ImportError:
            self.logger.warning(
                "未安装 sentence-transformers，使用关键词匹配降级方案。"
                "如需向量检索，请安装：pip install sentence-transformers"
            )
            return False
        except Exception as e:
            self.logger.warning(f"加载向量化模型失败：{e}，使用关键词匹配降级方案")
            return False

    def add_case(
        self,
        account_id: int,
        user_question: str,
        ai_reply: str,
        human_reply: str,
        category: str = "general",
        tags: Optional[str] = None
    ) -> int:
        """
        添加相似案例

        Args:
            account_id: 账号 ID
            user_question: 用户问题
            ai_reply: AI 原始回复
            human_reply: 人工优化回复
            category: 问题分类
            tags: 标签，逗号分隔

        Returns:
            案例 ID，失败返回 -1
        """
        session = db_manager.get_session()
        try:
            # 计算向量（如果可用）
            embedding = None
            if self.has_embedding and self.embedding_model:
                try:
                    vec = self.embedding_model.encode(user_question)
                    embedding = json.dumps(vec.tolist())
                except Exception as e:
                    self.logger.warning(f"计算向量失败：{e}")

            case = SimilarCase(
                account_id=account_id,
                user_question=user_question,
                ai_original_reply=ai_reply,
                human_optimized_reply=human_reply,
                question_embedding=embedding,
                category=category,
                tags=tags or "",
                status=0  # 待审核
            )

            session.add(case)
            session.commit()
            case_id = case.id
            self.logger.info(f"添加相似案例成功：case_id={case_id}, category={category}")
            return case_id

        except Exception as e:
            session.rollback()
            self.logger.error(f"添加案例失败：{e}")
            return -1
        finally:
            session.close()

    def search_similar(
        self,
        question: str,
        top_k: int = 3,
        min_similarity: float = 0.7,
        category: Optional[str] = None
    ) -> List[Dict]:
        """
        检索相似案例

        Args:
            question: 用户问题
            top_k: 返回数量
            min_similarity: 最小相似度阈值
            category: 问题分类过滤

        Returns:
            相似案例列表，包含案例对象和相似度
        """
        session = db_manager.get_session()
        try:
            if self.has_embedding and self.embedding_model:
                return self._search_by_embedding(
                    session, question, top_k, min_similarity, category
                )
            else:
                return self._search_by_keywords(
                    session, question, top_k, category
                )

        except Exception as e:
            self.logger.error(f"检索案例失败：{e}")
            return []
        finally:
            session.close()

    def _search_by_embedding(
        self,
        session,
        question: str,
        top_k: int,
        min_similarity: float,
        category: Optional[str]
    ) -> List[Dict]:
        """向量检索模式"""
        try:
            query_vec = np.array(self.embedding_model.encode(question))

            # 获取已启用的案例
            query = session.query(SimilarCase).filter(SimilarCase.status == 1)
            if category:
                query = query.filter(SimilarCase.category == category)
            cases = query.all()

            results = []
            for case in cases:
                if case.question_embedding:
                    try:
                        case_vec = np.array(json.loads(case.question_embedding))
                        similarity = self._cosine_similarity(query_vec, case_vec)
                        if similarity >= min_similarity:
                            results.append({
                                "case": case,
                                "similarity": float(similarity)
                            })
                    except Exception as e:
                        self.logger.debug(f"解析案例向量失败：{e}")

            # 按相似度排序
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]

        except Exception as e:
            self.logger.error(f"向量检索失败：{e}")
            return []

    def _search_by_keywords(
        self,
        session,
        question: str,
        top_k: int,
        category: Optional[str]
    ) -> List[Dict]:
        """关键词匹配模式（降级方案）"""
        # 获取已启用的案例
        query = session.query(SimilarCase).filter(SimilarCase.status == 1)
        if category:
            query = query.filter(SimilarCase.category == category)
        cases = query.all()

        # 分词（简单按空格和标点分割）
        import re
        question_words = set(re.split(r'[,\s,.!?;，。！？；]+', question))
        question_words = {w for w in question_words if w}  # 移除空字符串

        results = []
        for case in cases:
            # 计算词匹配得分
            score = sum(1 for word in question_words if word in case.user_question)
            if score > 0:
                similarity = score / max(len(question_words), 1)
                results.append({
                    "case": case,
                    "similarity": float(similarity)
                })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def get_case_by_id(self, case_id: int) -> Optional[SimilarCase]:
        """根据 ID 获取案例"""
        session = db_manager.get_session()
        try:
            case = session.query(SimilarCase).filter(
                SimilarCase.id == case_id
            ).first()
            return case
        except Exception as e:
            self.logger.error(f"获取案例失败：{e}")
            return None
        finally:
            session.close()

    def update_case_status(
        self,
        case_id: int,
        status: int,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """
        更新案例状态

        Args:
            case_id: 案例 ID
            status: 状态 (0-待审核，1-已启用，2-已禁用)
            reviewed_by: 审核人

        Returns:
            是否成功
        """
        session = db_manager.get_session()
        try:
            case = session.query(SimilarCase).filter(
                SimilarCase.id == case_id
            ).first()
            if case:
                case.status = status
                if reviewed_by:
                    case.reviewed_by = reviewed_by
                session.commit()
                self.logger.info(
                    f"更新案例状态：case_id={case_id}, status={status}"
                )
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"更新案例状态失败：{e}")
            return False
        finally:
            session.close()

    def get_pending_cases(
        self,
        account_id: Optional[int] = None,
        limit: int = 50
    ) -> List[SimilarCase]:
        """获取待审核案例列表"""
        session = db_manager.get_session()
        try:
            query = session.query(SimilarCase).filter(
                SimilarCase.status == 0  # 待审核
            )
            if account_id:
                query = query.filter(SimilarCase.account_id == account_id)
            return query.order_by(
                SimilarCase.created_at.desc()
            ).limit(limit).all()
        except Exception as e:
            self.logger.error(f"获取待审核案例失败：{e}")
            return []
        finally:
            session.close()

    def get_enabled_cases(
        self,
        account_id: Optional[int] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[SimilarCase]:
        """获取已启用案例列表"""
        session = db_manager.get_session()
        try:
            query = session.query(SimilarCase).filter(
                SimilarCase.status == 1  # 已启用
            )
            if account_id:
                query = query.filter(SimilarCase.account_id == account_id)
            if category:
                query = query.filter(SimilarCase.category == category)
            return query.order_by(
                SimilarCase.usage_count.desc()
            ).limit(limit).all()
        except Exception as e:
            self.logger.error(f"获取已启用案例失败：{e}")
            return []
        finally:
            session.close()

    def delete_case(self, case_id: int) -> bool:
        """删除案例"""
        session = db_manager.get_session()
        try:
            case = session.query(SimilarCase).filter(
                SimilarCase.id == case_id
            ).first()
            if case:
                session.delete(case)
                session.commit()
                self.logger.info(f"删除案例成功：case_id={case_id}")
                return True
            return False
        except Exception as e:
            session.rollback()
            self.logger.error(f"删除案例失败：{e}")
            return False
        finally:
            session.close()

    def get_statistics(self, account_id: Optional[int] = None) -> Dict:
        """获取案例统计信息"""
        session = db_manager.get_session()
        try:
            query = session.query(SimilarCase)
            if account_id:
                query = query.filter(SimilarCase.account_id == account_id)

            total = query.count()
            pending = query.filter(SimilarCase.status == 0).count()
            enabled = query.filter(SimilarCase.status == 1).count()
            disabled = query.filter(SimilarCase.status == 2).count()

            return {
                "total": total,
                "pending": pending,
                "enabled": enabled,
                "disabled": disabled
            }
        except Exception as e:
            self.logger.error(f"获取统计信息失败：{e}")
            return {"total": 0, "pending": 0, "enabled": 0, "disabled": 0}
        finally:
            session.close()
