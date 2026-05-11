import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def _run_diary():
    from skills.diary import generate_diary
    logger.info("Scheduler: iniciando geração automática do diário.")
    try:
        await generate_diary()
        logger.info("Scheduler: diário salvo com sucesso.")
    except Exception:
        logger.exception("Scheduler: erro ao gerar diário automático.")


def start_scheduler(_app=None):
    _scheduler.add_job(
        _run_diary,
        trigger=CronTrigger(hour=config.DIARY_HOUR, minute=config.DIARY_MINUTE),
        id="daily_diary",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler iniciado — diário automático às %02d:%02d.",
        config.DIARY_HOUR,
        config.DIARY_MINUTE,
    )
