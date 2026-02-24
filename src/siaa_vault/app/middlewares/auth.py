"""
app/middlewares/auth.py — Autenticação de rotas do Vault.

Dois fluxos de autenticação:

1. JWT (módulos externos via /auth/token):
   - Bearer token no header Authorization
   - Valida assinatura + expiração
   - Extrai client_id e namespaces permitidos
   - Usado por siaa-bot, módulos plugáveis via SDK

2. Token Interno Rotativo (containers internos via /internal/*):
   - X-Internal-Token: <token_rotativo>
   - Autenticado pela INTERNAL_SECRET_KEY para buscar o token atual
   - Mais leve que JWT — sem expiração de sessão curta
   - Usado por módulos que fazem consultas frequentes (ex: multas/RENAVAN)
"""
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt

from app.services.jwt_service import verify_token
from app.services.token_rotator import validate_internal_token
from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dependência: JWT (módulos externos)
# ---------------------------------------------------------------------------

async def require_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """
    Valida o Bearer JWT. Retorna o payload com sub (client_id) e namespaces.
    Lança 401 se inválido ou expirado.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = verify_token(credentials.credentials)
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado. Renove via POST /auth/token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_namespace(namespace: str):
    """
    Factory: retorna dependência que verifica se o JWT autoriza o namespace.
    
    Uso:
        @router.get("/secrets/{namespace}/{key}")
        async def get_secret(
            namespace: str,
            key: str,
            payload: dict = Depends(require_namespace("{namespace}")),
        ):
    
    Na prática, use o require_jwt e chame check_namespace_access manualmente
    para rotas com namespace dinâmico.
    """
    async def _check(payload: dict = Depends(require_jwt)) -> dict:
        check_namespace_access(payload, namespace)
        return payload
    return _check


def check_namespace_access(payload: dict, namespace: str):
    """
    Verifica se o payload JWT autoriza acesso ao namespace.
    Lança 403 se não autorizado.
    """
    allowed: list[str] = payload.get("namespaces", [])
    if "*" not in allowed and namespace not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso ao namespace '{namespace}' não autorizado para este cliente.",
        )


# ---------------------------------------------------------------------------
# Dependência: Admin (senha estática no .env)
# ---------------------------------------------------------------------------

async def require_admin(x_admin_password: str = Header(..., alias="X-Admin-Password")):
    """Valida a senha de admin. Usada nas rotas /admin/*"""
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Senha de admin incorreta.",
        )


# ---------------------------------------------------------------------------
# Dependência: Token Interno Rotativo
# ---------------------------------------------------------------------------

async def require_internal_token(
    x_internal_token: str = Header(..., alias="X-Internal-Token"),
):
    """
    Valida o token interno rotativo.
    Usado por módulos que fazem consultas frequentes sem fluxo JWT completo.
    """
    valid = await validate_internal_token(x_internal_token)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token interno inválido ou expirado. Busque o atual via GET /internal/current-token.",
        )


async def require_internal_secret(
    x_secret_key: str = Header(..., alias="X-Secret-Key"),
):
    """
    Valida a chave secreta fixa para acessar o endpoint de token atual.
    Idêntico ao siaa-proxy: INTERNAL_SECRET_KEY do .env.
    """
    if x_secret_key != settings.INTERNAL_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave secreta inválida.",
        )
