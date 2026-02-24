"""
framework/siaa_proxy_client.py — versão com renovação automática de token e resiliência

Funcionalidades:
- Handshake automático de Tokens (Renovação via secret_key)
- Retentativa (Retry) automática se o proxy bloquear a conexão (ex: túnel HTTPS/403)
- Denúncia automática (Report Failure) para rebaixar proxies ruins no servidor
- Fallback automático para conexão direta caso a rede de proxies falhe
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

    def _force_renew(self) -> str | None:
        """Invalida o cache e busca imediatamente um novo token."""
        SiaaProxyClient._cached_token  = None
        SiaaProxyClient._token_expires = 0
        return self._get_token()

    @property
    def _headers(self) -> dict:
        token = self._get_token()
        return {"X-API-Token": token or ""}

    # ------------------------------------------------------------------
    # Proxy HTTP rotativo com Denúncia (Report Failure)
    # ------------------------------------------------------------------

    def _get_best_proxy_info(self) -> dict | None:
        """Retorna um dicionário com o ID do proxy e a URL formatada."""
        try:
            r = requests.get(
                f"{self._base}/proxies/best",
                headers=self._headers,
                timeout=5,
            )
            # print(f"   /proxies/best → HTTP {r.status_code}") # Ocultado para poluir menos no loop

            if r.status_code == 200:
                p = r.json()
                auth = ""
                if p.get("username") and p.get("password"):
                    auth = f"{p['username']}:{p['password']}@"
                url = f"{p['protocol']}://{auth}{p['host']}:{p['port']}"
                print(f"   ✅ Proxy Alocado: ID {p['id']} | {p['host']}:{p['port']} ({p.get('latency_ms', '?')}ms)")
                return {"id": p["id"], "url": url}

            elif r.status_code == 401:
                print("   🔄 Token rejeitado (401) — renovando e tentando novamente...")
                new_token = self._force_renew()
                if not new_token:
                    print("   ❌ Não foi possível renovar o token.")
                    return None

                retry = requests.get(f"{self._base}/proxies/best", headers={"X-API-Token": new_token}, timeout=5)
                if retry.status_code == 200:
                    p = retry.json()
                    auth = ""
                    if p.get("username") and p.get("password"):
                        auth = f"{p['username']}:{p['password']}@"
                    url = f"{p['protocol']}://{auth}{p['host']}:{p['port']}"
                    print(f"   ✅ Proxy Alocado (retry): ID {p['id']} | {p['host']}:{p['port']}")
                    return {"id": p["id"], "url": url}

            elif r.status_code == 404:
                print("   ⚠️  Nenhum proxy validado disponível no servidor.")

        except requests.exceptions.ConnectionError:
            print(f"   ❌ siaa-proxy inacessível em {self._base}")
        except Exception as e:
            print(f"   ❌ Erro inesperado ao buscar proxy: {e}")
            
        return None

    def _report_failure(self, proxy_id: int):
        """Avisa o servidor de proxy que este IP falhou e deve ser rebaixado."""
        try:
            requests.post(
                f"{self._base}/proxies/{proxy_id}/report-failure", 
                headers=self._headers, 
                timeout=3
            )
            print(f"   📉 Proxy {proxy_id} denunciado e rebaixado.")
        except:
            pass # Ignora erros aqui para não travar o fluxo principal

    # ------------------------------------------------------------------
    # GET / POST com Sistema de Retry e Fallback
    # ------------------------------------------------------------------

    def get(self, url: str, params: dict = None, timeout: int = 10, max_retries: int = 3) -> dict | None:
        """Tenta fazer GET usando proxies diferentes. Cai pro Fallback se tudo falhar."""
        for attempt in range(1, max_retries + 1):
            proxy_info = self._get_best_proxy_info()
            
            if not proxy_info:
                print("   ⚠️  Sem proxy disponível no momento. Indo direto pro fallback...")
                break
                
            proxy_url = proxy_info["url"]
            proxy_id  = proxy_info["id"]
            proxies   = {"http": proxy_url, "https": proxy_url}
            
            print(f"   🌐 GET via proxy → Tentativa {attempt}/{max_retries} → {url}")
            
            try:
                r = requests.get(url, params=params, proxies=proxies, timeout=timeout)
                r.raise_for_status()
                print(f"   ✅ GET OK via Proxy (HTTP {r.status_code})")
                return r.json()
                
            except (requests.exceptions.ProxyError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                print(f"   ❌ Erro de túnel/conexão. O proxy bloqueou a requisição.")
                self._report_failure(proxy_id) # Dedura o proxy pro servidor
            except requests.exceptions.RequestException as e:
                print(f"   ❌ GET falhou (Erro HTTP ou Alvo bloqueou): {e}")
                break # Erro não relacionado a proxy (ex: 404 do site alvo), interrompe o loop

        # --- FALLBACK DIRETO ---
        print(f"   ⚠️  Tentando conexão direta (Fallback)...")
        try:
            r_direct = requests.get(url, params=params, timeout=timeout)
            r_direct.raise_for_status()
            print(f"   ✅ GET Direto OK (HTTP {r_direct.status_code})")
            return r_direct.json()
        except Exception as ex:
            print(f"   ❌ GET Direto também falhou: {ex}")
            
        return None

    def post(self, url: str, json: dict = None, timeout: int = 10, max_retries: int = 3) -> dict | None:
        """Tenta fazer POST usando proxies diferentes. Cai pro Fallback se tudo falhar."""
        for attempt in range(1, max_retries + 1):
            proxy_info = self._get_best_proxy_info()
            
            if not proxy_info:
                break
                
            proxy_url = proxy_info["url"]
            proxy_id  = proxy_info["id"]
            proxies   = {"http": proxy_url, "https": proxy_url}
            
            print(f"   🌐 POST via proxy → Tentativa {attempt}/{max_retries} → {url}")
            
            try:
                r = requests.post(url, json=json, proxies=proxies, timeout=timeout)
                r.raise_for_status()
                print(f"   ✅ POST OK via Proxy (HTTP {r.status_code})")
                return r.json()
                
            except (requests.exceptions.ProxyError, requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                print(f"   ❌ Erro de túnel/conexão no POST.")
                self._report_failure(proxy_id)
            except requests.exceptions.RequestException as e:
                print(f"   ❌ POST falhou (Erro HTTP ou Alvo): {e}")
                break

        print(f"   ⚠️  Tentando conexão direta (Fallback)...")
        try:
            r_direct = requests.post(url, json=json, timeout=timeout)
            r_direct.raise_for_status()
            print(f"   ✅ POST Direto OK (HTTP {r_direct.status_code})")
            return r_direct.json()
        except Exception as ex:
            print(f"   ❌ POST Direto também falhou: {ex}")
            
        return None

    # ------------------------------------------------------------------
    # BROWSE (Navegador Headless roda no servidor do Proxy, não sofre do erro 403 local)
    # ------------------------------------------------------------------

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
            
            if r.status_code == 401:
                print("   🔄 Token rejeitado no browse — renovando...")
                new_token = self._force_renew()
                if new_token:
                    r = requests.post(
                        f"{self._base}/proxies/browse",
                        headers={"X-API-Token": new_token},
                        json=payload,
                        timeout=timeout,
                    )

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