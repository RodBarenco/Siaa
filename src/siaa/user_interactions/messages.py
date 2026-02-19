class BotMessages:
    # --- CONFIRMAÇÕES ---
    CONFIRM_AGENDA_REM = "❓ Encontrei: **{title}** ({date} às {time}).\nConfirma a remoção? (Sim/Não)"
    CONFIRM_FINANCE_REM = "❓ Encontrei o lançamento: **{desc}** no valor de R$ {amount:.2f}.\nDeseja apagar este registro? (Sim/Não)"
    
    # --- FEEDBACK DE SUCESSO ---
    SUCCESS_AGENDA_ADD = "✅ Compromisso agendado: {title} para {date} às {time}."
    SUCCESS_FINANCE_ADD = "💰 Registro financeiro salvo: {desc} (R$ {amount:.2f})."
    SUCCESS_REM = "🗑️ Feito! O registro foi removido com sucesso."
    SUCCESS_LIST_EMPTY = "📭 Não há registros encontrados no momento."
    
    # --- CANCELAMENTO / ERROS ---
    CANCEL_ACTION = "Certo, operação cancelada. O registro foi mantido. 👍"
    NOT_FOUND = "🔍 Não consegui encontrar nada parecido."
    VAL_REQUIRED = "❓ Não identifiquei os detalhes (valor ou título). Poderia repetir?"
    ERROR_GENERIC = "❌ Ocorreu um erro ao processar essa tarefa."