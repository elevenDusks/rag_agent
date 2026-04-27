"""LangGraph Agent 测试脚本

用于测试 LangGraph Agent 的基本功能。
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from rag_agent.agent.langgraph import LangGraphAgent


async def test_basic():
    """测试基本问答（不需要工具）"""
    print("=" * 60)
    print("测试 1: 基本问答（不需要工具）")
    print("=" * 60)
    
    agent = LangGraphAgent(max_iterations=5)
    result = await agent.run("你好，请介绍一下你自己")
    
    print(f"问题: 你好，请介绍一下你自己")
    print(f"答案: {result.answer}")
    print(f"迭代次数: {result.iterations}")
    print(f"工具调用: {len(result.tool_calls)}")
    print()


async def test_datetime():
    """测试日期时间工具"""
    print("=" * 60)
    print("测试 2: 日期时间查询（需要工具）")
    print("=" * 60)
    
    agent = LangGraphAgent(max_iterations=5)
    result = await agent.run("今天几号？")
    
    print(f"问题: 今天几号？")
    print(f"答案: {result.answer}")
    print(f"迭代次数: {result.iterations}")
    print(f"工具调用: {result.tool_calls}")
    print()


async def test_calculator():
    """测试计算器工具"""
    print("=" * 60)
    print("测试 3: 数学计算（需要工具）")
    print("=" * 60)
    
    agent = LangGraphAgent(max_iterations=5)
    result = await agent.run("250 加 380 等于多少？")
    
    print(f"问题: 250 加 380 等于多少？")
    print(f"答案: {result.answer}")
    print(f"迭代次数: {result.iterations}")
    print(f"工具调用: {result.tool_calls}")
    print()


async def test_intermediate_steps():
    """测试中间步骤记录"""
    print("=" * 60)
    print("测试 4: 中间步骤记录")
    print("=" * 60)
    
    agent = LangGraphAgent(max_iterations=5)
    result = await agent.run("今天的日期是什么？")
    
    print(f"问题: 今天的日期是什么？")
    print(f"答案: {result.answer}")
    print(f"迭代次数: {result.iterations}")
    print(f"中间步骤:")
    for i, step in enumerate(result.intermediate_steps):
        print(f"  {i+1}. {step[:100]}...")
    print()


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("LangGraph Agent 测试")
    print("=" * 60 + "\n")
    
    try:
        await test_basic()
    except Exception as e:
        print(f"测试 1 失败: {e}\n")
    
    try:
        await test_datetime()
    except Exception as e:
        print(f"测试 2 失败: {e}\n")
    
    try:
        await test_calculator()
    except Exception as e:
        print(f"测试 3 失败: {e}\n")
    
    try:
        await test_intermediate_steps()
    except Exception as e:
        print(f"测试 4 失败: {e}\n")
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
