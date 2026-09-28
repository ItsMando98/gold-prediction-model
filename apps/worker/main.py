"""Worker entrypoint: schedules ingestion and the weekly Friday prediction.

MVP scheduler per plan section 5 ("APScheduler for MVP"). Replace with
Celery/Temporal once ingestion outgrows a single process.
"""

import asyncio
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from apps.worker.jobs import generate_weekly_prediction, ingest_daily
from packages.common.config import get_settings
from packages.common.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    scheduler = AsyncIOScheduler(timezone="UTC")

    # Weekdays 22:00 UTC -- after the US session close.
    scheduler.add_job(
        ingest_daily, CronTrigger(day_of_week="mon-fri", hour=22, minute=0), id="ingest_daily"
    )
    # Friday 21:15 UTC -- after close, ahead of the weekend news window.
    scheduler.add_job(
        generate_weekly_prediction,
        CronTrigger(day_of_week="fri", hour=21, minute=15),
        id="generate_weekly_prediction",
    )

    scheduler.start()
    logger.info("worker_started", jobs=[job.id for job in scheduler.get_jobs()])

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
