"""
app/services/jwt_service.py — Criação e validação de JWTs para sessões de módulos.
"""
from datetime import datetime, timedelta, timezone

import jwt
from loguru import logger

from app.config import settings


def create_token(client_id: str, allowed_namespaces: list[str]) -> dict:
    """
    Cria JWT para um módulo autenticado.
    Retorna dict com access_token e expires_in_minutes.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    payload = {
        "sub": client_id,
        "namespaces": allowed_namespaces,
        "iat": now,
        "exp": expires_at,
    }

    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in_minutes": settings.JWT_EXPIRE_MINUTES,
    }


def verify_token(token: str) -> dict:
    """
    Valida JWT e retorna payload.
    Lança jwt.ExpiredSignatureError ou jwt.InvalidTokenError se inválido.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
