from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.database.deps import get_db
from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.models.pending_work import PendingWork
from app.services.export_service import (
    export_completed_tasks_report,
    export_tasklog_pdf,
    export_to_excel,
)
from app.services.reporting_service import _aggregate_completed_by_task
from app.utils.dates import today_ist, week_bounds
from app.utils.text_parser import tasks_from_json

router = APIRouter(prefix="/api/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# /export/pdf  — Today's task-log PDF
# ---------------------------------------------------------------------------

@router.get("/export/pdf")
def export_pdf(db: Session = Depends(get_db)):

    report_date = date.today()

    updates = (
        db.query(DailyUpdate, Employee)
        .join(Employee, DailyUpdate.employee_id == Employee.id)
        .filter(func.date(DailyUpdate.timestamp) == report_date)
        .all()
    )

    # Build work_map exactly the same way the today-page does,
    # using tasks_from_json so the JSON structure is respected.
    work_map: dict[str, list[str]] = {}

    for update, employee in updates:

        completed = tasks_from_json(update.completed_tasks)

        if not completed:
            continue

        for item in completed:

            if isinstance(item, dict):
                task      = item.get("task", "").strip().lower()
                emp_names = item.get("employees", [])
                if not emp_names:
                    emp_names = [employee.name]
            else:
                task      = str(item).strip().lower()
                emp_names = [employee.name]

            if not task or task in ("on leave", "leave", "wfh", "holiday"):
                continue

            bucket = work_map.setdefault(task, set())
            for name in emp_names:
                if name:
                    bucket.add(name)

    # Convert sets → sorted lists for the PDF renderer
    work_map_sorted = {
        task: sorted(users)
        for task, users in work_map.items()
    }

    filename = report_date.strftime("%d%m%y") + "_TaskLog.pdf"
    pdf_path = export_tasklog_pdf(work_map_sorted, report_date, filename)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# /tasks/report/download  — Date-range completed-tasks PDF
# ---------------------------------------------------------------------------

@router.get("/tasks/report/download")
def download_completed_tasks_report(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
):
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end   = datetime.strptime(end_date,   "%Y-%m-%d").date()

    updates = (
        db.query(DailyUpdate, Employee)
        .join(Employee, DailyUpdate.employee_id == Employee.id)
        .filter(
            func.date(DailyUpdate.timestamp) >= start,
            func.date(DailyUpdate.timestamp) <= end,
        )
        .all()
    )

    rows = []

    for update, employee in updates:

        completed = tasks_from_json(update.completed_tasks)

        if not completed:
            continue

        for item in completed:

            if isinstance(item, dict):
                task      = item.get("task", "").strip()
                emp_names = item.get("employees", [employee.name])
                if not emp_names:
                    emp_names = [employee.name]
            else:
                task      = str(item).strip()
                emp_names = [employee.name]

            if not task:
                continue

            rows.append(
                {
                    "month":     update.timestamp.strftime("%B %Y"),
                    "week":      f"Week {update.timestamp.isocalendar().week}",
                    "date":      update.timestamp.strftime("%d-%m-%Y"),
                    "day":       update.timestamp.strftime("%A"),
                    "task":      task,
                    "employees": ", ".join(emp_names),
                }
            )

    filename = f"Tasks_{start}_{end}.pdf"
    pdf_path = export_completed_tasks_report(rows, filename)

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
    )


# ---------------------------------------------------------------------------
# /tasks/report  — Report page
# ---------------------------------------------------------------------------

@router.get("/tasks/report")
def task_report_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="pages/task_report.html",
        context={},
    )


# ---------------------------------------------------------------------------
# /daily-activity  — JSON API
# ---------------------------------------------------------------------------

@router.get("/daily-activity")
def daily_activity(
    report_date: date | None = Query(None),
    db: Session = Depends(get_db),
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
            "employee":  emp.name,
            "completed": tasks_from_json(up.completed_tasks),
            "pending":   tasks_from_json(up.pending_tasks),
            "is_leave":  up.is_leave,
        }
        for up, emp in updates
    ]

    return {"status": "success", "date": str(report_date), "data": data}


# ---------------------------------------------------------------------------
# /reports  — Trend analysis JSON API
# ---------------------------------------------------------------------------

@router.get("/reports")
def trend_analysis(
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
):
    from datetime import timedelta

    end   = today_ist()
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
        daily_counts[d] = (
            daily_counts.get(d, 0)
            + len(tasks_from_json(u.completed_tasks))
        )

    return {
        "status": "success",
        "period": {"start": str(start), "end": str(end)},
        "task_volume_by_day": [
            {"date": k, "tasks": v}
            for k, v in sorted(daily_counts.items())
        ],
    }


# ---------------------------------------------------------------------------
# /export/excel
# ---------------------------------------------------------------------------

@router.get("/export/excel")
def export_excel(db: Session = Depends(get_db)):

    result = daily_activity(db=db)
    rows = [
        {
            "employee":  item["employee"],
            "completed": ", ".join(
                i.get("task", i) if isinstance(i, dict) else i
                for i in item["completed"]
            ),
            "pending": ", ".join(
                i if isinstance(i, str) else str(i)
                for i in item["pending"]
            ),
        }
        for item in result["data"]
    ]

    path = export_to_excel(rows, f"daily_activity_{today_ist()}.xlsx")

    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=Path(path).name,
    )