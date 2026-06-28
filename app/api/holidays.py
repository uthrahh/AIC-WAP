import csv
import io
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.auth import require_super_admin
from app.database.deps import get_db
from app.models.holiday import Holiday
from app.schemas.holiday import HolidayCreate, HolidayOut
from app.services.audit_service import log_event
from fastapi import Request, Form
from fastapi.responses import RedirectResponse
from app.core.templates import templates
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    Request,
    Form
)
from datetime import datetime
from fastapi.responses import (
    RedirectResponse
)
from fastapi.responses import FileResponse
import pandas as pd
from app.core.templates import templates

router = APIRouter(prefix="/api/holidays", tags=["Holidays"])

@router.get("/holidays/add")
def add_holiday_page(request: Request):

    return templates.TemplateResponse(
        "holidays/add.html",
        {
            "request": request
        }
    )

@router.get("/delete/{holiday_id}")
def delete_holiday_page(
    holiday_id: int,
    db: Session = Depends(get_db)
):

    holiday = (
        db.query(Holiday)
        .filter(Holiday.id == holiday_id)
        .first()
    )

    if holiday:

        db.delete(holiday)
        db.commit()

    return RedirectResponse(
        "/settings?holiday_manage=1",
        status_code=303
    )

@router.get("/holidays/manage")
def manage_holidays(
    request: Request,
    db: Session = Depends(get_db)
):

    holidays = (
        db.query(Holiday)
        .order_by(Holiday.date)
        .all()
    )

    return templates.TemplateResponse(
        "holidays/manage.html",
        {
            "request": request,
            "holidays": holidays
        }
    )

@router.post("/add")
def add_holiday(
    date: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):

    holiday = Holiday(
        name=name,
        date=date
    )

    db.add(holiday)
    db.commit()

    return RedirectResponse(
        "/settings?holiday_manage=1",
        status_code=303
    )


@router.get("/")
def list_holidays(
    db: Session = Depends(get_db),
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
            date=datetime.strptime(
                row["date"],
                "%d-%m-%Y"
            ).date(),
            location=row.get("location"),
            is_optional=row.get("is_optional", "false").lower() == "true",
            created_by=manager.get("sub", "manager"),
        )
        db.add(holiday)
        count += 1
    db.commit()
    log_event(db, "HOLIDAY_IMPORT", f"Imported {count} holidays")
    return {"status": "success", "imported": count}

@router.get("/edit/{holiday_id}")
def edit_holiday_page(
    holiday_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    holiday = (
        db.query(Holiday)
        .filter(Holiday.id == holiday_id)
        .first()
    )

    return templates.TemplateResponse(
        request=request,
        name="pages/edit_holiday.html",
        context={
            "holiday": holiday
        }
    )


@router.post("/edit/{holiday_id}")
def edit_holiday(
    holiday_id: int,
    date: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):

    holiday = (
        db.query(Holiday)
        .filter(Holiday.id == holiday_id)
        .first()
    )

    holiday.date = date
    holiday.name = name

    db.commit()

    return RedirectResponse(
        "/settings?holiday_manage=1",
        status_code=303
    )

@router.get("/download")
def download_holidays(
    db: Session = Depends(get_db)
):

    holidays = (
        db.query(Holiday)
        .order_by(Holiday.date)
        .all()
    )

    rows = []

    for h in holidays:

        rows.append(
            {
                "Date": h.date,
                "Day": h.date.strftime("%A"),
                "Holiday": h.name
            }
        )

    df = pd.DataFrame(rows)

    filename = "holidays.xlsx"

    df.to_excel(
        filename,
        index=False
    )

    return FileResponse(
        filename,
        filename=filename
    )