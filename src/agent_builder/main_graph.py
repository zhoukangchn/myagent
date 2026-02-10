"""主流程入口

展示如何组合多个子图构建复杂 Agent 系统
"""

from langgraph.graph import StateGraph, END

from agent_builder.core.state import AgentState
from agent_builder.subgraphs import loop_subgraph, main_graph


def create_advanced_graph():
    """创建高级流程 - 演示子图组合"""
    # 这是一个占位，后续扩展
    pass


if __name__ == "__main__":
    # 运行嵌套子图示例
    print("=" * 50)
    print("运行嵌套子图示例")
    print("=" * 50)
    
    result = main_graph.invoke({
        "input_text": "测试输入",
        "processed_by_subgraph": "",
        "final_output": "",
    })
    
    print(f"\n最终结果: {result['final_output']}")
