"""LangChain Memory 统一管理

提供与 LangChain Memory API 兼容的记忆系统。
同时支持 Redis（短期记忆）和 Chroma（长期语义记忆）。
"""
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.memory import BaseMemory

from ..core.logger import logger
from ..core.config import settings
from ..db.redis_client import redis_client


# ============================================================
# LangChain BaseChatMessageHistory 实现（Redis）
# ============================================================
class RedisChatMessageHistory(BaseChatMessageHistory):
    """Redis 存储的聊天历史，与 LangChain 兼容"""

    def __init__(
        self,
        session_id: str,
        max_messages: int = 50,
        prefix: str = None
    ):
        self.session_id = session_id
        self.max_messages = max_messages
        self.prefix = prefix or settings.CHAT_MEMORY_PREFIX
        self.key = f"{self.prefix}:{session_id}"

    @property
    def messages(self) -> List[BaseMessage]:
        """获取消息历史"""
        try:
            import json
            raw_messages = redis_client.lrange(self.key, 0, -1)
            result = []
            for raw in raw_messages:
                msg_dict = json.loads(raw)
                role = msg_dict.get("role", "")
                content = msg_dict.get("content", "")
                if role == "user":
                    result.append(HumanMessage(content=content))
                elif role == "assistant":
                    result.append(AIMessage(content=content))
                elif role == "system":
                    result.append(SystemMessage(content=content))
            return result
        except Exception as e:
            logger.error(f"获取消息历史失败: {e}")
            return []

    def add_message(self, message: BaseMessage) -> None:
        """添加消息"""
        import json
        try:
            role = self._get_role_from_message(message)
            content = message.content if hasattr(message, 'content') else str(message)
            msg_dict = {"role": role, "content": content}
            
            redis_client.rpush(self.key, json.dumps(msg_dict, ensure_ascii=False))
            redis_client.ltrim(self.key, 0, self.max_messages * 2 - 1)
            redis_client.expire(self.key, settings.CHAT_MEMORY_EXPIRE_SECONDS)
        except Exception as e:
            logger.error(f"添加消息失败: {e}")

    def add_user_message(self, message: str) -> None:
        """添加用户消息"""
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        """添加 AI 消息"""
        self.add_message(AIMessage(content=message))

    def clear(self) -> None:
        """清空历史"""
        redis_client.delete(self.key)

    def _get_role_from_message(self, message: BaseMessage) -> str:
        """从消息类型推断角色"""
        if isinstance(message, HumanMessage):
            return "user"
        elif isinstance(message, AIMessage):
            return "assistant"
        elif isinstance(message, SystemMessage):
            return "system"
        return "unknown"


