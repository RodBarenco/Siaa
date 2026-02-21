"""
framework/thinking.py

Context manager que mostra feedback visual enquanto o bot processa.

Comportamento:
  - Imediatamente: ativa o indicador "digitando..." do Telegram
  - Se demorar mais que `patience` segundos: envia mensagem "pensando..."
  - Ao terminar: edita a mensagem para sumir (ou deixa o reply substituir)

Uso nos módulos/entities:
    async with Thinking(update, context):
        reply = self.mem._llm(prompt)

Uso no app.py (nível de handler):
    async with Thinking(update, context, patience=2):
        intent, reply, close = agent.process(msg_text, history)
"""

import asyncio
import random
from contextlib import asynccontextmanager

_THINKING_MSGS = [
    "⏳ Pensando...",
    "⏳ Processando...",
    "⏳ Um segundo...",
]

@asynccontextmanager
async def Thinking(update, context, patience: float = 1.5):
    """
    Context manager assíncrono para feedback visual.
    Ativa o 'digitando' e envia uma mensagem se demorar.
    """
    status_msg = None
    typing_task = None
    delayed_task = None

    # Segurança: verifica se existe uma mensagem para responder
    message = update.effective_message
    if not message:
        yield
        return

    async def _keep_typing():
        """Mantém o status 'digitando...' ativo no topo do chat."""
        try:
            while True:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action="typing",
                )
                await asyncio.sleep(4) # Chat action dura ~5s
        except (asyncio.CancelledError, Exception):
            pass

    async def _delayed_status():
        """Envia mensagem de texto 'Pensando...' após o tempo de paciência."""
        nonlocal status_msg
        try:
            await asyncio.sleep(patience)
            txt = random.choice(_THINKING_MSGS)
            status_msg = await message.reply_text(txt)
        except (asyncio.CancelledError, Exception):
            pass

    # Inicia as tarefas em background
    typing_task = asyncio.create_task(_keep_typing())
    delayed_task = asyncio.create_task(_delayed_status())

    try:
        yield
    finally:
        # Cancela as tarefas ao sair do bloco 'with'
        if typing_task:
            typing_task.cancel()
        if delayed_task:
            delayed_task.cancel()
        
        # Aguarda cancelamento silenciosamente
        await asyncio.gather(typing_task, delayed_task, return_exceptions=True)

        # Remove a mensagem de texto se ela chegou a ser enviada
        if status_msg:
            try:
                await status_msg.delete()
            except Exception:
                pass