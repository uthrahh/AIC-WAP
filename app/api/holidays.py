import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import get_current_manager, require_super_admin
from app.database.deps import get_db
from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayOut
from app.services.audit_service import log_event

router = APIRouter(prefix="/api/holidays", tags=["Holidays"])


@router.get("/")
def list_holidays(
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    holidays = db.query(Holiday).order_by(Holiday.date).all()
    return {
        "status": "success",
        "data": [HolidayOut.model_validate(h).model_dump() for h in holidays],
    }


@router.post("/")
def create_holiday(
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    manager=Depends(require_super_admin),
):
    holiday = Holiday(
        name=payload.name,
        date=payload.date,
        location=payload.location,
        is_optional=payload.is_optional,
        created_by=manager.get("sub", "manager"),
    )
    db.add(holiday)
    db.commit()
    db.refresh(holiday)
    log_event(db, "HOLIDAY_CREATED", f"Holiday {payload.name} on {payload.date}")
    return {"status": "success", "data": HolidayOut.model_validate(holiday).model_dump()}


@router.put("/{holiday_id}")
def update_holiday(
    holiday_id: int,
    payload: HolidayCreate,
    db: Session = Depends(get_db),
    manager=Depends(require_super_admin),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    holiday.name = payload.name
    holiday.date = payload.date
    holiday.location = payload.location
    holiday.is_optional = payload.is_optional
    db.commit()
    log_event(db, "HOLIDAY_UPDATED", f"Holiday {holiday_id} updated")
    return {"status": "success", "data": HolidayOut.model_validate(holiday).model_dump()}


@router.delete("/{holiday_id}")
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    manager=Depends(require_super_admin),
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(holiday)
    db.commit()
    log_event(db, "HOLIDAY_DELETED", f"Holiday {holiday_id} deleted")
    return {"status": "success"}


@router.post("/import")
async def import_holidays(
    file: UploadFile,
    db: Session = Depends(get_db),
    manager=Depends(require_super_admin),
):
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    count = 0
    for row in reader:
        holiday = Holiday(
            name=row.get("name", ""),
            date=date.fromisoformat(row["date"]),
            location=row.get("location"),
            is_optional=row.get("is_optional", "false").lower() == "true",
            created_by=manager.get("sub", "manager"),
        )
        db.add(holiday)
        count += 1
    db.commit()
    log_event(db, "HOLIDAY_IMPORT", f"Imported {count} holidays")
    return {"status": "success", "imported": count}
