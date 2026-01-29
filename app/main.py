"""FastAPI 入口 - 支持流式输出"""

import sys
from pathlib import Path

# 支持直接运行
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from app.agent import agent

app = FastAPI(
    title="RAG Agent API",
    description="Agentic RAG with LangGraph + DeepSeek + Self-Reflection",
    version="0.2.0",
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    used_knowledge: bool
    iterations: int


@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG Agent API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口（非流式）"""
    try:
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "knowledge_context": "",
            "need_knowledge": False,
            "current_answer": "",
            "reflection": "",
            "is_satisfied": False,
            "iteration": 0,
        }
        
        result = await agent.ainvoke(initial_state)
        
        messages = result.get("messages", [])
        reply = messages[-1].content if messages else "抱歉，我无法生成回复。"
        used_knowledge = bool(result.get("knowledge_context"))
        iterations = result.get("iteration", 1)
        
        return ChatResponse(reply=reply, used_knowledge=used_knowledge, iterations=iterations)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口 - 实时显示每个步骤"""
    
    async def generate():
        try:
            initial_state = {
                "messages": [HumanMessage(content=request.message)],
                "knowledge_context": "",
                "need_knowledge": False,
                "current_answer": "",
                "reflection": "",
                "is_satisfied": False,
                "iteration": 0,
            }
            
            # 使用 astream 流式输出
            async for event in agent.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    step_info = {"step": node_name}
                    
                    if node_name == "check":
                        need_knowledge = node_output.get("need_knowledge", False)
                        step_info["detail"] = f"需要检索知识: {'是' if need_knowledge else '否'}"
                    
                    elif node_name == "retrieve":
                        context = node_output.get("knowledge_context", "")
                        step_info["detail"] = f"检索到 {len(context)} 字符的知识"
                        if context:
                            # 截取前200字符预览
                            step_info["preview"] = context[:200] + "..." if len(context) > 200 else context
                    
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
            
            # 发送结束信号
            yield f"data: {json.dumps({'step': 'done'}, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'detail': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
