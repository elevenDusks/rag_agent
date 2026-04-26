"""情景记忆

基于 Redis 存储的对话片段记忆。
"""
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from ..db.redis_client import redis_client
from ..core.logger import logger
from ..core.config import settings


class EpisodicMemory:
    """情景记忆（Redis 存储）
    
    存储对话片段，支持按时间范围检索和重要性评分。
    """
    
    # Redis key 前缀
    PREFIX = f"{settings.CHAT_MEMORY_PREFIX}:episodic"
    
    @classmethod
    def _get_key(cls, session_id: str) -> str:
        """生成 key"""
        return f"{cls.PREFIX}:{session_id}"
    
    @classmethod
    async def save_episode(
        cls,
        session_id: str,
        episode_type: str,
        content: str,
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> bool:
        """保存对话片段
        
        Args:
            session_id: 会话 ID
            episode_type: 片段类型 (chat, tool_call, error)
            content: 内容
            importance: 重要性 0-1
            metadata: 元数据
            
        Returns:
            bool: 是否成功
        """
        try:
            key = cls._get_key(session_id)
            
            episode = {
                "type": episode_type,
                "content": content,
                "importance": importance,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # 存储片段
            episode_json = json.dumps(episode)
            redis_client.rpush(key, episode_json)
            
            # 设置过期时间（7天）
            redis_client.expire(key, 7 * 24 * 60 * 60)
            
            logger.info(f"保存情景记忆: {session_id}, 类型: {episode_type}")
            return True
            
        except Exception as e:
            logger.error(f"保存情景记忆失败: {str(e)}")
            return False
    
    @classmethod
    async def get_recent_episodes(
        cls,
        session_id: str,
        limit: int = 10,
        episode_type: Optional[str] = None
    ) -> List[Dict]:
        """获取最近的片段
        
        Args:
            session_id: 会话 ID
            limit: 返回数量
            episode_type: 可选的类型过滤
            
        Returns:
            List[Dict]: 片段列表
        """
        try:
            key = cls._get_key(session_id)
            raw_episodes = redis_client.lrange(key, -limit, -1)
            
            episodes = []
            for raw in raw_episodes:
                episode = json.loads(raw)
                if episode_type is None or episode.get("type") == episode_type:
                    episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"获取情景记忆失败: {str(e)}")
            return []
    
    @classmethod
    async def get_important_episodes(
        cls,
        session_id: str,
        min_importance: float = 0.7,
        limit: int = 5
    ) -> List[Dict]:
        """获取重要的片段
        
        Args:
            session_id: 会话 ID
            min_importance: 最小重要性阈值
            limit: 返回数量
            
        Returns:
            List[Dict]: 重要片段列表
        """
        try:
            key = cls._get_key(session_id)
            raw_episodes = redis_client.lrange(key, 0, -1)
            
            episodes = []
            for raw in raw_episodes:
                episode = json.loads(raw)
                if episode.get("importance", 0) >= min_importance:
                    episodes.append(episode)
            
            # 按重要性排序
            episodes.sort(key=lambda x: x.get("importance", 0), reverse=True)
            return episodes[:limit]
            
        except Exception as e:
            logger.error(f"获取重要情景记忆失败: {str(e)}")
            return []
    
    @classmethod
    async def get_episodes_by_timerange(
        cls,
        session_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """按时间范围获取片段
        
        Args:
            session_id: 会话 ID
            start_time: 开始时间
            end_time: 结束时间（默认当前时间）
            
        Returns:
            List[Dict]: 时间范围内的片段
        """
        try:
            key = cls._get_key(session_id)
            raw_episodes = redis_client.lrange(key, 0, -1)
            
            end_time = end_time or datetime.now()
            episodes = []
            
            for raw in raw_episodes:
                episode = json.loads(raw)
                ts_str = episode.get("timestamp", "")
                if ts_str:
                    ts = datetime.fromisoformat(ts_str)
                    if start_time <= ts <= end_time:
                        episodes.append(episode)
            
            return episodes
            
        except Exception as e:
            logger.error(f"按时间范围获取记忆失败: {str(e)}")
            return []
    
    @classmethod
    async def clear_episodes(cls, session_id: str) -> bool:
        """清空情景记忆
        
        Args:
            session_id: 会话 ID
            
        Returns:
            bool: 是否成功
        """
        try:
            key = cls._get_key(session_id)
            redis_client.delete(key)
            logger.info(f"清空情景记忆: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"清空情景记忆失败: {str(e)}")
            return False
