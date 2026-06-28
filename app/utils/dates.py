from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.holiday import Holiday


def get_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().timezone)


def now_ist() -> datetime:
    return datetime.now(get_tz())


def today_ist() -> date:
    return now_ist().date()


def is_weekend(check_date: date | None = None) -> bool:
    d = check_date or today_ist()
    return d.weekday() >= 5


def is_holiday(db: Session, check_date: date | None = None) -> bool:
    d = check_date or today_ist()
    return (
        db.query(Holiday)
        .filter(Holiday.date == d, Holiday.is_optional.is_(False))
        .first()
        is not None
    )


def is_working_day(db: Session, check_date: date | None = None) -> bool:
    d = check_date or today_ist()
    if is_weekend(d):
        return False
    return not is_holiday(db, d)


def week_bounds(check_date: date | None = None) -> tuple[date, date]:
    d = check_date or today_ist()
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=4)
    return start, end


def parse_date_flexible(value: str) -> date | None:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def office_window(check_date: date | None = None) -> tuple[datetime, datetime]:
    settings = get_settings()
    d = check_date or today_ist()
    tz = get_tz()
    start = datetime(d.year, d.month, d.day, settings.office_start_hour, 0, tzinfo=tz)
    end = datetime(d.year, d.month, d.day, settings.office_end_hour, 0, tzinfo=tz)
    return start, end
