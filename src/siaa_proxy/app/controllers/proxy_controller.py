from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from pydantic import BaseModel
from app.models.proxy import Proxy


class ProxyCreate(BaseModel):
    protocol: str = "http"
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    source: Optional[str] = None
    country: Optional[str] = None
    anonymity: Optional[str] = None


class ProxyOut(BaseModel):
    id: int
    protocol: str
    host: str
    port: int
    is_active: bool
    is_validated: bool
    latency_ms: Optional[float]
    country: Optional[str]
    anonymity: Optional[str]
    success_count: int
    failure_count: int
    success_rate: float
    source: Optional[str]
    last_checked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ProxyController:

    @staticmethod
    async def create(db: AsyncSession, data: ProxyCreate) -> Proxy:
        proxy = Proxy(**data.model_dump())
        db.add(proxy)
        await db.commit()
        await db.refresh(proxy)
        return proxy

    @staticmethod
    async def get_all(
        db: AsyncSession,
        only_active: bool = True,
        only_validated: bool = False,
        protocol: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Proxy]:
        q = select(Proxy)
        if only_active:
            q = q.where(Proxy.is_active == True)
        if only_validated:
            q = q.where(Proxy.is_validated == True)
        if protocol:
            q = q.where(Proxy.protocol == protocol)
        q = q.order_by(Proxy.latency_ms.asc().nullslast()).limit(limit).offset(offset)
        result = await db.execute(q)
        return result.scalars().all()

    @staticmethod
    async def get_best(db: AsyncSession, protocol: Optional[str] = None) -> Optional[Proxy]:
        q = (
            select(Proxy)
            .where(Proxy.is_active == True, Proxy.is_validated == True)
            .order_by(Proxy.latency_ms.asc().nullslast())
        )
        if protocol:
            q = q.where(Proxy.protocol == protocol)
        result = await db.execute(q.limit(1))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, proxy_id: int) -> Optional[Proxy]:
        result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_validated(db: AsyncSession, proxy_id: int, latency_ms: float) -> None:
        await db.execute(
            update(Proxy).where(Proxy.id == proxy_id).values(
                is_validated=True, is_active=True, latency_ms=latency_ms,
                last_checked_at=datetime.utcnow(),
                success_count=Proxy.success_count + 1,
            )
        )
        await db.commit()

    @staticmethod
    async def mark_failed(db: AsyncSession, proxy_id: int) -> None:
        await db.execute(
            update(Proxy).where(Proxy.id == proxy_id).values(
                is_validated=False, is_active=False, latency_ms=None,
                last_checked_at=datetime.utcnow(),
                failure_count=Proxy.failure_count + 1,
            )
        )
        await db.commit()

    @staticmethod
    async def delete(db: AsyncSession, proxy_id: int) -> bool:
        proxy = await ProxyController.get_by_id(db, proxy_id)
        if not proxy:
            return False
        await db.delete(proxy)
        await db.commit()
        return True

    @staticmethod
    async def stats(db: AsyncSession) -> dict:
        total     = await db.scalar(select(func.count(Proxy.id)))
        active    = await db.scalar(select(func.count(Proxy.id)).where(Proxy.is_active == True))
        validated = await db.scalar(select(func.count(Proxy.id)).where(Proxy.is_validated == True))
        return {"total": total, "active": active, "validated": validated, "inactive": total - active}

    @staticmethod
    async def bulk_upsert(db: AsyncSession, proxies: list[ProxyCreate]) -> int:
        added = 0
        for data in proxies:
            exists = await db.scalar(
                select(Proxy.id).where(Proxy.host == data.host, Proxy.port == data.port)
            )
            if not exists:
                db.add(Proxy(**data.model_dump()))
                added += 1
        await db.commit()
        return added
