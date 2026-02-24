"""
app/models/secret.py — KV store cifrado por namespace (módulo).

Cada módulo tem seu próprio namespace e pode guardar qualquer
par key→value que precisar. O vault não interpreta o conteúdo.

Exemplos reais:
  namespace="multas"   key="renavan"         value="ABC-1234"
  namespace="multas"   key="cpf"             value="123.456.789-00"
  namespace="multas"   key="cookie_sessao"   value="eyJhbGc..."
  namespace="multas"   key="ultima_consulta" value="2024-01-15"

  namespace="enel"     key="usuario"         value="joao@email.com"
  namespace="enel"     key="senha"           value="s3nha!"
  namespace="enel"     key="cpf"             value="123.456.789-00"
  namespace="enel"     key="token_api"       value="Bearer xyz"
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Secret(Base):
    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # namespace = módulo dono do dado
    # key       = identificador livre — o módulo decide
    namespace: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False)

    # Valor cifrado com Fernet — o vault não lê o conteúdo
    value_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    # Descrição opcional — nunca cifrada, só para referência humana no admin
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Auditoria de acesso
    last_accessed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
