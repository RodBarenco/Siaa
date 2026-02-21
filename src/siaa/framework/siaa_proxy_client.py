"""
framework/siaa_proxy_client.py — versão com renovação automática de token

Substitui o siaa_proxy_client.py anterior.
"""

import os
import time
import requests


class SiaaProxyClient:
    # Token compartilhado em memória entre instâncias (class-level)
    _cached_token:   str | None = None
    _token_expires:  float      = 0       # timestamp unix

    def __init__(self):
        self._base       = os.getenv("PROXY_SERVER_URL", "").rstrip("/")
        self._secret_key = os.getenv("PROXY_SECRET_KEY", "")

        if not self._base:
            raise RuntimeError("PROXY_SERVER_URL não configurado.")

        token_status = f"token={'✅ em cache' if self._cached_token else '⏳ será buscado'}"
        print(f"🔌 SiaaProxyClient → {self._base} ({token_status})")

    # ------------------------------------------------------------------
    # Renovação automática de token
    # ------------------------------------------------------------------

    def _get_token(self) -> str | None:
        """
        Retorna o token atual. Se expirado ou ausente, busca /internal/current-token.
        Usa margem de 5min para renovar antes de expirar de fato.
        """
        margin = 5 * 60  # 5 minutos em segundos
        now    = time.time()

        if SiaaProxyClient._cached_token and now < (SiaaProxyClient._token_expires - margin):
            return SiaaProxyClient._cached_token

        print("🔄 Token expirado ou ausente — buscando novo token...")
        try:
            r = requests.get(
                f"{self._base}/internal/current-token",
                headers={"X-Secret-Key": self._secret_key},
                timeout=5,
            )
            print(f"   /internal/current-token → HTTP {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                SiaaProxyClient._cached_token = data["token"]

                # Converte expires_at ISO → timestamp unix
                if data.get("expires_at"):
                    from datetime import datetime, timezone
                    dt = datetime.fromisoformat(data["expires_at"])
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    SiaaProxyClient._token_expires = dt.timestamp()
                else:
                    # Sem vencimento → renova daqui 1h por precaução
                    SiaaProxyClient._token_expires = now + 3600

                print(f"   ✅ Novo token obtido (expira: {data.get('expires_at', 'nunca')})")
                return SiaaProxyClient._cached_token

            elif r.status_code == 403:
                print("   ❌ PROXY_SECRET_KEY incorreta — verifique o .env do siaa")
            else:
                print(f"   ⚠️  Resposta inesperada: {r.status_code} {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-proxy inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ Erro ao buscar token: {e}")

        return SiaaProxyClient._cached_token  # usa o último válido como fallback

    @property
    def _headers(self) -> dict:
        token = self._get_token()
        return {"X-API-Token": token or ""}

    # ------------------------------------------------------------------
    # Proxy HTTP rotativo
    # ------------------------------------------------------------------

    def _get_best_proxy_url(self) -> str | None:
        try:
            r = requests.get(
                f"{self._base}/proxies/best",
                headers=self._headers,
                timeout=5,
            )
            print(f"   /proxies/best → HTTP {r.status_code}")

            if r.status_code == 200:
                p = r.json()
                auth = ""
                if p.get("username") and p.get("password"):
                    auth = f"{p['username']}:{p['password']}@"
                url = f"{p['protocol']}://{auth}{p['host']}:{p['port']}"
                print(f"   ✅ Proxy: {p['host']}:{p['port']} ({p.get('latency_ms', '?')}ms)")
                return url
            elif r.status_code == 401:
                print("   ❌ Token inválido — forçando renovação...")
                SiaaProxyClient._cached_token  = None
                SiaaProxyClient._token_expires  = 0
            elif r.status_code == 404:
                print("   ⚠️  Nenhum proxy validado disponível no banco")
            else:
                print(f"   ⚠️  {r.status_code}: {r.text[:100]}")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-proxy inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ Erro inesperado: {e}")
        return None

    def _proxies_dict(self) -> dict | None:
        url = self._get_best_proxy_url()
        return {"http": url, "https": url} if url else None

    # ------------------------------------------------------------------
    # GET / POST / BROWSE (igual ao anterior)
    # ------------------------------------------------------------------

    def get(self, url: str, params: dict = None, timeout: int = 10) -> dict | None:
        proxies = self._proxies_dict()
        print(f"   {'🌐 GET via proxy' if proxies else '⚠️  GET direto'} → {url}")
        try:
            r = requests.get(url, params=params, proxies=proxies, timeout=timeout)
            r.raise_for_status()
            print(f"   ✅ GET OK (HTTP {r.status_code})")
            return r.json()
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout: {url}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ GET falhou: {e}")
        return None

    def post(self, url: str, json: dict = None, timeout: int = 10) -> dict | None:
        proxies = self._proxies_dict()
        print(f"   {'🌐 POST via proxy' if proxies else '⚠️  POST direto'} → {url}")
        try:
            r = requests.post(url, json=json, proxies=proxies, timeout=timeout)
            r.raise_for_status()
            print(f"   ✅ POST OK (HTTP {r.status_code})")
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"   ❌ POST falhou: {e}")
        return None

    def browse(self, url: str, extract: str = "text", wait_for: str = None, timeout: int = 30) -> str | None:
        print(f"   🎭 BROWSE → {url}")
        payload = {"url": url, "use_proxy": True, "extract": extract}
        if wait_for:
            payload["wait_for"] = wait_for
        try:
            r = requests.post(
                f"{self._base}/proxies/browse",
                headers=self._headers,
                json=payload,
                timeout=timeout,
            )
            print(f"   /proxies/browse → HTTP {r.status_code}")
            r.raise_for_status()
            data = r.json()
            if data.get("success"):
                print(f"   ✅ BROWSE OK ({len(data.get('content', ''))} chars)")
                return data.get("content")
            print(f"   ⚠️  BROWSE falhou: {data.get('error', '?')}")
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout no browse")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ BROWSE erro: {e}")
        return None