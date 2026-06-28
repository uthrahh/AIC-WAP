from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date
)
from app.database.base import Base

class PendingWork(Base):
    __tablename__ = "pending_work"

    id = Column(Integer, primary_key=True)

    task_name = Column(String, nullable=False)

    description = Column(Text)

    status = Column(String, default="PENDING")

    created_date = Column(Date)

    completed_date = Column(Date)

    created_by = Column(String)

    completed_by = Column(String)

    source_message = Column(Text)