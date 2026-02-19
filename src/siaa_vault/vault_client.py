"""
VaultClient — módulos registrados que podem abrir sessão no Vault.
Ex: siaa-bot, siaa-proxy, siaa-scraper

Cada cliente tem um client_id e um client_secret (hash bcrypt).
"""
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class VaultClient(Base):
    __tablename__ = "vault_clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    client_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # ex: "siaa-bot", "siaa-proxy"

    client_secret_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    # bcrypt hash — nunca guarda o secret em texto puro

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Controle de acesso por namespace
    # Ex: "conta-luz,boletos" — só acessa segredos desses namespaces
    allowed_namespaces: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # None = acesso a todos

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    @property
    def namespaces(self) -> list[str] | None:
        if not self.allowed_namespaces:
            return None  # acesso total
        return [n.strip() for n in self.allowed_namespaces.split(",")]

    def __repr__(self):
        return f"<VaultClient {self.client_id} active={self.is_active}>"
