from datetime import date

from sqlalchemy.orm import Session

from app.models.pending_work import PendingWork
from app.utils.dates import parse_date_flexible
from app.utils.text_parser import normalize_task_name, tasks_match


def add_pending_items(
    db: Session,
    tasks: list[str],
    created_date: date,
    created_by: str,
    source_message: str,
) -> list[PendingWork]:
    created = []
    for task in tasks:
        normalized = normalize_task_name(task)
        existing = (
            db.query(PendingWork)
            .filter(
                PendingWork.status == "PENDING",
                PendingWork.task_name.ilike(f"%{task.strip()}%"),
            )
            .first()
        )
        if existing:
            continue
        item = PendingWork(
            task_name=task.strip(),
            description=normalized,
            status="PENDING",
            created_date=created_date,
            created_by=created_by,
            source_message=source_message,
        )
        db.add(item)
        created.append(item)
    db.commit()
    return created


def reconcile_completed_tasks(
    db: Session,
    completed_tasks: list[str],
    completed_by: str,
    completed_date: date,
) -> list[PendingWork]:
    updated = []
    pending_items = db.query(PendingWork).filter(PendingWork.status == "PENDING").all()
    for task in completed_tasks:
        for item in pending_items:
            if tasks_match(task, item.task_name):
                item.status = "COMPLETED"
                item.completed_date = completed_date
                item.completed_by = completed_by
                updated.append(item)
                break
    if updated:
        db.commit()
    return updated


def get_active_pending_work(db: Session) -> list[PendingWork]:
    return (
        db.query(PendingWork)
        .filter(PendingWork.status == "PENDING")
        .order_by(PendingWork.created_date.asc())
        .all()
    )


def register_from_whatsapp_message(
    db: Session,
    date_str: str,
    tasks: list[str],
    created_by: str,
    source_message: str,
) -> list[PendingWork]:
    created_date = parse_date_flexible(date_str) or date.today()
    return add_pending_items(db, tasks, created_date, created_by, source_message)
