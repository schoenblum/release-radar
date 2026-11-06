"""Async SQLAlchemy engine, session factory and declarative base."""

from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# Deterministic constraint names keep Alembic migrations reviewable and reversible.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Each test runs on its own event loop and an asyncpg connection cannot cross
# loops, so the test suite opens a fresh connection per session.
_engine_options: dict = (
    {"poolclass": NullPool} if settings.ENVIRONMENT == "test" else {"pool_pre_ping": True}
)
engine = create_async_engine(settings.DATABASE_URL, **_engine_options)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Read server-generated values back on every write, including updated_at on updates.
    # Otherwise the next access would trigger a lazy load, which fails under async.
    __mapper_args__ = {"eager_defaults": True}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session and roll back if the request fails."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
