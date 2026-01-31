"""测试 Executor Agent 工作流"""

import pytest
from src.sre.agents.executor.graph import executor_agent

@pytest.mark.asyncio
async def test_executor_flow():
    """测试 Executor Agent 完整运行流程"""
    initial_state = {
        "incident_id": "TEST-EXEC-001",
        "diagnosis_report": "Root cause: DB Connection Leak",
        "action_plan": [],
        "pending_approval": [],
        "executed_actions": [],
        "requires_human_approval": False,
        "current_action": None
    }
    
    # 运行 Graph
    result = await executor_agent.ainvoke(initial_state)
    
    # 验证输出
    assert len(result["action_plan"]) > 0
    assert result["action_plan"][0]["tool_name"] == "restart_pod"
    assert len(result["executed_actions"]) > 0
    assert result["executed_actions"][0]["status"] == "success"
    assert "[Verification]" in result["diagnosis_report"]
