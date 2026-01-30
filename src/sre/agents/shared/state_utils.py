"""状态管理工具函数"""

from datetime import datetime
from uuid import uuid4

from src.sre.agents.shared.state import (
    ActionItem,
    ActionResult,
    IncidentStatus,
    SREState,
    Severity,
)


def create_initial_state(
    alert_source: str,
    severity: Severity,
    title: str,
    description: str = "",
    max_iterations: int = 5,
) -> SREState:
    """创建初始事件状态"""
    
    now = datetime.now()
    incident_id = f"INC-{now.strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
    
    return SREState(
        incident_id=incident_id,
        alert_source=alert_source,
        severity=severity,
        title=title,
        description=description,
        created_at=now,
        updated_at=now,
        messages=[],
        metrics_data={},
        log_entries=[],
        resource_info={},
        time_context={},
        knowledge_context="",
        diagnosis_report="",
        root_cause_hypotheses=[],
        selected_hypothesis=None,
        confidence_score=0.0,
        action_plan=[],
        pending_approval=[],
        executed_actions=[],
        rejected_actions=[],
        status=IncidentStatus.MONITORING,
        previous_status=None,
        iteration=0,
        max_iterations=max_iterations,
        assigned_to=None,
        human_notes=[],
        approval_decisions=[],
        final_report=None,
        resolution_summary=None,
    )


def update_status(state: SREState, new_status: IncidentStatus, reason: str = "") -> SREState:
    """更新事件状态"""
    
    return {
        **state,
        "previous_status": state["status"],
        "status": new_status,
        "updated_at": datetime.now(),
    }


def add_action_to_plan(state: SREState, action: ActionItem) -> SREState:
    """添加操作到计划"""
    
    current_plan = state.get("action_plan", [])
    return {
        **state,
        "action_plan": [*current_plan, action],
        "updated_at": datetime.now(),
    }


def record_action_result(state: SREState, result: ActionResult) -> SREState:
    """记录操作执行结果"""
    
    executed = state.get("executed_actions", [])
    return {
        **state,
        "executed_actions": [*executed, result],
        "updated_at": datetime.now(),
    }


def get_current_hypothesis(state: SREState) -> dict | None:
    """获取当前选中的根因假设"""
    
    idx = state.get("selected_hypothesis")
    hypotheses = state.get("root_cause_hypotheses", [])
    
    if idx is not None and 0 <= idx < len(hypotheses):
        return hypotheses[idx]
    return None


def is_auto_approvable(state: SREState) -> bool:
    """检查当前操作是否可自动批准 (基于策略)"""
    
    pending = state.get("pending_approval", [])
    if not pending:
        return True
    
    # 策略：只有 QUERY/DIAGNOSTIC 类型可自动执行
    for action in pending:
        if action["type"] not in ["query", "diagnostic"]:
            return False
    
    return True
