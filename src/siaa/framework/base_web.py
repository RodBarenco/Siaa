"""
framework/base_web.py

Base para módulos que consomem APIs externas.

Fluxo de requisição:
  1. Se PROXY_SERVER_URL estiver definido no .env:
     → tenta via SiaaProxyClient (melhor proxy HTTP disponível)
  2. Se proxy indisponível ou falhar → fallback direto (requests simples)
  3. Se tudo falhar → retorna None com log
"""

import os
from abc import ABC, abstractmethod


class BaseWeb(ABC):
    DEFAULT_TIMEOUT = 10

    def _use_proxy(self) -> bool:
        return bool(os.getenv("PROXY_SERVER_URL", "").strip())

    def _proxy_client(self):
        try:
            from framework.siaa_proxy_client import SiaaProxyClient
            return SiaaProxyClient()
        except RuntimeError as e:
            # PROXY_SERVER_URL não configurado — esperado
            print(f"⚠️  Proxy não configurado: {e}")
            return None
        except Exception as e:
            print(f"⚠️  SiaaProxyClient falhou ao inicializar: {e}")
            return None

    # ------------------------------------------------------------------
    # GET
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict = None, timeout: int = None, use_proxy: bool = None) -> dict | None:
        should_proxy = use_proxy if use_proxy is not None else self._use_proxy()

        if should_proxy:
            print(f"🔀 [{self.__class__.__name__}] Tentando via proxy...")
            result = self._proxy_get(url, params=params, timeout=timeout)
            if result is not None:
                return result
            print(f"🔀 [{self.__class__.__name__}] Proxy falhou → fallback direto")
        else:
            print(f"🔀 [{self.__class__.__name__}] PROXY_SERVER_URL não definido → conexão direta")

        return self._direct_get(url, params=params, timeout=timeout)

    def _direct_get(self, url: str, params: dict = None, timeout: int = None) -> dict | None:
        import requests
        print(f"   📡 GET direto → {url}")
        try:
            r = requests.get(url, params=params, timeout=timeout or self.DEFAULT_TIMEOUT)
            r.raise_for_status()
            print(f"   ✅ GET direto OK (HTTP {r.status_code})")
            return r.json()
        except requests.exceptions.Timeout:
            print(f"   ⏱️  Timeout direto: {url}")
        except requests.exceptions.RequestException as e:
            print(f"   ❌ GET direto falhou: {e}")
        return None

    def _proxy_get(self, url: str, params: dict = None, timeout: int = None) -> dict | None:
        client = self._proxy_client()
        if not client:
            return None
        try:
            return client.get(url, params=params, timeout=timeout or self.DEFAULT_TIMEOUT)
        except Exception as e:
            print(f"   ❌ proxy_get inesperado: {e}")
            return None

    # ------------------------------------------------------------------
    # POST
    # ------------------------------------------------------------------

    def _post(self, url: str, json: dict = None, timeout: int = None, use_proxy: bool = None) -> dict | None:
        should_proxy = use_proxy if use_proxy is not None else self._use_proxy()

        if should_proxy:
            print(f"🔀 [{self.__class__.__name__}] Tentando POST via proxy...")
            result = self._proxy_post(url, json=json, timeout=timeout)
            if result is not None:
                return result
            print(f"🔀 [{self.__class__.__name__}] Proxy falhou → fallback direto")
        else:
            print(f"🔀 [{self.__class__.__name__}] PROXY_SERVER_URL não definido → POST direto")

        return self._direct_post(url, json=json, timeout=timeout)

    def _direct_post(self, url: str, json: dict = None, timeout: int = None) -> dict | None:
        import requests
        print(f"   📡 POST direto → {url}")
        try:
            r = requests.post(url, json=json, timeout=timeout or self.DEFAULT_TIMEOUT)
            r.raise_for_status()
            print(f"   ✅ POST direto OK (HTTP {r.status_code})")
            return r.json()
        except requests.exceptions.RequestException as e:
            print(f"   ❌ POST direto falhou: {e}")
        return None

    def _proxy_post(self, url: str, json: dict = None, timeout: int = None) -> dict | None:
        client = self._proxy_client()
        if not client:
            return None
        try:
            return client.post(url, json=json, timeout=timeout or self.DEFAULT_TIMEOUT)
        except Exception as e:
            print(f"   ❌ proxy_post inesperado: {e}")
            return None

    # ------------------------------------------------------------------
    # BROWSE — Playwright via siaa-proxy
    # ------------------------------------------------------------------

    def _browse(self, url: str, extract: str = "text", wait_for: str = None) -> str | None:
        print(f"🔀 [{self.__class__.__name__}] BROWSE → {url}")
        client = self._proxy_client()
        if not client:
            print(f"   ⚠️  browse indisponível — configure PROXY_SERVER_URL")
            return None
        try:
            return client.browse(url=url, extract=extract, wait_for=wait_for)
        except Exception as e:
            print(f"   ❌ browse inesperado: {e}")
            return None

    # ------------------------------------------------------------------
    # Interface obrigatória
    # ------------------------------------------------------------------

    @abstractmethod
    def fetch(self, **kwargs):
        raise NotImplementedError