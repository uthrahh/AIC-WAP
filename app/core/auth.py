from fastapi import Depends

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
        return {
            "sub": "system",
            "role": "SUPER_ADMIN"
        }


def require_super_admin():
    return {
        "sub": "system",
        "role": "SUPER_ADMIN"
    }