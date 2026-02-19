from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app.config import settings
from app.database import init_db
from app.routes import auth_routes, secret_routes, admin_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🔐 Iniciando {settings.APP_NAME}...")
    await init_db()
    logger.info("✅ Banco inicializado. Vault pronto.")
    yield
    logger.info("🛑 Vault encerrado.")


app = FastAPI(
    title="Siaa Vault",
    description="Cofre de credenciais para os módulos do Siaa",
    version="1.0.0",
    lifespan=lifespan,
    # Em produção: desative a documentação pública
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url=None,
)

app.include_router(auth_routes.router)
app.include_router(secret_routes.router)
app.include_router(admin_routes.router)


@app.get("/", tags=["Health"])
async def health():
    return {"status": "ok", "vault": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
    )
