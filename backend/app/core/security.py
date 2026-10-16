
import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password securely before storing it."""
    if not password:
        raise ValueError("Password cannot be empty.")

    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    return password_hash.verify(password, hashed_password)


def create_access_token(
    subject: str,
    expires_minutes: int = 15,
) -> str:
    """Create a short-lived JWT access token."""
    if not subject.strip():
        raise ValueError("Token subject cannot be empty.")

    if expires_minutes <= 0:
        raise ValueError("Token expiry must be positive.")

    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict:
    """Validate and decode an access token."""
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=["HS256"],
        options={"require": ["sub", "iat", "exp"]},
    )

    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Invalid token type.")

    return payload
