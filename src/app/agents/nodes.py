from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agents.state import AgentState
from src.core.config import settings
from src.core.logging import logger
from src.core.prompts import (
    CHECK_PROMPT_DEFAULT,
    CHECK_PROMPT_REFLECTION,
    GENERATE_SYSTEM_PROMPT_BASE,
    GENERATE_SYSTEM_PROMPT_KNOWLEDGE,
    GENERATE_SYSTEM_PROMPT_REFLECTION,
    REFINE_PROMPT,
    REFLECT_PROMPT,
)
from src.services.knowledge import knowledge_service
from src.services.llm import llm


def get_last_content(messages: list) -> str:
    """获取最后一条消息的内容"""
    if not messages:
        return ""
    content = messages[-1].content
    return str(content) if content is not None else ""


async def check_node(state: AgentState) -> dict[str, Any]:
    """判断是否需要检索知识"""
    messages = state["messages"]
    last_message = get_last_content(messages)
    reflection = state.get("reflection", "")

    if reflection:
        check_prompt = CHECK_PROMPT_REFLECTION.format(
            reflection=reflection, last_message=last_message
        )
    else:
        check_prompt = CHECK_PROMPT_DEFAULT.format(last_message=last_message)

    response = await llm.ainvoke([HumanMessage(content=check_prompt)])
    content = str(response.content)
    need_knowledge = "YES" in content.upper()

    logger.info(f"需要检索知识: {need_knowledge}")
    return {"need_knowledge": need_knowledge}


async def retrieve_node(state: AgentState) -> dict[str, Any]:
    """检索外部知识"""
    if not state.get("need_knowledge", False):
        return {"knowledge_context": ""}

    messages = state["messages"]
    query = get_last_content(messages)
    reflection = state.get("reflection", "")

    # 如果有反思，优化查询
    if reflection:
        refine_prompt = REFINE_PROMPT.format(query=query, reflection=reflection)
        response = await llm.ainvoke([HumanMessage(content=refine_prompt)])
        query = str(response.content).strip()
        logger.info(f"优化后的查询: {query}")

    results = await knowledge_service.search(query)

    if results:
        old_context = state.get("knowledge_context", "")
        new_context = "\n\n".join(
            [f"[来源: {r.get('source', '未知')}]\n{r.get('content', '')}" for r in results]
        )
        context = (
            f"{old_context}\n\n--- 新检索结果 ---\n{new_context}" if old_context else new_context
        )
    else:
        context = state.get("knowledge_context", "")

    return {"knowledge_context": context}


async def generate_node(state: AgentState) -> dict[str, Any]:
    """生成回答"""
    messages = state["messages"]
    knowledge_context = state.get("knowledge_context", "")
    reflection = state.get("reflection", "")
    iteration = state.get("iteration", 0)

    system_prompt = GENERATE_SYSTEM_PROMPT_BASE

    if knowledge_context:
        system_prompt += GENERATE_SYSTEM_PROMPT_KNOWLEDGE.format(
            knowledge_context=knowledge_context
        )

    if reflection and iteration > 0:
        system_prompt += GENERATE_SYSTEM_PROMPT_REFLECTION.format(reflection=reflection)

    all_messages = [SystemMessage(content=system_prompt)] + messages
    response = await llm.ainvoke(all_messages)

    logger.info(f"生成回答 (第 {iteration + 1} 轮)")
    return {"current_answer": str(response.content), "iteration": iteration + 1}


async def reflect_node(state: AgentState) -> dict[str, Any]:
    """反思评估回答质量"""
    messages = state["messages"]
    question = get_last_content(messages)
    answer = state.get("current_answer", "")
    knowledge_context = state.get("knowledge_context", "")
    iteration = state.get("iteration", 0)

    # 达到最大迭代次数，直接满意
    if iteration >= settings.max_iterations:
        logger.info(f"达到最大迭代次数 {settings.max_iterations}，结束反思")
        return {"is_satisfied": True, "reflection": ""}

    reflect_prompt = REFLECT_PROMPT.format(
        question=question,
        answer=answer,
        knowledge_context=knowledge_context[:1000] if knowledge_context else "无外部知识",
    )

    response = await llm.ainvoke([HumanMessage(content=reflect_prompt)])
    response_text = str(response.content).strip()

    if "SATISFIED" in response_text.upper() and "NEEDS_IMPROVEMENT" not in response_text.upper():
        logger.info("反思评估: 满意")
        return {"is_satisfied": True, "reflection": ""}
    else:
        reflection = response_text.replace("NEEDS_IMPROVEMENT", "").strip()
        logger.info(f"反思评估: 需要改进 - {reflection[:50]}...")
        return {"is_satisfied": False, "reflection": reflection}


async def finalize_node(state: AgentState) -> dict[str, Any]:
    """最终确认回答"""
    answer = state.get("current_answer", "")
    logger.info("Agent 完成")
    return {"messages": [AIMessage(content=answer)]}
