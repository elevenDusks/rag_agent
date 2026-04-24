"""登录认证测试脚本

测试项目中的用户注册、登录、Token验证等功能
"""
import asyncio
import sys
import os
import httpx

sys.path.insert(0, "backend/src")
os.chdir("d:/it/project/my-rag-agent")

from dotenv import load_dotenv
load_dotenv("backend/.env")


BASE_URL = "http://localhost:8000"


async def test_register(client: httpx.AsyncClient, username: str, email: str, password: str):
    """测试用户注册"""
    print(f"\n📝 注册用户: {username}")
    try:
        response = await client.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "full_name": f"Test {username}"
            }
        )
        if response.status_code == 200:
            user = response.json()
            print(f"✅ 注册成功! 用户ID: {user['id']}, 用户名: {user['username']}")
            return user
        else:
            print(f"❌ 注册失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 注册请求失败: {e}")
        return None


async def test_login(client: httpx.AsyncClient, username: str, password: str):
    """测试用户登录"""
    print(f"\n🔐 登录用户: {username}")
    try:
        response = await client.post(
            f"{BASE_URL}/api/auth/login",
            data={
                "username": username,
                "password": password
            }
        )
        if response.status_code == 200:
            token_data = response.json()
            print(f"✅ 登录成功! Token: {token_data['access_token'][:50]}...")
            return token_data["access_token"]
        else:
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 登录请求失败: {e}")
        return None


async def test_get_me(client: httpx.AsyncClient, token: str):
    """测试获取当前用户信息"""
    print(f"\n👤 获取当前用户信息")
    try:
        response = await client.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            user = response.json()
            print(f"✅ 获取成功! 用户名: {user['username']}, 邮箱: {user['email']}")
            return user
        else:
            print(f"❌ 获取失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 获取用户信息请求失败: {e}")
        return None


async def test_protected_endpoint(client: httpx.AsyncClient, token: str):
    """测试访问受保护的端点"""
    print(f"\n🔒 测试访问受保护端点")

    # 测试不带 token 访问
    print("  - 不带 Token 访问...")
    response = await client.get(f"{BASE_URL}/api/auth/me")
    if response.status_code == 401:
        print("    ✅ 正确拒绝: 需要认证")
    else:
        print(f"    ⚠️ 意外响应: {response.status_code}")

    # 测试带错误 token 访问
    print("  - 带错误 Token 访问...")
    response = await client.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    if response.status_code == 401:
        print("    ✅ 正确拒绝: 无效 Token")
    else:
        print(f"    ⚠️ 意外响应: {response.status_code}")

    # 测试带正确 token 访问
    print("  - 带正确 Token 访问...")
    response = await client.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        print("    ✅ 访问成功!")
    else:
        print(f"    ⚠️ 意外响应: {response.status_code}")


async def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 开始登录认证测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 测试用户名和密码
        test_username = "testuser001"
        test_email = "testuser001@example.com"
        test_password = "test123456"

        # 1. 注册用户
        print("\n" + "=" * 60)
        print("测试 1: 用户注册")
        print("=" * 60)
        await test_register(client, test_username, test_email, test_password)

        # 2. 登录获取 Token
        print("\n" + "=" * 60)
        print("测试 2: 用户登录")
        print("=" * 60)
        token = await test_login(client, test_username, test_password)

        # 3. 使用 Token 获取用户信息
        if token:
            print("\n" + "=" * 60)
            print("测试 3: 使用 Token 获取用户信息")
            print("=" * 60)
            await test_get_me(client, token)

            # 4. 测试受保护的端点
            print("\n" + "=" * 60)
            print("测试 4: 访问受保护的端点")
            print("=" * 60)
            await test_protected_endpoint(client, token)

        # 5. 测试错误密码登录
        print("\n" + "=" * 60)
        print("测试 5: 错误密码登录")
        print("=" * 60)
        await test_login(client, test_username, "wrong_password")

        # 6. 测试重复注册
        print("\n" + "=" * 60)
        print("测试 6: 重复注册")
        print("=" * 60)
        await test_register(client, test_username, test_email, test_password)

    print("\n" + "=" * 60)
    print("🎉 所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    print("⚠️  请确保 FastAPI 服务正在运行 (uvicorn main:app)")
    print("⚠️  默认服务地址: http://localhost:8000\n")
    asyncio.run(main())
