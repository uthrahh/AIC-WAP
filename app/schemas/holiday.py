from datetime import date, datetime

from pydantic import BaseModel


class HolidayCreate(BaseModel):
    name: str
    date: date
    location: str | None = None
    is_optional: bool = False


class HolidayOut(BaseModel):
    id: int
    name: str
    date: date
    location: str | None
    is_optional: bool
    created_by: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True
