"""
app/config.py — Configurações centralizadas via .env
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "siaa-vault"
    APP_ENV: str = "development"
    APP_PORT: int = 8002

    # Chave mestre de criptografia — NUNCA muda após o primeiro deploy
    MASTER_KEY: str

    # JWT para sessões de módulos externos
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 15

    # Admin
    ADMIN_PASSWORD: str

    # Token rotativo interno (modelo siaa-proxy)
    # Usado para comunicação direta container→vault sem JWT
    INTERNAL_SECRET_KEY: str   # chave fixa para buscar o token rotativo
    TOKEN_ROTATE_HOURS: int = 1

    # Banco
    DATABASE_URL: str = "sqlite+aiosqlite:///./siaa_vault.db"

    class Config:
        env_file = ".env"


settings = Settings()
