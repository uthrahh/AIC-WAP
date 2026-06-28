from sqlalchemy import (
    Column,
    Integer,
    Float,
    Date,
    ForeignKey
)
from app.database.base import Base

class EmployeeMetrics(Base):
    __tablename__ = "employee_metrics"

    id = Column(Integer, primary_key=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    date = Column(Date)

    task_completion_rate = Column(Float)

    tasks_per_day = Column(Float)

    active_days = Column(Integer)

    productivity_score = Column(Float)

    consistency_score = Column(Float)