# ============================================================
# LangChain BaseMemory 实现（自动管理历史）
# ============================================================
class BufferMemory(BaseMemory):
    """缓冲区记忆，自动管理对话历史"""

    def __init__(
        self,
        chat_memory: BaseChatMessageHistory = None,
        max_messages: int = 20,
        return_messages: bool = True,
        input_key: str = "input",
        output_key: str = "output"
    ):
        self.chat_memory = chat_memory or RedisChatMessageHistory(
            session_id="default",
            max_messages=max_messages
        )
        self.max_messages = max_messages
        self.return_messages = return_messages
        self.input_key = input_key
        self.output_key = output_key

    @property
    def memory_variables(self) -> List[str]:
        """返回可用的记忆变量"""
        return ["history"]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载记忆变量"""
        messages = self.chat_memory.messages
        # 只保留最近的消息
        recent_messages = messages[-self.max_messages:] if self.max_messages else messages
        
        if self.return_messages:
            return {"history": recent_messages}
        else:
            # 返回格式化字符串
            history_str = self._format_messages(recent_messages)
            return {"history": history_str}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """保存上下文（输入和输出）"""
        input_text = inputs.get(self.input_key, "")
        output_text = outputs.get(self.output_key, "")
        
        if input_text:
            self.chat_memory.add_user_message(input_text)
        if output_text:
            self.chat_memory.add_ai_message(output_text)

    def clear(self) -> None:
        """清空记忆"""
        self.chat_memory.clear()

    def _format_messages(self, messages: List[BaseMessage]) -> str:
        """格式化消息为字符串"""
        result = []
        for msg in messages:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            content = msg.content if hasattr(msg, 'content') else str(msg)
            result.append(f"{role}：{content}")
        return "\n".join(result)


# ============================================================
# 向量存储记忆（语义记忆）
# ============================================================
class VectorStoreMemory(BaseMemory):
    """向量存储记忆，支持语义检索"""

    def __init__(
        self,
        vector_store: Any = None,
        session_id: str = "default",
        memory_key: str = "semantic_memory",
        search_kwargs: Dict[str, Any] = None
    ):
        self.vector_store = vector_store
        self.session_id = session_id
        self.memory_key = memory_key
        self.search_kwargs = search_kwargs or {"k": 3}

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """加载语义记忆"""
        if not self.vector_store:
            return {self.memory_key: ""}

        query = inputs.get("input", "")
        if not query:
            return {self.memory_key: ""}

        try:
            docs = self.vector_store.similarity_search(query, **self.search_kwargs)
            memory_text = "\n\n".join([doc.page_content for doc in docs])
            return {self.memory_key: memory_text}
        except Exception as e:
            logger.error(f"加载语义记忆失败: {e}")
            return {self.memory_key: ""}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """保存上下文到向量存储"""
        if not self.vector_store:
            return

        content = inputs.get("input", "") + "\n" + outputs.get("output", "")
        if content.strip():
            from langchain_core.documents import Document
            doc = Document(
                page_content=content,
                metadata={"session_id": self.session_id}
            )
            self.vector_store.add_documents([doc])

    def clear(self) -> None:
        """清空向量存储中的相关记忆"""
        # 实现删除逻辑
        pass


# ============================================================
# 统一记忆管理器
# ============================================================
class LangChainMemoryManager:
    """统一记忆管理器

    整合 BufferMemory 和 VectorStoreMemory，
    提供完整的三层记忆支持。
    """

    def __init__(
        self,
        session_id: str,
        max_buffer_messages: int = 20,
        vector_store: Any = None
    ):
        self.session_id = session_id
        
        # 短期记忆（Redis）
        self.chat_history = RedisChatMessageHistory(
            session_id=session_id,
            max_messages=max_buffer_messages
        )
        
        # 缓冲区记忆
        self.buffer_memory = BufferMemory(
            chat_memory=self.chat_history,
            max_messages=max_buffer_messages,
            return_messages=True
        )
        
        # 语义记忆
        self.semantic_memory = VectorStoreMemory(
            vector_store=vector_store,
            session_id=session_id
        )

    def get_messages(self) -> List[BaseMessage]:
        """获取所有消息"""
        return self.chat_history.messages

    def add_user_message(self, content: str) -> None:
        """添加用户消息"""
        self.chat_history.add_user_message(content)

    def add_ai_message(self, content: str) -> None:
        """添加 AI 消息"""
        self.chat_history.add_ai_message(content)

    def clear(self) -> None:
        """清空所有记忆"""
        self.chat_history.clear()

    def get_context_for_llm(self, current_input: str) -> Dict[str, Any]:
        """获取 LLM 所需的上下文

        Args:
            current_input: 当前输入

        Returns:
            Dict: 包含 history 和 semantic_memory 的上下文
        """
        # 获取对话历史
        history_result = self.buffer_memory.load_memory_variables({"input": current_input})
        
        # 获取语义记忆
        semantic_result = self.semantic_memory.load_memory_variables({"input": current_input})
        
        return {
            "history": history_result.get("history", []),
            "semantic_memory": semantic_result.get("semantic_memory", ""),
            "history_str": self._format_history(history_result.get("history", []))
        }

    def _format_history(self, messages: List[BaseMessage]) -> str:
        """格式化历史消息"""
        result = []
        for msg in messages:
            role = "用户" if isinstance(msg, HumanMessage) else "助手"
            content = msg.content if hasattr(msg, 'content') else str(msg)
            result.append(f"{role}：{content}")
        return "\n".join(result)

    @property
    def memory_variables(self) -> List[str]:
        """获取所有记忆变量"""
        return ["history", "semantic_memory"]
