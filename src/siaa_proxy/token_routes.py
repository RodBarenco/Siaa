from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.controllers.token_controller import TokenController, TokenCreate, TokenOut

router = APIRouter(prefix="/tokens", tags=["Tokens"])

# Nota: estas rotas não exigem token para você poder criar o primeiro.
# Em produção, proteja com uma senha de admin via variável de ambiente.


@router.post("/", response_model=TokenOut, status_code=201)
async def create_token(
    data: TokenCreate,
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo token de API. Guarde o token retornado - não é exibido novamente."""
    token = await TokenController.create(db, data)
    return token


@router.get("/", response_model=list[TokenOut])
async def list_tokens(db: AsyncSession = Depends(get_db)):
    """Lista todos os tokens."""
    return await TokenController.list_all(db)


@router.delete("/{token_id}", status_code=204)
async def revoke_token(token_id: int, db: AsyncSession = Depends(get_db)):
    """Revoga (desativa) um token."""
    ok = await TokenController.revoke(db, token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token não encontrado.")
