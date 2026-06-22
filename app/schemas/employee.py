from datetime import date, datetime

from pydantic import BaseModel


class EmployeeOut(BaseModel):
    id: int
    name: str
    phone_number: str
    whatsapp_name: str | None
    designation: str | None
    is_active: bool

    class Config:
        from_attributes = True


class DailyUpdateOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str | None = None
    timestamp: datetime | None
    completed_tasks: list[str]
    pending_tasks: list[str]
    blockers: list[str]
    is_leave: bool

    class Config:
        from_attributes = True
