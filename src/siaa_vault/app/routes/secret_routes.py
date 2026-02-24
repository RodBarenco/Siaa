"""
app/routes/secret_routes.py — API KV por namespace.

Todos os endpoints requerem JWT válido.
O namespace no path é validado contra os namespaces do JWT.

Interface intencional simples:
  PUT  /secrets/{ns}/{key}   → salva ou atualiza um valor
  GET  /secrets/{ns}/{key}   → lê um valor
  GET  /secrets/{ns}         → lê todos os pares key→value do módulo
  GET  /secrets/{ns}/keys    → lista chaves sem valores
  DEL  /secrets/{ns}/{key}   → remove uma chave
  DEL  /secrets/{ns}         → remove todo o namespace (cuidado)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.controllers.secret_controller import SecretController, SecretRead, SecretWithValue
from app.database import get_db
from app.middlewares.auth import check_namespace_access, require_jwt

router = APIRouter(prefix="/secrets", tags=["Secrets"])


def _ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


class WriteBody(BaseModel):
    value: str
    description: Optional[str] = None  # humano-legível, nunca cifrado


# ---------------------------------------------------------------------------
# Namespace
# ---------------------------------------------------------------------------

@router.get("/namespaces", summary="Listar namespaces acessíveis")
async def list_namespaces(
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    all_ns = await SecretController.list_namespaces(db)
    allowed = payload.get("namespaces", [])
    if "*" in allowed:
        return {"namespaces": all_ns}
    return {"namespaces": [ns for ns in all_ns if ns in allowed]}


# ---------------------------------------------------------------------------
# Todas as chaves de um namespace
# ---------------------------------------------------------------------------

@router.get("/{namespace}", summary="Buscar todos os valores do namespace")
async def get_all(
    namespace: str,
    request: Request,
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna todos os pares key→value do namespace, decifrados.

    Resposta: `{"renavan": "ABC-1234", "cpf": "123...", "cookie": "eyJ..."}`

    O módulo recebe tudo de uma vez e decide o que usar.
    """
    check_namespace_access(payload, namespace)
    return await SecretController.read_all(db, namespace, payload["sub"], _ip(request))


@router.get("/{namespace}/keys", response_model=list[SecretRead], summary="Listar chaves sem valores")
async def list_keys(
    namespace: str,
    request: Request,
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Lista metadados das chaves do namespace — sem decifrar os valores."""
    check_namespace_access(payload, namespace)
    return await SecretController.list_keys(db, namespace, payload["sub"], _ip(request))


@router.delete("/{namespace}", summary="Remover namespace inteiro")
async def delete_namespace(
    namespace: str,
    request: Request,
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Remove todas as chaves de um namespace. Operação irreversível."""
    check_namespace_access(payload, namespace)
    count = await SecretController.delete_namespace(db, namespace, payload["sub"], _ip(request))
    return {"deleted": count, "namespace": namespace}


# ---------------------------------------------------------------------------
# Chave individual
# ---------------------------------------------------------------------------

@router.get("/{namespace}/{key}", response_model=SecretWithValue, summary="Buscar um valor")
async def get_one(
    namespace: str,
    key: str,
    request: Request,
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    """Retorna o valor decifrado de uma chave específica."""
    check_namespace_access(payload, namespace)
    secret = await SecretController.read(db, namespace, key, payload["sub"], _ip(request))
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chave '{key}' não encontrada.")
    return secret


@router.put("/{namespace}/{key}", response_model=SecretRead, summary="Salvar ou atualizar valor")
async def upsert(
    namespace: str,
    key: str,
    body: WriteBody,
    request: Request,
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    """
    Salva ou atualiza um valor (upsert).

    O `value` pode ser qualquer string — o vault não interpreta.
    Use `description` para anotar o que é (opcional, não cifrado).
    """
    check_namespace_access(payload, namespace)
    from app.controllers.secret_controller import SecretWrite
    data = SecretWrite(namespace=namespace, key=key, value=body.value, description=body.description)
    secret = await SecretController.write(db, data, payload["sub"], _ip(request))
    return SecretRead.model_validate(secret)


@router.delete("/{namespace}/{key}", summary="Remover uma chave")
async def delete_one(
    namespace: str,
    key: str,
    request: Request,
    payload: dict = Depends(require_jwt),
    db: AsyncSession = Depends(get_db),
):
    check_namespace_access(payload, namespace)
    deleted = await SecretController.delete(db, namespace, key, payload["sub"], _ip(request))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chave '{key}' não encontrada.")
    return {"deleted": True, "namespace": namespace, "key": key}
