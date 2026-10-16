
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token


def assert_rejected(token: str, label: str) -> None:
    try:
        decode_access_token(token)
    except jwt.InvalidTokenError:
        print(f"PASS: {label} rejected")
        return

    raise AssertionError(f"FAIL: {label} was accepted")


now = datetime.now(timezone.utc)

# 1. Expired token
expired_payload = {
    "sub": "test-user",
    "iat": now - timedelta(minutes=20),
    "exp": now - timedelta(minutes=5),
    "type": "access",
}
expired_token = jwt.encode(
    expired_payload, settings.JWT_SECRET, algorithm="HS256"
)
assert_rejected(expired_token, "expired token")

# 2. Wrong token type
refresh_payload = {
    "sub": "test-user",
    "iat": now,
    "exp": now + timedelta(minutes=5),
    "type": "refresh",
}
refresh_token = jwt.encode(
    refresh_payload, settings.JWT_SECRET, algorithm="HS256"
)
assert_rejected(refresh_token, "wrong token type")

# 3. Tampered token
valid_token = create_access_token("test-user")
parts = valid_token.split(".")
parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
tampered_token = ".".join(parts)
assert_rejected(tampered_token, "tampered token")
