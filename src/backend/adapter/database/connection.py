"""
Database connection utilities.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import Base


async def init_db(db_url: str):
    """Initialize the database."""
    engine = create_async_engine(db_url, echo=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return engine


def get_session_factory(engine):
    """Get a session factory for the engine."""
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    ) 