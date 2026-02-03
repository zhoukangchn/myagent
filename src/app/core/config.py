"""配置管理"""

import urllib.parse
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

    # Database
    db_type: str = "postgresql"
    db_host: str = "localhost"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "rag_test"

    @property
    def database_url(self) -> str:
        """根据配置生成异步数据库连接字符串（包含密码转义）"""
        safe_password = urllib.parse.quote_plus(self.db_password)
        if self.db_type.lower() == "mysql":
            return f"mysql+aiomysql://{self.db_user}:{safe_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return f"postgresql+asyncpg://{self.db_user}:{safe_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    # API Auth (User & Password for URL calls)
    api_auth_username: str = ""
    api_auth_password: str = ""

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
