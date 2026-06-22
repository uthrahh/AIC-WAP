from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_manager
from app.database.deps import get_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit", tags=["Audit"])


@router.get("/")
def list_audit_logs(
    limit: int = Query(50, le=200),
    event_type: str | None = Query(None),
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    logs = query.limit(limit).all()
    return {
        "status": "success",
        "data": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "user_id": log.user_id,
                "description": log.description,
                "timestamp": str(log.timestamp),
            }
            for log in logs
        ],
    }
