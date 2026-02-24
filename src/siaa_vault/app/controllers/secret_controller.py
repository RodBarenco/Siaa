"""
app/controllers/secret_controller.py — KV store cifrado por namespace.

Filosofia simples:
  - namespace = o módulo dono dos dados
  - key       = qualquer string que o módulo queira usar
  - value     = qualquer string (o vault não interpreta)
  - description = campo humano opcional para o admin entender o que é

O módulo de multas pode guardar renavan, cpf, cookie, última consulta.
O módulo de energia pode guardar usuario, senha, cpf, token de sessão.
O vault não se importa com o que é — só cifra e devolve.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.secret import Secret
from app.services.crypto import decrypt, encrypt


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SecretWrite(BaseModel):
    namespace: str
    key: str
    value: str
    description: Optional[str] = None  # opcional — só pra referência humana no admin


class SecretRead(BaseModel):
    id: int
    namespace: str
    key: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_accessed_by: Optional[str]
    last_accessed_at: Optional[datetime]
    access_count: int

    class Config:
        from_attributes = True


class SecretWithValue(SecretRead):
    value: str  # decifrado, só retornado em endpoints de leitura


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class SecretController:

    @staticmethod
    async def _log(db, client_id, action, namespace=None, key=None, detail=None, ip=None):
        db.add(AuditLog(
            client_id=client_id, action=action,
            namespace=namespace, key=key, detail=detail, ip=ip,
        ))

    @staticmethod
    async def write(
        db: AsyncSession,
        data: SecretWrite,
        client_id: str,
        ip: Optional[str] = None,
    ) -> Secret:
        """Upsert: cria ou atualiza pelo par namespace+key."""
        encrypted = encrypt(data.value)

        result = await db.execute(
            select(Secret).where(Secret.namespace == data.namespace, Secret.key == data.key)
        )
        secret = result.scalar_one_or_none()

        if secret:
            secret.value_encrypted = encrypted
            secret.description = data.description
            secret.updated_at = datetime.utcnow()
            action = "update"
        else:
            secret = Secret(
                namespace=data.namespace,
                key=data.key,
                value_encrypted=encrypted,
                description=data.description,
            )
            db.add(secret)
            action = "write"

        await SecretController._log(db, client_id, action, data.namespace, data.key, ip=ip)
        await db.commit()
        await db.refresh(secret)
        return secret

    @staticmethod
    async def read(
        db: AsyncSession,
        namespace: str,
        key: str,
        client_id: str,
        ip: Optional[str] = None,
    ) -> Optional[SecretWithValue]:
        """Lê e decifra um valor pelo par namespace+key."""
        result = await db.execute(
            select(Secret).where(
                Secret.namespace == namespace,
                Secret.key == key,
                Secret.is_active == True,
            )
        )
        secret = result.scalar_one_or_none()

        if not secret:
            await SecretController._log(db, client_id, "read_miss", namespace, key, ip=ip)
            await db.commit()
            return None

        plain = decrypt(secret.value_encrypted)
        secret.last_accessed_by = client_id
        secret.last_accessed_at = datetime.utcnow()
        secret.access_count += 1

        await SecretController._log(db, client_id, "read", namespace, key, ip=ip)
        await db.commit()

        return SecretWithValue(**SecretRead.model_validate(secret).model_dump(), value=plain)

    @staticmethod
    async def read_all(
        db: AsyncSession,
        namespace: str,
        client_id: str,
        ip: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Retorna todos os pares key→value de um namespace decifrados.

        Retorno: {"renavan": "ABC-1234", "cpf": "123...", "cookie": "eyJ..."}

        O módulo recebe tudo de uma vez e decide o que usar.
        """
        result = await db.execute(
            select(Secret).where(Secret.namespace == namespace, Secret.is_active == True)
        )
        secrets = result.scalars().all()

        output = {}
        for s in secrets:
            output[s.key] = decrypt(s.value_encrypted)
            s.last_accessed_by = client_id
            s.last_accessed_at = datetime.utcnow()
            s.access_count += 1

        await SecretController._log(
            db, client_id, "read_all", namespace, detail=f"{len(secrets)} keys", ip=ip
        )
        await db.commit()
        return output

    @staticmethod
    async def list_keys(
        db: AsyncSession,
        namespace: str,
        client_id: str,
        ip: Optional[str] = None,
    ) -> list[SecretRead]:
        """Lista as chaves de um namespace sem decifrar os valores."""
        result = await db.execute(
            select(Secret).where(Secret.namespace == namespace, Secret.is_active == True)
        )
        secrets = result.scalars().all()
        await SecretController._log(db, client_id, "list", namespace, ip=ip)
        await db.commit()
        return [SecretRead.model_validate(s) for s in secrets]

    @staticmethod
    async def list_namespaces(db: AsyncSession) -> list[str]:
        result = await db.execute(select(Secret.namespace).distinct())
        return [row[0] for row in result.all()]

    @staticmethod
    async def delete(
        db: AsyncSession,
        namespace: str,
        key: str,
        client_id: str,
        ip: Optional[str] = None,
    ) -> bool:
        result = await db.execute(
            select(Secret).where(Secret.namespace == namespace, Secret.key == key)
        )
        secret = result.scalar_one_or_none()
        if not secret:
            return False
        await db.delete(secret)
        await SecretController._log(db, client_id, "delete", namespace, key, ip=ip)
        await db.commit()
        return True

    @staticmethod
    async def delete_namespace(
        db: AsyncSession,
        namespace: str,
        client_id: str,
        ip: Optional[str] = None,
    ) -> int:
        """Remove todas as chaves de um namespace. Retorna quantas foram removidas."""
        result = await db.execute(
            select(Secret).where(Secret.namespace == namespace)
        )
        secrets = result.scalars().all()
        count = len(secrets)
        for s in secrets:
            await db.delete(s)
        await SecretController._log(
            db, client_id, "delete_namespace", namespace, detail=f"{count} keys", ip=ip
        )
        await db.commit()
        return count
