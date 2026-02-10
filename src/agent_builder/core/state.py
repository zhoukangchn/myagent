"""核心模块 - 状态定义与共享组件"""

from typing import TypedDict, Annotated
from operator import add


class AgentState(TypedDict):
    """主图状态定义"""
    messages: Annotated[list, add]  # 消息历史
    current_step: str               # 当前步骤标识
    subgraph_results: dict          # 子图执行结果
    loop_count: int                 # 循环计数
    is_complete: bool               # 是否完成
