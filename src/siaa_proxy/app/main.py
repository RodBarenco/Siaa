from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from app.config import settings
from app.database import init_db
from app.jobs.scheduler import setup_jobs
from app.routes import proxy_routes, token_routes, job_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 Iniciando {settings.APP_NAME}...")
    await init_db()
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


@app.get("/", tags=["Health"])
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
    )
