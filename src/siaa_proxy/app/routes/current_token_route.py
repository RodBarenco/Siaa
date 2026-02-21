"""
app/routes/current_token_route.py
"""
from fastapi import APIRouter, Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.token import APIToken

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get("/current-token")
async def get_current_token(
    x_secret_key: str = Header(..., alias="X-Secret-Key"),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o token ativo atual para o siaa renovar automaticamente.
    Protegido por X-Secret-Key (mesmo valor de SECRET_KEY no .env).
    """
    if x_secret_key != settings.SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chave inválida.")

    result = await db.execute(
        select(APIToken)
        .where(APIToken.is_active == True)
        .order_by(APIToken.created_at.desc())
        .limit(1)
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sem token ativo.")

    return {
        "token":      token.token,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
    }