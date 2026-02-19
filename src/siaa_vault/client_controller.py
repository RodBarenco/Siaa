from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from passlib.context import CryptContext
from app.models.vault_client import VaultClient

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ClientCreate(BaseModel):
    client_id: str
    client_secret: str
    description: Optional[str] = None
    allowed_namespaces: Optional[str] = None
    # Ex: "conta-luz,boletos" ou None para acesso total


class ClientOut(BaseModel):
    id: int
    client_id: str
    description: Optional[str]
    is_active: bool
    allowed_namespaces: Optional[str]
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class VaultClientController:

    @staticmethod
    async def create(db: AsyncSession, data: ClientCreate) -> VaultClient:
        secret_hash = pwd_ctx.hash(data.client_secret)
        client = VaultClient(
            client_id=data.client_id,
            client_secret_hash=secret_hash,
            description=data.description,
            allowed_namespaces=data.allowed_namespaces,
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)
        return client

    @staticmethod
    async def authenticate(
        db: AsyncSession, client_id: str, client_secret: str
    ) -> Optional[VaultClient]:
        """Verifica credenciais. Retorna o cliente ou None."""
        result = await db.execute(
            select(VaultClient).where(
                VaultClient.client_id == client_id,
                VaultClient.is_active == True,
            )
        )
        client = result.scalar_one_or_none()
        if not client:
            return None
        if not pwd_ctx.verify(client_secret, client.client_secret_hash):
            return None
        # Atualiza last_login
        client.last_login_at = datetime.utcnow()
        await db.commit()
        return client

    @staticmethod
    async def list_all(db: AsyncSession) -> list[VaultClient]:
        result = await db.execute(select(VaultClient).order_by(VaultClient.created_at))
        return result.scalars().all()

    @staticmethod
    async def revoke(db: AsyncSession, client_id: str) -> bool:
        result = await db.execute(
            select(VaultClient).where(VaultClient.client_id == client_id)
        )
        client = result.scalar_one_or_none()
        if not client:
            return False
        client.is_active = False
        await db.commit()
        return True
