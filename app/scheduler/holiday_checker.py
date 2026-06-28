from datetime import date

from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.utils.dates import is_weekend, is_working_day


def should_run_scheduled_job(check_date: date | None = None) -> bool:
    db: Session = SessionLocal()
    try:
        return is_working_day(db, check_date)
    finally:
        db.close()


def is_working_day_legacy() -> bool:
    return should_run_scheduled_job()
