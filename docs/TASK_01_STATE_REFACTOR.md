# First Technical Task: Refactoring state.py

## Task Overview

**目标**: 设计 SRE 全局状态 `SREState`，取代现有单 Agent 状态，支持 Multi-Agent 协作和状态机管理。

**预计时间**: 2-3 小时
**优先级**: 🔴 High (阻塞后续所有开发)
**难度**: Medium

---

## Current State Analysis

```python
# src/app/agents/state.py (现有)
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    knowledge_context: str
    need_knowledge: bool
    current_answer: str
    reflection: str
    is_satisfied: bool
    iteration: int
```

**局限性**:
- 仅支持单 Agent 对话流程
- 无事件/告警上下文
- 无多 Agent 协作状态
- 无状态机管理
- 无操作执行追踪

---

## Implementation Steps

### Step 1: Create `src/sre/agents/shared/state.py`

```python
"""SRE Agent 全局状态定义

支持 Multi-Agent 协作和事件状态机管理
"""

from typing import Annotated, Any, TypedDict
from datetime import datetime
from enum import Enum

from langgraph.graph.message import add_messages


class IncidentStatus(str, Enum):
    """事件状态枚举"""
    
    MONITORING = "monitoring"          # 监控收集信息
    DIAGNOSING = "diagnosing"          # 诊断分析中
    AWAITING_APPROVAL = "awaiting_approval"  # 等待人工审批
    EXECUTING = "executing"            # 执行修复操作
    VERIFYING = "verifying"            # 验证修复效果
    RESOLVED = "resolved"              # 已解决
    ESCALATED = "escalated"            # 已升级人工
    REJECTED = "rejected"              # 被拒绝/取消


class Severity(str, Enum):
    """事件严重级别"""
    
    CRITICAL = "critical"      # 生产事故
    HIGH = "high"              # 严重影响
    MEDIUM = "medium"          # 中度影响
    LOW = "low"                # 轻微问题
    INFO = "info"              # 信息提示


class ActionType(str, Enum):
    """操作类型"""
    
    QUERY = "query"                    # 查询类 (自动执行)
    DIAGNOSTIC = "diagnostic"          # 诊断类 (自动执行)
    REMEDIATION = "remediation"        # 修复类 (需审批)
    DESTRUCTIVE = "destructive"        # 高危类 (需二次确认)


class ActionItem(TypedDict):
    """计划执行的操作项"""
    
    id: str                            # 操作 ID
    type: ActionType                   # 操作类型
    tool_name: str                     # 工具名称
    parameters: dict[str, Any]         # 参数
    description: str                   # 操作说明
    requires_approval: bool            # 是否需要审批
    estimated_impact: str              # 预估影响
    created_at: datetime               # 创建时间


class ActionResult(TypedDict):
    """操作执行结果"""
    
    action_id: str                     # 对应 ActionItem ID
    status: str                        # success / failed / cancelled
    output: str                        # 执行输出
    error: str | None                  # 错误信息
    executed_at: datetime              # 执行时间
    executed_by: str                   # 执行者 (agent / user)


class SREState(TypedDict):
    """SRE Agent 全局状态
    
    用于在 Supervisor 和子 Agent 之间传递状态
    """
    
    # ==================== 基础信息 ====================
    incident_id: str                   # 事件唯一 ID
    alert_source: str                  # 告警来源 (prometheus/pagerduty/manual)
    severity: Severity                 # 严重级别
    title: str                         # 事件标题
    description: str                   # 事件描述
    created_at: datetime               # 创建时间
    updated_at: datetime               # 最后更新时间
    
    # ==================== 对话历史 ====================
    messages: Annotated[list, add_messages]  # 对话历史 (Human/AI)
    
    # ==================== 监控数据 ====================
    # Monitor Agent 收集的数据
    metrics_data: dict[str, Any]       # 指标数据 {metric_name: value}
    log_entries: list[dict]            # 相关日志条目
    resource_info: dict[str, Any]      # 受影响的资源信息
    time_context: dict[str, Any]       # 时间上下文 (部署时间、变更记录等)
    
    # ==================== 诊断结果 ====================
    # Diagnoser Agent 分析结果
    knowledge_context: str             # RAG 检索的知识
    diagnosis_report: str              # 诊断报告
    root_cause_hypotheses: list[dict]  # 根因假设列表
    # 每项: {"hypothesis": str, "confidence": float, "evidence": list}
    selected_hypothesis: int | None    # 选中的假设索引
    confidence_score: float            # 整体置信度 (0-1)
    
    # ==================== 执行计划 ====================
    # Executor Agent 管理
    action_plan: list[ActionItem]      # 生成的操作计划
    pending_approval: list[ActionItem] # 待审批的操作
    executed_actions: list[ActionResult]  # 已执行的操作结果
    rejected_actions: list[ActionItem] # 被拒绝的操作
    
    # ==================== 状态机 ====================
    status: IncidentStatus             # 当前事件状态
    previous_status: IncidentStatus | None  # 上一个状态
    
    # ==================== 迭代控制 ====================
    iteration: int                     # 当前迭代次数
    max_iterations: int                # 最大迭代次数
    
    # ==================== 人工介入 ====================
    assigned_to: str | None            # 分配给的处理人
    human_notes: list[dict]            # 人工备注
    approval_decisions: list[dict]     # 审批决策记录
    
    # ==================== 结果输出 ====================
    final_report: str | None           # 最终报告
    resolution_summary: str | None     # 解决方案摘要


# ==================== Agent 子集状态 (用于子 Agent 内部) ====================

class MonitorState(TypedDict):
    """Monitor Agent 内部状态"""
    
    incident_id: str
    resource_info: dict[str, Any]
    metrics_data: dict[str, Any]
    log_entries: list[dict]
    time_context: dict[str, Any]
    max_age_minutes: int               # 数据最大时间范围


class DiagnoserState(TypedDict):
    """Diagnoser Agent 内部状态"""
    
    incident_id: str
    monitor_data: MonitorState         # 引用监控数据
    knowledge_context: str
    iteration: int
    max_iterations: int
    current_hypotheses: list[dict]
    is_satisfied: bool                 # 是否满意诊断结果
    reflection: str                    # 改进建议


class ExecutorState(TypedDict):
    """Executor Agent 内部状态"""
    
    incident_id: str
    diagnosis_report: str
    action_plan: list[ActionItem]
    pending_approval: list[ActionItem]
    executed_actions: list[ActionResult]
    requires_human_approval: bool       # 是否需要人工审批
    current_action: ActionItem | None   # 当前执行的操作


class SupervisorState(TypedDict):
    """Supervisor Agent 内部状态"""
    
    incident_id: str
    status: IncidentStatus
    current_agent: str | None           # 当前激活的子 Agent
    next_agent: str | None              # 下一步调用的 Agent
    decision_reason: str                # 决策理由
    escalation_reason: str | None       # 升级理由
    requires_immediate_attention: bool  # 是否需要立即处理
```

