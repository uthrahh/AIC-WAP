from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_event(
    db: Session,
    event_type: str,
    description: str,
    user_id: int | None = None,
):
    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        description=description,
    )
    db.add(entry)
    db.commit()
    return entry
