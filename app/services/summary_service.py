from datetime import date

from sqlalchemy.orm import Session

from app.models.daily_update import DailyUpdate
from app.models.employee import Employee
from app.models.weekly_report import WeeklyReport
from app.services.audit_service import log_event
from app.services.extraction_service import run_extraction_for_day
from app.services.reporting_service import (
    format_daily_summary,
    format_weekly_summary,
    generate_contribution_report,
    generate_productivity_report,
)
from app.services.sheets_service import sync_daily_updates_to_sheets
from app.services.whatsapp_service import whatsapp_service
from app.utils.dates import today_ist, week_bounds
from app.utils.text_parser import WAP_MENU, parse_wap_command


def run_daily_summary(db: Session, summary_date: date | None = None) -> str:
    summary_date = summary_date or today_ist()
    text = format_daily_summary(db, summary_date)
    whatsapp_service.send_message(text)
    log_event(db, "DAILY_SUMMARY", f"Daily summary generated for {summary_date}")
    return text


def run_weekly_summary(db: Session, ref_date: date | None = None) -> str:
    ref_date = ref_date or today_ist()
    week_start, week_end = week_bounds(ref_date)
    text = format_weekly_summary(db, week_start, week_end)

    report = WeeklyReport(
        week_start=week_start,
        week_end=week_end,
        summary=text,
    )
    db.add(report)
    db.commit()

    whatsapp_service.send_message(text)
    log_event(db, "WEEKLY_SUMMARY", f"Weekly summary {week_start} to {week_end}")
    return text


def handle_wap_command(db: Session, message: str, sender_name: str) -> str | None:
    command = parse_wap_command(message)
    if command is None:
        return None

    if command == "menu":
        return WAP_MENU

    today = today_ist()
    week_start, week_end = week_bounds(today)

    if command == "daily_summary":
        return run_daily_summary(db, today)
    if command == "weekly_summary":
        return run_weekly_summary(db, today)
    if command == "project_summary":
        daily = format_daily_summary(db, today)
        pending_section = format_weekly_summary(db, week_start, week_end)
        return f"{daily}\n\n---\n\n{pending_section}"
    if command == "productivity_report":
        return generate_productivity_report(db, today)
    if command == "contribution_report":
        return generate_contribution_report(db, week_start, week_end)
    if command == "pending_work":
        return None  # handled separately in ingest
    if command.startswith("custom:"):
        custom = command.split(":", 1)[1]
        return f"Custom report request from {sender_name}:\n{custom}\n\nUse dashboard for detailed custom reports."

    return WAP_MENU


def sync_worklogs_to_sheets(db: Session, work_date: date):
    updates = (
        db.query(DailyUpdate, Employee)
        .join(Employee, DailyUpdate.employee_id == Employee.id)
        .filter(DailyUpdate.timestamp >= work_date)
        .all()
    )
    records = [
        {
            "date": str(u.timestamp.date()) if u.timestamp else "",
            "employee": e.name,
            "phone": e.phone_number,
            "completed": u.completed_tasks,
            "pending": u.pending_tasks,
            "is_leave": u.is_leave,
        }
        for u, e in updates
    ]
    sync_daily_updates_to_sheets(records)
