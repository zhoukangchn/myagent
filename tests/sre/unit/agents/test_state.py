"""测试 SREState 定义和工具函数"""

import pytest
from datetime import datetime

from src.sre.agents.shared.state import (
    SREState,
    IncidentStatus,
    Severity,
    ActionType,
    ActionItem,
    ActionResult,
)
from src.sre.agents.shared.state_utils import (
    create_initial_state,
    update_status,
    add_action_to_plan,
    record_action_result,
)


class TestSREState:
    """测试状态定义"""
    
    def test_create_initial_state(self):
        """测试初始状态创建"""
        state = create_initial_state(
            alert_source="prometheus",
            severity=Severity.HIGH,
            title="High CPU Usage",
            description="CPU > 90% for 5 minutes",
        )
        
        assert state["alert_source"] == "prometheus"
        assert state["severity"] == Severity.HIGH
        assert state["title"] == "High CPU Usage"
        assert state["status"] == IncidentStatus.MONITORING
        assert state["iteration"] == 0
        assert state["incident_id"].startswith("INC-")
    
    def test_update_status(self):
        """测试状态更新"""
        state = create_initial_state(
            alert_source="test",
            severity=Severity.LOW,
            title="Test",
        )
        
        new_state = update_status(state, IncidentStatus.DIAGNOSING, "开始诊断")
        
        assert new_state["status"] == IncidentStatus.DIAGNOSING
        assert new_state["previous_status"] == IncidentStatus.MONITORING
        assert new_state["updated_at"] > state["updated_at"]
    
    def test_add_action_to_plan(self):
        """测试添加操作"""
        state = create_initial_state(
            alert_source="test",
            severity=Severity.LOW,
            title="Test",
        )
        
        action: ActionItem = {
            "id": "act-001",
            "type": ActionType.QUERY,
            "tool_name": "get_pod_logs",
            "parameters": {"pod": "web-0"},
            "description": "查询 Pod 日志",
            "requires_approval": False,
            "estimated_impact": "无",
            "created_at": datetime.now(),
        }
        
        new_state = add_action_to_plan(state, action)
        
        assert len(new_state["action_plan"]) == 1
        assert new_state["action_plan"][0]["id"] == "act-001"
