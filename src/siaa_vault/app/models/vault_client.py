"""
app/models/vault_client.py — Módulos registrados no Vault.

Cada módulo (siaa-bot, siaa-proxy, modulo-multas…) tem:
- client_id / client_secret (hash) para autenticar via JWT
- allowed_namespaces: lista dos namespaces que pode acessar
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VaultClient(Base):
    __tablename__ = "vault_clients"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    client_secret_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Namespaces permitidos — separados por vírgula
    # Ex: "enel-rj,dados-pessoais,multas"
    allowed_namespaces: Mapped[str] = mapped_column(Text, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def get_namespaces(self) -> list[str]:
        """Retorna lista de namespaces permitidos."""
        if not self.allowed_namespaces:
            return []
        return [ns.strip() for ns in self.allowed_namespaces.split(",") if ns.strip()]

    def can_access(self, namespace: str) -> bool:
        """Verifica se este cliente pode acessar o namespace solicitado."""
        allowed = self.get_namespaces()
        # Namespace especial "*" = acesso total (apenas admin)
        return "*" in allowed or namespace in allowed
