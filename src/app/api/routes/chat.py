"""聊天路由"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from src.agents.graph import agent
from src.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def get_initial_state(message: str) -> dict:
    """获取初始状态"""
    return {
        "messages": [HumanMessage(content=message)],
        "knowledge_context": "",
        "need_knowledge": False,
        "current_answer": "",
        "reflection": "",
        "is_satisfied": False,
        "iteration": 0,
    }


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """聊天接口（非流式）"""
    result = await agent.ainvoke(get_initial_state(request.message))

    messages = result.get("messages", [])
    reply = messages[-1].content if messages else "抱歉，我无法生成回复。"

    return ChatResponse(
        reply=str(reply),
        used_knowledge=bool(result.get("knowledge_context")),
        iterations=result.get("iteration", 1),
    )


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """流式聊天接口"""

    async def generate() -> AsyncGenerator[str, None]:
        try:
            async for event in agent.astream(
                get_initial_state(request.message), stream_mode="updates"
            ):
                for node_name, node_output in event.items():
                    step_info = {"step": node_name}

                    if node_name == "check":
                        need_knowledge = node_output.get("need_knowledge", False)
                        step_info["detail"] = f"需要检索知识: {'是' if need_knowledge else '否'}"

                    elif node_name == "retrieve":
                        context = node_output.get("knowledge_context", "")
                        step_info["detail"] = f"检索到 {len(context)} 字符的知识"
                        if context:
                            step_info["preview"] = (
                                context[:200] + "..." if len(context) > 200 else context
                            )

                    elif node_name == "generate":
                        answer = node_output.get("current_answer", "")
                        iteration = node_output.get("iteration", 0)
                        step_info["detail"] = f"生成回答 (第 {iteration} 轮)"
                        step_info["answer"] = answer

                    elif node_name == "reflect":
                        is_satisfied = node_output.get("is_satisfied", False)
                        reflection = node_output.get("reflection", "")
                        step_info["detail"] = f"反思评估: {'满意' if is_satisfied else '需要改进'}"
                        if reflection:
                            step_info["reflection"] = reflection

                    elif node_name == "finalize":
                        step_info["detail"] = "完成"

                    yield f"data: {json.dumps(step_info, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'step': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'detail': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
