from datetime import datetime
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.token import APIToken

api_key_header = APIKeyHeader(name="X-API-Token", auto_error=True)


async def require_token(
    token: str = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> APIToken:
    result = await db.execute(
        select(APIToken).where(APIToken.token == token, APIToken.is_active == True)
    )
    api_token = result.scalar_one_or_none()

    if not api_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")

    if api_token.is_expired():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado.")

    api_token.last_used_at = datetime.utcnow()
    await db.commit()
    return api_token
