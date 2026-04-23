from ..core.config import settings

class ChatMemory:

    def __init__(self, redis_client):
        self.redis = redis_client

    def _build_key(self, session_id: str):
        return f"{settings.CHAT_MEMORY_PREFIX}:{session_id}"

    async def get_history(self, session_id: str) -> list:
        """
        返回格式：
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
        """

    async def append_message(self, session_id: str, role: str, content: str):
        """
        写入一条消息
        """

    async def trim_history(self, session_id: str):
        """
        保留最近 N 轮（你配置的 MAX_ROUNDS）
        """