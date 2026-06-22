import json
from datetime import date, datetime

from loguru import logger
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.daily_update import DailyUpdate
from app.models.work_item import WorkItem
from app.models.employee import Employee
from app.services.audit_service import log_event
from app.services.message_store_service import (
    get_unprocessed_messages_for_day,
    mark_processed,
)
from app.services.metrics_service import calculate_all_metrics
from app.services.pending_work_service import reconcile_completed_tasks
from app.services.ai_extraction_service import extract_with_ai
from app.utils.text_parser import parse_worklog_message, tasks_to_json


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())[-10:]


def find_employee(db: Session, phone: str, whatsapp_name: str) -> Employee | None:
    normalized = _normalize_phone(phone)
    employee = (
        db.query(Employee)
        .filter(Employee.phone_number.like(f"%{normalized}"))
        .first()
    )
    if employee:
        return employee
    if whatsapp_name:
        return (
            db.query(Employee)
            .filter(Employee.whatsapp_name.ilike(f"%{whatsapp_name.strip()}%"))
            .first()
        )
    return None


def _has_update_for_day(db: Session, employee_id: int, work_date: date) -> bool:
    return (
        db.query(DailyUpdate)
        .filter(
            DailyUpdate.employee_id == employee_id,
            func.date(DailyUpdate.timestamp) == work_date,
        )
        .first()
        is not None
    )


def process_single_message(
    db: Session,
    *,
    sender_phone: str,
    sender_name: str,
    message_body: str,
    timestamp: datetime,
    work_date: date | None = None,
) -> DailyUpdate | None:
    work_date = work_date or timestamp.date()
    parsed = extract_with_ai(message_body)
    employee = find_employee(db, sender_phone, sender_name)
    if not employee:
        logger.warning(f"Unknown employee: {sender_name} ({sender_phone})")
        return None

    if _has_update_for_day(db, employee.id, work_date):
        logger.info(f"Duplicate update skipped for {employee.name} on {work_date}")
        return None

    update = DailyUpdate(
        employee_id=employee.id,
        timestamp=timestamp,
        completed_tasks=tasks_to_json(parsed.completed_tasks),
        pending_tasks=tasks_to_json(parsed.pending_tasks),
        raw_message=message_body,
        is_leave=parsed.is_leave,
    )
    db.add(update)

    for task in parsed.completed_tasks:

        item = (
            db.query(WorkItem)
            .filter(
                WorkItem.task_name.ilike(task)
            )
            .first()
        )

        if item:

            item.status = "COMPLETED"

            item.completed_by = employee.name

    db.commit()
    db.refresh(update)

    if not parsed.is_leave and parsed.completed_tasks:
        reconcile_completed_tasks(
            db,
            parsed.completed_tasks,
            employee.name,
            work_date,
        )

    log_event(
        db,
        "WORKLOG_EXTRACTED",
        f"Extracted worklog for {employee.name} on {work_date}",
        employee.id,
    )
    return update


def run_extraction_for_day(db: Session, work_date: date | None = None) -> dict:
    work_date = work_date or date.today()
    messages = get_unprocessed_messages_for_day(db, work_date)
    processed_ids = []
    created = 0
    skipped = 0

    for msg in messages:
        result = process_single_message(
            db,
            sender_phone=msg.sender_phone or "",
            sender_name=msg.sender_name or "",
            message_body=msg.message_body or "",
            timestamp=msg.timestamp,
            work_date=work_date,
        )
        processed_ids.append(msg.id)
        if result:
            created += 1
        else:
            skipped += 1

    mark_processed(db, processed_ids)
    calculate_all_metrics(db, work_date)

    summary = {
        "date": str(work_date),
        "messages_processed": len(messages),
        "updates_created": created,
        "skipped": skipped,
    }
    log_event(db, "EXTRACTION_JOB", json.dumps(summary))
    logger.info(f"Extraction complete: {summary}")
    return summary
