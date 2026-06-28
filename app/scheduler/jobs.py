from loguru import logger

from app.database.session import SessionLocal
from app.scheduler.holiday_checker import should_run_scheduled_job
from app.services.extraction_service import run_extraction_for_day
from app.services.reminder_service import send_reminders
from app.services.summary_service import (
    run_daily_summary,
    run_weekly_summary,
    sync_worklogs_to_sheets,
)
from app.utils.dates import today_ist


def _with_db(fn):
    def wrapper():
        if not should_run_scheduled_job():
            logger.info("Skipping job — not a working day")
            return
        db = SessionLocal()
        try:
            return fn(db)
        except Exception as exc:
            logger.exception(f"Scheduled job failed: {exc}")
            db.rollback()
        finally:
            db.close()

    return wrapper


@_with_db
def information_extraction_job(db):
    logger.info("Information Extraction Running")
    work_date = today_ist()
    result = run_extraction_for_day(db, work_date)
    sync_worklogs_to_sheets(db, work_date)
    return result


@_with_db
def reminder_job(db):
    logger.info("Reminder Running")
    return send_reminders(db)


@_with_db
def daily_summary_job(db):
    logger.info("Daily Summary Running")
    return run_daily_summary(db)


@_with_db
def weekly_summary_job(db):
    logger.info("Weekly Summary Running")
    return run_weekly_summary(db)
