"""
Secret — credencial armazenada cifrada no banco.

Estrutura flexível:
  - namespace: agrupa por serviço (ex: "conta-luz", "boletos", "telegram")
  - key: nome do campo (ex: "username", "password", "cpf", "api_key")
  - value_encrypted: valor cifrado com Fernet (MASTER_KEY)

Exemplo de uso:
  namespace="enel-rj", key="login",    value="joao@email.com"
  namespace="enel-rj", key="password", value="minha-senha-123"
  namespace="enel-rj", key="cpf",      value="123.456.789-00"
  namespace="telegram", key="bot_token", value="7xxx:AAA..."
"""
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Secret(Base):
    __tablename__ = "secrets"

    __table_args__ = (
        # namespace + key são únicos — não duplica o mesmo campo
        UniqueConstraint("namespace", "key", name="uq_namespace_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    namespace: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # Ex: "conta-luz", "boleto-bradesco", "meu-cpf", "telegram"

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    # Ex: "username", "password", "cpf", "api_key", "token"

    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    # Valor cifrado com Fernet — ilegível sem a MASTER_KEY

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Anotação humana opcional: "senha do portal Enel"

    secret_type: Mapped[str] = mapped_column(String(50), default="credential")
    # "credential" | "personal_data" | "api_key" | "token"

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Auditoria — quem acessou por último
    last_accessed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    access_count: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Secret {self.namespace}/{self.key}>"