### Step 2: Update imports and references

```python
# src/sre/agents/__init__.py
from src.sre.agents.shared.state import (
    SREState,
    MonitorState,
    DiagnoserState,
    ExecutorState,
    SupervisorState,
    IncidentStatus,
    Severity,
    ActionType,
    ActionItem,
    ActionResult,
)

__all__ = [
    "SREState",
    "MonitorState",
    "DiagnoserState",
    "ExecutorState",
    "SupervisorState",
    "IncidentStatus",
    "Severity",
    "ActionType",
    "ActionItem",
    "ActionResult",
]
```

### Step 3: Create state utilities

```python
# src/sre/agents/shared/state_utils.py
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
```

---

## Testing Requirements

创建 `tests/sre/unit/agents/test_state.py`:

```python
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
```

---

## Verification Checklist

- [ ] `SREState` 定义完整，包含所有必要字段
- [ ] 子 Agent 状态 (Monitor/Diagnoser/Executor/Supervisor) 已定义
- [ ] 枚举类型 (IncidentStatus, Severity, ActionType) 已定义
- [ ] 状态工具函数 (create_initial_state, update_status 等) 已实现
- [ ] 单元测试覆盖率 > 90%
- [ ] 通过 ruff format 和 ruff check
- [ ] 类型注解完整

---

## Next Steps After This Task

1. **Implement State Machine** (`src/sre/core/state_machine.py`)
   - 定义状态转换规则
   - 实现状态转换验证

2. **Create Monitor Agent Skeleton**
   - 基于 `MonitorState` 实现 Monitor Graph

3. **Setup Knowledge Module**
   - 实现 `shared/knowledge/` 基础结构
