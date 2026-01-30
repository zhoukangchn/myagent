from unittest.mock import AsyncMock, patch
import pytest
from src.app.agents.graph import agent
from langchain_core.messages import HumanMessage, AIMessage

@pytest.mark.asyncio
async def test_full_graph_simple_flow(mock_llm):
    """测试完整图流程：简单问候（不循环）"""
    # 1. Searcher 说不需要检索
    # 2. Writer 生成回答
    # 3. Reviewer 说满意
    
    # 模拟三个阶段的 LLM 返回
    # 注意：mock_llm.ainvoke 会按顺序被调用
    mock_llm.ainvoke.side_effect = [
        AIMessage(content="NO"),         # Searcher: need_knowledge
        AIMessage(content="你好！我是助手"), # Writer: current_answer
        AIMessage(content="SATISFIED")   # Reviewer: is_satisfied
    ]
    
    inputs = {"messages": [HumanMessage(content="你好")]}
    result = await agent.ainvoke(inputs)
    
    assert len(result["messages"]) > 1
    assert "助手" in result["messages"][-1].content
    assert result["iteration"] == 1
