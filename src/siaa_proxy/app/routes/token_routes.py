from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.controllers.token_controller import TokenController, TokenCreate, TokenOut

router = APIRouter(prefix="/tokens", tags=["Tokens"])


@router.post("/", response_model=TokenOut, status_code=201)
async def create_token(data: TokenCreate, db: AsyncSession = Depends(get_db)):
    return await TokenController.create(db, data)


@router.get("/", response_model=list[TokenOut])
async def list_tokens(db: AsyncSession = Depends(get_db)):
    return await TokenController.list_all(db)


@router.delete("/{token_id}", status_code=204)
async def revoke_token(token_id: int, db: AsyncSession = Depends(get_db)):
    ok = await TokenController.revoke(db, token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token não encontrado.")
