from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database.base import Base

class Manager(Base):
    __tablename__ = "managers"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)

    email = Column(String, unique=True, nullable=False)

    password_hash = Column(String, nullable=False)

    role = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())