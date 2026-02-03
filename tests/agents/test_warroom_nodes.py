import pytest
from src.app.agents.warroom_nodes import sentinel_node

@pytest.mark.asyncio
async def test_sentinel_node_success():
    # 模拟状态
    state = {
        "raw_alert": {
            "id": "INC-TEST-001",
            "severity": "P1",
            "message": "CPU Usage High"
        }
    }
    
    # 执行节点
    result = await sentinel_node(state)
    
    # 验证结果
    assert result["incident_id"] == "INC-TEST-001"
    assert result["incident_severity"] == "P1"
    assert result["incident_status"] == "open"
    assert result["next_agent"] == "strategist"

@pytest.mark.asyncio
async def test_sentinel_node_missing_alert():
    # 模拟空状态
    state = {}
    
    # 执行节点
    result = await sentinel_node(state)
    
    # 验证回退逻辑
    assert result["incident_id"] == "UNKNOWN"
    assert result["next_agent"] == "end"
