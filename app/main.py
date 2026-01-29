"""FastAPI 入口"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from app.agent import agent

app = FastAPI(
    title="RAG Agent API",
    description="Agentic RAG with LangGraph + DeepSeek",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    used_knowledge: bool


@app.get("/")
async def root():
    return {"status": "ok", "message": "RAG Agent API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        # 初始状态
        initial_state = {
            "messages": [HumanMessage(content=request.message)],
            "knowledge_context": "",
            "need_knowledge": False,
        }
        
        # 运行 agent
        result = await agent.ainvoke(initial_state)
        
        # 获取回复
        messages = result.get("messages", [])
        reply = messages[-1].content if messages else "抱歉，我无法生成回复。"
        used_knowledge = bool(result.get("knowledge_context"))
        
        return ChatResponse(reply=reply, used_knowledge=used_knowledge)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
