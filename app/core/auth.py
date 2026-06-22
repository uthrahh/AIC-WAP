from fastapi import (
    Depends,
    HTTPException
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from app.core.security import decode_token

security = HTTPBearer()


def get_current_manager(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        payload = decode_token(
            credentials.credentials
        )

        return payload

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


def require_super_admin(
    manager=Depends(get_current_manager)
):
    if manager["role"] != "SUPER_ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Access denied"
        )

    return manager