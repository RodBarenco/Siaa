MODULE_NAME = "finance"

INTENTS = [
    "FINANCE_ADD",
    "FINANCE_LIST",
    "FINANCE_REM",
]

INTENT_DESCRIPTIONS = {
    "FINANCE_ADD":  "Registrar gasto, pagamento ou despesa financeira",
    "FINANCE_LIST": "Consultar ou resumir gastos e movimentações financeiras",
    "FINANCE_REM":  "Remover ou apagar um lançamento financeiro",
}

HAS_CRON = False
HAS_WEB  = False
