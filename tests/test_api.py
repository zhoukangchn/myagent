"""API 集成测试"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """健康检查端点测试"""

    def test_root(self):
        """测试根路径"""
        from src.api.app import app

        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health(self):
        """测试健康检查"""
        from src.api.app import app

        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestChatEndpoint:
    """聊天端点测试"""

    def test_chat_request_validation(self):
        """测试请求验证"""
        from src.api.app import app

        client = TestClient(app)

        # 缺少 message 字段
        response = client.post("/chat", json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """测试聊天成功响应"""
        from src.api.app import app

        with patch("src.api.routes.chat.agent") as mock_agent:
            mock_agent.ainvoke = AsyncMock(
                return_value={
                    "messages": [type("Msg", (), {"content": "测试回复"})()],
                    "knowledge_context": "some context",
                    "iteration": 1,
                }
            )

            client = TestClient(app)
            response = client.post("/chat", json={"message": "你好"})

            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "used_knowledge" in data
            assert "iterations" in data
