"""
Database usage example for rag-test project.
Shows how to define a model and use the DatabaseService for CRUD operations.
"""

import asyncio
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from src.app.core.database import db_service, Base
from src.app.core.logging import logger

# 1. Define a Sample Model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

async def run_example():
    # 2. Initialize Database (Create Tables)
    logger.info("Initializing database...")
    await db_service.init_db()
    
    # 3. Usage: Create a record
    async with db_service.get_session() as session:
        new_user = User(username="LobsterAhLong", email="lobster@example.com")
        session.add(new_user)
        logger.info(f"Adding user: {new_user.username}")
        # Session auto-commits when exiting the 'async with' block if no errors occur
    
    # 4. Usage: Query a record
    from sqlalchemy import select
    async with db_service.get_session() as session:
        result = await session.execute(select(User).filter(User.username == "LobsterAhLong"))
        user = result.scalars().first()
        if user:
            logger.info(f"Found user: {user.username} (ID: {user.id})")
        else:
            logger.warning("User not found")

    # 5. Shutdown (Close engine)
    await db_service.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_example())
    except Exception as e:
        logger.error(f"Example failed: {e}")
