class BotMessages:
    # --- CONFIRMAÇÕES ---
    CONFIRM_AGENDA_REM  = "❓ Encontrei: *{title}* ({date} às {time}).\nConfirma a remoção? (Sim/Não)"
    CONFIRM_FINANCE_REM = "❓ Encontrei: *{desc}* R$ {amount:.2f}.\nDeseja apagar? (Sim/Não)"

    # --- SUCESSO ---
    SUCCESS_AGENDA_ADD  = "✅ Agendado: *{title}* para {date} às {time}."
    SUCCESS_FINANCE_ADD = "💰 Salvo: *{desc}* (R$ {amount:.2f}) em {date}."
    SUCCESS_REM         = "🗑️ Removido com sucesso!"
    SUCCESS_LIST_EMPTY  = "📭 Não há registros no momento."

    # --- CANCELAMENTO / ERROS ---
    CANCEL_REM      = "👍 Operação cancelada. O registro foi mantido."
    NOT_FOUND       = "🔍 Não encontrei nada parecido."
    VAL_REQUIRED    = "❓ Não identifiquei os detalhes. Pode repetir?"
    ERROR_GENERIC   = "❌ Ocorreu um erro ao processar. Pode tentar novamente?"