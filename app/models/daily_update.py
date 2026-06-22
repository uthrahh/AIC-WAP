from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    Boolean,
    ForeignKey
)
from sqlalchemy.sql import func
from app.database.base import Base

class DailyUpdate(Base):
    __tablename__ = "daily_updates"

    id = Column(Integer, primary_key=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    timestamp = Column(DateTime)

    completed_tasks = Column(Text)

    pending_tasks = Column(Text)

    blockers = Column(Text)

    raw_message = Column(Text)

    is_leave = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())