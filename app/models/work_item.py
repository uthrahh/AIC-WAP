from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func

from app.database.base import Base


class WorkItem(Base):

    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True)

    task_name = Column(String, nullable=False)

    description = Column(String)

    target_date = Column(Date)

    status = Column(
        String,
        default="PENDING"
    )

    completed_by = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )