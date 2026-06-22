from sqlalchemy.orm import Session

from app.models.manager import Manager

from app.core.security import (
    verify_password,
    create_access_token
)

def login_manager(
    email: str,
    password: str,
    db: Session
):

    manager = (
        db.query(Manager)
        .filter(
            Manager.email == email
        )
        .first()
    )

    if not manager:
        return None

    if not verify_password(
        password,
        manager.password_hash
    ):
        return None

    token = create_access_token(
        {
            "sub": str(manager.id),
            "role": manager.role
        }
    )

    return token