import os, subprocess, tempfile, shutil, time, re
import whisper as _whisper_lib
import torch

# Modelo carregado uma vez na memória
_WHISPER_MODEL = None

def _get_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        size = os.getenv("WHISPER_MODEL_SIZE", "base")
        print(f"📦 Carregando Whisper ({size})...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _WHISPER_MODEL = _whisper_lib.load_model(size, device=device)
        print(f"✅ Whisper pronto no {device}.")
    return _WHISPER_MODEL


def _process_audio(audio_bytes: bytes, speed: float = 1.6) -> str:
    """
    Acelera, remove ruído ambiente e silêncios, e normaliza o áudio.
    """
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "input.ogg")
    dst = os.path.join(tmp, "output.wav")
    
    with open(src, "wb") as f:
        f.write(audio_bytes)

    # Pipeline de filtros avançado:
    # 1. afftdn: Redução de ruído baseada em FFT (remove chiado/barulho ambiente)
    # 2. silenceremove: Remove silêncios mortos
    # 3. loudnorm: Normaliza o volume (ganho inteligente)
    # 4. atempo: Acelera para a velocidade desejada (1.6x)
    filters = (
        f"afftdn,"
        f"silenceremove=1:0.1:-50dB,"
        f"loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"atempo={speed}"
    )

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-af", filters,
             "-ar", "16000", "-ac", "1", dst],
            check=True, capture_output=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ffmpeg: {e.stderr.decode()}")
        raise e

    return dst


def _transcribe(wav_path: str) -> str:
    """Transcreve com foco em comandos em português."""
    model = _get_model()
    result = model.transcribe(
        wav_path,
        language="pt",
        task="transcribe",
        fp16=False,
        initial_prompt="Transcrição de áudio em português brasileiro. Comandos de agenda, finanças e lembretes."
    )
    
    text = result.get("text", "").strip()
    
    # Filtro de alucinações (Whisper base às vezes inventa frases em silêncio)
    alucinacoes = [r"obrigado por assistir", r"legendas por", r"inscreva-se", r"deixe seu like"]
    for pattern in alucinacoes:
        if re.search(pattern, text, re.I):
            return ""
            
    return text


async def handle_voice(update, context, agent, session, memory) -> None:
    user_id = str(update.effective_chat.id)
    if user_id != os.getenv("TELEGRAM_CHAT_ID"):
        return

    voice = update.message.voice
    chat_id = update.effective_chat.id
    
    if voice.duration < 0.5:
        return # Ignora ruídos curtíssimos

    print(f"🎤 Áudio recebido ({voice.duration}s)")
    status = await update.message.reply_text("🎤 Processando áudio...")

    wav_path = None
    try:
        await context.bot.send_chat_action(chat_id, "record_voice")
        
        # 1. Download
        tg_file = await context.bot.get_file(voice.file_id)
        audio_bytes = bytes(await tg_file.download_as_bytearray())

        # 2. Processamento (1.6x + Denoiser)
        await status.edit_text("⚡ Limpando ruído e acelerando...")
        wav_path = _process_audio(audio_bytes, speed=1.6)

        # 3. Transcrição
        await status.edit_text("📝 Transcrevendo...")
        await context.bot.send_chat_action(chat_id, "typing")
        text = _transcribe(wav_path)

        if not text:
            await status.edit_text("❓ Não consegui entender o áudio. O som estava muito baixo ou ruidoso?")
            return

        print(f"📝 Transcrito: '{text}'")
        await status.edit_text(f"🎤 _{text}_\n\n⏳ Pensando...", parse_mode="Markdown")

        # 4. Lógica de Sessão e Processamento
        now = time.time()
        if now - session.get("last_time", 0) > int(os.getenv("SESSION_TIMEOUT", 300)):
            session["history"] = ""

        intent, reply, close = agent.process(text, session["history"])

        # Salva na memória se for uma ação concluída
        if close:
            memory.save_memory(intent, text, reply)
            session["history"] = "" 
        else:
            bot_name = os.getenv("BOT_NAME", "Cynbot")
            session["history"] += f"\nUsuário: {text}\n{bot_name}: {reply}"

        session["last_time"] = now

        # Resposta final
        await status.edit_text(f"🎤 _{text}_", parse_mode="Markdown")
        await update.message.reply_text(reply)

    except Exception as e:
        print(f"❌ Erro áudio: {e}")
        await status.edit_text("❌ Erro ao processar sua voz.")
    
    finally:
        if wav_path and os.path.exists(os.path.dirname(wav_path)):
            shutil.rmtree(os.path.dirname(wav_path), ignore_errors=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()