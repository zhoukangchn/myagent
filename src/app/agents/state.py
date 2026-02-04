from typing import Any, Annotated, List, Optional, TypedDict
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """基础 Agent 状态"""
    messages: Annotated[list, add_messages]  # 对话历史
    knowledge_context: str      # 检索到的知识
    need_knowledge: bool        # 是否需要检索
    current_answer: str         # 当前生成的回答
    reflection: str             # 反思意见
    is_satisfied: bool          # 是否满意当前回答
    iteration: int              # 当前迭代轮次（最大 3）
    next_agent: Optional[str]   # 下一个执行的 Agent

class WarroomState(AgentState):
    """作战室 Agent 扩展状态"""
    
    # 故障基本信息
    incident_id: str
    incident_severity: str  # P0, P1, P2, etc.
    incident_status: str    # open, investigating, resolved
    
    # 团队协作
    assigned_team: str      # SRE, DBA, Middleware, etc.
    warroom_channel_id: str # Slack/Discord channel ID
    
    # 调查进展
    investigation_plan: List[str]
    root_cause: Optional[str]
    
    # 时间轴记录 (Historian 维护)
    timeline_logs: List[dict]  # {"timestamp": "", "event": "", "source": ""}
    
    # RAG 增强
    similar_past_incidents: List[str]
    
    # 原始告警数据 (用于 Sentinel 解析)
    raw_alert: Optional[dict]

