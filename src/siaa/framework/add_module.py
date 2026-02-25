"""
add_module.py — Gerador de módulos para o Siaa.

Cria toda a estrutura de um novo módulo em modules/<nome>/:
  config.py, entity.py, actions.py, cron.py (opcional),
  web.py (opcional), training.json

Se o módulo tiver cron job, também cria o arquivo de config em:
  volumes/siaa-data/contexts/cron-jobs/<nome>.json

Zero edição manual em arquivos do core.
"""

import os
import json


def _write(path: str, content: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"  ✅ {path}")


def _write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  ✅ {path}")


def _ask_cron_config(name: str) -> dict:
    """
    Pergunta ao dev as configurações do cron job de forma interativa.
    Retorna o dict que será salvo no JSON de config.
    """
    print(f"\n⚙️  Configuração do Cron Job '{name}':")
    print("   (Enter para usar o valor padrão entre colchetes)\n")

    # Tipo de schedule
    print("   Tipo de agendamento:")
    print("   1. Horário fixo diário (ex: toda manhã às 8h)  [padrão]")
    print("   2. Intervalo periódico (ex: a cada 30 minutos)")
    schedule_type = input("   Escolha (1/2): ").strip() or "1"

    schedule = {}
    if schedule_type == "2":
        raw = input("   Intervalo em minutos [60]: ").strip() or "60"
        schedule = {"trigger": "interval", "minutes": int(raw)}
    else:
        hour   = input("   Hora de execução (0-23) [8]: ").strip() or "8"
        minute = input("   Minuto (0-59) [0]: ").strip() or "0"
        schedule = {"trigger": "cron", "hour": int(hour), "minute": int(minute)}

    # Settings customizados
    print("\n   Deseja adicionar configurações extras ao módulo?")
    print("   (Ex: locale, max_items, threshold — acessíveis via self._cron_setting())")
    settings = {}
    while True:
        key = input("   Nome da config (Enter para terminar): ").strip()
        if not key:
            break
        val = input(f"   Valor de '{key}': ").strip()
        # Tenta converter para int/float se possível
        try:
            val = int(val)
        except ValueError:
            try:
                val = float(val)
            except ValueError:
                pass
        settings[key] = val

    return {
        "enabled":  True,
        "schedule": schedule,
        "settings": settings,
    }


