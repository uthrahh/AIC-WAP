from datetime import datetime

from pydantic import BaseModel


class MessageIngest(BaseModel):
    message_id: str | None = None
    group_id: str | None = None
    sender_phone: str
    sender_name: str
    message_body: str
    timestamp: datetime | None = None
