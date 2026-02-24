"""
app/models/internal_token.py — Tokens rotativos para comunicação interna.

Modelo idêntico ao siaa-proxy: tokens de curta duração que rotacionam
automaticamente via APScheduler, usados por containers internos que
precisam de acesso ao vault sem passar pelo fluxo JWT completo.

Exemplo de uso: módulo de multas precisa buscar um RENAVAN sem
ter que autenticar via client_id/secret a cada request.

Fluxo:
  1. Container sobe → busca token atual via GET /internal/current-token
     (autenticado com INTERNAL_SECRET_KEY do .env)
  2. Usa o token nas requests: Header X-Internal-Token: <token>
  3. APScheduler rotaciona a cada TOKEN_ROTATE_HOURS
  4. Container percebe 401 → busca novo token → continua
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InternalToken(Base):
    __tablename__ = "internal_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    token: Mapped[str] = mapped_column(String(256), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
