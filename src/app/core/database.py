"""数据库工具层"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.app.core.config import settings
from src.app.core.logging import logger


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""


def _validate_database_url(url: str) -> None:
    """验证数据库 URL 是否使用异步驱动"""
    if not any(driver in url for driver in ("asyncpg", "aiomysql")):
        raise ValueError(
            f"Database URL must use an asynchronous driver (asyncpg or aiomysql). "
            f"Got: {url}"
        )


class DatabaseService:
    """异步数据库服务"""

    def __init__(self):
        self._engine = None
        self._session_factory = None

    def _get_engine(self):
        """获取或创建引擎（懒加载）"""
        if self._engine is None:
            _validate_database_url(settings.database_url)
            self._engine = create_async_engine(
                settings.database_url,
                echo=settings.debug,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
            )
        return self._engine

    def _get_session_factory(self):
        """获取或创建会话工厂（懒加载）"""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self._get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话上下文管理器"""
        session = self._get_session_factory()()
        try:
            logger.debug("Database session created")
            yield session
            await session.commit()
            logger.debug("Database session committed")
        except Exception:
            await session.rollback()
            logger.error("Database session rolled back", exc_info=True)
            raise
        finally:
            await session.close()
            logger.debug("Database session closed")

    async def init_db(self) -> None:
        """初始化数据库表"""
        async with self._get_engine().begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully")

    async def health_check(self) -> bool:
        """验证数据库连接是否正常"""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
            logger.debug("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._engine is not None:
            await self._engine.dispose()
            logger.info("Database engine closed")


db_service = DatabaseService()
