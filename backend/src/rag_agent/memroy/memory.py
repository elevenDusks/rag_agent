import json
from typing import List, Dict
from ..db.redis_client import redis_client
from ..core.logger import logger
from ..core.config import settings

class ChatMemory:
    """对话记忆服务（Redis存储）"""

    @staticmethod
    async def _get_key(session_id: str) -> str:
        """生成用户唯一记忆Key"""
        return f"{settings.CHAT_MEMORY_PREFIX}:{session_id}"

    @classmethod
    async def get_history(cls,session_id: str) -> List[Dict]:
        """获取历史对话"""
        try:
            key = await cls._get_key(session_id)
            history_data = redis_client.lrange(key, 0, -1)
            return [json.loads(item) for item in history_data]
        except Exception as e:
            logger.error(f"获取对话记忆失败: {str(e)}")
            return []

    @classmethod
    async def add_message(cls,session_id: str, role: str, content: str):
        """追加对话到记忆（自动截断+自动过期）"""
        try:
            key = await cls._get_key(session_id)
            message = json.dumps({"role": role, "content": content})
            redis_client.rpush(key, message)
            # 截断：只保留最近 N 轮（保留索引 0 到 MAX*2-1）
            redis_client.ltrim(key, 0, settings.CHAT_MEMORY_MAX_ROUNDS * 2 - 1)
            # 刷新过期时间
            redis_client.expire(key, settings.CHAT_MEMORY_EXPIRE_SECONDS)
        except Exception as e:
            logger.error(f"写入对话记忆失败: {str(e)}")

    @classmethod
    async def clear_memory(cls,session_id: str):
        """清空用户会话记忆"""
        try:
            key = await cls._get_key(session_id)
            redis_client.delete(key)
            logger.info(f"清空记忆成功: {key}")
        except Exception as e:
            logger.error(f"清空记忆失败: {str(e)}")

    @classmethod
    async def build_chat_context_str(cls, session_id: str, question: str) -> str:
        """
        拼接历史对话 + 当前问题，返回**纯字符串**
        格式：自动区分用户/助手，换行分隔，适配大模型输入
        """
        history_list: List[Dict] = await cls.get_history(session_id)

        context_text = []
        for msg in history_list:
            prefix = "用户" if msg["role"] == "user" else "助手"
            context_text.append(f"{prefix}：{msg['content']}")

        context_text.append(f"用户：{question}")

        return "\n".join(context_text)