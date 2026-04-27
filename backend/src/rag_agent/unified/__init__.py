"""统一 LangChain/LangGraph 架构

提供完整的 LangChain/LangGraph 集成，统一管理：
- Memory: 记忆系统（Redis + Chroma）
- RAG Chain: 检索增强生成链
- Agent: 基于 LangGraph 的智能体
- State: 统一的状态管理

架构设计：
┌─────────────────────────────────────────────────────────────┐
│                    Unified Architecture                       │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LangGraph StateGraph                       │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │  route   │→│ retrieve │→│ generate │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
│                              ↓                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           LangChain LCEL Chains                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │  Retriever   │→ │   Reranker   │→ │  Generator   │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                              ↓                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           LangChain Memory API                          │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │ Buffer   │  │ Vector   │  │ Summary  │            │ │
│  │  │ Memory   │  │ Memory   │  │ Memory   │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
"""
from .memory import (
    LangChainMemoryManager,
    RedisChatMemory,
    VectorStoreMemory,
)
from .rag_chain import (
    RAGChainBuilder,
    HybridRetrieverChain,
)
from .agent import (
    UnifiedAgent,
    AgentConfig,
)
from .state import (
    UnifiedState,
    create_initial_state,
)

__all__ = [
    # Memory
    "LangChainMemoryManager",
    "RedisChatMemory",
    "VectorStoreMemory",
    # RAG Chain
    "RAGChainBuilder",
    "HybridRetrieverChain",
    # Agent
    "UnifiedAgent",
    "AgentConfig",
    # State
    "UnifiedState",
    "create_initial_state",
]
