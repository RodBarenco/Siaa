MODULE_NAME = "agenda"

INTENTS = [
    "AGENDA_ADD",
    "AGENDA_LIST",
    "AGENDA_REM",
]

INTENT_DESCRIPTIONS = {
    "AGENDA_ADD":  "Adicionar compromisso, evento ou lembrete na agenda",
    "AGENDA_LIST": "Consultar ou listar compromissos agendados",
    "AGENDA_REM":  "Remover ou cancelar um compromisso da agenda",
}

HAS_CRON = True
HAS_WEB  = False
