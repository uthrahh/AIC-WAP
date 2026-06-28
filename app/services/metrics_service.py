from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.models.employee_metrics import EmployeeMetrics
from app.models.pending_work import PendingWork
from app.utils.text_parser import tasks_from_json


def calculate_employee_metrics(
    db: Session,
    employee_id: int,
    metric_date: date,
) -> EmployeeMetrics:
    
    print("NEW METRICS CODE RUNNING")

    updates = (
        db.query(DailyUpdate)
        .filter(
            DailyUpdate.employee_id == employee_id,
            func.date(DailyUpdate.timestamp) <= metric_date,
            DailyUpdate.is_leave.is_(False),
        )
        .all()
    )

    active_days = len(
        {u.timestamp.date() for u in updates if u.timestamp}
    )
    today_update = next(
        (u for u in updates if u.timestamp and u.timestamp.date() == metric_date),
        None,
    )
    completed_count = 0
    pending_count = 0

    if today_update:

        completed_count = len(
            tasks_from_json(
                today_update.completed_tasks
            )
        )

        pending_count = len(
            tasks_from_json(
                today_update.pending_tasks
            )
        )


    total_tasks = completed_count + pending_count

    completion_rate = (
        (completed_count / total_tasks) * 100
        if total_tasks > 0
        else 0
    )

    print(
        f"Employee={employee_id}, "
        f"Completed={completed_count}, "
        f"Pending={pending_count}, "
        f"Rate={completion_rate}"
    )

    tasks_per_day = completed_count
    tasks_per_day = completed_count
    consistency = (active_days / max(active_days, 1)) * 100
    productivity_score = min(
        100.0,
        (completed_count * 15)
        + (completion_rate * 0.3)
        + (consistency * 0.2),
    )

    existing = (
        db.query(EmployeeMetrics)
        .filter(
            EmployeeMetrics.employee_id == employee_id,
            EmployeeMetrics.date == metric_date,
        )
        .first()
    )

    if existing:
        existing.task_completion_rate = round(completion_rate, 2)
        existing.tasks_per_day = float(tasks_per_day)
        existing.active_days = active_days
        existing.productivity_score = round(productivity_score, 2)
        existing.consistency_score = round(consistency, 2)
        db.commit()
        db.refresh(existing)
        return existing

    metrics = EmployeeMetrics(
        employee_id=employee_id,
        date=metric_date,
        task_completion_rate=round(completion_rate, 2),
        tasks_per_day=float(tasks_per_day),
        active_days=active_days,
        productivity_score=round(productivity_score, 2),
        consistency_score=round(consistency, 2),
    )

    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    return metrics


def calculate_all_metrics(db: Session, metric_date: date):
    employees = db.query(Employee).filter(Employee.is_active.is_(True)).all()
    return [
        calculate_employee_metrics(db, emp.id, metric_date)
        for emp in employees
    ]
