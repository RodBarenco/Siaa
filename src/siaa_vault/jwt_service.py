"""
Sessões JWT de curta duração para abrir o Vault.

Fluxo:
  1. Módulo (ex: siaa-bot) faz POST /auth/token com client_id + client_secret
  2. Recebe JWT válido por JWT_EXPIRE_MINUTES (padrão 15min)
  3. Usa o JWT no header Authorization: Bearer <token>
  4. Após expirar, precisa renovar — sem acesso silencioso infinito
"""
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException, status
from app.config import settings


def create_access_token(client_id: str, scopes: list[str] | None = None) -> str:
    payload = {
        "sub": client_id,
        "scopes": scopes or [],
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
        "type": "vault_session",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """Valida o JWT e retorna o payload. Lança 401 se inválido/expirado."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "vault_session":
            raise JWTError("Tipo de token inválido.")
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sessão inválida ou expirada: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
