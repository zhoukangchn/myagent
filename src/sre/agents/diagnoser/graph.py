"""Diagnoser Agent 工作流定义"""

from langgraph.graph import StateGraph, START, END
from src.sre.agents.shared.state import DiagnoserState
from src.sre.agents.diagnoser.nodes import (
    query_knowledge_node,
    analyze_correlation_node,
    generate_hypothesis_node,
)

def build_diagnoser_graph():
    """构建 Diagnoser Agent 的内部工作流"""
    builder = StateGraph(DiagnoserState)
    
    # 添加节点
    builder.add_node("query_knowledge", query_knowledge_node)
    builder.add_node("analyze_correlation", analyze_correlation_node)
    builder.add_node("generate_hypothesis", generate_hypothesis_node)
    
    # 定义流程
    builder.add_edge(START, "query_knowledge")
    builder.add_edge("query_knowledge", "analyze_correlation")
    builder.add_edge("analyze_correlation", "generate_hypothesis")
    builder.add_edge("generate_hypothesis", END)
    
    return builder.compile()

# 导出编译后的 Graph
diagnoser_agent = build_diagnoser_graph()
