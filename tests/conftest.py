"""测试配置"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_llm():
    """Mock DeepSeek LLM"""
    with patch("src.agents.nodes.llm") as mock:
        mock.ainvoke = AsyncMock(return_value=AsyncMock(content="NO"))
        yield mock


@pytest.fixture
def mock_knowledge_service():
    """Mock 知识检索服务"""
    with patch("src.agents.nodes.knowledge_service") as mock:
        mock.search = AsyncMock(return_value=[
            {"content": "测试内容", "source": "https://example.com", "score": 0.9}
        ])
        yield mock
