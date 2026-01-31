"""测试 Diagnoser Agent 工作流"""

import pytest
from src.sre.agents.diagnoser.graph import diagnoser_agent

@pytest.mark.asyncio
async def test_diagnoser_flow():
    """测试 Diagnoser Agent 完整运行流程"""
    initial_state = {
        "incident_id": "TEST-DIAG-001",
        "monitor_data": {
            "metrics_data": {"cpu": 0.9},
            "log_entries": [{"message": "error"}]
        },
        "knowledge_context": "",
        "iteration": 0,
        "max_iterations": 3,
        "current_hypotheses": [],
        "is_satisfied": False,
        "reflection": ""
    }
    
    # 运行 Graph
    result = await diagnoser_agent.ainvoke(initial_state)
    
    # 验证输出
    assert "knowledge_context" in result
    assert len(result["current_hypotheses"]) > 0
    assert result["is_satisfied"] is True
    assert result["current_hypotheses"][0]["confidence"] > 0
