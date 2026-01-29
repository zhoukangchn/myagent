"""Agent 节点定义"""

from langchain_core.messages import HumanMessage, AIMessage

from src.agents.state import AgentState
from src.services.llm import llm
from src.services.knowledge import knowledge_service
from src.core.config import settings
from src.core.logging import logger


async def check_node(state: AgentState) -> AgentState:
    """判断是否需要检索知识"""
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    reflection = state.get("reflection", "")
    
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
    
    logger.info(f"需要检索知识: {need_knowledge}")
    return {**state, "need_knowledge": need_knowledge}


async def retrieve_node(state: AgentState) -> AgentState:
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
        logger.info(f"优化后的查询: {query}")
    
    results = await knowledge_service.search(query)
    
    if results:
        old_context = state.get("knowledge_context", "")
        new_context = "\n\n".join([
            f"[来源: {r.get('source', '未知')}]\n{r.get('content', '')}"
            for r in results
        ])
        context = f"{old_context}\n\n--- 新检索结果 ---\n{new_context}" if old_context else new_context
    else:
        context = state.get("knowledge_context", "")
    
    return {**state, "knowledge_context": context}


async def generate_node(state: AgentState) -> AgentState:
    """生成回答"""
    from langchain_core.messages import SystemMessage
    
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
    
    logger.info(f"生成回答 (第 {iteration + 1} 轮)")
    return {
        **state,
        "current_answer": response.content,
        "iteration": iteration + 1
    }


async def reflect_node(state: AgentState) -> AgentState:
    """反思评估回答质量"""
    messages = state["messages"]
    question = messages[-1].content if messages else ""
    answer = state.get("current_answer", "")
    knowledge_context = state.get("knowledge_context", "")
    iteration = state.get("iteration", 0)
    
    # 达到最大迭代次数，直接满意
    if iteration >= settings.max_iterations:
        logger.info(f"达到最大迭代次数 {settings.max_iterations}，结束反思")
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
        logger.info("反思评估: 满意")
        return {**state, "is_satisfied": True, "reflection": ""}
    else:
        reflection = response_text.replace("NEEDS_IMPROVEMENT", "").strip()
        logger.info(f"反思评估: 需要改进 - {reflection[:50]}...")
        return {**state, "is_satisfied": False, "reflection": reflection}


async def finalize_node(state: AgentState) -> AgentState:
    """最终确认回答"""
    answer = state.get("current_answer", "")
    logger.info("Agent 完成")
    return {"messages": [AIMessage(content=answer)]}
