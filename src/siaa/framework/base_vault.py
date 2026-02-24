"""
framework/base_vault.py

Base para módulos que precisam persistir ou ler dados sensíveis.

Fluxo:
  1. Se VAULT_SERVER_URL estiver definido no .env:
     → usa SiaaVaultClient para ler/escrever via vault cifrado
  2. Se vault indisponível → retorna None com log (nunca quebra o módulo)

Uso — módulo herda BaseVault e usa os métodos _vault_*  - exemplo:

    class MultasModule(BaseVault):
        MODULE_NAME = "modulo-multas"   # namespace no vault

        def buscar(self):
            dados = self._vault_get_all()
            if not dados:
                return "Nenhum dado configurado."

            renavan = dados.get("renavan")
            cpf     = dados.get("cpf")
            # ... faz a consulta com renavan e cpf

        def salvar_cookie(self, cookie: str):
            self._vault_set("cookie_sessao", cookie, description="cookie do detran")

Convenção de namespace:
  - Cada módulo define MODULE_NAME (ex: "modulo-multas")
  - Esse nome é o namespace no vault — isolado dos outros módulos
  - Se MODULE_NAME não for definido, usa o nome da classe em lowercase
"""

import os
from abc import ABC


class BaseVault(ABC):

    # Subclasses podem sobrescrever para definir o namespace
    MODULE_NAME: str = None

    def _vault_available(self) -> bool:
        return bool(os.getenv("VAULT_SERVER_URL", "").strip()) and \
               bool(os.getenv("VAULT_CLIENT_SECRET", "").strip())

    def _namespace(self) -> str:
        return self.MODULE_NAME or self.__class__.__name__.lower()

    def _vault_client(self):
        if not self._vault_available():
            print(f"⚠️  [{self._namespace()}] Vault não configurado — VAULT_SERVER_URL ou VAULT_CLIENT_SECRET ausente.")
            return None
        try:
            from framework.siaa_vault_client import SiaaVaultClient
            return SiaaVaultClient(namespace=self._namespace())
        except RuntimeError as e:
            print(f"⚠️  [{self._namespace()}] Vault indisponível: {e}")
            return None
        except Exception as e:
            print(f"⚠️  [{self._namespace()}] SiaaVaultClient falhou: {e}")
            return None

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def _vault_get_all(self) -> dict | None:
        """
        Retorna todos os pares key→value do namespace deste módulo.

        Padrão recomendado: chamar uma vez no início da operação
        e usar o dict localmente — evita múltiplas chamadas ao vault.

        Retorno: {"cpf": "123...", "renavan": "ABC-1234", ...} ou None.
        """
        print(f"🔐 [{self._namespace()}] Carregando dados do vault...")
        client = self._vault_client()
        if not client:
            return None
        try:
            return client.get_all()
        except Exception as e:
            print(f"   ❌ _vault_get_all inesperado: {e}")
            return None

    def _vault_get(self, key: str) -> str | None:
        """
        Retorna o valor de uma chave específica do namespace.
        Use _vault_get_all() quando precisar de múltiplas chaves.
        """
        client = self._vault_client()
        if not client:
            return None
        try:
            return client.get(key)
        except Exception as e:
            print(f"   ❌ _vault_get('{key}') inesperado: {e}")
            return None

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def _vault_set(self, key: str, value: str, description: str = None) -> bool:
        """
        Salva ou atualiza um valor no vault.

        Exemplos de uso:
            self._vault_set("cookie_sessao", cookie, description="cookie do detran")
            self._vault_set("ultima_consulta", "2024-01-15")
            self._vault_set("renavan", renavan)
        """
        print(f"🔐 [{self._namespace()}] vault.set('{key}')...")
        client = self._vault_client()
        if not client:
            return False
        try:
            return client.set(key, value, description=description)
        except Exception as e:
            print(f"   ❌ _vault_set('{key}') inesperado: {e}")
            return False

    def _vault_delete(self, key: str) -> bool:
        """Remove uma chave do namespace deste módulo."""
        client = self._vault_client()
        if not client:
            return False
        try:
            return client.delete(key)
        except Exception as e:
            print(f"   ❌ _vault_delete('{key}') inesperado: {e}")
            return False

    # ------------------------------------------------------------------
    # Utilitário
    # ------------------------------------------------------------------

    def _vault_list_keys(self) -> list[str]:
        """Lista as chaves salvas no namespace deste módulo (sem valores)."""
        client = self._vault_client()
        if not client:
            return []
        try:
            return client.list_keys()
        except Exception as e:
            print(f"   ❌ _vault_list_keys inesperado: {e}")
            return []

    def _vault_has(self, key: str) -> bool:
        """Verifica se uma chave existe no namespace sem buscar o valor."""
        return key in self._vault_list_keys()