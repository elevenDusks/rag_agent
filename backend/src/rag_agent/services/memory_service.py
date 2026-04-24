import json
from typing import List, Dict
from ..db.redis_client import redis_client
from ..core.logger import logger
from ..core.config import settings

class ChatMemoryService:
    """对话记忆服务（Redis存储）"""

    @staticmethod
    def _get_key(user_id: str, session_id: str) -> str:
        """生成用户唯一记忆Key"""
        return f"{settings.CHAT_MEMORY_PREFIX}:{user_id}:{session_id}"

    @classmethod
    def get_history(cls, user_id: str, session_id: str) -> List[Dict]:
        """获取历史对话"""
        try:
            key = cls._get_key(user_id, session_id)
            history_data = redis_client.lrange(key, 0, -1)
            return [json.loads(item) for item in history_data]
        except Exception as e:
            logger.error(f"获取对话记忆失败: {str(e)}")
            return []  # 异常降级：返回空历史

    @classmethod
    def add_message(cls, user_id: str, session_id: str, role: str, content: str):
        """追加对话到记忆（自动截断+自动过期）"""
        try:
            key = cls._get_key(user_id, session_id)
            message = json.dumps({"role": role, "content": content})
            # 追加对话
            redis_client.rpush(key, message)
            # 截断：只保留最近 N 轮（保留索引 0 到 MAX*2-1）
            redis_client.ltrim(key, 0, settings.CHAT_MEMORY_MAX_ROUNDS * 2 - 1)
            # 刷新过期时间
            redis_client.expire(key, settings.CHAT_MEMORY_EXPIRE_SECONDS)
        except Exception as e:
            logger.error(f"写入对话记忆失败: {str(e)}")

    @classmethod
    def clear_memory(cls, user_id: str, session_id: str):
        """清空用户会话记忆"""
        try:
            key = cls._get_key(user_id, session_id)
            redis_client.delete(key)
            logger.info(f"清空记忆成功: {key}")
        except Exception as e:
            logger.error(f"清空记忆失败: {str(e)}")