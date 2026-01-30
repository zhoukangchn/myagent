"""华为云认证服务"""

import logging

import httpx

from src.core.config import settings

logger = logging.getLogger(__name__)


class HuaweiAuthService:
    """华为云 IAM 认证服务"""

    def __init__(self) -> None:
        self.auth_url = settings.huawei_iam_endpoint
        self.domain_name = settings.huawei_domain_name
        self.username = settings.huawei_username
        self.password = settings.huawei_password
        self.project_name = settings.huawei_project_name

    async def get_token(self) -> str | None:
        """获取华为云 IAM Token (X-Subject-Token)"""
        if not all([self.domain_name, self.username, self.password]):
            logger.error("Missing Huawei Cloud credentials in settings")
            return None

        payload = {
            "auth": {
                "identity": {
                    "methods": ["password"],
                    "password": {
                        "user": {
                            "name": self.username,
                            "password": self.password,
                            "domain": {"name": self.domain_name},
                        }
                    },
                },
                "scope": {"project": {"name": self.project_name}}
                if self.project_name
                else {"domain": {"name": self.domain_name}},
            }
        }

        headers = {"Content-Type": "application/json;charset=utf8"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.auth_url, json=payload, headers=headers, timeout=10.0
                )

                if response.status_code == 201:
                    token = response.headers.get("X-Subject-Token")
                    if token:
                        logger.info("Successfully retrieved Huawei Cloud token")
                        return str(token)
                    else:
                        logger.error("X-Subject-Token header not found in response")
                else:
                    logger.error(f"Failed to get token: {response.status_code} - {response.text}")

        except httpx.RequestError as e:
            logger.error(f"Network error while fetching Huawei token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while fetching Huawei token: {e}")

        return None
