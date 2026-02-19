"""
siaa_vault_client.py — SDK leve para o Siaa (e outros módulos) acessar o Vault.

Cole este arquivo no seu projeto principal e use assim:

    from siaa_vault_client import VaultClient

    vault = VaultClient(
        base_url="http://localhost:8001",
        client_id="siaa-bot",
        client_secret="seu-secret",
    )

    # Pega todas as credenciais de um serviço
    creds = await vault.get_namespace("enel-rj")
    # → {"username": "joao@email.com", "password": "senha123", "cpf": "123..."}

    # Pega uma credencial específica
    token = await vault.get("telegram", "bot_token")
"""
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional


class VaultClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    async def _ensure_token(self):
        """Renova o token se expirado ou ausente."""
        now = datetime.now(timezone.utc)
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return  # token ainda válido

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/auth/token",
                json={"client_id": self.client_id, "client_secret": self.client_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            # Renova 1 minuto antes de expirar
            self._token_expires_at = now + timedelta(minutes=data["expires_in_minutes"] - 1)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    async def get(self, namespace: str, key: str) -> str:
        """Busca uma credencial específica. Retorna o valor em texto puro."""
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{namespace}/{key}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()["value"]

    async def get_namespace(self, namespace: str) -> dict[str, str]:
        """
        Busca todas as credenciais de um namespace de uma vez.
        Ideal para montar o contexto completo de um serviço.
        """
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{namespace}/all",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def set(
        self,
        namespace: str,
        key: str,
        value: str,
        description: str = "",
        secret_type: str = "credential",
    ) -> None:
        """Grava ou atualiza uma credencial."""
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/secrets/{namespace}/{key}",
                headers=self._headers(),
                json={
                    "namespace": namespace,
                    "key": key,
                    "value": value,
                    "description": description,
                    "secret_type": secret_type,
                },
            )
            resp.raise_for_status()

    async def delete(self, namespace: str, key: str) -> None:
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.base_url}/secrets/{namespace}/{key}",
                headers=self._headers(),
            )
            resp.raise_for_status()
