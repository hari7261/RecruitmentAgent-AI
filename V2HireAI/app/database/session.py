"""
Async SQLAlchemy engine and session factory.

DATABASE_URL is read from Settings so switching to PostgreSQL
(asyncpg) requires only an env var change — no code changes here.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# connect_args is SQLite-specific; remove for PostgreSQL
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_connect_args,
)

# ── Session Factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency-injection–ready async session generator.

    Usage in FastAPI endpoints:
        session: AsyncSession = Depends(get_session)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


from contextlib import asynccontextmanager
get_session_ctx = asynccontextmanager(get_session)


async def init_db() -> None:
    """
    Create all tables on startup (dev convenience).

    In production use Alembic migrations instead.
    """
    from app.database.base import Base  # noqa: F401
    # Import all models so metadata is populated
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
