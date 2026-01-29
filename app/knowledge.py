"""Tavily 知识检索"""

from tavily import AsyncTavilyClient
from app.config import TAVILY_API_KEY


async def search_knowledge(query: str) -> list[dict]:
    """
    使用 Tavily 搜索相关内容
    
    返回格式: [{"content": "...", "source": "...", "score": 0.9}, ...]
    """
    if not TAVILY_API_KEY:
        print("警告: 未配置 TAVILY_API_KEY")
        return []
    
    try:
        client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
        
        response = await client.search(
            query=query,
            search_depth="basic",  # "basic" 免费，"advanced" 消耗更多额度
            max_results=5,
            include_answer=True,   # 让 Tavily 生成一个简短答案
        )
        
        results = []
        
        # 如果有直接答案，加到最前面
        if response.get("answer"):
            results.append({
                "content": response["answer"],
                "source": "Tavily AI Summary",
                "score": 1.0
            })
        
        # 添加搜索结果
        for item in response.get("results", []):
            results.append({
                "content": item.get("content", ""),
                "source": item.get("url", ""),
                "score": item.get("score", 0.0)
            })
        
        return results
    
    except Exception as e:
        print(f"Tavily 搜索失败: {e}")
        return []
