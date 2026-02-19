"""
Rotas de admin — protegidas por senha de admin (header X-Admin-Password).
Usadas para criar/revogar clientes e ver audit logs.
Não usa JWT — acesso direto com senha do .env.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.config import settings
from app.controllers.client_controller import VaultClientController, ClientCreate, ClientOut
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(x_admin_password: str = Header(...)):
    if x_admin_password != settings.ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Senha de admin incorreta.",
        )


@router.post("/clients", response_model=ClientOut, status_code=201)
async def create_client(
    data: ClientCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """
    Registra um novo módulo no Vault.
    Guarde o client_secret — não é exibido novamente.
    """
    client = await VaultClientController.create(db, data)
    return client


@router.get("/clients", response_model=list[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    return await VaultClientController.list_all(db)


@router.delete("/clients/{client_id}", status_code=204)
async def revoke_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    ok = await VaultClientController.revoke(db, client_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")


@router.get("/audit")
async def audit_logs(
    limit: int = 100,
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    """Visualiza o log de auditoria de acessos ao vault."""
    q = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    if client_id:
        q = q.where(AuditLog.client_id == client_id)
    result = await db.execute(q)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "client_id": l.client_id,
            "action": l.action,
            "namespace": l.namespace,
            "key": l.key,
            "detail": l.detail,
            "ip_address": l.ip_address,
            "created_at": l.created_at,
        }
        for l in logs
    ]
