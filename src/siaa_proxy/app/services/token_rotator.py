"""
app/services/token_rotator.py
"""
import secrets
from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.token import APIToken


async def rotate_token(db: AsyncSession) -> str:
    """
    1. Desativa todos os tokens ativos
    2. Cria novo token com validade = TOKEN_ROTATE_HOURS + 30min de margem
    3. Retorna o valor do novo token
    """
    await db.execute(
        update(APIToken)
        .where(APIToken.is_active == True)
        .values(is_active=False)
    )

    expires_at = datetime.utcnow() + timedelta(
        hours=settings.TOKEN_ROTATE_HOURS,
        minutes=30,  # margem para o siaa renovar antes de expirar
    )

    raw_token = secrets.token_urlsafe(48)
    db.add(APIToken(
        name=f"auto ({datetime.utcnow().strftime('%d/%m %H:%M')})",
        token=raw_token,
        is_active=True,
        expires_at=expires_at,
    ))
    await db.commit()

    logger.info(
        f"🔄 Token rotacionado — expira em "
        f"{settings.TOKEN_ROTATE_HOURS}h30 "
        f"({expires_at.strftime('%d/%m %H:%M')})"
    )
    return raw_token