"""配置管理"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """应用配置"""

    # 应用
    app_name: str = "RAG Agent"
    app_version: str = "0.1.0"
    debug: bool = False

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Tavily
    tavily_api_key: str = ""

    # Agent
    max_iterations: int = 3

    # Huawei Cloud
    huawei_iam_endpoint: str = "https://iam.myhuaweicloud.com/v3/auth/tokens"
    huawei_domain_name: str = ""
    huawei_username: str = ""
    huawei_password: str = ""
    huawei_project_name: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


settings = get_settings()
