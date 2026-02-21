from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "siaa-proxy"
    APP_ENV: str = "development"
    APP_PORT: int = 8000

    SECRET_KEY: str = "troque-em-producao"
    API_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str = "sqlite+aiosqlite:////proxy-data/siaa_proxy.db"

    CRON_FETCH_PROXIES_MINUTES: int = 60
    CRON_VALIDATE_PROXIES_MINUTES: int = 15

    PROXY_TIMEOUT_SECONDS: int = 10
    PROXY_TEST_URL: str = "https://httpbin.org/ip"
    MAX_CONCURRENT_VALIDATIONS: int = 30

    BROWSER_TIMEOUT_MS: int = 30000
    BROWSER_HEADLESS: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
