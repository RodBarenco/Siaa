from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from app.models.secret import Secret
from app.models.audit_log import AuditLog
from app.services.crypto import encrypt, decrypt


# ---------- Schemas ----------

class SecretWrite(BaseModel):
    namespace: str
    key: str
    value: str               # texto puro — cifrado antes de salvar
    description: Optional[str] = None
    secret_type: str = "credential"
    # "credential" | "personal_data" | "api_key" | "token"


class SecretRead(BaseModel):
    id: int
    namespace: str
    key: str
    description: Optional[str]
    secret_type: str
    is_active: bool
    access_count: int
    last_accessed_by: Optional[str]
    last_accessed_at: Optional[datetime]
    created_at: datetime
    # ⚠️ value NÃO está aqui — retornado separado só quando explicitamente pedido

    class Config:
        from_attributes = True


class SecretWithValue(SecretRead):
    value: str  # decifrado — só retornado em GET /secrets/{ns}/{key}


# ---------- Controller ----------

class SecretController:

    @staticmethod
    async def _log(
        db: AsyncSession,
        client_id: str,
        action: str,
        namespace: str | None = None,
        key: str | None = None,
        detail: str | None = None,
        ip: str | None = None,
    ):
        db.add(AuditLog(
            client_id=client_id,
            action=action,
            namespace=namespace,
            key=key,
            detail=detail,
            ip_address=ip,
        ))
        # não faz commit aqui — quem chama faz junto com a operação principal

    @staticmethod
    async def write(
        db: AsyncSession,
        data: SecretWrite,
        client_id: str,
        ip: str | None = None,
    ) -> Secret:
        """Cria ou atualiza um segredo (upsert por namespace+key)."""
        encrypted_value = encrypt(data.value)

        result = await db.execute(
            select(Secret).where(Secret.namespace == data.namespace, Secret.key == data.key)
        )
        secret = result.scalar_one_or_none()

        if secret:
            secret.value_encrypted = encrypted_value
            secret.description = data.description
            secret.secret_type = data.secret_type
            action = "update"
        else:
            secret = Secret(
                namespace=data.namespace,
                key=data.key,
                value_encrypted=encrypted_value,
                description=data.description,
                secret_type=data.secret_type,
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
        ip: str | None = None,
    ) -> SecretWithValue:
        """Lê e decifra um segredo. Registra auditoria."""
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

        # Decifra
        plain_value = decrypt(secret.value_encrypted)

        # Atualiza auditoria no registro
        secret.last_accessed_by = client_id
        secret.last_accessed_at = datetime.utcnow()
        secret.access_count += 1

        await SecretController._log(db, client_id, "read", namespace, key, ip=ip)
        await db.commit()

        return SecretWithValue(
            **SecretRead.model_validate(secret).model_dump(),
            value=plain_value,
        )

    @staticmethod
    async def read_namespace(
        db: AsyncSession,
        namespace: str,
        client_id: str,
        ip: str | None = None,
    ) -> dict[str, str]:
        """
        Lê TODOS os segredos de um namespace de uma vez.
        Retorna dict {key: value} — útil para o Siaa montar credenciais completas.
        Ex: {"username": "joao@email.com", "password": "senha123", "cpf": "123..."}
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
            db, client_id, "read_namespace", namespace, detail=f"{len(secrets)} keys", ip=ip
        )
        await db.commit()
        return output

    @staticmethod
    async def list_keys(
        db: AsyncSession,
        namespace: str,
        client_id: str,
        ip: str | None = None,
    ) -> list[SecretRead]:
        """Lista metadados dos segredos do namespace — SEM decifrar valores."""
        result = await db.execute(
            select(Secret).where(Secret.namespace == namespace, Secret.is_active == True)
        )
        secrets = result.scalars().all()
        await SecretController._log(db, client_id, "list", namespace, ip=ip)
        await db.commit()
        return [SecretRead.model_validate(s) for s in secrets]

    @staticmethod
    async def list_namespaces(db: AsyncSession) -> list[str]:
        """Lista todos os namespaces existentes."""
        result = await db.execute(select(Secret.namespace).distinct())
        return [row[0] for row in result.all()]

    @staticmethod
    async def delete(
        db: AsyncSession,
        namespace: str,
        key: str,
        client_id: str,
        ip: str | None = None,
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
