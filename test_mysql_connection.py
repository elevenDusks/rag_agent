"""测试 MySQL 数据库连接"""
import asyncio
import sys
import os

sys.path.insert(0, "backend/src")
os.chdir("d:/it/project/my-rag-agent")

from dotenv import load_dotenv
load_dotenv("backend/.env")

from rag_agent.db.mysql_client import async_engine


async def test_connection():
    print("正在测试 MySQL 连接...")
    print(f"连接 URL: mysql+aiomysql://root:***@localhost:3306/agent")

    try:
        async with async_engine.connect() as conn:
            from sqlalchemy import text
            result = await conn.execute(text("SELECT 1"))
            row = result.fetchone()
            print(f"\n✅ 连接成功！查询结果: {row}")

            result = await conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"📊 MySQL 版本: {version}")

            result = await conn.execute(text("SHOW DATABASES"))
            dbs = [row[0] for row in result.fetchall()]
            print(f"📦 数据库列表: {dbs}")

            if 'agent' in dbs:
                print("✅ 'agent' 数据库已存在")
            else:
                print("⚠️  'agent' 数据库不存在，需要手动创建")
            return True

    except Exception as e:
        print(f"\n❌ 连接失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)
