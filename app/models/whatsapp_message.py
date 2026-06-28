from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database.base import Base


class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(Integer, primary_key=True)
    message_id = Column(String, unique=True, nullable=True)
    group_id = Column(String)
    sender_phone = Column(String)
    sender_name = Column(String)
    message_body = Column(Text)
    timestamp = Column(DateTime(timezone=True))
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
