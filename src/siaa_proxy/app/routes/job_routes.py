from fastapi import APIRouter, BackgroundTasks, Depends
from app.middlewares.auth import require_token
from app.models.token import APIToken
from app.services.fetcher import fetch_public_proxies
from app.services.validator import validate_all_proxies

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/fetch-proxies")
async def trigger_fetch(background_tasks: BackgroundTasks, _: APIToken = Depends(require_token)):
    background_tasks.add_task(fetch_public_proxies)
    return {"message": "Job de busca iniciado em background."}


@router.post("/validate-proxies")
async def trigger_validate(background_tasks: BackgroundTasks, _: APIToken = Depends(require_token)):
    background_tasks.add_task(validate_all_proxies)
    return {"message": "Job de validação iniciado em background."}
