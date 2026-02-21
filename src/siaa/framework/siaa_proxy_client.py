"""
framework/siaa_proxy_client.py

Interface do Siaa para consumir o siaa-proxy server.

Configuração no .env do siaa:
    PROXY_SERVER_URL=http://siaa-proxy:8000   (container)
    PROXY_SERVER_URL=http://localhost:8000    (local)
    PROXY_API_TOKEN=seu_token_aqui
"""

import os
import requests


class SiaaProxyClient:
    def __init__(self):
        self.base_url = os.getenv("PROXY_SERVER_URL", "").rstrip("/")
        self.token    = os.getenv("PROXY_API_TOKEN", "")
        self.timeout  = int(os.getenv("PROXY_CLIENT_TIMEOUT", "30"))

        if not self.base_url:
            raise RuntimeError("PROXY_SERVER_URL não definido — proxy desabilitado.")

    @property
    def _headers(self) -> dict:
        return {"X-API-Token": self.token, "Content-Type": "application/json"}

    def _get_best_proxy(self) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/proxies/best",
                             headers=self._headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                user, pwd = data.get("username"), data.get("password")
                proto, host, port = data.get("protocol","http"), data.get("host"), data.get("port")
                url = (f"{proto}://{user}:{pwd}@{host}:{port}" if user and pwd
                       else f"{proto}://{host}:{port}")
                return {"url": url, **data}
            elif r.status_code == 404:
                print("⚠️  Nenhum proxy validado disponível.")
        except Exception as e:
            print(f"⚠️  siaa-proxy inacessível: {e}")
        return None

    def get(self, url: str, params: dict = None, timeout: int = None) -> dict | None:
        try:
            proxy_info = self._get_best_proxy()
            if not proxy_info:
                return None
            proxies = {"http": proxy_info["url"], "https": proxy_info["url"]}
            r = requests.get(url, params=params, proxies=proxies,
                             timeout=timeout or self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"⚠️  SiaaProxyClient.get: {e}")
            return None

    def post(self, url: str, json: dict = None, timeout: int = None) -> dict | None:
        try:
            proxy_info = self._get_best_proxy()
            if not proxy_info:
                return None
            proxies = {"http": proxy_info["url"], "https": proxy_info["url"]}
            r = requests.post(url, json=json, proxies=proxies,
                              timeout=timeout or self.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"⚠️  SiaaProxyClient.post: {e}")
            return None

    def browse(self, url: str, extract: str = "text",
               wait_for: str = None, use_proxy: bool = True) -> str | None:
        try:
            payload = {"url": url, "use_proxy": use_proxy, "extract": extract}
            if wait_for:
                payload["wait_for"] = wait_for
            r = requests.post(f"{self.base_url}/proxies/browse",
                              headers=self._headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            if data.get("success"):
                return data.get("content")
            print(f"⚠️  browse erro: {data.get('error')}")
        except Exception as e:
            print(f"❌ SiaaProxyClient.browse [{url}]: {e}")
        return None

    def stats(self) -> dict | None:
        try:
            r = requests.get(f"{self.base_url}/proxies/stats",
                             headers=self._headers, timeout=5)
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None
