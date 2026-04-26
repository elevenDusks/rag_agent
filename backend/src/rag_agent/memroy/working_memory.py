"""工作记忆

当前对话的短期上下文，存储在内存中。
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """消息结构"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


class WorkingMemory:
    """工作记忆（短期记忆）
    
    存储当前对话的上下文信息，容量有限，需要定期清理。
    """
    
    def __init__(self, max_messages: int = 20):
        """
        Args:
            max_messages: 最大保存的消息数量
        """
        self._messages: List[Message] = []
        self._max_messages = max_messages
    
    def add(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """添加消息
        
        Args:
            role: 消息角色
            content: 消息内容
            metadata: 可选的元数据
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self._messages.append(message)
        
        # 如果超过最大数量，移除最早的消息
        if len(self._messages) > self._max_messages:
            self._messages.pop(0)
    
    def add_user(self, content: str) -> None:
        """添加用户消息"""
        self.add("user", content)
    
    def add_assistant(self, content: str, metadata: Optional[Dict] = None) -> None:
        """添加助手消息"""
        self.add("assistant", content, metadata)
    
    def add_system(self, content: str) -> None:
        """添加系统消息"""
        self.add("system", content)
    
    def get_messages(self) -> List[Dict]:
        """获取所有消息"""
        return [
            {"role": m.role, "content": m.content}
            for m in self._messages
        ]
    
    def get_last_n(self, n: int) -> List[Dict]:
        """获取最近 N 条消息"""
        messages = self._messages[-n:] if n > 0 else self._messages
        return [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
    
    def clear(self) -> None:
        """清空工作记忆"""
        self._messages.clear()
    
    def __len__(self) -> int:
        return len(self._messages)
    
    @property
    def is_empty(self) -> bool:
        return len(self._messages) == 0
