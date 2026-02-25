# =============================================================
# Trecho do app.py que registra os crons no APScheduler.
# Substitui a função setup_cron_jobs existente.
#
# A mudança principal: get_schedule() agora retorna list[dict]
# em vez de dict — para suportar múltiplos schedules por módulo.
# =============================================================

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.module_loader import load_crons


def setup_cron_jobs(scheduler: AsyncIOScheduler, memory, bot_send_func, chat_id: str):
    """
    Registra todos os cron jobs dos módulos no APScheduler.

    Cada módulo com HAS_CRON=True e cron.py é carregado via module_loader.
    get_schedule() retorna list[dict] — cada dict vira um add_job separado.
    Isso permite múltiplos schedules no mesmo módulo (ex: 8h e 18h).
    """
    cron_instances = load_crons(memory)

    for cron in cron_instances:
        # Injeta o bot_send agora que temos a referência
        cron.bot_send = bot_send_func

        if not cron.is_enabled():
            print(f"⏸️  [{cron.__class__.__name__}] Desabilitado — pulando registro.")
            continue

        schedules = cron.get_schedule()  # sempre list[dict]

        for i, schedule in enumerate(schedules):
            trigger  = schedule.pop("trigger")  # remove 'trigger' do dict de kwargs
            job_id   = f"{cron.__class__.__name__}_{i}"
            job_name = cron.__class__.__name__ if i == 0 else f"{cron.__class__.__name__} #{i+1}"

            scheduler.add_job(
                cron.run,
                trigger=trigger,
                kwargs={"chat_id": str(chat_id)},
                id=job_id,
                name=job_name,
                replace_existing=True,
                misfire_grace_time=60,
                **schedule,  # hour, minute / minutes, etc.
            )
            print(f"⏰ Job registrado: {job_name} | trigger={trigger} | params={schedule}")
