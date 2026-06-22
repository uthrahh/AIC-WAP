from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_manager
from app.database.deps import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeOut

router = APIRouter(prefix="/api/employees", tags=["Employees"])


@router.get("/", response_model=dict)
def get_employees(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    query = db.query(Employee)
    if active_only:
        query = query.filter(Employee.is_active.is_(True))
    employees = query.order_by(Employee.name).all()
    return {
        "status": "success",
        "count": len(employees),
        "data": [EmployeeOut.model_validate(e).model_dump() for e in employees],
    }


@router.get("/{employee_id}", response_model=dict)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    manager=Depends(get_current_manager),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"status": "success", "data": EmployeeOut.model_validate(employee).model_dump()}
