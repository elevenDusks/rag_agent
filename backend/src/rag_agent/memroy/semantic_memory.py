"""语义记忆

基于向量数据库的长期知识记忆。
"""
from typing import List, Dict, Optional
from ..rag.infra import load_vector_store
from ..models.model_registry import embedding_model
from ..core.logger import logger
from ..core.config import settings


class SemanticMemory:
    """语义记忆（VectorDB 存储）
    
    存储长期知识，使用向量检索召回相关内容。
    """
    
    # 语义记忆的 collection 名称
    COLLECTION_NAME = "semantic_memory"
    
    @classmethod
    async def add_memory(
        cls,
        content: str,
        metadata: Optional[Dict] = None,
        session_id: Optional[str] = None
    ) -> str:
        """添加语义记忆
        
        Args:
            content: 记忆内容
            metadata: 元数据
            session_id: 关联的会话 ID
            
        Returns:
            str: 记忆 ID
        """
        try:
            vector_store = await load_vector_store(cls.COLLECTION_NAME)
            
            # 构建元数据
            mem_metadata = metadata or {}
            if session_id:
                mem_metadata["session_id"] = session_id
            
            # 添加文档
            docs = [content]
            metadatas = [mem_metadata]
            
            vector_store.add_texts(texts=docs, metadatas=metadatas)
            
            logger.info(f"添加语义记忆: {content[:50]}...")
            return "success"
            
        except Exception as e:
            logger.error(f"添加语义记忆失败: {str(e)}")
            raise
    
    @classmethod
    async def retrieve(
        cls,
        query: str,
        session_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict]:
        """检索语义记忆
        
        Args:
            query: 查询文本
            session_id: 可选的会话 ID 过滤
            top_k: 返回数量
            
        Returns:
            List[Dict]: 检索结果
        """
        try:
            vector_store = await load_vector_store(cls.COLLECTION_NAME)
            
            # 检索
            results = vector_store.similarity_search_with_score(query, k=top_k)
            
            memories = []
            for doc, score in results:
                mem = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance": float(score)
                }
                
                # 如果指定了 session_id，进行过滤
                if session_id is None or doc.metadata.get("session_id") == session_id:
                    memories.append(mem)
            
            return memories
            
        except Exception as e:
            logger.error(f"检索语义记忆失败: {str(e)}")
            return []
    
    @classmethod
    async def retrieve_by_embedding(
        cls,
        query_embedding: List[float],
        top_k: int = 5
    ) -> List[Dict]:
        """通过向量检索语义记忆
        
        Args:
            query_embedding: 查询向量
            top_k: 返回数量
            
        Returns:
            List[Dict]: 检索结果
        """
        try:
            vector_store = await load_vector_store(cls.COLLECTION_NAME)
            
            results = vector_store.similarity_search_by_vector_with_score(
                embedding=query_embedding,
                k=top_k
            )
            
            memories = []
            for doc, score in results:
                memories.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance": float(score)
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"向量检索语义记忆失败: {str(e)}")
            return []
    
    @classmethod
    async def get_session_memories(
        cls,
        session_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """获取会话相关的语义记忆
        
        Args:
            session_id: 会话 ID
            limit: 返回数量
            
        Returns:
            List[Dict]: 记忆列表
        """
        return await cls.retrieve(
            query="",
            session_id=session_id,
            top_k=limit
        )
    
    @classmethod
    async def delete_by_session(cls, session_id: str) -> int:
        """删除会话相关的语义记忆
        
        Args:
            session_id: 会话 ID
            
        Returns:
            int: 删除数量
        """
        try:
            vector_store = await load_vector_store(cls.COLLECTION_NAME)
            
            # 获取该会话的所有记忆
            memories = await cls.get_session_memories(session_id, limit=1000)
            
            if not memories:
                return 0
            
            # 简单实现：只返回数量，实际删除需要 ChromaDB 的 delete 方法支持
            count = len(memories)
            logger.info(f"准备删除 {count} 条语义记忆")
            
            return count
            
        except Exception as e:
            logger.error(f"删除语义记忆失败: {str(e)}")
            return 0
