from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.schemas.worklog import MessageIngest
from app.services.audit_service import log_event
from app.services.extraction_service import process_single_message
from app.services.message_store_service import store_message
from app.services.pending_work_service import register_from_whatsapp_message
from app.services.summary_service import handle_wap_command
from app.services.whatsapp_service import whatsapp_service
from app.utils.dates import now_ist
from app.utils.text_parser import parse_pending_work_command, parse_wap_command

router = APIRouter(prefix="/api/worklogs", tags=["Worklogs"])


@router.post("/ingest")
def ingest_worklog(payload: MessageIngest, db: Session = Depends(get_db)):
    timestamp = payload.timestamp or now_ist()
    message_body = payload.message_body.strip()

    stored = store_message(
        db,
        message_id=payload.message_id,
        group_id=payload.group_id,
        sender_phone=payload.sender_phone,
        sender_name=payload.sender_name,
        message_body=message_body,
        timestamp=timestamp,
    )

    response = {"status": "success", "stored": stored is not None}

    command = parse_wap_command(message_body)
    if command == "pending_work":
        date_str, tasks = parse_pending_work_command(message_body)
        if tasks:
            items = register_from_whatsapp_message(
                db,
                date_str or timestamp.strftime("%d-%m-%Y"),
                tasks,
                payload.sender_name,
                message_body,
            )
            reply = f"Registered {len(items)} pending work item(s)."
            whatsapp_service.send_message(reply)
            log_event(db, "PENDING_WORK_ADDED", reply)
            response["pending_work_added"] = len(items)
        return response

    if command and command != "pending_work":
        reply = handle_wap_command(db, message_body, payload.sender_name)
        if reply:
            whatsapp_service.send_message(reply)
            response["wap_reply"] = True
        return response

    update = process_single_message(
        db,
        sender_phone=payload.sender_phone,
        sender_name=payload.sender_name,
        message_body=message_body,
        timestamp=timestamp,
    )
    response["worklog_processed"] = update is not None
    return response


@router.post("/process-day")
def process_day(db: Session = Depends(get_db)):
    from app.services.extraction_service import run_extraction_for_day

    result = run_extraction_for_day(db)
    return {"status": "success", **result}
