"""
app/controllers/client_controller.py — Registro e autenticação de módulos.
"""
import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault_client import VaultClient
from app.models.audit_log import AuditLog
from app.services.jwt_service import create_token


def _hash_secret(secret: str) -> str:
    """SHA-256 simples para armazenar o client_secret."""
    return hashlib.sha256(secret.encode()).hexdigest()


class ClientController:

    @staticmethod
    async def register(
        db: AsyncSession,
        client_id: str,
        client_secret: str,
        description: str | None,
        allowed_namespaces: str,
    ) -> VaultClient:
        """Registra um novo módulo no vault."""
        # Verifica se já existe
        result = await db.execute(
            select(VaultClient).where(VaultClient.client_id == client_id)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Cliente '{client_id}' já registrado.")

        client = VaultClient(
            client_id=client_id,
            client_secret_hash=_hash_secret(client_secret),
            description=description,
            allowed_namespaces=allowed_namespaces,
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)
        return client

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        client_id: str,
        client_secret: str,
        ip: str | None = None,
    ) -> dict:
        """
        Autentica um módulo e retorna JWT.
        Lança ValueError se credenciais inválidas.
        """
        result = await db.execute(
            select(VaultClient).where(
                VaultClient.client_id == client_id,
                VaultClient.is_active == True,
            )
        )
        client = result.scalar_one_or_none()

        if not client or client.client_secret_hash != _hash_secret(client_secret):
            # Log tentativa falha
            db.add(AuditLog(client_id=client_id, action="auth_fail", ip=ip))
            await db.commit()
            raise ValueError("Credenciais inválidas.")

        # Atualiza last_seen
        client.last_seen = datetime.utcnow()

        db.add(AuditLog(client_id=client_id, action="auth", ip=ip))
        await db.commit()

        return create_token(client_id, client.get_namespaces())

    @staticmethod
    async def list_clients(db: AsyncSession) -> list[VaultClient]:
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

    @staticmethod
    async def generate_secret() -> str:
        """Gera um client_secret forte para novos módulos."""
        return secrets.token_urlsafe(32)
