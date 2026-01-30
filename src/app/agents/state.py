"""Agent 状态定义"""

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Agent 状态"""

    # 对话历史
    messages: Annotated[list, add_messages]

    # 检索相关
    knowledge_context: str
    need_knowledge: bool

    # 生成相关
    current_answer: str

    # 反思相关
    reflection: str
    is_satisfied: bool

    # 控制
    iteration: int
