"""
module_loader.py — Coração da arquitetura modular do Siaa.

Responsabilidades:
  1. Varrer modules/ e descobrir todos os módulos instalados
  2. Ler o config.py de cada módulo (intents, flags HAS_CRON, HAS_WEB)
  3. Carregar dinamicamente entity.py, actions.py, cron.py, web.py
  4. Devolver ao agent.py e intent_handler.py tudo que precisam

Adicionar um novo módulo = criar a pasta modules/<nome>/ com os arquivos.
Zero edição em arquivos do core.
"""

import importlib
import os
import sys


# Garante que 'src/siaa/' está no path para imports absolutos funcionarem
_SIAA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SIAA_ROOT not in sys.path:
    sys.path.insert(0, _SIAA_ROOT)

_MODULES_DIR = os.path.join(_SIAA_ROOT, "modules")


def _discover_modules() -> list[str]:
    """Retorna lista de nomes de módulos instalados (pastas com config.py)."""
    if not os.path.isdir(_MODULES_DIR):
        print(f"⚠️  Diretório de módulos não encontrado: {_MODULES_DIR}")
        return []

    found = []
    for name in sorted(os.listdir(_MODULES_DIR)):
        module_path = os.path.join(_MODULES_DIR, name)
        if os.path.isdir(module_path) and os.path.exists(
            os.path.join(module_path, "config.py")
        ):
            found.append(name)
    return found


def _import(module_name: str, file: str):
    """Importa um arquivo de um módulo. Retorna None se não existir."""
    dotpath = f"modules.{module_name}.{file}"
    try:
        return importlib.import_module(dotpath)
    except ModuleNotFoundError:
        return None
    except Exception as e:
        print(f"❌ Erro ao importar {dotpath}: {e}")
        return None


def load_entities(memory) -> dict:
    """
    Carrega e instancia todas as entidades dos módulos descobertos.
    Retorna: {"AGENDA": AgendaEntity(memory), "FINANCE": FinanceEntity(memory), ...}
    """
    entities = {}

    for name in _discover_modules():
        cfg = _import(name, "config")
        if cfg is None:
            continue

        entity_mod = _import(name, "entity")
        if entity_mod is None:
            print(f"⚠️  Módulo '{name}' sem entity.py — ignorado.")
            continue

        # Convenção: classe se chama <Name>Entity
        class_name   = name.capitalize() + "Entity"
        entity_class = getattr(entity_mod, class_name, None)

        if entity_class is None:
            print(f"⚠️  '{class_name}' não encontrada em modules/{name}/entity.py")
            continue

        # Registra uma entrada por prefixo de intent declarado no config
        # Ex: INTENTS = ["AGENDA_ADD", "AGENDA_LIST"] → chave "AGENDA"
        prefix = getattr(cfg, "MODULE_NAME", name).upper()
        entities[prefix] = entity_class(memory)
        print(f"✅ Módulo carregado: {prefix}")

    return entities


def load_intents() -> list[str]:
    """
    Coleta todas as intenções declaradas nos config.py dos módulos.
    Usado pelo intent_handler para montar a lista de labels válidos do SVM.
    """
    all_intents = []
    for name in _discover_modules():
        cfg = _import(name, "config")
        if cfg is None:
            continue
        intents = getattr(cfg, "INTENTS", [])
        all_intents.extend(intents)
    return all_intents


def load_intent_descriptions() -> str:
    """
    Coleta as descrições de intenções para o prompt do LLM fallback.
    Cada config.py pode ter INTENT_DESCRIPTIONS: dict[str, str].
    """
    lines = []
    for name in _discover_modules():
        cfg = _import(name, "config")
        if cfg is None:
            continue
        descriptions = getattr(cfg, "INTENT_DESCRIPTIONS", {})
        for intent, desc in descriptions.items():
            lines.append(f"- {intent}: {desc}")
    return "\n".join(lines)


def load_crons(memory) -> list:
    """
    Carrega instâncias de cron jobs dos módulos que possuem cron.py.
    Retorna lista de instâncias BaseCron prontas para o scheduler.
    """
    crons = []
    for name in _discover_modules():
        cfg = _import(name, "config")
        if cfg is None or not getattr(cfg, "HAS_CRON", False):
            continue

        cron_mod = _import(name, "cron")
        if cron_mod is None:
            continue

        class_name = name.capitalize() + "Cron"
        cron_class = getattr(cron_mod, class_name, None)
        if cron_class:
            crons.append(cron_class(memory))
            print(f"⏰ Cron registrado: {class_name}")

    return crons


def get_module_names() -> list[str]:
    """Lista pública dos módulos descobertos. Útil para diagnóstico."""
    return _discover_modules()
