"""
app/main.py — Ponto de entrada do Siaa-Vault.

Inicializa o banco, registra as rotas e sobe o APScheduler
para rotação periódica dos tokens de acesso interno.
"""
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from loguru import logger

from app.config import settings
from app.database import init_db
from app.routes.auth_routes import router as auth_router
from app.routes.secret_routes import router as secret_router
from app.routes.admin_routes import router as admin_router
from app.routes.internal_routes import router as internal_router
from app.services.token_rotator import rotate_internal_token, provision_initial_token


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---------- Startup ----------
    logger.info(f"🔐 {settings.APP_NAME} iniciando…")
    await init_db()
    await provision_initial_token()

    # Rotação de token interno — mesma lógica do siaa-proxy
    scheduler.add_job(
        rotate_internal_token,
        "interval",
        hours=settings.TOKEN_ROTATE_HOURS,
        id="rotate_vault_token",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        f"⏱️  Token rotativo configurado — intervalo: {settings.TOKEN_ROTATE_HOURS}h"
    )

    yield

    # ---------- Shutdown ----------
    scheduler.shutdown()
    logger.info("🔒 Vault encerrado.")


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description="Cofre de credenciais e dados sensíveis do ecossistema Siaa.",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url=None,
)

app.include_router(auth_router)
app.include_router(secret_router)
app.include_router(admin_router)
app.include_router(internal_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
