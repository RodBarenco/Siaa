"""
siaa_vault_client.py — SDK para módulos do Siaa acessarem o Vault.

Interface intencional simples: o módulo passa seu nome como namespace
e usa get/set/delete com chaves livres. O vault cuida do resto.

USO BÁSICO:

    from siaa_vault_client import VaultClient

    vault = VaultClient(
        base_url="http://siaa-vault:8002",
        client_id="modulo-multas",       # nome do módulo = namespace
        client_secret="...",
    )

    # Salvar qualquer coisa
    await vault.set("renavan", "ABC-1234")
    await vault.set("cpf", "123.456.789-00")
    await vault.set("cookie_sessao", "eyJhbGc...")
    await vault.set("ultima_consulta", "2024-01-15", description="data da última busca")

    # Ler uma chave
    renavan = await vault.get("renavan")

    # Ler tudo de uma vez (o mais comum — módulo pega tudo no início)
    dados = await vault.get_all()
    # → {"renavan": "ABC-1234", "cpf": "123...", "cookie_sessao": "eyJ..."}

    # Remover
    await vault.delete("cookie_sessao")

O namespace é automaticamente o client_id do módulo.
Um módulo não acessa dados de outro módulo.
"""
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx


class VaultClient:
    """
    Client assíncrono para o Siaa-Vault.

    Renovação automática de JWT — o módulo não precisa gerenciar tokens.
    Namespace = client_id: cada módulo vive no seu próprio espaço.
    """

    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id          # também é o namespace padrão
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Auth interna
    # ------------------------------------------------------------------

    async def _ensure_token(self):
        """Renova o JWT se expirado ou ausente. Transparente para o módulo."""
        now = datetime.now(timezone.utc)
        if self._token and self._token_expires_at and now < self._token_expires_at - timedelta(minutes=1):
            return

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/auth/token",
                json={"client_id": self.client_id, "client_secret": self.client_secret},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            self._token = data["access_token"]
            self._token_expires_at = now + timedelta(minutes=data["expires_in_minutes"])

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    # ------------------------------------------------------------------
    # Interface principal — namespace = client_id (padrão)
    # ------------------------------------------------------------------

    async def get(self, key: str) -> Optional[str]:
        """
        Retorna o valor de uma chave do namespace deste módulo.
        Retorna None se a chave não existir.
        """
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{self.client_id}/{key}",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()["value"]

    async def get_all(self) -> dict[str, str]:
        """
        Retorna todos os pares key→value do namespace deste módulo.

        Padrão recomendado: chamar no início da execução do módulo
        para ter todos os dados disponíveis de uma vez.

        Retorno: {"renavan": "...", "cpf": "...", "cookie": "..."}
        """
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{self.client_id}",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()

    async def set(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """
        Salva ou atualiza um valor. Cria se não existir, atualiza se existir.

        description: anotação humana opcional (não cifrada, só para o admin).
        """
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/secrets/{self.client_id}/{key}",
                headers=self._headers(),
                json={"value": value, "description": description},
                timeout=10,
            )
            resp.raise_for_status()
            return True

    async def delete(self, key: str) -> bool:
        """Remove uma chave. Retorna False se não existia."""
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"{self.base_url}/secrets/{self.client_id}/{key}",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            return True

    async def list_keys(self) -> list[dict]:
        """Lista as chaves do namespace sem decifrar os valores."""
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{self.client_id}/keys",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Acesso cruzado — quando um módulo precisa ler namespace de outro
    # (requer que o admin tenha autorizado esse namespace no client)
    # ------------------------------------------------------------------

    async def get_from(self, namespace: str, key: str) -> Optional[str]:
        """Lê uma chave de outro namespace (requer permissão no admin)."""
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{namespace}/{key}",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()["value"]

    async def get_all_from(self, namespace: str) -> dict[str, str]:
        """Lê todos os valores de outro namespace (requer permissão no admin)."""
        await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/secrets/{namespace}",
                headers=self._headers(),
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()


# ------------------------------------------------------------------
# Client via Token Interno Rotativo
# Para módulos internos que fazem requisições frequentes
# e preferem o modelo leve do siaa-proxy.
# ------------------------------------------------------------------

class VaultInternalClient:
    """
    Client assíncrono via token rotativo interno.

    Mesmo padrão do SiaaProxyClient:
      1. Busca token atual via GET /internal/current-token
      2. Usa o token nas requests (X-Internal-Token)
      3. Ao receber 401, busca novo token automaticamente

    Use quando o módulo faz muitas requisições e o overhead
    do JWT é desnecessário.

    Requer no .env do módulo:
      VAULT_URL=http://siaa-vault:8002
      VAULT_INTERNAL_SECRET_KEY=<valor do .env do vault>
    """

    _cached_token: Optional[str] = None
    _token_expires: float = 0.0

    def __init__(self, base_url: str, internal_secret_key: str, namespace: str):
        self._base = base_url.rstrip("/")
        self._secret_key = internal_secret_key
        self._namespace = namespace  # namespace deste módulo

    async def _get_token(self) -> Optional[str]:
        margin = 5 * 60
        now = time.time()

        if VaultInternalClient._cached_token and now < (VaultInternalClient._token_expires - margin):
            return VaultInternalClient._cached_token

        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    f"{self._base}/internal/current-token",
                    headers={"X-Secret-Key": self._secret_key},
                    timeout=5,
                )
                if r.status_code == 200:
                    data = r.json()
                    VaultInternalClient._cached_token = data["token"]
                    if data.get("expires_at"):
                        dt = datetime.fromisoformat(data["expires_at"])
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        VaultInternalClient._token_expires = dt.timestamp()
                    else:
                        VaultInternalClient._token_expires = now + 3600
                    return VaultInternalClient._cached_token
        except Exception as e:
            print(f"❌ VaultInternalClient: erro ao buscar token: {e}")

        return VaultInternalClient._cached_token

    async def _headers(self) -> dict:
        token = await self._get_token()
        return {"X-Internal-Token": token or ""}

    async def _get(self, url: str) -> httpx.Response:
        """GET com renovação automática de token em caso de 401."""
        headers = await self._headers()
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10)
            if resp.status_code == 401:
                VaultInternalClient._cached_token = None
                VaultInternalClient._token_expires = 0
                headers = await self._headers()
                resp = await client.get(url, headers=headers, timeout=10)
            return resp

    async def get(self, key: str) -> Optional[str]:
        resp = await self._get(f"{self._base}/secrets/{self._namespace}/{key}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()["value"]

    async def get_all(self) -> dict[str, str]:
        resp = await self._get(f"{self._base}/secrets/{self._namespace}")
        resp.raise_for_status()
        return resp.json()
