from sqlalchemy import (
    Column,
    Integer,
    Date,
    Text,
    String,
    DateTime
)
from sqlalchemy.sql import func
from app.database.base import Base

class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True)

    week_start = Column(Date)

    week_end = Column(Date)

    summary = Column(Text)

    pdf_path = Column(String)

    excel_path = Column(String)

    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )