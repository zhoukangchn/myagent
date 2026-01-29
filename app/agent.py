"""LangGraph Agent 定义"""

from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.knowledge import search_knowledge


# Agent 状态定义
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    knowledge_context: str
    need_knowledge: bool


# 初始化 DeepSeek LLM
llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.7,
)


async def should_retrieve(state: AgentState) -> AgentState:
    """判断是否需要检索知识"""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    
    # 用 LLM 判断是否需要外部知识
    check_prompt = f"""判断以下问题是否需要查询外部知识库来回答。
如果是事实性问题、需要特定领域知识、或用户明确要求查询，回答 "YES"。
如果是闲聊、简单问候、或你能直接回答的通用问题，回答 "NO"。

问题: {last_message}

只回答 YES 或 NO:"""
    
    response = await llm.ainvoke([HumanMessage(content=check_prompt)])
    need_knowledge = "YES" in response.content.upper()
    
    return {**state, "need_knowledge": need_knowledge}


async def retrieve_knowledge(state: AgentState) -> AgentState:
    """检索外部知识"""
    if not state.get("need_knowledge", False):
        return {**state, "knowledge_context": ""}
    
    messages = state["messages"]
    query = messages[-1].content if messages else ""
    
    results = await search_knowledge(query)
    
    if results:
        context = "\n\n".join([
            f"[来源: {r.get('source', '未知')}]\n{r.get('content', '')}"
            for r in results
        ])
    else:
        context = ""
    
    return {**state, "knowledge_context": context}


async def generate_response(state: AgentState) -> AgentState:
    """生成回答"""
    messages = state["messages"]
    knowledge_context = state.get("knowledge_context", "")
    
    system_prompt = "你是一个有帮助的 AI 助手。"
    
    if knowledge_context:
        system_prompt += f"""

以下是从知识库中检索到的相关信息，请基于这些信息回答用户问题：

{knowledge_context}

如果检索到的信息不足以回答问题，请诚实说明。"""
    
    all_messages = [SystemMessage(content=system_prompt)] + messages
    response = await llm.ainvoke(all_messages)
    
    return {"messages": [response]}


def route_after_check(state: AgentState) -> str:
    """路由：是否需要检索"""
    if state.get("need_knowledge", False):
        return "retrieve"
    return "generate"


# 构建 Graph
def build_graph():
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("check", should_retrieve)
    graph.add_node("retrieve", retrieve_knowledge)
    graph.add_node("generate", generate_response)
    
    # 添加边
    graph.add_edge(START, "check")
    graph.add_conditional_edges(
        "check",
        route_after_check,
        {"retrieve": "retrieve", "generate": "generate"}
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    
    return graph.compile()


# 创建 agent 实例
agent = build_graph()
