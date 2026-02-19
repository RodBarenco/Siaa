"""
AuditLog — toda operação no vault é registrada.
Segurança: se algo vazar, você sabe quem/quando acessou.
"""
from datetime import datetime
from sqlalchemy import String, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    client_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # "read", "write", "delete", "login", "login_failed", "list"

    namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Info adicional (ex: "acesso negado - namespace não permitido")

    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog {self.client_id} {self.action} {self.namespace}/{self.key}>"
