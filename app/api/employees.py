from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeOut

router = APIRouter(
    prefix="/api/employees",
    tags=["Employees"]
)


@router.get("/", response_model=dict)
def get_employees(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):

    query = db.query(Employee)

    if active_only:
        query = query.filter(
            Employee.is_active.is_(True)
        )

    employees = (
        query
        .order_by(Employee.name)
        .all()
    )

    return {
        "status": "success",
        "count": len(employees),
        "data": [
            EmployeeOut
            .model_validate(e)
            .model_dump()
            for e in employees
        ]
    }


@router.get("/{employee_id}")
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:

        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return {
        "status": "success",
        "data": EmployeeOut
        .model_validate(employee)
        .model_dump()
    }


@router.delete("/{employee_id}")
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):

    employee = (
        db.query(Employee)
        .filter(Employee.id == employee_id)
        .first()
    )

    if not employee:

        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    db.delete(employee)

    db.commit()

    return {
        "status": "success"
    }