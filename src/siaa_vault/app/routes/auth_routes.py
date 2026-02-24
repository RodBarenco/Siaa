"""
app/routes/auth_routes.py — POST /auth/token

Módulos (siaa-bot, módulo-multas, etc.) usam este endpoint
para obter um JWT de sessão curta (15min).

Fluxo:
  1. Módulo envia client_id + client_secret
  2. Vault valida e retorna JWT com namespaces permitidos
  3. Módulo usa JWT nas requests seguintes
  4. JWT expira → módulo renova automaticamente
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.client_controller import ClientController
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


@router.post("/token", summary="Autenticar módulo e obter JWT")
async def get_token(
    body: TokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Autentica um módulo registrado e retorna um JWT de sessão.
    
    - **client_id**: ID do módulo registrado no vault
    - **client_secret**: Secret gerado no registro
    
    Retorna JWT válido por `JWT_EXPIRE_MINUTES` (padrão: 15min).
    """
    try:
        ip = request.client.host if request.client else None
        token_data = await ClientController.authenticate(
            db, body.client_id, body.client_secret, ip=ip
        )
        return token_data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
