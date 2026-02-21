import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.models.token import APIToken


class TokenCreate(BaseModel):
    name: str
    expire_days: Optional[int] = None


class TokenOut(BaseModel):
    id: int
    name: str
    token: str
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenController:

    @staticmethod
    async def create(db: AsyncSession, data: TokenCreate) -> APIToken:
        raw_token  = secrets.token_urlsafe(48)
        expires_at = None
        if data.expire_days:
            expires_at = datetime.utcnow() + timedelta(days=data.expire_days)
        token = APIToken(name=data.name, token=raw_token, expires_at=expires_at)
        db.add(token)
        await db.commit()
        await db.refresh(token)
        return token

    @staticmethod
    async def list_all(db: AsyncSession) -> list[APIToken]:
        result = await db.execute(select(APIToken).order_by(APIToken.created_at.desc()))
        return result.scalars().all()

    @staticmethod
    async def revoke(db: AsyncSession, token_id: int) -> bool:
        result = await db.execute(select(APIToken).where(APIToken.id == token_id))
        token = result.scalar_one_or_none()
        if not token:
            return False
        token.is_active = False
        await db.commit()
        return True
