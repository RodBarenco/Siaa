from datetime import datetime


_DIAS_SEMANA = [
    "Segunda-feira", "Terça-feira", "Quarta-feira",
    "Quinta-feira", "Sexta-feira", "Sábado", "Domingo",
]

_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def get_situational_context() -> str:
    """
    Retorna um bloco de texto com data/hora atual para ser injetado
    no início de todo prompt enviado ao LLM, resolvendo o problema
    de modelos locais não terem noção do tempo real.
    """
    now        = datetime.now()
    dia_semana = _DIAS_SEMANA[now.weekday()]
    mes_nome   = _MESES[now.month - 1]

    # Período do dia
    if now.hour < 12:
        periodo = "manhã"
    elif now.hour < 18:
        periodo = "tarde"
    else:
        periodo = "noite"

    # Tipo de dia
    tipo_dia = "fim de semana" if now.weekday() >= 5 else "dia útil"

    return (
        f"[CONTEXTO SITUACIONAL]\n"
        f"Hoje é {dia_semana}, {now.day} de {mes_nome} de {now.year}.\n"
        f"Hora atual: {now.strftime('%H:%M')}. Período: {periodo}. ({tipo_dia})\n"
        f"[FIM DO CONTEXTO SITUACIONAL]\n"
    )
