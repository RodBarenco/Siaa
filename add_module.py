import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"✅ Arquivo criado: {path}")

def to_camel_case(text):
    return text.capitalize()

def add_module():
    print("🚀 --- GERADOR DE MÓDULOS CYNBOT --- 🚀")
    module_name = input("Nome do novo módulo (ex: notas, tarefas): ").lower().strip()
    
    if not module_name:
        print("❌ Nome inválido.")
        return

    class_name = to_camel_case(module_name)
    upper_name = module_name.upper()

    # ---------------------------------------------------------
    # 1. CRIAR ARQUIVO DE ACTION
    # ---------------------------------------------------------
    action_content = f"""
from .base_actions import BaseActions
from .shared_utils import tokenize
from datetime import datetime

class {class_name}Actions(BaseActions):
    def __init__(self, db_path):
        schema = "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, time TEXT, title TEXT, keywords TEXT, content TEXT"
        super().__init__(db_path, "{module_name}", schema)

    def extract_and_prepare(self, message, llm_func):
        prompt = f"TASK: Extraia o título para {module_name}. Mensagem: '{{message}}'. Título:"
        title = llm_func(prompt, fast=True)
        
        return {{
            "date": datetime.now().strftime("%d/%m/%Y"),
            "time": datetime.now().strftime("%H:%M"),
            "title": title or message,
            "keywords": ",".join(tokenize(title or message)),
            "content": message
        }}
"""
    create_file(f"memory_actions/{module_name}_actions.py", action_content)

    # ---------------------------------------------------------
    # 2. CRIAR ARQUIVO DE ENTITY
    # ---------------------------------------------------------
    entity_content = f"""
from .base import BaseEntity
from memory_actions.{module_name}_actions import {class_name}Actions

class {class_name}Entity(BaseEntity):
    def __init__(self, memory):
        super().__init__(memory)
        self.actions = {class_name}Actions(memory.db_path)

    def run(self, message: str, intent: str, history: str = "") -> tuple:
        # CONFIRMAÇÃO DE REMOÇÃO
        if self.mem.pending_action and self.mem.pending_action["domain"] == "{upper_name}":
            if any(w in message.lower() for w in ["sim", "pode", "vrau", "confirmar"]):
                self.actions.delete(self.mem.pending_action["id"])
                self.mem.pending_action = None
                return "🗑️ Item removido com sucesso!", True
            self.mem.pending_action = None
            return "👍 Operação cancelada.", True

        # ADICIONAR
        if intent == "{upper_name}_ADD":
            data = self.actions.extract_and_prepare(message, self.mem._llm)
            self.actions.insert(data)
            return f"✅ Salvo em {class_name}: {{data['title']}}", True

        # REMOVER
        if intent == "{upper_name}_REM":
            target = self.actions.search_smart(message, ["title", "keywords", "content"])
            if target:
                self.mem.pending_action = {{ "domain": "{upper_name}", "id": target["id"] }}
                return f"❓ Deseja apagar '{{target['title']}}'?", False
            return "❌ Não encontrei esse item.", True

        # LISTAR
        if intent == "{upper_name}_LIST":
            items = self.actions.list_all()
            if not items: return "📭 A lista está vazia.", True
            res = "📋 **{class_name}:**\\n" + "\\n".join([f"• {{i['date']}}: {{i['title']}}" for i in items])
            return res, True

        return "Desculpe, não entendi o que fazer com este módulo.", False
"""
    create_file(f"entities/{module_name}.py", entity_content)

    # ---------------------------------------------------------
    # 3. MODIFICAR AGENT.PY (NA PASTA CORE)
    # ---------------------------------------------------------
    print("🔄 Atualizando core/agent.py...")
    try:
        with open("core/agent.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_agent_lines = []
        for line in lines:
            if "# [NOVOS_IMPORTS_AQUI]" in line:
                new_agent_lines.append(f"from entities.{module_name} import {class_name}Entity\n")
                new_agent_lines.append(line)
            elif "# [NOVAS_ENTIDADES_AQUI]" in line:
                new_agent_lines.append(f'            # "{upper_name}": {class_name}Entity(memory),\n')
                new_agent_lines.append(line)
            else:
                new_agent_lines.append(line)

        with open("core/agent.py", "w", encoding="utf-8") as f:
            f.writelines(new_agent_lines)
    except FileNotFoundError:
        print("❌ Arquivo 'core/agent.py' não encontrado. Você moveu o arquivo para a pasta core?")

    # ---------------------------------------------------------
    # 4. MODIFICAR INTENT_HANDLER.PY (NA PASTA CORE)
    # ---------------------------------------------------------
    print("🔄 Atualizando core/intent_handler.py...")
    try:
        with open("core/intent_handler.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_handler_lines = []
        for line in lines:
            new_handler_lines.append(line)
            if 'valid_labels = [' in line:
                new_handler_lines.append(f'            # "{upper_name}_ADD", "{upper_name}_LIST", "{upper_name}_REM",\n')

        with open("core/intent_handler.py", "w", encoding="utf-8") as f:
            f.writelines(new_handler_lines)
    except FileNotFoundError:
        print("❌ Arquivo 'core/intent_handler.py' não encontrado.")

    print("\n✨ --- MÓDULO INSTALADO COM SUCESSO --- ✨")
    print(f"👉 Arquivos gerados:")
    print(f"   - memory_actions/{module_name}_actions.py")
    print(f"   - entities/{module_name}.py")
    print("\n🛠️  PASSOS FINAIS:")
    print(f"1. Vá em 'core/agent.py' e apague o # da linha '{upper_name}'")
    print(f"2. Vá em 'core/intent_handler.py' e apague o # da lista valid_labels")
    print(f"3. Ainda em 'core/intent_handler.py', digite a descrição de {upper_name} dentro do prompt (ex: '{upper_name}_ADD: Adicionar uma nova nota').")

if __name__ == "__main__":
    add_module()