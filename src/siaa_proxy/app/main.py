"""
app/main.py
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.jobs.scheduler import setup_jobs
from app.routes import proxy_routes, token_routes, job_routes
from app.routes.current_token_route import router as internal_router


async def _provision_initial_token():
    """
    No startup, garante que existe pelo menos um token ativo e não expirado.
    Se o token existente estiver expirado, rotaciona imediatamente.
    """
    from datetime import datetime
    from sqlalchemy import select, func
    from app.models.token import APIToken
    from app.services.token_rotator import rotate_token

    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()

        # Conta apenas tokens ativos E não expirados
        count = await db.scalar(
            select(func.count(APIToken.id)).where(
                APIToken.is_active == True,
                (APIToken.expires_at == None) | (APIToken.expires_at > now),
            )
        )

        if count == 0:
            logger.info("🔑 Nenhum token válido encontrado — gerando novo token...")
            await rotate_token(db)
            logger.info("🔑 Token inicial gerado.")
        else:
            logger.info(f"🔑 {count} token(s) ativo(s) e válido(s) no banco.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Iniciando {settings.APP_NAME}...")
    await init_db()
    await _provision_initial_token()
    setup_jobs()
    yield
    logger.info("🛑 Encerrando servidor.")


app = FastAPI(
    title="Siaa Proxy Server",
    description="Gerenciador de proxies para o Siaa — IA Bot",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(proxy_routes.router)
app.include_router(token_routes.router)
app.include_router(job_routes.router)
app.include_router(internal_router)   # GET /internal/current-token


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
    )