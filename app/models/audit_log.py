from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime
)
from sqlalchemy.sql import func
from app.database.base import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    event_type = Column(String)

    user_id = Column(Integer)

    description = Column(Text)

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )