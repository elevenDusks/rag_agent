"""测试认证模块"""
import asyncio
import sys
import os

sys.path.insert(0, "backend/src")
os.chdir("d:/it/project/my-rag-agent")

from dotenv import load_dotenv
load_dotenv("backend/.env")


async def test_auth():
    print("测试认证模块...")
    
    from rag_agent.auth.oauth2 import get_password_hash, verify_password, create_access_token, decode_token
    
    # 测试密码哈希
    password = "test123"
    hashed = get_password_hash(password)
    print(f"密码哈希: {hashed[:50]}...")
    assert verify_password(password, hashed), "密码验证失败"
    assert not verify_password("wrong", hashed), "错误密码应该验证失败"
    print("✅ 密码哈希测试通过")
    
    # 测试 JWT
    token = create_access_token({"sub": "testuser", "user_id": 1})
    print(f"JWT Token: {token[:50]}...")
    data = decode_token(token)
    assert data.username == "testuser", "Token 解码失败"
    assert data.user_id == 1, "Token user_id 解码失败"
    print("✅ JWT 测试通过")
    
    print("\n🎉 认证模块测试完成！")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_auth())
    sys.exit(0 if success else 1)
