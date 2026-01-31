"""SRE 事件状态机逻辑

管理 IncidentStatus 的合法转换和验证逻辑。
"""

from typing import Dict, Set, List
from src.sre.agents.shared.state import IncidentStatus

# 定义状态转换规则：{当前状态: {可以跳转的下一个状态}}
VALID_TRANSITIONS: Dict[IncidentStatus, Set[IncidentStatus]] = {
    IncidentStatus.MONITORING: {
        IncidentStatus.DIAGNOSING,
        IncidentStatus.ESCALATED,
        IncidentStatus.REJECTED
    },
    IncidentStatus.DIAGNOSING: {
        IncidentStatus.AWAITING_APPROVAL,
        IncidentStatus.EXECUTING,
        IncidentStatus.ESCALATED,
        IncidentStatus.MONITORING,
        IncidentStatus.REJECTED
    },
    IncidentStatus.AWAITING_APPROVAL: {
        IncidentStatus.EXECUTING,
        IncidentStatus.REJECTED,
        IncidentStatus.ESCALATED
    },
    IncidentStatus.EXECUTING: {
        IncidentStatus.VERIFYING,
        IncidentStatus.ESCALATED
    },
    IncidentStatus.VERIFYING: {
        IncidentStatus.RESOLVED,
        IncidentStatus.DIAGNOSING,
        IncidentStatus.ESCALATED
    },
    IncidentStatus.RESOLVED: {
        IncidentStatus.MONITORING  # 允许重新开启监控，处理回归问题
    },
    IncidentStatus.ESCALATED: {
        IncidentStatus.RESOLVED,
        IncidentStatus.REJECTED
    },
    IncidentStatus.REJECTED: set()  # 终态
}

def validate_transition(current_status: IncidentStatus, next_status: IncidentStatus) -> bool:
    """
    验证状态转换是否合法。
    
    Args:
        current_status: 当前状态
        next_status: 目标状态
        
    Returns:
        bool: 是否允许转换
    """
    if current_status == next_status:
        return True
        
    allowed_next = VALID_TRANSITIONS.get(current_status, set())
    return next_status in allowed_next

def get_allowed_transitions(current_status: IncidentStatus) -> List[IncidentStatus]:
    """
    获取当前状态下所有允许跳转的后续状态。
    """
    return list(VALID_TRANSITIONS.get(current_status, set()))

class StateTransitionError(Exception):
    """当尝试进行非法状态转换时抛出的异常"""
    def __init__(self, current: IncidentStatus, target: IncidentStatus):
        self.current = current
        self.target = target
        super().__init__(f"Invalid state transition: {current} -> {target}")
