from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel
from app.database import get_db
from app.middlewares.auth import require_token
from app.models.token import APIToken
from app.controllers.proxy_controller import ProxyController, ProxyCreate, ProxyOut
from app.services.browser import browse_url

router = APIRouter(prefix="/proxies", tags=["Proxies"])


class BrowseBody(BaseModel):
    url: str
    use_proxy: bool = True
    extract: str = "text"   # "text" | "html" | "screenshot"
    wait_for: Optional[str] = None


@router.get("/", response_model=list[ProxyOut])
async def list_proxies(
    only_validated: bool = Query(False),
    protocol: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    _: APIToken = Depends(require_token),
):
    return await ProxyController.get_all(db, only_validated=only_validated,
                                          protocol=protocol, limit=limit, offset=offset)


@router.get("/best", response_model=ProxyOut)
async def get_best_proxy(
    protocol: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: APIToken = Depends(require_token),
):
    proxy = await ProxyController.get_best(db, protocol=protocol)
    if not proxy:
        raise HTTPException(status_code=404, detail="Nenhum proxy validado disponível.")
    return proxy


@router.get("/stats")
async def proxy_stats(db: AsyncSession = Depends(get_db), _: APIToken = Depends(require_token)):
    return await ProxyController.stats(db)


@router.post("/", response_model=ProxyOut, status_code=201)
async def add_proxy(data: ProxyCreate, db: AsyncSession = Depends(get_db),
                    _: APIToken = Depends(require_token)):
    return await ProxyController.create(db, data)


@router.delete("/{proxy_id}", status_code=204)
async def delete_proxy(proxy_id: int, db: AsyncSession = Depends(get_db),
                       _: APIToken = Depends(require_token)):
    ok = await ProxyController.delete(db, proxy_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Proxy não encontrado.")


@router.post("/browse")
async def browse(body: BrowseBody, db: AsyncSession = Depends(get_db),
                 _: APIToken = Depends(require_token)):
    proxy_url = None
    if body.use_proxy:
        proxy = await ProxyController.get_best(db)
        if proxy:
            proxy_url = proxy.url
    return await browse_url(url=body.url, proxy_url=proxy_url,
                             extract=body.extract, wait_for=body.wait_for)
