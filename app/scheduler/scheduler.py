from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.scheduler.jobs import (
    daily_summary_job,
    information_extraction_job,
    reminder_job,
    weekly_summary_job,
)

settings = get_settings()
scheduler = BackgroundScheduler(timezone=settings.timezone)

scheduler.add_job(
    information_extraction_job,
    CronTrigger(hour=19, minute=0, timezone=settings.timezone),
    id="information_extraction",
    replace_existing=True,
    max_instances=1,
)

for minute in (1, 31):
    scheduler.add_job(
        reminder_job,
        CronTrigger(hour=19, minute=minute, timezone=settings.timezone),
        id=f"reminder_19_{minute:02d}",
        replace_existing=True,
        max_instances=1,
    )

for minute in (1, 31):
    scheduler.add_job(
        reminder_job,
        CronTrigger(hour=20, minute=minute, timezone=settings.timezone),
        id=f"reminder_20_{minute:02d}",
        replace_existing=True,
        max_instances=1,
    )

scheduler.add_job(
    daily_summary_job,
    CronTrigger(hour=20, minute=0, timezone=settings.timezone),
    id="daily_summary",
    replace_existing=True,
    max_instances=1,
)

scheduler.add_job(
    weekly_summary_job,
    CronTrigger(day_of_week="fri", hour=20, minute=0, timezone=settings.timezone),
    id="weekly_summary",
    replace_existing=True,
    max_instances=1,
)
