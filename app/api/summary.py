from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_manager
from app.database.deps import get_db
from app.models.weekly_report import WeeklyReport
from app.services.reporting_service import format_daily_summary, format_weekly_summary
from app.services.summary_service import run_daily_summary, run_weekly_summary
from app.utils.dates import today_ist, week_bounds

router = APIRouter(prefix="/api/summary", tags=["Summary"])


@router.get("/daily")
def get_daily_summary(
    summary_date: date | None = Query(None),
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    summary_date = summary_date or today_ist()
    text = format_daily_summary(db, summary_date)
    return {"status": "success", "date": str(summary_date), "summary": text}


@router.get("/weekly")
def get_weekly_summary(
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    week_start, week_end = week_bounds()
    text = format_weekly_summary(db, week_start, week_end)
    return {
        "status": "success",
        "week_start": str(week_start),
        "week_end": str(week_end),
        "summary": text,
    }


@router.post("/daily/generate")
def generate_daily_summary(
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    text = run_daily_summary(db)
    return {"status": "success", "summary": text}


@router.post("/weekly/generate")
def generate_weekly_summary(
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    text = run_weekly_summary(db)
    return {"status": "success", "summary": text}


@router.get("/history")
def summary_history(
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    reports = (
        db.query(WeeklyReport)
        .order_by(WeeklyReport.generated_at.desc())
        .limit(20)
        .all()
    )
    return {
        "status": "success",
        "data": [
            {
                "id": r.id,
                "week_start": str(r.week_start),
                "week_end": str(r.week_end),
                "summary": r.summary,
                "generated_at": str(r.generated_at),
            }
            for r in reports
        ],
    }
