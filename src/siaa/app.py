import os
import re
import time
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ------------------------------------------------------------------
# 0. PRE-PROCESSAMENTO (Obrigatório para o SVM)
# ------------------------------------------------------------------
def pre_process(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"(\?)", r" \1", text)
    text = re.sub(r"[^a-z0-9\s\?]", "", text)
    return text

# Imports do Core
from core.memory_manager import MemoryManager
from core.agent import CynbotAgent
from core.audio_handler import handle_voice
from core.module_loader import load_crons

# ------------------------------------------------------------------
# 1. INICIALIZAÇÃO DE AMBIENTE E CORE
# ------------------------------------------------------------------
load_dotenv()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
AUTH_ID = os.getenv("TELEGRAM_CHAT_ID")
TIMEOUT = int(os.getenv("SESSION_TIMEOUT", 300))

print("🔄 Inicializando Memória...")
memory = MemoryManager()

# Nota: Se o Ollama demorar, o bot ficará parado aqui até terminar o resumo.
# Isso é normal no primeiro boot.
print("📚 Consolidando Memória (Pode demorar se o Ollama estiver carregando)...")
memory.run_maintenance()

print("🤖 Inicializando Agente e Módulos...")
agent = CynbotAgent(memory)

# ------------------------------------------------------------------
# 2. ESTADO DE SESSÃO
# ------------------------------------------------------------------
session: dict = {
    "history":    "",
    "last_time":  time.time(),
}

processed: set = set()
BOOT_TIME = time.time()

# ------------------------------------------------------------------
# 3. HELPERS E HANDLERS
# ------------------------------------------------------------------

async def send_safe_reply(update: Update, text: str):
    """Envia mensagem e evita crash por Markdown mal formatado pela IA."""
    try:
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        print(f"⚠️ Erro de Markdown no Telegram (enviando texto puro): {e}")
        await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid      = update.update_id
    user_id  = str(update.effective_chat.id)
    msg_text = update.message.text
    msg_ts   = update.message.date.timestamp()

    # Ignora mensagens antigas do histórico do Telegram (pré-boot)
    if msg_ts < BOOT_TIME or uid in processed:
        return
    processed.add(uid)

    # Segurança: Só responde ao dono
    if user_id != AUTH_ID:
        print(f"🚫 Acesso negado: {user_id}")
        return

    # Gestão de Sessão (Limpa histórico se ficar muito tempo sem falar)
    now = time.time()
    if now - session["last_time"] > TIMEOUT:
        session["history"] = ""
        print("⏱️ Sessão expirada, histórico limpo.")
    session["last_time"] = now

    # Execução Principal (to_thread impede que o bot "congele" durante o processamento)
    try:
        # Aqui a SVM vai printar o log no console do Docker
        intent, reply, close = await asyncio.to_thread(
            agent.process, msg_text, session["history"]
        )
    except Exception as e:
        print(f"🔥 Erro Crítico no Agente: {e}")
        await update.message.reply_text("Tive um problema ao processar. Pode repetir?")
        return

    # Resposta ao Usuário
    await send_safe_reply(update, reply)

    # Persistência de Memória se a interação foi concluída
    if close:
        memory.save_memory(intent, msg_text, reply)
        # Atualiza o histórico de chat da sessão atual
        session["history"] += f"\nUsuário: {msg_text}\n{memory.bot_name}: {reply}"
        session["history"]  = session["history"][-2000:] # Mantém apenas o final

async def handle_voice_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delega o processamento de áudio para o core."""
    try:
        # O audio_handler deve transcrever e retornar o texto ou processar direto
        await handle_voice(update, context, agent, session, memory)
    except Exception as e:
        print(f"❌ Erro no processamento de voz: {e}")
        await update.message.reply_text("Não consegui processar seu áudio.")

# ------------------------------------------------------------------
# 4. REGISTRO DE CRONS (Agendamentos dos Módulos)
# ------------------------------------------------------------------
def register_crons(app: Application):
    scheduler = app.job_queue
    if not scheduler:
        print("⚠️ JobQueue não disponível. Instale 'python-telegram-bot[job-queue]'")
        return

    crons = load_crons(memory)
    for cron in crons:
        schedule = cron.get_schedule()
        trigger  = schedule.pop("trigger", "interval")
        cron.bot_send = app.bot.send_message

        if trigger == "interval":
            scheduler.run_repeating(
                callback=lambda ctx, c=cron: c.run(AUTH_ID),
                interval=schedule.get("minutes", 60) * 60,
                first=10,
            )
        print(f"⏰ Cron registrado: {cron.__class__.__name__}")

# ------------------------------------------------------------------
# 5. EXECUÇÃO
# ------------------------------------------------------------------
def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN não configurado no .env")
        return

    # Build da Aplicação
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_msg))

    # Ativa agendamentos (se houver)
    register_crons(app)

    print(f"\n🚀 {memory.bot_name} online! Aguardando mensagens no Docker...\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()