import os, time
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# =========================================================
# 🔥 A FUNÇÃO DE LIMPEZA PRECISA ESTAR AQUI NO APP.PY
# =========================================================
def pre_process(text):
    """Garante que o '?' seja tratado como um token isolado."""
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'(\?)', r' \1', text)
    text = re.sub(r'[^a-z0-9\s\?]', '', text)
    return text

# Módulos Internos (Agora vêm da pasta core)
from core.memory_manager import MemoryManager
from core.agent import CynbotAgent
from core.audio_handler import handle_voice

# ---------------------------------------------------------
# 1. CONFIGURAÇÕES E INICIALIZAÇÃO
# ---------------------------------------------------------
load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
AUTH_ID = os.getenv("TELEGRAM_CHAT_ID")
TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 300))

print("🔄 Inicializando Memória e Configurações...")
memory = MemoryManager()

# Faz o resumo dos últimos papos do SQL para o TXT de médio prazo
print("📚 Consolidando a Memória de Médio Prazo (Broader Context)...")
memory.run_maintenance()

print("🤖 Inicializando Agente Principal...")
agent  = CynbotAgent(memory)

# ... (Todo o resto do seu código a partir daqui continua EXATAMENTE igual) ...

# ---------------------------------------------------------
# 2. CONTROLE DE ESTADO E SESSÃO
# ---------------------------------------------------------
session = {
    "history":    "",
    "last_time":  time.time(),
    "close_next": False,
}

processed: set = set()
BOOT_TIME = time.time()

# ---------------------------------------------------------
# 3. HANDLERS (TEXTO E ÁUDIO)
# ---------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid      = update.update_id
    user_id  = str(update.effective_chat.id)
    msg_text = update.message.text
    msg_ts   = update.message.date.timestamp()

    print(f"\n{'='*55}")
    print(f"📩 uid={uid} | user={user_id} | ts={msg_ts:.0f}")
    print(f"📝 '{msg_text}'")

    # Filtros de Segurança e Duplicidade
    if msg_ts < BOOT_TIME:
        print("⏭️  Pré-boot, ignorando.")
        return

    if uid in processed:
        print("⚠️  Duplicado, ignorando.")
        return
        
    processed.add(uid)
    if len(processed) > 200:
        processed.discard(min(processed))

    if user_id != AUTH_ID:
        print("🚫 Não autorizado.")
        return

    # Controle de Timeout da Sessão
    now     = time.time()
    elapsed = now - session["last_time"]

    if session["close_next"] or elapsed > TIMEOUT:
        reason = "ação concluída" if session["close_next"] else f"timeout {elapsed:.0f}s"
        print(f"🔄 Sessão resetada ({reason}).")
        session["history"]    = ""
        session["close_next"] = False

    # Processamento via Agente
    print("▶️  Processando no Núcleo de IA...")
    intent, reply, close = agent.process(msg_text, session["history"])

    # Tratamento de Fechamento de Ciclo
    if close:
        print(f"🏁 Sessão de assunto encerrada ({intent}).")
        memory.save_memory(intent, msg_text, reply)
        session["close_next"] = True
    else:
        bot_name = memory.bot_name
        session["history"] += f"\nUsuário: {msg_text}\n{bot_name}: {reply}"

    session["last_time"] = now
    await update.message.reply_text(reply)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verifica autorização também no áudio
    if str(update.effective_chat.id) != AUTH_ID:
        print("🚫 Áudio não autorizado.")
        return
        
    print(f"\n{'='*55}")
    print("🎤 Áudio recebido.")
    
    # O timeout logic pode ser espelhado dentro do handle_voice se desejar, 
    # mas o básico de repasse já está aqui.
    await handle_voice(update, context, agent, session, memory)


# ---------------------------------------------------------
# 4. LOOP PRINCIPAL
# ---------------------------------------------------------
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: TELEGRAM_TOKEN não configurado no .env")
        exit(1)

    app = Application.builder().token(TOKEN).build()
    
    # Adiciona os Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))
    
    print(f"🚀 {memory.bot_name} online para {memory.user_name}!")
    
    # Inicia o bot ignorando mensagens que chegaram enquanto ele estava offline
    app.run_polling(drop_pending_updates=True)