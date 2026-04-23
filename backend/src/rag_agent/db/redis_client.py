# 导入你统一的配置类
from ..core.config import settings
import redis

# ====================== Redis 客户端（统一配置，自动读取） ======================
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    decode_responses=True  # 自动解码字符串，不用处理bytes
)

# ====================== 测试连接 ======================
if __name__ == "__main__":
    try:
        redis_client.ping()
        print("✅ Redis 连接成功！配置读取自统一 Settings")
    except Exception as e:
        print(f"❌ Redis 连接失败：{e}")