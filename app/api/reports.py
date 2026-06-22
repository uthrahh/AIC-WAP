from datetime import date

from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_manager
from app.database.deps import get_db
from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.models.pending_work import PendingWork
from app.services.export_service import export_to_excel, export_to_pdf
from app.services.reporting_service import _aggregate_completed_by_task
from app.utils.dates import today_ist, week_bounds
from app.utils.text_parser import tasks_from_json

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/daily-activity")
def daily_activity(
    report_date: date | None = Query(None),
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    report_date = report_date or today_ist()
    updates = (
        db.query(DailyUpdate, Employee)
        .join(Employee, DailyUpdate.employee_id == Employee.id)
        .filter(func.date(DailyUpdate.timestamp) == report_date)
        .all()
    )
    data = [
        {
            "employee": emp.name,
            "completed": tasks_from_json(up.completed_tasks),
            "pending": tasks_from_json(up.pending_tasks),
            "is_leave": up.is_leave,
        }
        for up, emp in updates
    ]
    return {"status": "success", "date": str(report_date), "data": data}

@router.get("/reports")
def trend_analysis(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    from datetime import timedelta

    end = today_ist()
    start = end - timedelta(days=days)
    updates = (
        db.query(DailyUpdate)
        .filter(
            func.date(DailyUpdate.timestamp) >= start,
            func.date(DailyUpdate.timestamp) <= end,
            DailyUpdate.is_leave.is_(False),
        )
        .all()
    )
    daily_counts: dict[str, int] = {}
    for u in updates:
        d = str(u.timestamp.date()) if u.timestamp else "unknown"
        daily_counts[d] = daily_counts.get(d, 0) + len(tasks_from_json(u.completed_tasks))

    return {
        "status": "success",
        "period": {"start": str(start), "end": str(end)},
        "task_volume_by_day": [
            {"date": k, "tasks": v} for k, v in sorted(daily_counts.items())
        ],
    }


@router.get("/export/pdf")
def export_pdf(
    report_type: str = Query("daily-activity"),
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    from app.services.reporting_service import format_daily_summary

    content = format_daily_summary(db, today_ist())
    path = export_to_pdf(report_type, content, f"{report_type}_{today_ist()}.pdf")
    return FileResponse(path, media_type="application/pdf", filename=Path(path).name)


@router.get("/export/excel")
def export_excel(
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    result = daily_activity(db=db, manager=manager)
    rows = []
    for item in result["data"]:
        rows.append(
            {
                "employee": item["employee"],
                "completed": ", ".join(item["completed"]),
                "pending": ", ".join(item["pending"]),
                "is_leave": item["is_leave"],
            }
        )
    path = export_to_excel(rows, f"daily_activity_{today_ist()}.xlsx")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(path).name,
    )
