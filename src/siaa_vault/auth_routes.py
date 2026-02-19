from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.controllers.client_controller import VaultClientController
from app.services.jwt_service import create_access_token
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/auth", tags=["Auth"])


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


@router.post("/token", response_model=TokenResponse)
async def login(
    body: TokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Autentica um módulo e retorna um JWT de sessão curta.

    O token expira em JWT_EXPIRE_MINUTES (padrão 15min).
    Após expirar, o módulo deve chamar este endpoint novamente.
    """
    client = await VaultClientController.authenticate(db, body.client_id, body.client_secret)

    ip = request.client.host if request.client else None

    if not client:
        # Registra tentativa falha
        db.add(AuditLog(
            client_id=body.client_id,
            action="login_failed",
            detail="Credenciais inválidas",
            ip_address=ip,
        ))
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="client_id ou client_secret incorretos.",
        )

    db.add(AuditLog(
        client_id=client.client_id,
        action="login",
        detail="Sessão iniciada",
        ip_address=ip,
    ))
    await db.commit()

    token = create_access_token(client.client_id)
    from app.config import settings
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.JWT_EXPIRE_MINUTES,
    )
