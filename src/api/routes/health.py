"""健康检查路由"""

from fastapi import APIRouter
from src.api.schemas import HealthResponse
from src.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
async def root():
    """根路径"""
    return HealthResponse(version=settings.app_version)


@router.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return HealthResponse(version=settings.app_version)
