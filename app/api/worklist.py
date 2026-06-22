from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.models.work_item import WorkItem

router = APIRouter(
    prefix="/api/worklist",
    tags=["Work List"]
)


@router.get("/")
def get_worklist(
    db: Session = Depends(get_db)
):

    items = (
        db.query(WorkItem)
        .order_by(WorkItem.target_date)
        .all()
    )

    return {
        "status": "success",
        "data": [
            {
                "id": item.id,
                "task_name": item.task_name,
                "description": item.description,
                "target_date": str(item.target_date),
                "status": item.status,
                "completed_by": item.completed_by
            }
            for item in items
        ]
    }


@router.post("/")
def add_work_item(
    payload: dict,
    db: Session = Depends(get_db)
):

    item = WorkItem(
        task_name=payload["task_name"],
        description=payload.get(
            "description"
        ),
        target_date=payload.get(
            "target_date"
        )
    )

    db.add(item)

    db.commit()

    db.refresh(item)

    return {
        "status": "success"
    }