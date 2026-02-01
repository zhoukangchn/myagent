"""Supervisor Agent 工作流定义"""

from langgraph.graph import StateGraph, START, END
from src.sre.agents.shared.state import SREState, IncidentStatus
from src.sre.agents.supervisor.nodes import (
    initialize_incident_node,
    router_node,
    finalize_report_node,
)
from src.sre.agents.monitor.graph import monitor_agent
from src.sre.agents.diagnoser.graph import diagnoser_agent
from src.sre.agents.executor.graph import executor_agent

def build_supervisor_graph():
    """构建 SRE 主工作流 Graph"""
    builder = StateGraph(SREState)
    
    # 1. 添加管理节点
    builder.add_node("initialize", initialize_incident_node)
    builder.add_node("finalize", finalize_report_node)
    
    # 2. 嵌入子 Agent (作为 Sub-graphs)
    # 注意：这里需要一些状态转换适配器，或者确保子 Agent 使用兼容的 State
    builder.add_node("monitor_agent", monitor_agent)
    builder.add_node("diagnoser_agent", diagnoser_agent)
    builder.add_node("executor_agent", executor_agent)
    
    # 3. 定义主流程
    builder.add_edge(START, "initialize")
    
    # 使用条件路由
    builder.add_conditional_edges(
        "initialize",
        router_node,
        {
            "monitor": "monitor_agent",
            "diagnoser": "diagnoser_agent",
            "executor": "executor_agent",
            "end": "finalize"
        }
    )
    
    # 子 Agent 完成后，回归路由中心
    builder.add_edge("monitor_agent", "initialize")
    builder.add_edge("diagnoser_agent", "initialize")
    builder.add_edge("executor_agent", "initialize")
    
    builder.add_edge("finalize", END)
    
    return builder.compile()

# 导出顶级指挥官
sre_supervisor = build_supervisor_graph()
