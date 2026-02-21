import asyncio
import os
import re
import time

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

def pre_process(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"(\?)", r" \1", text)
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text


from core.memory_manager import MemoryManager
from core.agent import CynbotAgent
from core.audio_handler import handle_voice

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

session: dict = {
    "history":    "",
    "last_time":  time.time(),
    "close_next": False,
}

processed: set = set()
BOOT_TIME = time.time()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid      = update.update_id
    user_id  = str(update.effective_chat.id)
    chat_id  = update.effective_chat.id
    msg_text = update.message.text
    msg_ts   = update.message.date.timestamp()

    print(f"\n{'='*55}")
    print(f"📩 uid={uid} | user={user_id} | ts={msg_ts:.0f}")
    print(f"📝 '{msg_text}'")

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

    now     = time.time()
    elapsed = now - session["last_time"]

    if session["close_next"] or elapsed > TIMEOUT:
        reason = "ação concluída" if session["close_next"] else f"timeout {elapsed:.0f}s"
        print(f"🔄 Sessão resetada ({reason}).")
        session["history"]    = ""
        session["close_next"] = False

    # ------------------------------------------------------------------
    # Status progressivo amarrado às fases reais do processamento.
    #
    # O callback é chamado de dentro da thread do agente/LLM.
    # Como editar mensagem do Telegram requer o event loop async,
    # usamos loop.call_soon_threadsafe para agendar a edição com segurança.
    # ------------------------------------------------------------------
    loop   = asyncio.get_event_loop()
    status = await update.message.reply_text("💬 Lendo mensagem...")

    def set_status(text: str):
        """Chamado de dentro da thread síncrona do agente."""
        asyncio.run_coroutine_threadsafe(status.edit_text(text), loop)

    print("▶️  Processando no Núcleo de IA...")

    intent, reply, close = await asyncio.to_thread(
        agent.process, msg_text, session["history"], set_status
    )

    if close:
        print(f"🏁 Sessão de assunto encerrada ({intent}).")
        memory.save_memory(intent, msg_text, reply)
        session["close_next"] = True
    else:
        session["history"] += f"\n{memory.user_name}: {msg_text}\n{memory.bot_name}: {reply}"

    session["last_time"] = now

    await status.delete()
    await update.message.reply_text(reply)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != AUTH_ID:
        print("🚫 Áudio não autorizado.")
        return

    print(f"\n{'='*55}")
    print("🎤 Áudio recebido.")
    await handle_voice(update, context, agent, session, memory)


if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRO: TELEGRAM_TOKEN não configurado no .env")
        exit(1)

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_audio))

    print(f"🚀 {memory.bot_name} online para {memory.user_name}!")
    app.run_polling(drop_pending_updates=True)