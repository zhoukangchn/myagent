"""Supervisor Agent 节点逻辑

作为整个 SRE 系统的“指挥官”，负责状态路由和子 Agent 调度。
"""

from typing import Any, Dict, Literal
from src.app.core.logging import logger
from src.sre.agents.shared.state import SREState, IncidentStatus
from src.sre.core.state_machine import validate_transition

async def initialize_incident_node(state: SREState) -> Dict[str, Any]:
    """初始化事件：接收原始告警并设定初始状态"""
    logger.info(f"[Supervisor] 接收到新告警: {state.get('title', 'Unknown Incident')}")
    # 逻辑：如果状态是空的，设为 MONITORING
    if not state.get("status"):
        return {"status": IncidentStatus.MONITORING}
    return {}

async def router_node(state: SREState) -> Literal["monitor", "diagnoser", "executor", "end"]:
    """
    智能路由节点：根据当前状态机决定下一步跳转。
    """
    status = state.get("status")
    logger.info(f"[Supervisor] 当前事件状态: {status}")

    # 获取允许的状态转换（虽然目前仅用于日志和防御）
    allowed = get_allowed_transitions(status)
    logger.debug(f"[Supervisor] 允许的后续状态: {allowed}")

    if status == IncidentStatus.MONITORING:
        return "monitor"
    elif status == IncidentStatus.DIAGNOSING:
        return "diagnoser"
    elif status == IncidentStatus.EXECUTING:
        return "executor"
    elif status in [IncidentStatus.RESOLVED, IncidentStatus.REJECTED, IncidentStatus.ESCALATED]:
        return "end"
    
    # 如果状态不在预期内，尝试根据状态转换逻辑进行防御性路由
    if IncidentStatus.MONITORING in allowed:
        return "monitor"
    
    return "end"

async def finalize_report_node(state: SREState) -> Dict[str, Any]:
    """生成最终处理报告"""
    logger.info(f"[Supervisor] 正在生成事件 {state['incident_id']} 的闭环报告...")
    report = f"""
### SRE 事件闭环报告
- **ID**: {state['incident_id']}
- **结果**: {state['status']}
- **耗时**: {state.get('iteration', 0)} 次迭代
- **最终总结**: {state.get('resolution_summary', '处理完成')}
    """
    return {"final_report": report}
