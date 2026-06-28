from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Boolean,
    DateTime
)
from sqlalchemy.sql import func
from app.database.base import Base

class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True)

    name = Column(String)

    date = Column(Date)

    location = Column(String)

    is_optional = Column(Boolean, default=False)

    created_by = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )