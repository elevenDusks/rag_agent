"""数据库初始化脚本"""
import asyncio
import sys
sys.path.insert(0, 'backend/src')

from rag_agent.db.mysql_client import create_tables, AsyncSessionLocal
from rag_agent.models.user import User
from rag_agent.core.security import get_password_hash


async def init_db():
    print("正在创建数据库表...")
    await create_tables()
    print("数据库表创建完成")

    print("正在创建管理员账号...")
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.username == "admin")
        result = await session.execute(stmt)
        existing_admin = result.scalar_one_or_none()
        
        if not existing_admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                is_superuser=True,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            print("管理员账号创建完成: admin / admin123")
        else:
            print("管理员账号已存在")


if __name__ == "__main__":
    asyncio.run(init_db())
