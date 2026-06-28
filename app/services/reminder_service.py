from datetime import date

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.services.audit_service import log_event
from app.services.whatsapp_service import whatsapp_service


def get_missing_employees(db: Session, work_date: date) -> list[Employee]:
    active = db.query(Employee).filter(Employee.is_active.is_(True)).all()
    missing = []
    for emp in active:
        update = (
            db.query(DailyUpdate)
            .filter(
                DailyUpdate.employee_id == emp.id,
                func.date(DailyUpdate.timestamp) == work_date,
            )
            .first()
        )
        if update:
            continue
        missing.append(emp)
    return missing


def send_reminders(db: Session, work_date: date | None = None) -> dict:
    work_date = work_date or date.today()
    missing = get_missing_employees(db, work_date)
    if not missing:
        log_event(db, "REMINDER_JOB", f"No reminders needed for {work_date}")
        return {"sent": False, "missing_count": 0}

    mentions = "\n".join(f"@{emp.whatsapp_name or emp.name}" for emp in missing)
    message = f"Reminder:\n\n{mentions}\n\nPlease submit today's worklog."
    sent = whatsapp_service.send_message(message)

    log_event(
        db,
        "REMINDER_SENT",
        f"Reminder sent to {len(missing)} employees for {work_date}",
    )
    logger.info(f"Reminder sent to {len(missing)} employees")
    return {"sent": sent, "missing_count": len(missing), "employees": [e.name for e in missing]}
