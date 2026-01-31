"""Executor Agent 工作流定义"""

from langgraph.graph import StateGraph, START, END
from src.sre.agents.shared.state import ExecutorState
from src.sre.agents.executor.nodes import (
    plan_actions_node,
    execute_tool_node,
    verify_result_node,
)

def build_executor_graph():
    """构建 Executor Agent 的内部工作流"""
    builder = StateGraph(ExecutorState)
    
    # 添加节点
    builder.add_node("plan_actions", plan_actions_node)
    builder.add_node("execute_tool", execute_tool_node)
    builder.add_node("verify_result", verify_result_node)
    
    # 定义流程
    builder.add_edge(START, "plan_actions")
    builder.add_edge("plan_actions", "execute_tool")
    builder.add_edge("execute_tool", "verify_result")
    builder.add_edge("verify_result", END)
    
    return builder.compile()

# 导出编译后的 Graph
executor_agent = build_executor_graph()
