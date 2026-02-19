from datetime import datetime
from sqlalchemy import String, Integer, Boolean, Float, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # --- Dados do proxy ---
    protocol: Mapped[str] = mapped_column(String(10), nullable=False, default="http")
    # ex: "http", "https", "socks4", "socks5"

    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)

    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Status ---
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    # --- Fonte ---
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # de qual lista pública veio

    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    anonymity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "transparent" | "anonymous" | "elite"

    # --- Estatísticas ---
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    # --- Timestamps ---
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    @property
    def url(self) -> str:
        """Monta a URL completa do proxy."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0
        return round(self.success_count / total * 100, 1)

    def __repr__(self):
        return f"<Proxy {self.protocol}://{self.host}:{self.port} active={self.is_active}>"
