"""Tavily 知识检索服务"""

from tavily import AsyncTavilyClient

from src.core.config import settings
from src.core.logging import logger


class KnowledgeService:
    """知识检索服务"""

    def __init__(self) -> None:
        self.api_key = settings.tavily_api_key
        self.client = None

        if self.api_key:
            self.client = AsyncTavilyClient(api_key=self.api_key)

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        搜索知识

        Args:
            query: 搜索查询词
            max_results: 最大结果数

        Returns:
            检索结果列表
        """
        if not self.client:
            logger.warning("Tavily API Key 未配置")
            return []

        try:
            response = await self.client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                include_answer=True,
            )

            results = []

            # 添加 AI 摘要
            if response.get("answer"):
                results.append(
                    {"content": response["answer"], "source": "Tavily AI Summary", "score": 1.0}
                )

            # 添加搜索结果
            for item in response.get("results", []):
                results.append(
                    {
                        "content": item.get("content", ""),
                        "source": item.get("url", ""),
                        "score": item.get("score", 0.0),
                    }
                )

            logger.info(f"检索到 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return []


# 服务单例
knowledge_service = KnowledgeService()
