"""SQLAlchemy async database engine and session factory."""
import asyncio
import sys

# psycopg on Windows requires SelectorEventLoop for async operations
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Build the URL: replace asyncpg dialect with psycopg for psycopg3 async
_db_url = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg://"
).replace(
    "postgresql://", "postgresql+psycopg://"
)

engine = create_async_engine(
    _db_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup."""
    async with engine.begin() as conn:
        from app import models  # noqa: F401 — ensure models are imported
        await conn.run_sync(Base.metadata.create_all)
