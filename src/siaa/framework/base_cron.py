import json
import os
from abc import ABC, abstractmethod


class BaseCron(ABC):
    """
    Base para tarefas agendadas (cron jobs) de módulos.

    Config em: <SIAA_DATA_DIR>/contexts/cron-jobs/<module_name>.json

    Estrutura padrão (um schedule):
        {
          "enabled": true,
          "trigger": "cron",
          "cron":     { "hour": 8, "minute": 0 },
          "interval": null,
          "settings": { ... }
        }

    Estrutura com múltiplos schedules (exceção):
        {
          "enabled": true,
          "trigger": "cron",
          "cron": [
            { "hour": 8,  "minute": 0 },
            { "hour": 18, "minute": 0 }
          ],
          "interval": null,
          "settings": { ... }
        }

    Triggers suportados: "cron" | "interval"
    """

    MODULE_NAME: str = None

    def __init__(self, memory, bot_send_func=None):
        self.mem           = memory
        self.bot_send      = bot_send_func
        self._config_cache = None

    @abstractmethod
    async def run(self, chat_id: str):
        """Lógica principal do job. Chamada pelo scheduler."""
        raise NotImplementedError

    def get_schedule(self) -> list[dict]:
        """
        Retorna lista de dicts prontos para o APScheduler.
        Lê do JSON de config — subclasses raramente precisam sobrescrever.

        Retorno sempre é lista para suportar múltiplos schedules:
            [{"trigger": "cron", "hour": 8, "minute": 0}]
            [{"trigger": "interval", "minutes": 30}]
            [{"trigger": "cron", "hour": 8}, {"trigger": "cron", "hour": 18}]
        """
        cfg     = self._cron_config()
        trigger = cfg.get("trigger", "cron")
        block   = cfg.get(trigger)

        if not block:
            print(f"⚠️  [{self.__class__.__name__}] Bloco '{trigger}' ausente na config — usando padrão (cron 8h).")
            return [{"trigger": "cron", "hour": 8, "minute": 0}]

        # Normaliza: objeto único → lista de um elemento
        entries   = block if isinstance(block, list) else [block]
        schedules = []
        for entry in entries:
            s = dict(entry)
            s["trigger"] = trigger
            schedules.append(s)

        return schedules

    # ------------------------------------------------------------------
    # Helpers de config
    # ------------------------------------------------------------------

    def _module_name(self) -> str:
        if self.MODULE_NAME:
            return self.MODULE_NAME
        name = self.__class__.__name__
        return name[:-4].lower() if name.endswith("Cron") else name.lower()

    def _cron_config_path(self) -> str:
        data_dir = os.getenv("SIAA_DATA_DIR", "/siaa-data")
        return os.path.join(data_dir, "contexts", "cron-jobs", f"{self._module_name()}.json")

    def _cron_config(self) -> dict:
        """Carrega (com cache) o JSON de config do cron job."""
        if self._config_cache is not None:
            return self._config_cache

        path = self._cron_config_path()
        if not os.path.exists(path):
            print(f"⚠️  [{self.__class__.__name__}] Config não encontrada em {path} — usando padrões.")
            self._config_cache = {}
            return self._config_cache

        try:
            with open(path, "r", encoding="utf-8") as f:
                self._config_cache = json.load(f)
            print(f"✅ [{self.__class__.__name__}] Config carregada de {path}")
        except Exception as e:
            print(f"❌ [{self.__class__.__name__}] Erro ao ler config: {e}")
            self._config_cache = {}

        return self._config_cache

    def _cron_setting(self, key: str, default=None):
        """Atalho para ler um valor de config['settings']."""
        return self._cron_config().get("settings", {}).get(key, default)

    def is_enabled(self) -> bool:
        """Retorna True se o cron está habilitado (padrão: True)."""
        return self._cron_config().get("enabled", True)
