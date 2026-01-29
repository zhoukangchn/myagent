"""LangGraph Agent 定义 - 带自我反思"""

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
    current_answer: str
    reflection: str
    is_satisfied: bool
    iteration: int  # 防止无限循环


# 初始化 DeepSeek LLM
llm = ChatOpenAI(
    model=DEEPSEEK_MODEL,
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    temperature=0.7,
)

MAX_ITERATIONS = 3  # 最多反思次数


async def should_retrieve(state: AgentState) -> AgentState:
    """判断是否需要检索知识"""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    reflection = state.get("reflection", "")
    
    # 如果有反思反馈，考虑进去
    if reflection:
        check_prompt = f"""之前的回答被评估为不够好，反思意见如下：
{reflection}

原问题: {last_message}

判断是否需要重新查询外部知识库来改进回答。
回答 YES 或 NO:"""
    else:
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
    reflection = state.get("reflection", "")
    
    # 如果有反思，优化查询
    if reflection:
        refine_prompt = f"""原问题: {query}

之前的回答不够好，反思意见: {reflection}

请生成一个更好的搜索查询来获取缺失的信息。只输出查询词，不要解释:"""
        response = await llm.ainvoke([HumanMessage(content=refine_prompt)])
        query = response.content.strip()
    
    results = await search_knowledge(query)
    
    if results:
        # 合并新旧知识
        old_context = state.get("knowledge_context", "")
        new_context = "\n\n".join([
            f"[来源: {r.get('source', '未知')}]\n{r.get('content', '')}"
            for r in results
        ])
        context = f"{old_context}\n\n--- 新检索结果 ---\n{new_context}" if old_context else new_context
    else:
        context = state.get("knowledge_context", "")
    
    return {**state, "knowledge_context": context}


async def generate_response(state: AgentState) -> AgentState:
    """生成回答"""
    messages = state["messages"]
    knowledge_context = state.get("knowledge_context", "")
    reflection = state.get("reflection", "")
    iteration = state.get("iteration", 0)
    
    system_prompt = "你是一个有帮助的 AI 助手。请提供准确、完整、有深度的回答。"
    
    if knowledge_context:
        system_prompt += f"""

以下是从知识库中检索到的相关信息：

{knowledge_context}

请基于这些信息回答用户问题。如果信息不足，请诚实说明。"""
    
    if reflection and iteration > 0:
        system_prompt += f"""

之前的回答有以下问题，请在这次回答中改进：
{reflection}"""
    
    all_messages = [SystemMessage(content=system_prompt)] + messages
    response = await llm.ainvoke(all_messages)
    
    return {
        **state,
        "current_answer": response.content,
        "iteration": iteration + 1
    }


async def reflect_on_answer(state: AgentState) -> AgentState:
    """反思评估回答质量"""
    messages = state["messages"]
    question = messages[-1].content if messages else ""
    answer = state.get("current_answer", "")
    knowledge_context = state.get("knowledge_context", "")
    iteration = state.get("iteration", 0)
    
    # 如果已经达到最大迭代次数，直接满意
    if iteration >= MAX_ITERATIONS:
        return {**state, "is_satisfied": True, "reflection": ""}
    
    reflect_prompt = f"""请评估以下问答的质量。

用户问题: {question}

AI 回答: {answer}

可用知识: {knowledge_context[:1000] if knowledge_context else "无外部知识"}

请从以下几个方面评估：
1. 准确性：回答是否准确？有没有事实错误？
2. 完整性：回答是否完整？有没有遗漏重要信息？
3. 相关性：回答是否切题？有没有跑题？
4. 深度：回答是否有足够的深度和见解？

如果回答质量足够好，请回复：SATISFIED

如果回答需要改进，请回复：
NEEDS_IMPROVEMENT
[具体说明需要改进的地方，以及如何改进]"""

    response = await llm.ainvoke([HumanMessage(content=reflect_prompt)])
    response_text = response.content.strip()
    
    if "SATISFIED" in response_text.upper() and "NEEDS_IMPROVEMENT" not in response_text.upper():
        return {**state, "is_satisfied": True, "reflection": ""}
    else:
        # 提取改进建议
        reflection = response_text.replace("NEEDS_IMPROVEMENT", "").strip()
        return {**state, "is_satisfied": False, "reflection": reflection}


async def finalize_response(state: AgentState) -> AgentState:
    """最终确认回答"""
    answer = state.get("current_answer", "")
    return {"messages": [AIMessage(content=answer)]}


def route_after_check(state: AgentState) -> str:
    """路由：是否需要检索"""
    if state.get("need_knowledge", False):
        return "retrieve"
    return "generate"


def route_after_reflect(state: AgentState) -> str:
    """路由：反思后是否满意"""
    if state.get("is_satisfied", False):
        return "finalize"
    return "check"  # 不满意则重新检索


# 构建 Graph
def build_graph():
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("check", should_retrieve)
    graph.add_node("retrieve", retrieve_knowledge)
    graph.add_node("generate", generate_response)
    graph.add_node("reflect", reflect_on_answer)
    graph.add_node("finalize", finalize_response)
    
    # 添加边
    graph.add_edge(START, "check")
    graph.add_conditional_edges(
        "check",
        route_after_check,
        {"retrieve": "retrieve", "generate": "generate"}
    )
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "reflect")
    graph.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"finalize": "finalize", "check": "check"}
    )
    graph.add_edge("finalize", END)
    
    return graph.compile()


# 创建 agent 实例
agent = build_graph()
