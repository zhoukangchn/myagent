"""Agent Graph 构建"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.app.agents.specialized_nodes import (
    searcher_agent,
    writer_agent,
    reviewer_agent,
)
from src.app.agents.nodes import finalize_node
from src.app.agents.state import AgentState


def route_after_reviewer(state: AgentState) -> str:
    """路由：根据 Reviewer 的决定路由"""
    next_agent = state.get("next_agent", "end")
    if next_agent == "searcher":
        return "searcher"
    return "finalize"


def build_graph() -> CompiledStateGraph:
    """构建多智能体协同 Graph"""
    graph = StateGraph(AgentState)

    # 添加专家节点
    graph.add_node("searcher", searcher_agent)
    graph.add_node("writer", writer_agent)
    graph.add_node("reviewer", reviewer_agent)
    graph.add_node("finalize", finalize_node)

    # 定义流程
    graph.add_edge(START, "searcher")
    graph.add_edge("searcher", "writer")
    graph.add_edge("writer", "reviewer")
    
    # Reviewer 决定是打回重写还是最终交付
    graph.add_conditional_edges(
        "reviewer", 
        route_after_reviewer, 
        {"searcher": "searcher", "finalize": "finalize"}
    )
    
    graph.add_edge("finalize", END)

    return graph.compile()


# Agent 单例
agent = build_graph()
