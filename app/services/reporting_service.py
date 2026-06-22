from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.models.employee_metrics import EmployeeMetrics
from app.services.pending_work_service import get_active_pending_work
from app.utils.text_parser import tasks_from_json


def _aggregate_completed_by_task(db: Session, start: date, end: date) -> list[dict]:
    updates = (
        db.query(DailyUpdate, Employee)
        .join(Employee, DailyUpdate.employee_id == Employee.id)
        .filter(
            func.date(DailyUpdate.timestamp) >= start,
            func.date(DailyUpdate.timestamp) <= end,
            DailyUpdate.is_leave.is_(False),
        )
        .all()
    )

    task_map: dict[str, set[str]] = {}
    for update, employee in updates:
        for task in tasks_from_json(update.completed_tasks):
            task_map.setdefault(task, set()).add(employee.name)

    return [
        {"task": task, "employees": sorted(employees)}
        for task, employees in sorted(task_map.items())
    ]


def format_daily_summary(db: Session, summary_date: date) -> str:
    completed = _aggregate_completed_by_task(db, summary_date, summary_date)
    pending = get_active_pending_work(db)

    lines = [summary_date.strftime("%d-%m-%Y"), ""]
    for idx, item in enumerate(completed, 1):
        lines.append(f"{idx}. {item['task']}")
        for emp in item["employees"]:
            lines.append(f"   - {emp}")
        lines.append("")

    lines.append("Pending Work:")
    for idx, item in enumerate(pending, 1):
        lines.append(f"{idx}. {item.task_name}")

    return "\n".join(lines).strip()


def format_weekly_summary(db: Session, week_start: date, week_end: date) -> str:
    completed = _aggregate_completed_by_task(db, week_start, week_end)
    pending = get_active_pending_work(db)

    lines = [
        f"Week: {week_start.strftime('%d-%m-%Y')} to {week_end.strftime('%d-%m-%Y')}",
        "",
    ]
    for idx, item in enumerate(completed, 1):
        lines.append(f"{idx}. {item['task']}")
        for emp in item["employees"]:
            lines.append(f"   - {emp}")
        lines.append("")

    lines.append("Pending Work:")
    for idx, item in enumerate(pending, 1):
        lines.append(f"{idx}. {item.task_name}")

    return "\n".join(lines).strip()


def generate_blocker_report(db: Session, start: date, end: date) -> str:
    updates = (
        db.query(DailyUpdate, Employee)
        .join(Employee, DailyUpdate.employee_id == Employee.id)
        .filter(
            func.date(DailyUpdate.timestamp) >= start,
            func.date(DailyUpdate.timestamp) <= end,
        )
        .all()
    )
    lines = ["Blocker Report", ""]
    for update, employee in updates:
        blockers = tasks_from_json(update.blockers)
        if blockers:
            lines.append(f"{employee.name} ({update.timestamp.date()}):")
            for b in blockers:
                lines.append(f"  - {b}")
            lines.append("")
    return "\n".join(lines).strip() or "No blockers reported."


def generate_productivity_report(db: Session, report_date: date) -> str:
    metrics = (
        db.query(EmployeeMetrics, Employee)
        .join(Employee, EmployeeMetrics.employee_id == Employee.id)
        .filter(EmployeeMetrics.date == report_date)
        .order_by(EmployeeMetrics.productivity_score.desc())
        .all()
    )
    lines = [f"Productivity Report - {report_date.strftime('%d-%m-%Y')}", ""]
    for m, emp in metrics:
        lines.append(
            f"{emp.name}: score={m.productivity_score}, "
            f"tasks={m.tasks_per_day}, blockers={m.blocker_count}"
        )
    return "\n".join(lines).strip()


def generate_contribution_report(db: Session, start: date, end: date) -> str:
    completed = _aggregate_completed_by_task(db, start, end)
    emp_counts: dict[str, int] = {}
    for item in completed:
        for emp in item["employees"]:
            emp_counts[emp] = emp_counts.get(emp, 0) + 1

    lines = [f"Employee Contributions ({start} to {end})", ""]
    for emp, count in sorted(emp_counts.items(), key=lambda x: -x[1]):
        lines.append(f"{emp}: {count} task(s)")
    return "\n".join(lines).strip() or "No contributions recorded."
