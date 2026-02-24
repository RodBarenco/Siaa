"""
app/database.py — Conexão assíncrona com SQLite via SQLAlchemy.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Cria todas as tabelas se não existirem."""
    from app.models import vault_client, secret, audit_log, internal_token  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency FastAPI para injetar sessão DB."""
    async with AsyncSessionLocal() as session:
        yield session
