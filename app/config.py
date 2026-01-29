import os
from dotenv import load_dotenv

load_dotenv()

# DeepSeek 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 外部知识接口配置
KNOWLEDGE_API_URL = os.getenv("KNOWLEDGE_API_URL", "")
KNOWLEDGE_API_KEY = os.getenv("KNOWLEDGE_API_KEY", "")
