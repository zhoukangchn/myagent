"""嵌套子图示例

展示如何将一个子图作为节点嵌入到另一个图中。
典型场景：模块化设计、复用通用逻辑
"""

from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, END

from agent_builder.subgraphs.loop_example import loop_subgraph


class MainState(TypedDict):
    """主图状态"""
    input_text: str
    processed_by_subgraph: str
    final_output: str


# 模拟子图调用（实际使用 StateGraph 的 add_node 传入子图）
def call_loop_subgraph(state: MainState) -> MainState:
    """调用循环子图"""
    print(f"[主图] 调用子图处理: {state['input_text']}")
    
    # 准备子图输入
    subgraph_input = {
        "input_data": state["input_text"],
        "iteration": 0,
        "max_iterations": 3,
        "result": "",
        "is_satisfied": False,
    }
    
    # 执行子图
    result = loop_subgraph.invoke(subgraph_input)
    
    print(f"[主图] 子图返回: {result['result']}")
    
    return {
        **state,
        "processed_by_subgraph": result["result"],
    }


def finalize(state: MainState) -> MainState:
    """最终处理"""
    return {
        **state,
        "final_output": f"完成: {state['processed_by_subgraph']}",
    }


def create_main_graph():
    """创建包含子图的主图"""
    builder = StateGraph(MainState)
    
    builder.add_node("subgraph_call", call_loop_subgraph)
    builder.add_node("finalize", finalize)
    
    builder.set_entry_point("subgraph_call")
    builder.add_edge("subgraph_call", "finalize")
    builder.add_edge("finalize", END)
    
    return builder.compile()


# 导出入口
main_graph = create_main_graph()
