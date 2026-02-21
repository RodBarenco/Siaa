from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    APP_NAME: str = "siaa-proxy"
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    # Obrigatório — sem default. Se não estiver no .env, o servidor não sobe.
    # Gere com: openssl rand -hex 32
    # Coloque o MESMO valor em PROXY_SECRET_KEY no .env do siaa.
    SECRET_KEY: str

    DATABASE_URL: str = "sqlite+aiosqlite:////proxy-data/siaa_proxy.db"

    CRON_FETCH_PROXIES_MINUTES: int = 60
    CRON_VALIDATE_PROXIES_MINUTES: int = 15
    TOKEN_ROTATE_HOURS: int = 1

    PROXY_TIMEOUT_SECONDS: int = 10
    PROXY_TEST_URL: str = "https://httpbin.org/ip"
    MAX_CONCURRENT_VALIDATIONS: int = 30

    BROWSER_TIMEOUT_MS: int = 30000
    BROWSER_HEADLESS: bool = True

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if not v or v in ("troque-em-producao", "changeme", "secret"):
            raise ValueError(
                "SECRET_KEY inválida. Gere uma com: openssl rand -hex 32"
            )
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY muito curta (mínimo 32 caracteres). "
                "Gere uma com: openssl rand -hex 32"
            )
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()