def add_module():
    print("\n🚀 ——— GERADOR DE MÓDULOS SIAA ———\n")

    name = input("Nome do módulo (ex: notas, tarefas, email): ").lower().strip()
    if not name or not name.isalpha():
        print("❌ Nome inválido. Use apenas letras.")
        return

    base_dir   = os.path.join("modules", name)
    class_name = name.capitalize()
    upper      = name.upper()

    if os.path.exists(base_dir):
        print(f"❌ Módulo '{name}' já existe em {base_dir}")
        return

    has_cron = input("Tem cron job? (s/N): ").lower().strip() == "s"
    has_web  = input("Consome API externa? (s/N): ").lower().strip() == "s"

    intents_raw = input(
        f"Intenções (Enter para padrão [{upper}_ADD, {upper}_LIST, {upper}_REM]): "
    ).strip()
    if intents_raw:
        intents = [i.strip().upper() for i in intents_raw.split(",")]
    else:
        intents = [f"{upper}_ADD", f"{upper}_LIST", f"{upper}_REM"]

    # Se puramente cron (sem intents de conversa), pergunta se quer lista vazia
    if has_cron and not intents_raw:
        only_cron = input("Módulo puramente cron (sem intents de conversa)? (s/N): ").lower().strip() == "s"
        if only_cron:
            intents = []

    # Coleta config do cron de forma interativa
    cron_config_data = None
    if has_cron:
        cron_config_data = _ask_cron_config(name)

    print(f"\n📁 Criando modules/{name}/")

    # ------------------------------------------------------------------
    # config.py
    # ------------------------------------------------------------------
    intent_list  = json.dumps(intents, ensure_ascii=False)
    descriptions = "\n    ".join([f'"{i}": "",' for i in intents])
    _write(f"{base_dir}/config.py", f"""
MODULE_NAME = "{name}"

INTENTS = {intent_list}

INTENT_DESCRIPTIONS = {{
    {descriptions}
}}

HAS_CRON = {str(has_cron)}
HAS_WEB  = {str(has_web)}
""")

    # ------------------------------------------------------------------
    # actions.py  (não gerado para módulos puramente cron)
    # ------------------------------------------------------------------
    if intents:
        _write(f"{base_dir}/actions.py", f"""
from datetime import datetime
from framework.base_actions import BaseActions
from framework.shared_utils import tokenize


class {class_name}Actions(BaseActions):
    def __init__(self, db_path: str):
        schema = (
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "date TEXT, time TEXT, title TEXT, keywords TEXT, content TEXT"
        )
        super().__init__(db_path, "{name}", schema)

    def extract_and_prepare(self, message: str, llm_func) -> dict:
        prompt = (
            f"Extraia o título principal da mensagem em até 5 palavras.\\n"
            f"Responda SOMENTE com o título, sem explicações.\\n"
            f"Mensagem: '{{message}}'"
        )
        title = llm_func(prompt, fast=True).strip() or message[:40]
        return {{
            "date":     datetime.now().strftime("%d/%m/%Y"),
            "time":     datetime.now().strftime("%H:%M"),
            "title":    title,
            "keywords": ",".join(tokenize(title)),
            "content":  message,
        }}
""")

    # ------------------------------------------------------------------
    # entity.py  (não gerado para módulos puramente cron)
    # ------------------------------------------------------------------
    if intents:
        add_intent  = intents[0] if intents else f"{upper}_ADD"
        list_intent = intents[1] if len(intents) > 1 else f"{upper}_LIST"
        rem_intent  = intents[2] if len(intents) > 2 else f"{upper}_REM"

        _write(f"{base_dir}/entity.py", f"""
from framework.base_entity import BaseEntity
from modules.{name}.actions import {class_name}Actions


class {class_name}Entity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = {class_name}Actions(memory.db_path)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        try:
            # CONFIRMAÇÃO DE REMOÇÃO
            if intent == "CONFIRMATION" and self.mem.pending_action:
                if self.mem.pending_action.get("type") == "DELETE_CONFIRM":
                    if any(w in message.lower() for w in ["sim", "pode", "vrau", "confirmar", "ok"]):
                        self.actions.delete(self.mem.pending_action["ids"])
                        self.mem.pending_action = None
                        return "🗑️ Item removido com sucesso!", True
                    self.mem.pending_action = None
                    return "👍 Operação cancelada.", True

            # SELEÇÃO
            if intent == "SELECTION_RESPONSE" and self.mem.pending_action:
                ids = self.actions.parse_selection(message, self.mem.pending_action["items"])
                if not ids:
                    self.mem.pending_action = None
                    return "👍 Operação cancelada.", True
                self.mem.pending_action = {{
                    "domain": "{upper}", "type": "DELETE_CONFIRM", "ids": ids
                }}
                return f"Selecionei {{len(ids)}} item(ns). Confirmar? (Sim/Não)", False

            if intent == "{add_intent}":
                data = self.actions.extract_and_prepare(message, self.mem._llm)
                if self.actions.insert(data):
                    return f"✅ Salvo: {{data['title']}}", True
                return "❌ Falha ao salvar.", True

            if intent == "{rem_intent}":
                results = self.actions.search_multiple(message, ["title", "keywords", "content"])
                if not results:
                    items = self.actions.list_all(limit=5)
                    if not items:
                        return "📭 Lista vazia.", True
                    lista = "\\n".join([f"{{i+1}}. {{r['title']}}" for i, r in enumerate(items)])
                    self.mem.pending_action = {{
                        "domain": "{upper}", "type": "SELECTION", "items": items
                    }}
                    return f"Não encontrei. Qual remover?\\n{{lista}}", False
                self.mem.pending_action = {{
                    "domain": "{upper}", "type": "DELETE_CONFIRM",
                    "ids": [results[0]["id"]]
                }}
                return f"❓ Remover '{{results[0]['title']}}'? (Sim/Não)", False

            if intent == "{list_intent}":
                items = self.actions.list_all(limit=10)
                if not items:
                    return "📭 Lista vazia.", True
                lista = "\\n".join([f"• {{r['date']}} — {{r['title']}}" for r in reversed(items)])
                return f"📋 *{class_name}:*\\n{{lista}}", True

            return "Desculpe, não entendi o que fazer.", True

        except Exception as e:
            print(f"❌ {class_name}Entity: {{e}}")
            self.mem.pending_action = None
            return "Tive um problema. Pode repetir?", True
""")

    # ------------------------------------------------------------------
    # cron.py (opcional)
    # ------------------------------------------------------------------
    if has_cron:
        trigger_example = json.dumps(cron_config_data["schedule"]) if cron_config_data else '{"trigger": "cron", "hour": 8, "minute": 0}'
        _write(f"{base_dir}/cron.py", f"""
from framework.base_cron import BaseCron


class {class_name}Cron(BaseCron):
    \"\"\"
    Cron job do módulo {name}.
    Config em: <SIAA_DATA_DIR>/contexts/cron-jobs/{name}.json
    \"\"\"

    def get_schedule(self) -> dict:
        schedule = self._cron_schedule()
        # Usa config do JSON se disponível, senão usa padrão
        trigger = schedule.get("trigger", "{cron_config_data['schedule'].get('trigger', 'cron') if cron_config_data else 'cron'}")
        if trigger == "interval":
            return {{"trigger": "interval", "minutes": schedule.get("minutes", 60)}}
        return {{
            "trigger": "cron",
            "hour":   schedule.get("hour", 8),
            "minute": schedule.get("minute", 0),
        }}

    async def run(self, chat_id: str):
        if not self.bot_send:
            return

        if not self.is_enabled():
            print(f"⏸️  [{class_name}Cron] Desabilitado na config — pulando.")
            return

        # TODO: implementar lógica do cron
        # settings = self._cron_config().get("settings", {{}})
        # await self.bot_send(chat_id=chat_id, text="...", parse_mode="Markdown")
        pass
""")

        # Salva o JSON de config do cron nos volumes
        cron_config_path = os.path.join(
            "volumes", "siaa-data", "contexts", "cron-jobs", f"{name}.json"
        )
        _write_json(cron_config_path, cron_config_data)

    # ------------------------------------------------------------------
    # web.py (opcional)
    # ------------------------------------------------------------------
    if has_web:
        _write(f"{base_dir}/web.py", f"""
from framework.base_web import BaseWeb


class {class_name}Web(BaseWeb):
    def __init__(self, settings: dict = None):
        self.settings = settings or {{}}

    def fetch(self, **kwargs):
        # TODO: implementar chamada à API externa
        # return self._get("https://api.example.com/endpoint", params={{...}})
        raise NotImplementedError
""")

    # ------------------------------------------------------------------
    # training.json
    # ------------------------------------------------------------------
    training = {intent: [] for intent in intents}
    _write(
        f"{base_dir}/training.json",
        json.dumps(training, indent=2, ensure_ascii=False),
    )

    # ------------------------------------------------------------------
    # __init__.py
    # ------------------------------------------------------------------
    _write(f"{base_dir}/__init__.py", f"# módulo {name}")

    cron_config_note = ""
    if has_cron and cron_config_data:
        cron_config_note = f"\n   volumes/siaa-data/contexts/cron-jobs/{name}.json  ← config do cron (edite sem rebuild)"

    print(f"""
✨ ——— MÓDULO '{upper}' CRIADO ——— ✨

📁 modules/{name}/
   config.py      ← intenções registradas automaticamente
{'   entity.py      ← lógica de conversa (TODO: ajustar)' if intents else '   (sem entity — módulo puramente cron)'}
{'   actions.py     ← CRUD SQLite (TODO: ajustar schema se necessário)' if intents else ''}
   training.json  ← adicione exemplos de frases por intent
{'   cron.py        ← job agendado (TODO: implementar lógica)' if has_cron else ''}
{'   web.py         ← API externa (TODO: implementar)' if has_web else ''}
{cron_config_note}

🎯 PRÓXIMOS PASSOS:
{'   1. Preencha training.json com frases de exemplo' if intents else '   1. Implemente a lógica em cron.py'}
{'   2. Rode: python train_svm.py' if intents else '   2. Ajuste as settings em volumes/siaa-data/contexts/cron-jobs/' + name + '.json'}
   3. Reinicie o bot — o módulo já será carregado automaticamente!
""")


if __name__ == "__main__":
    add_module()
