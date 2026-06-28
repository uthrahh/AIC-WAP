from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from app.schemas.auth import (
    LoginRequest,
    TokenResponse
)

from app.database.deps import get_db

from app.services.auth_service import (
    login_manager
)

router = APIRouter()

@router.post(
    "/login",
    response_model=TokenResponse
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    token = login_manager(
        request.email,
        request.password,
        db
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

from app.core.auth import get_current_manager
from fastapi import Depends

@router.get("/test")
def test(
    manager=Depends(get_current_manager)
):
    return manager