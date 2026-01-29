"""外部知识接口调用"""

import httpx
from app.config import KNOWLEDGE_API_URL, KNOWLEDGE_API_KEY


async def search_knowledge(query: str) -> list[dict]:
    """
    调用外部知识接口搜索相关内容
    
    返回格式: [{"content": "...", "source": "...", "score": 0.9}, ...]
    
    TODO: 根据实际接口调整请求格式和响应解析
    """
    if not KNOWLEDGE_API_URL:
        return []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {}
        if KNOWLEDGE_API_KEY:
            headers["Authorization"] = f"Bearer {KNOWLEDGE_API_KEY}"
        
        try:
            response = await client.post(
                KNOWLEDGE_API_URL,
                headers=headers,
                json={"query": query, "top_k": 5}
            )
            response.raise_for_status()
            data = response.json()
            
            # TODO: 根据实际返回格式解析
            # 假设返回 {"results": [{"content": "...", "source": "..."}]}
            return data.get("results", [])
        
        except Exception as e:
            print(f"知识接口调用失败: {e}")
            return []
