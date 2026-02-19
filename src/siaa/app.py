import os
import re
import time

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ------------------------------------------------------------------
# Função de limpeza — precisa estar aqui para o Pickle do SVM
# carregar corretamente no contexto do app.
# ------------------------------------------------------------------
def pre_process(text):
    """Garante que '?' seja tratado como token isolado."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"(\?)", r" \1", text)
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text


# ------------------------------------------------------------------
# Módulos internos
# Estrutura nova:
#   src/siaa/
#     core/         ← memory_manager, agent, intent_handler
#     entities/
#     memory_actions/
#     web_actions/
#     cron_jobs/
#     user_interactions/
# ------------------------------------------------------------------
from core.memory_manager import MemoryManager
from core.agent import CynbotAgent
from core.audio_handler import handle_voice

# ------------------------------------------------------------------
# 1. CONFIGURAÇÕES E INICIALIZAÇÃO
# ------------------------------------------------------------------
load_dotenv()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
AUTH_ID = os.getenv("TELEGRAM_CHAT_ID")
TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 300))

print("🔄 Inicializando Memória e Configurações...")
memory = MemoryManager()

print("📚 Consolidando Memória de Médio Prazo (Broader Context)...")
memory.run_maintenance()

print("🤖 Inicializando Agente Principal...")
agent = CynbotAgent(memory)

# ------------------------------------------------------------------
# 2. CONTROLE DE ESTADO E SESSÃO
# ------------------------------------------------------------------
session: dict = {
    "history":    "",
    "last_time":  time.time(),
    "close_next": False,
}

processed: set = set()
BOOT_TIME = time.time()

# ------------------------------------------------------------------
# 3. HANDLERS
# ------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid      = update.update_id
    user_id  = str(update.effective_chat.id)
    msg_text = update.message.text
    msg_ts   = update.message.date.timestamp()

    print(f"\n{'='*55}")
    print(f"📩 uid={uid} | user={user_id} | ts={msg_ts:.0f}")
    print(f"📝 '{msg_text}'")

    # Filtros de segurança e duplicidade
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

    # Controle de timeout da sessão
    now     = time.time()
    elapsed = now - session["last_time"]

    if session["close_next"] or elapsed > TIMEOUT:
        reason = "ação concluída" if session["close_next"] else f"timeout {elapsed:.0f}s"
        print(f"🔄 Sessão resetada ({reason}).")
        session["history"]    = ""
        session["close_next"] = False

    # Processamento via agente
    print("▶️  Processando no Núcleo de IA...")
    intent, reply, close = agent.process(msg_text, session["history"])

    if close:
        print(f"🏁 Sessão de assunto encerrada ({intent}).")
        memory.save_memory(intent, msg_text, reply)
        session["close_next"] = True
    else:
        session["history"] += f"\nUsuário: {msg_text}\n{memory.bot_name}: {reply}"

    session["last_time"] = now
    await update.message.reply_text(reply)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != AUTH_ID:
        print("🚫 Áudio não autorizado.")
        return

    print(f"\n{'='*55}")
    print("🎤 Áudio recebido.")
    await handle_voice(update, context, agent, session, memory)


# ------------------------------------------------------------------
# 4. LOOP PRINCIPAL
# ------------------------------------------------------------------
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: TELEGRAM_TOKEN não configurado no .env")
        exit(1)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))

    print(f"🚀 {memory.bot_name} online para {memory.user_name}!")
    app.run_polling(drop_pending_updates=True)