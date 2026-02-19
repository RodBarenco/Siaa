from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middlewares.auth import get_current_client, require_namespace_access
from app.models.vault_client import VaultClient
from app.controllers.secret_controller import SecretController, SecretWrite, SecretRead, SecretWithValue

router = APIRouter(prefix="/secrets", tags=["Secrets"])


@router.get("/namespaces")
async def list_namespaces(
    db: AsyncSession = Depends(get_db),
    client: VaultClient = Depends(get_current_client),
):
    """Lista todos os namespaces disponíveis."""
    namespaces = await SecretController.list_namespaces(db)
    # Filtra pelos namespaces permitidos do cliente
    if client.namespaces is not None:
        namespaces = [n for n in namespaces if n in client.namespaces]
    return {"namespaces": namespaces}


@router.get("/{namespace}", response_model=list[SecretRead])
async def list_keys(
    namespace: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: VaultClient = Depends(get_current_client),
):
    """Lista as chaves de um namespace — sem revelar os valores."""
    require_namespace_access(namespace, client)
    return await SecretController.list_keys(db, namespace, client.client_id, request.client.host)


@router.get("/{namespace}/all")
async def read_namespace(
    namespace: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: VaultClient = Depends(get_current_client),
):
    """
    Retorna TODOS os segredos de um namespace decifrados.
    Endpoint principal para o Siaa buscar credenciais completas de um serviço.

    Ex: GET /secrets/enel-rj/all
    → {"username": "joao@email.com", "password": "senha", "cpf": "123..."}
    """
    require_namespace_access(namespace, client)
    data = await SecretController.read_namespace(db, namespace, client.client_id, request.client.host)
    if not data:
        raise HTTPException(status_code=404, detail=f"Namespace '{namespace}' não encontrado.")
    return data


@router.get("/{namespace}/{key}", response_model=SecretWithValue)
async def read_secret(
    namespace: str,
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: VaultClient = Depends(get_current_client),
):
    """Lê e decifra um segredo específico."""
    require_namespace_access(namespace, client)
    secret = await SecretController.read(db, namespace, key, client.client_id, request.client.host)
    if not secret:
        raise HTTPException(status_code=404, detail=f"Segredo '{namespace}/{key}' não encontrado.")
    return secret


@router.put("/{namespace}/{key}", response_model=SecretRead, status_code=201)
async def write_secret(
    namespace: str,
    key: str,
    body: SecretWrite,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: VaultClient = Depends(get_current_client),
):
    """Cria ou atualiza um segredo (upsert)."""
    require_namespace_access(namespace, client)
    body.namespace = namespace
    body.key = key
    secret = await SecretController.write(db, body, client.client_id, request.client.host)
    return SecretRead.model_validate(secret)


@router.delete("/{namespace}/{key}", status_code=204)
async def delete_secret(
    namespace: str,
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: VaultClient = Depends(get_current_client),
):
    """Remove um segredo."""
    require_namespace_access(namespace, client)
    ok = await SecretController.delete(db, namespace, key, client.client_id, request.client.host)
    if not ok:
        raise HTTPException(status_code=404, detail="Segredo não encontrado.")
