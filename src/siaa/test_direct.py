import os
import sys
from dotenv import load_dotenv

# Garante que o Python encontra os módulos locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configura o ambiente para teste local
os.environ["SIAA_DATA_DIR"] = "../../volumes/siaa-data"
load_dotenv("../../.env")

from core.agent import Agent

def test_bot():
    print("🚀 Iniciando Teste Direto (Modo Terminal)")
    print("--- Digite 'sair' para encerrar ---")
    
    # Se estiver testando localmente SEM Docker, mude a URL no .env para localhost:11434
    # ou altere aqui temporariamente:
    # os.environ["OLLAMA_URL"] = "http://localhost:11434/api/generate"
    
    agent = Agent()
    history = ""
    
    while True:
        text = input("\nVocê: ")
        if text.lower() in ['sair', 'exit']: break
        
        try:
            intent, reply, close = agent.process(text, history)
            print(f"\n[Intenção]: {intent}")
            print(f"[Bot]: {reply}")
            
            if close:
                history = ""
                print("--- Sessão Finalizada ---")
            else:
                history += f"\nUsuário: {text}\nBot: {reply}"
                
        except Exception as e:
            print(f"❌ Erro: {e}")

if __name__ == "__main__":
    test_bot()