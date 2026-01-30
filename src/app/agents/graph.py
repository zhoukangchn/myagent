"""Agent Graph 构建"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.nodes import (
    check_node,
    finalize_node,
    generate_node,
    reflect_node,
    retrieve_node,
)
from src.agents.state import AgentState


def route_after_check(state: AgentState) -> str:
    """路由：是否需要检索"""
    if state.get("need_knowledge", False):
        return "retrieve"
    return "generate"


def route_after_reflect(state: AgentState) -> str:
    """路由：反思后是否满意"""
    if state.get("is_satisfied", False):
        return "finalize"
    return "check"


def build_graph() -> CompiledStateGraph:
    """构建 Agent Graph"""
    graph = StateGraph(AgentState)

    # 添加节点
    graph.add_node("check", check_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("reflect", reflect_node)
    graph.add_node("finalize", finalize_node)

    # 添加边
    graph.add_edge(START, "check")
    graph.add_conditional_edges(
        "check", route_after_check, {"retrieve": "retrieve", "generate": "generate"}
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "reflect")
    graph.add_conditional_edges(
        "reflect", route_after_reflect, {"finalize": "finalize", "check": "check"}
    )
    graph.add_edge("finalize", END)

    return graph.compile()


# Agent 单例
agent = build_graph()
