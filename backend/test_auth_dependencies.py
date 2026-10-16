
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.auth_dependencies import get_current_user
from app.core.config import settings


def check_rejected(credentials, label):
    try:
        get_current_user(
            credentials=credentials,
            db=Session(),  # Not reached for rejected tokens
        )
    except HTTPException as exc:
        assert exc.status_code == 401, (
            f"{label}: expected 401, got {exc.status_code}"
        )
        print(f"PASS: {label} rejected with 401")
    else:
        raise AssertionError(f"FAIL: {label} was accepted")


check_rejected(None, "missing token")

check_rejected(
    HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.token.value",
    ),
    "invalid token",
)

now = datetime.now(timezone.utc)
expired_token = jwt.encode(
    {
        "sub": "1",
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(minutes=5),
        "type": "access",
    },
    settings.JWT_SECRET,
    algorithm="HS256",
)

check_rejected(
    HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=expired_token,
    ),
    "expired token",
)
