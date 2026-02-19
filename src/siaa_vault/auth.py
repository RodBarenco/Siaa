from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.vault_client import VaultClient
from app.services.jwt_service import verify_token

bearer = HTTPBearer()


async def get_current_client(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> VaultClient:
    """
    Valida o JWT Bearer e retorna o VaultClient autenticado.
    Toda rota protegida usa: client = Depends(get_current_client)
    """
    payload = verify_token(credentials.credentials)
    client_id = payload.get("sub")

    result = await db.execute(
        select(VaultClient).where(
            VaultClient.client_id == client_id,
            VaultClient.is_active == True,
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cliente não encontrado ou desativado.",
        )

    return client


def require_namespace_access(namespace: str, client: VaultClient):
    """
    Verifica se o cliente tem permissão para acessar o namespace.
    None = acesso total (admin do vault).
    """
    if client.namespaces is None:
        return  # acesso total
    if namespace not in client.namespaces:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cliente '{client.client_id}' não tem acesso ao namespace '{namespace}'.",
        )
