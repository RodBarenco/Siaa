"""
framework/siaa_vault_client.py — Client para o Siaa-Vault.

Mesmo padrão do SiaaProxyClient:
  - token JWT renovado automaticamente quando expira
  - cache em nível de classe (compartilhado entre instâncias)
  - fallback gracioso se vault indisponível

Uso direto (raro — prefira BaseVault):
    client = SiaaVaultClient()
    dados  = client.get_all()           # tudo do namespace do módulo
    cpf    = client.get("cpf")          # uma chave
    client.set("cookie", "eyJ...")      # salva
    client.delete("cookie")             # remove
"""

import os
import time
import requests
from datetime import datetime, timezone


class SiaaVaultClient:
    # JWT compartilhado em memória entre instâncias (class-level)
    _cached_token:  str | None = None
    _token_expires: float      = 0       # timestamp unix

    def __init__(self, namespace: str = None):
        self._base          = os.getenv("VAULT_SERVER_URL", "").rstrip("/")
        self._client_id     = os.getenv("VAULT_CLIENT_ID", "")
        self._client_secret = os.getenv("VAULT_CLIENT_SECRET", "")

        # namespace = nome do módulo dono dos dados
        # se não passar, usa o client_id como namespace padrão
        self._namespace = namespace or self._client_id

        if not self._base:
            raise RuntimeError("VAULT_SERVER_URL não configurado.")
        if not self._client_id or not self._client_secret:
            raise RuntimeError("VAULT_CLIENT_ID ou VAULT_CLIENT_SECRET não configurados.")

        token_status = f"token={'✅ em cache' if self._cached_token else '⏳ será buscado'}"
        print(f"🔐 SiaaVaultClient → {self._base} | namespace={self._namespace} ({token_status})")

    # ------------------------------------------------------------------
    # Renovação automática de JWT
    # ------------------------------------------------------------------

    def _get_token(self) -> str | None:
        """
        Retorna o JWT atual. Se expirado ou ausente, autentica via /auth/token.
        Usa margem de 2min para renovar antes de expirar de fato.
        """
        margin = 2 * 60  # 2 minutos em segundos
        now    = time.time()

        if SiaaVaultClient._cached_token and now < (SiaaVaultClient._token_expires - margin):
            return SiaaVaultClient._cached_token

        print("🔄 JWT vault expirado ou ausente — autenticando...")
        try:
            r = requests.post(
                f"{self._base}/auth/token",
                json={
                    "client_id":     self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=5,
            )
            print(f"   /auth/token → HTTP {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                SiaaVaultClient._cached_token  = data["access_token"]
                SiaaVaultClient._token_expires = now + (data["expires_in_minutes"] * 60)
                print(f"   ✅ JWT obtido (expira em {data['expires_in_minutes']}min)")
                return SiaaVaultClient._cached_token

            elif r.status_code == 401:
                print("   ❌ VAULT_CLIENT_ID ou VAULT_CLIENT_SECRET incorretos.")
            else:
                print(f"   ⚠️  Resposta inesperada: {r.status_code} {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-vault inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ Erro ao autenticar no vault: {e}")

        return SiaaVaultClient._cached_token  # usa o último válido como fallback

    @property
    def _headers(self) -> dict:
        token = self._get_token()
        return {"Authorization": f"Bearer {token or ''}"}

    def _force_renew(self):
        """Força renovação do JWT no próximo acesso (chamado após 401)."""
        SiaaVaultClient._cached_token  = None
        SiaaVaultClient._token_expires = 0

    # ------------------------------------------------------------------
    # Operações KV
    # ------------------------------------------------------------------

    def get_all(self) -> dict | None:
        """
        Retorna todos os pares key→value do namespace deste módulo.
        Padrão recomendado: chamar uma vez no início e usar o dict localmente.

        Retorno: {"cpf": "123...", "senha": "...", "cookie": "eyJ..."} ou None se falhar.
        """
        try:
            r = requests.get(
                f"{self._base}/secrets/{self._namespace}",
                headers=self._headers,
                timeout=5,
            )
            print(f"   /secrets/{self._namespace} → HTTP {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                print(f"   ✅ {len(data)} chaves carregadas do vault")
                return data
            elif r.status_code == 401:
                print("   ❌ JWT inválido — forçando renovação...")
                self._force_renew()
            elif r.status_code == 403:
                print(f"   ❌ Acesso ao namespace '{self._namespace}' não autorizado.")
            else:
                print(f"   ⚠️  {r.status_code}: {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-vault inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ get_all inesperado: {e}")
        return None

    def get(self, key: str) -> str | None:
        """
        Retorna o valor de uma chave específica.
        Retorna None se a chave não existir ou vault indisponível.
        """
        try:
            r = requests.get(
                f"{self._base}/secrets/{self._namespace}/{key}",
                headers=self._headers,
                timeout=5,
            )
            if r.status_code == 200:
                return r.json()["value"]
            elif r.status_code == 404:
                print(f"   ⚠️  Chave '{key}' não encontrada no vault.")
            elif r.status_code == 401:
                self._force_renew()
            else:
                print(f"   ⚠️  {r.status_code}: {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-vault inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ get('{key}') inesperado: {e}")
        return None

    def set(self, key: str, value: str, description: str = None) -> bool:
        """
        Salva ou atualiza um valor no vault (upsert).
        Retorna True se sucesso, False se falhar.
        """
        try:
            r = requests.put(
                f"{self._base}/secrets/{self._namespace}/{key}",
                headers=self._headers,
                json={"value": value, "description": description},
                timeout=5,
            )
            if r.status_code == 200:
                print(f"   ✅ vault.set('{key}') OK")
                return True
            elif r.status_code == 401:
                self._force_renew()
            else:
                print(f"   ⚠️  set('{key}') → {r.status_code}: {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-vault inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ set('{key}') inesperado: {e}")
        return False

    def delete(self, key: str) -> bool:
        """Remove uma chave do vault. Retorna True se removida, False se não existia."""
        try:
            r = requests.delete(
                f"{self._base}/secrets/{self._namespace}/{key}",
                headers=self._headers,
                timeout=5,
            )
            if r.status_code == 200:
                print(f"   ✅ vault.delete('{key}') OK")
                return True
            elif r.status_code == 404:
                return False
            elif r.status_code == 401:
                self._force_renew()
            else:
                print(f"   ⚠️  delete('{key}') → {r.status_code}: {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-vault inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ delete('{key}') inesperado: {e}")
        return False

    def list_keys(self) -> list[str]:
        """Lista as chaves do namespace sem decifrar os valores."""
        try:
            r = requests.get(
                f"{self._base}/secrets/{self._namespace}/keys",
                headers=self._headers,
                timeout=5,
            )
            if r.status_code == 200:
                return [item["key"] for item in r.json()]
            elif r.status_code == 401:
                self._force_renew()
        except Exception as e:
            print(f"   ❌ list_keys inesperado: {e}")
        return []