"""测试 SRE 状态机"""

import pytest
from src.sre.agents.shared.state import IncidentStatus
from src.sre.core.state_machine import validate_transition, StateTransitionError

def test_valid_transitions():
    """测试合法的状态转换"""
    # 正常诊断流程
    assert validate_transition(IncidentStatus.MONITORING, IncidentStatus.DIAGNOSING) is True
    assert validate_transition(IncidentStatus.DIAGNOSING, IncidentStatus.EXECUTING) is True
    assert validate_transition(IncidentStatus.EXECUTING, IncidentStatus.VERIFYING) is True
    assert validate_transition(IncidentStatus.VERIFYING, IncidentStatus.RESOLVED) is True

def test_invalid_transitions():
    """测试非法的状态转换"""
    # 不能直接从监控跳到执行
    assert validate_transition(IncidentStatus.MONITORING, IncidentStatus.EXECUTING) is False
    # 已解决的状态不能直接跳到执行修复
    assert validate_transition(IncidentStatus.RESOLVED, IncidentStatus.EXECUTING) is False

def test_self_transition():
    """测试原地跳转（通常允许，表示状态未变）"""
    assert validate_transition(IncidentStatus.DIAGNOSING, IncidentStatus.DIAGNOSING) is True

def test_escalation_paths():
    """测试升级路径"""
    # 几乎所有中间状态都应该能升级人工
    assert validate_transition(IncidentStatus.MONITORING, IncidentStatus.ESCALATED) is True
    assert validate_transition(IncidentStatus.DIAGNOSING, IncidentStatus.ESCALATED) is True
    assert validate_transition(IncidentStatus.AWAITING_APPROVAL, IncidentStatus.ESCALATED) is True
