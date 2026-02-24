"""
app/routes/admin_routes.py — Gerenciamento de módulos e auditoria.

Todas as rotas requerem X-Admin-Password.
NUNCA exponha estas rotas externamente.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.client_controller import ClientController
from app.database import get_db
from app.middlewares.auth import require_admin
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ClientRegisterRequest(BaseModel):
    client_id: str
    client_secret: str | None = None  # se None, gera automaticamente
    description: str | None = None
    allowed_namespaces: str = ""
    # Ex: "enel-rj,dados-pessoais,multas"
    # Use "*" para acesso total (apenas módulos core confiáveis)


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

@router.post("/clients", summary="Registrar novo módulo")
async def register_client(
    body: ClientRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Registra um módulo no vault.
    
    Se `client_secret` não for fornecido, um seguro é gerado automaticamente.
    **Guarde o secret retornado — não é possível recuperá-lo depois.**
    
    `allowed_namespaces`: namespaces separados por vírgula.
    Use `*` para acesso total (apenas módulos core altamente confiáveis).
    """
    if not body.client_secret:
        body.client_secret = await ClientController.generate_secret()
        generated = True
    else:
        generated = False

    try:
        client = await ClientController.register(
            db,
            body.client_id,
            body.client_secret,
            body.description,
            body.allowed_namespaces,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return {
        "client_id": client.client_id,
        "client_secret": body.client_secret if generated else "***",
        "secret_generated": generated,
        "allowed_namespaces": client.get_namespaces(),
        "message": "⚠️ Guarde o client_secret agora — não será exibido novamente." if generated else "Cliente registrado.",
    }


@router.get("/clients", summary="Listar módulos registrados")
async def list_clients(db: AsyncSession = Depends(get_db)):
    clients = await ClientController.list_clients(db)
    return [
        {
            "client_id": c.client_id,
            "description": c.description,
            "allowed_namespaces": c.get_namespaces(),
            "is_active": c.is_active,
            "created_at": c.created_at,
            "last_seen": c.last_seen,
        }
        for c in clients
    ]


@router.delete("/clients/{client_id}", summary="Revogar acesso de módulo")
async def revoke_client(client_id: str, db: AsyncSession = Depends(get_db)):
    revoked = await ClientController.revoke(db, client_id)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado.")
    return {"revoked": True, "client_id": client_id}


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

@router.get("/audit", summary="Ver log de auditoria")
async def get_audit_log(
    limit: int = 100,
    client_id: str | None = None,
    namespace: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna o log de auditoria de acessos ao vault.
    Filtre por `client_id` e/ou `namespace` para narrowing.
    """
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Filtros em memória (tabela pequena)
    if client_id:
        logs = [l for l in logs if l.client_id == client_id]
    if namespace:
        logs = [l for l in logs if l.namespace == namespace]

    return [
        {
            "id": l.id,
            "client_id": l.client_id,
            "action": l.action,
            "namespace": l.namespace,
            "key": l.key,
            "detail": l.detail,
            "ip": l.ip,
            "created_at": l.created_at,
        }
        for l in logs
    ]
