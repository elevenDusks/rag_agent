"""Agent 统一记忆接口

整合工作记忆、情景记忆和语义记忆，提供统一的记忆接口。
"""
from typing import List, Dict, Optional
from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from ..core.logger import logger


class AgentMemory:
    """Agent 统一记忆管理
    
    整合三层记忆系统，为 Agent 提供完整的记忆能力。
    """
    
    def __init__(
        self,
        session_id: str,
        max_working_messages: int = 20,
        max_episodic_limit: int = 10
    ):
        """
        Args:
            session_id: 会话 ID
            max_working_messages: 工作记忆最大消息数
            max_episodic_limit: 情景记忆召回数量
        """
        self.session_id = session_id
        self.working_memory = WorkingMemory(max_messages=max_working_messages)
        self.max_episodic_limit = max_episodic_limit
    
    # ==================== 工作记忆操作 ====================
    
    def add_user_message(self, content: str) -> None:
        """添加用户消息到工作记忆"""
        self.working_memory.add_user(content)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> None:
        """添加助手消息到工作记忆"""
        self.working_memory.add_assistant(content, metadata)
    
    def get_working_context(self, max_messages: int = 10) -> List[Dict]:
        """获取工作记忆上下文
        
        Args:
            max_messages: 最大消息数
            
        Returns:
            List[Dict]: 消息列表
        """
        return self.working_memory.get_last_n(max_messages)
    
    # ==================== 情景记忆操作 ====================
    
    async def save_tool_call(
        self,
        tool_name: str,
        input_data: Dict,
        output: str,
        success: bool = True
    ) -> None:
        """保存工具调用到情景记忆
        
        Args:
            tool_name: 工具名称
            input_data: 输入参数
            output: 输出结果
            success: 是否成功
        """
        importance = 0.8 if success else 0.9  # 错误记录更重要
        
        await EpisodicMemory.save_episode(
            session_id=self.session_id,
            episode_type="tool_call",
            content=f"{tool_name}: {output[:100]}",
            importance=importance,
            metadata={
                "tool": tool_name,
                "input": input_data,
                "success": success
            }
        )
    
    async def save_error(self, error_message: str) -> None:
        """保存错误到情景记忆"""
        await EpisodicMemory.save_episode(
            session_id=self.session_id,
            episode_type="error",
            content=error_message,
            importance=0.9,
            metadata={"type": "error"}
        )
    
    async def get_recent_episodes(self, limit: int = 10) -> List[Dict]:
        """获取最近的情景记忆"""
        return await EpisodicMemory.get_recent_episodes(
            session_id=self.session_id,
            limit=limit
        )
    
    async def get_episode_summary(self) -> str:
        """获取情景记忆摘要
        
        Returns:
            str: 摘要文本
        """
        episodes = await self.get_recent_episodes(limit=self.max_episodic_limit)
        
        if not episodes:
            return "无历史记忆。"
        
        summary_parts = []
        for ep in episodes:
            ep_type = ep.get("type", "")
            content = ep.get("content", "")[:50]
            summary_parts.append(f"[{ep_type}] {content}...")
        
        return "最近的记忆:\n" + "\n".join(summary_parts)
    
    # ==================== 语义记忆操作 ====================
    
    async def save_to_semantic(self, content: str, metadata: Optional[Dict] = None) -> None:
        """保存内容到语义记忆
        
        Args:
            content: 内容
            metadata: 元数据
        """
        await SemanticMemory.add_memory(
            content=content,
            metadata=metadata,
            session_id=self.session_id
        )
    
    async def retrieve_semantic(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索语义记忆
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            List[Dict]: 检索结果
        """
        return await SemanticMemory.retrieve(
            query=query,
            session_id=self.session_id,
            top_k=top_k
        )
    
    # ==================== 统一接口 ====================
    
    async def get_full_context(self, max_working: int = 10) -> Dict[str, any]:
        """获取完整的记忆上下文
        
        Args:
            max_working: 工作记忆的最大消息数
            
        Returns:
            Dict: 包含各层记忆的上下文
        """
        return {
            "session_id": self.session_id,
            "working": self.get_working_context(max_working),
            "episodic_summary": await self.get_episode_summary(),
            "recent_episodes": await self.get_recent_episodes(limit=5)
        }
    
    async def clear_all(self) -> None:
        """清空所有记忆"""
        self.working_memory.clear()
        await EpisodicMemory.clear_episodes(self.session_id)
        await SemanticMemory.delete_by_session(self.session_id)
        logger.info(f"清空 Agent 全部记忆: {self.session_id}")
    
    def clear_working(self) -> None:
        """只清空工作记忆"""
        self.working_memory.clear()
