from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.whatsapp_message import WhatsAppMessage
from app.utils.dates import office_window


def store_message(
    db: Session,
    *,
    message_id: str | None,
    group_id: str | None,
    sender_phone: str,
    sender_name: str,
    message_body: str,
    timestamp: datetime,
) -> WhatsAppMessage | None:
    if message_id:
        existing = (
            db.query(WhatsAppMessage)
            .filter(WhatsAppMessage.message_id == message_id)
            .first()
        )
        if existing:
            return None

    msg = WhatsAppMessage(
        message_id=message_id,
        group_id=group_id,
        sender_phone=sender_phone,
        sender_name=sender_name,
        message_body=message_body,
        timestamp=timestamp,
        processed=False,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_unprocessed_messages_for_day(db: Session, work_date: date) -> list[WhatsAppMessage]:
    start, end = office_window(work_date)
    return (
        db.query(WhatsAppMessage)
        .filter(
            WhatsAppMessage.timestamp >= start,
            WhatsAppMessage.timestamp <= end,
            WhatsAppMessage.processed.is_(False),
        )
        .order_by(WhatsAppMessage.timestamp.asc())
        .all()
    )


def mark_processed(db: Session, message_ids: list[int]):
    if not message_ids:
        return
    db.query(WhatsAppMessage).filter(
        WhatsAppMessage.id.in_(message_ids)
    ).update({WhatsAppMessage.processed: True}, synchronize_session=False)
    db.commit()
