"""子图内循环示例

展示如何在子图内部实现自包含的循环逻辑。
典型场景：重试机制、迭代优化、批量处理
"""

from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, END


class LoopSubgraphState(TypedDict):
    """子图内部状态"""
    input_data: str
    iteration: int
    max_iterations: int
    result: str
    is_satisfied: bool


def process_node(state: LoopSubgraphState) -> LoopSubgraphState:
    """处理节点 - 模拟某种处理逻辑"""
    iteration = state["iteration"]
    print(f"  [子图循环] 第 {iteration + 1} 次处理...")
    
    # 模拟处理：达到最大次数或随机成功
    result = f"处理结果_{iteration}"
    is_satisfied = iteration >= 2  # 简化：第3次后满意
    
    return {
        **state,
        "iteration": iteration + 1,
        "result": result,
        "is_satisfied": is_satisfied,
    }


def check_condition(state: LoopSubgraphState) -> str:
    """条件检查 - 决定是否继续循环"""
    if state["is_satisfied"]:
        print("  [子图循环] 条件满足，退出循环")
        return "done"
    if state["iteration"] >= state["max_iterations"]:
        print("  [子图循环] 达到最大次数，退出循环")
        return "done"
    return "continue"


def create_loop_subgraph():
    """创建带有内部循环的子图"""
    builder = StateGraph(LoopSubgraphState)
    
    # 添加节点
    builder.add_node("process", process_node)
    builder.add_node("finalize", lambda s: {**s, "result": f"最终: {s['result']}"})
    
    # 设置入口
    builder.set_entry_point("process")
    
    # 添加条件边 - 核心：子图内的循环
    builder.add_conditional_edges(
        "process",
        check_condition,
        {
            "continue": "process",  # 循环回到自己
            "done": "finalize",     # 完成，进入结束
        }
    )
    
    builder.add_edge("finalize", END)
    
    return builder.compile()


# 导出入口
loop_subgraph = create_loop_subgraph()
