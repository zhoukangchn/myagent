"""请求/响应模型"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str = Field(..., description="用户消息", min_length=1)
    conversation_id: str | None = Field(None, description="会话 ID")


class ChatResponse(BaseModel):
    """聊天响应"""

    reply: str = Field(..., description="AI 回复")
    used_knowledge: bool = Field(..., description="是否使用了外部知识")
    iterations: int = Field(..., description="反思迭代次数")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = "healthy"
    version: str = "0.1.0"
