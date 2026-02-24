"""
app/services/token_rotator.py — Rotação automática de tokens internos.

Modelo idêntico ao siaa-proxy/token_rotator.py:
  1. Desativa todos os tokens ativos
  2. Cria novo token com validade = TOKEN_ROTATE_HOURS + 30min de margem
  3. Containers que recebem 401 buscam o novo via /internal/current-token

Diferença em relação ao siaa-proxy: aqui o token protege o VAULT,
não o proxy. Módulos que precisam de acesso direto (sem fluxo JWT completo)
usam esse canal interno.
"""
import secrets
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import update, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.internal_token import InternalToken


async def rotate_internal_token() -> str:
    """
    Rotaciona o token interno do vault.
    Chamado pelo APScheduler a cada TOKEN_ROTATE_HOURS.
    """
    async with AsyncSessionLocal() as db:
        # Desativa todos os tokens ativos
        await db.execute(
            update(InternalToken)
            .where(InternalToken.is_active == True)
            .values(is_active=False)
        )

        expires_at = datetime.utcnow() + timedelta(
            hours=settings.TOKEN_ROTATE_HOURS,
            minutes=30,  # margem de segurança
        )

        raw_token = secrets.token_urlsafe(48)
        db.add(InternalToken(
            name=f"auto ({datetime.utcnow().strftime('%d/%m %H:%M')})",
            token=raw_token,
            is_active=True,
            expires_at=expires_at,
        ))
        await db.commit()

    logger.info(
        f"🔄 Token interno rotacionado — expira em "
        f"{settings.TOKEN_ROTATE_HOURS}h30 "
        f"({expires_at.strftime('%d/%m %H:%M')})"
    )
    return raw_token


async def provision_initial_token():
    """
    Verifica se existe token ativo; se não, cria o primeiro.
    Chamado no startup.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InternalToken).where(InternalToken.is_active == True)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            logger.info("🔑 Nenhum token interno encontrado — provisionando...")
            await rotate_internal_token()
        else:
            logger.info(
                f"✅ Token interno ativo encontrado (expira: {existing.expires_at})"
            )


async def get_current_token() -> InternalToken | None:
    """Retorna o token interno ativo atual."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InternalToken)
            .where(InternalToken.is_active == True)
            .order_by(InternalToken.created_at.desc())
        )
        return result.scalar_one_or_none()


async def validate_internal_token(token: str) -> bool:
    """Verifica se um token interno é válido e não expirou."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(InternalToken).where(
                InternalToken.token == token,
                InternalToken.is_active == True,
            )
        )
        t = result.scalar_one_or_none()
        if not t:
            return False
        if t.expires_at and t.expires_at < datetime.utcnow():
            return False
        return True
