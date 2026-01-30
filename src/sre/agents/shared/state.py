"""SRE Agent 全局状态定义

支持 Multi-Agent 协作和事件状态机管理
"""

from typing import Annotated, Any, TypedDict, Literal
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
