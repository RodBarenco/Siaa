"""
framework/base_web.py

Base para módulos que consomem APIs externas.

Fluxo de requisição:
  1. Se USE_PROXY=True no config.py do módulo E módulo está na lista de permissões:
     → tenta via siaa-proxy (melhor proxy HTTP disponível)
  2. Se proxy indisponível ou falhar → fallback direto (requests simples)
  3. Se tudo falhar → retorna None com log

Para habilitar proxy num módulo, declare no config.py:
    USE_PROXY = True
"""

import os
from abc import ABC, abstractmethod


class BaseWeb(ABC):
    DEFAULT_TIMEOUT = 10

    def _use_proxy(self) -> bool:
        """
        Verifica se o proxy está configurado E se o servidor está acessível.
        Só retorna True se PROXY_SERVER_URL estiver definido no .env.
        """
        return bool(os.getenv("PROXY_SERVER_URL", "").strip())

    def _proxy_client(self):
        try:
            from framework.siaa_proxy_client import SiaaProxyClient
            return SiaaProxyClient()
        except Exception as e:
            print(f"⚠️  siaa-proxy indisponível: {e}")
            return None

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def _get(
        self,
        url: str,
        params: dict = None,
        timeout: int = None,
        use_proxy: bool = None,
    ) -> dict | None:
        should_proxy = use_proxy if use_proxy is not None else self._use_proxy()

        if should_proxy:
            result = self._proxy_get(url, params=params, timeout=timeout)
            if result is not None:
                return result
            print(f"⚠️  Proxy falhou para {url} — tentando direto...")

        return self._direct_get(url, params=params, timeout=timeout)

    def _direct_get(self, url: str, params: dict = None, timeout: int = None) -> dict | None:
        import requests
        try:
            r = requests.get(url, params=params, timeout=timeout or self.DEFAULT_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout: {url}")
        except requests.exceptions.RequestException as e:
            print(f"❌ GET [{url}]: {e}")
        return None

    def _proxy_get(self, url: str, params: dict = None, timeout: int = None) -> dict | None:
        client = self._proxy_client()
        if not client:
            return None
        try:
            return client.get(url, params=params, timeout=timeout or self.DEFAULT_TIMEOUT)
        except Exception as e:
            print(f"⚠️  proxy_get [{url}]: {e}")
            return None

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------

    def _post(
        self,
        url: str,
        json: dict = None,
        timeout: int = None,
        use_proxy: bool = None,
    ) -> dict | None:
        should_proxy = use_proxy if use_proxy is not None else self._use_proxy()

        if should_proxy:
            result = self._proxy_post(url, json=json, timeout=timeout)
            if result is not None:
                return result
            print(f"⚠️  Proxy falhou para POST {url} — tentando direto...")

        return self._direct_post(url, json=json, timeout=timeout)

    def _direct_post(self, url: str, json: dict = None, timeout: int = None) -> dict | None:
        import requests
        try:
            r = requests.post(url, json=json, timeout=timeout or self.DEFAULT_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ POST [{url}]: {e}")
        return None

    def _proxy_post(self, url: str, json: dict = None, timeout: int = None) -> dict | None:
        client = self._proxy_client()
        if not client:
            return None
        try:
            return client.post(url, json=json, timeout=timeout or self.DEFAULT_TIMEOUT)
        except Exception as e:
            print(f"⚠️  proxy_post [{url}]: {e}")
            return None

    # ------------------------------------------------------------------
    # BROWSE — Playwright via siaa-proxy
    # ------------------------------------------------------------------

    def _browse(
        self,
        url: str,
        extract: str = "text",
        wait_for: str = None,
    ) -> str | None:
        """
        Acessa URL via navegador headless (Playwright) no siaa-proxy.
        Ideal para sites com JS ou anti-bot.

        extract: "text" | "html" | "screenshot"
        """
        client = self._proxy_client()
        if not client:
            print(f"⚠️  browse indisponível — PROXY_SERVER_URL não configurado")
            return None
        try:
            return client.browse(url=url, extract=extract, wait_for=wait_for)
        except Exception as e:
            print(f"❌ browse [{url}]: {e}")
            return None

    # ------------------------------------------------------------------
    # Interface obrigatória
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch(self, **kwargs):
        raise NotImplementedError
