"""
app/routes/internal_routes.py — Endpoints internos para token rotativo.

Modelo idêntico ao siaa-proxy/internal:
  - GET /internal/current-token  → retorna token rotativo atual
    (autenticado com X-Secret-Key = INTERNAL_SECRET_KEY do .env)

Containers que usam este canal:
  - Módulos plugáveis com acesso frequente (multas, renavan, etc.)
  - Qualquer serviço interno que prefira não usar o fluxo JWT completo

Fluxo de uso:
  1. Container sobe → GET /internal/current-token (com X-Secret-Key)
  2. Recebe { token, expires_at }
  3. Usa nas requests: Header X-Internal-Token: <token>
  4. Vault middleware valida o token
  5. Token expira → container detecta 401 → volta para passo 1
"""
from fastapi import APIRouter, Depends

from app.middlewares.auth import require_internal_secret
from app.services.token_rotator import get_current_token

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.get(
    "/current-token",
    summary="Buscar token interno rotativo atual",
    dependencies=[Depends(require_internal_secret)],
)
async def get_vault_current_token():
    """
    Retorna o token interno rotativo ativo.
    
    Requer header: `X-Secret-Key: <INTERNAL_SECRET_KEY>`
    
    Resposta:
    ```json
    {
      "token": "...",
      "expires_at": "2024-01-01T15:30:00",
      "name": "auto (01/01 14:00)"
    }
    ```
    """
    token = await get_current_token()
    if not token:
        return {"error": "Nenhum token ativo. Vault pode estar inicializando."}
    return {
        "token": token.token,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "name": token.name,
    }
