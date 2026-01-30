"""LLM 服务"""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.core.config import settings


def get_llm() -> ChatOpenAI:
    """获取 LLM 实例"""
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=SecretStr(settings.deepseek_api_key) if settings.deepseek_api_key else None,
        base_url=settings.deepseek_base_url,
        temperature=0.7,
    )


# LLM 单例
llm = get_llm()
