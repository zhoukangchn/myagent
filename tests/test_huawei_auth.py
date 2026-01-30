"""华为云认证服务测试"""

import os
from unittest.mock import AsyncMock, patch

import pytest

from src.services.huawei_auth import HuaweiAuthService


# 标记为集成测试，需要真实环境配置才能跑通
# 运行时使用: pytest tests/test_huawei_auth.py -v -s
@pytest.mark.asyncio
async def test_get_huawei_token_real():
    """测试真实获取华为云 Token (需要 .env 配置)"""

    # 检查环境变量是否存在，不存在则跳过
    if not os.getenv("HUAWEI_USERNAME") or not os.getenv("HUAWEI_PASSWORD"):
        pytest.skip("Skipping real Huawei Cloud auth test: missing credentials in environment")

    service = HuaweiAuthService()
    token = await service.get_token()

    assert token is not None
    assert len(token) > 0
    print(f"\nSuccessfully retrieved token: {token[:20]}...")


@pytest.mark.asyncio
async def test_get_huawei_token_mock():
    """Mock 测试获取华为云 Token"""

    mock_response = AsyncMock()
    mock_response.status_code = 201
    mock_response.headers = {"X-Subject-Token": "mock_token_12345"}

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        service = HuaweiAuthService()
        # 临时注入假凭证以绕过 __init__ 中的某些检查（如果以后有的话）
        service.domain_name = "test_domain"
        service.username = "test_user"
        service.password = "test_pass"

        token = await service.get_token()

        assert token == "mock_token_12345"
