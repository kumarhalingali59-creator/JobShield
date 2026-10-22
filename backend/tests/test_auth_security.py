
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
from app.models.user import User

from pydantic import ValidationError
from app.core.config import Settings

# Register models and their foreign-key dependencies.
import app.models.company  # noqa: F401
import app.models.email  # noqa: F401
import app.models.job  # noqa: F401
import app.models.message  # noqa: F401
import app.models.phone_number  # noqa: F401
import app.models.recruiter  # noqa: F401
import app.models.website  # noqa: F401
import app.models.report  # noqa: F401
import app.models.evidence  # noqa: F401
import app.models.risk_score  # noqa: F401
import app.models.risk_signal  # noqa: F401


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_client():
    Base.metadata.create_all(bind=test_engine)
    fastapi_app.dependency_overrides[get_db] = override_get_db

    try:
        with TestSessionLocal() as db:
            active_user = User(
                email="auth-active@example.com",
                password_hash=hash_password("Test-Password-2026!"),
                is_active=True,
            )
            inactive_user = User(
                email="auth-inactive@example.com",
                password_hash=hash_password("Test-Password-2026!"),
                is_active=False,
            )

            db.add_all([active_user, inactive_user])
            db.commit()
            db.refresh(active_user)
            db.refresh(inactive_user)

            active_user_id = active_user.id
            inactive_user_id = inactive_user.id

        with TestClient(fastapi_app) as client:
            yield client, active_user_id, inactive_user_id

    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_me_rejects_missing_token(auth_client):
    client, _, _ = auth_client

    response = client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        "invalid.token.value",
        "",
    ],
)
def test_me_rejects_invalid_token(auth_client, token):
    client, _, _ = auth_client

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_accepts_valid_token(auth_client):
    client, active_user_id, _ = auth_client
    token = create_access_token(subject=str(active_user_id))

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["email"] == "auth-active@example.com"


def test_me_rejects_expired_token(auth_client):
    client, _, _ = auth_client
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "1",
            "iat": now - timedelta(minutes=20),
            "exp": now - timedelta(minutes=5),
            "type": "access",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_rejects_nonexistent_user(auth_client):
    client, _, _ = auth_client
    token = create_access_token(subject="999999")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_rejects_inactive_user(auth_client):
    client, _, inactive_user_id = auth_client
    token = create_access_token(subject=str(inactive_user_id))

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_rejects_token_with_wrong_type(auth_client):
    client, active_user_id, _ = auth_client
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": str(active_user_id),
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "refresh",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_rejects_token_with_non_numeric_subject(auth_client):
    client, _, _ = auth_client
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": "not-a-user-id",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_rejects_token_with_invalid_issued_at_claim(auth_client):
    client, active_user_id, _ = auth_client
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": str(active_user_id),
            "iat": "not-a-timestamp",
            "exp": now + timedelta(minutes=5),
            "type": "access",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_jwt_secret_rejects_missing_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, JWT_SECRET="")


def test_jwt_secret_rejects_short_value():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, JWT_SECRET="too-short")


def test_jwt_secret_rejects_surrounding_whitespace():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            JWT_SECRET="  " + "a" * 32 + "  ",
        )


def test_jwt_secret_accepts_valid_length_value():
    configured = Settings(
        _env_file=None,
        JWT_SECRET="a" * 32,
    )

    assert len(configured.JWT_SECRET) >= 32

def test_me_rejects_token_signed_with_wrong_secret(auth_client):
    client, active_user_id, _ = auth_client
    token = jwt.encode(
        {
            "sub": str(active_user_id),
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "type": "access",
        },
        "wrong-test-secret-that-is-at-least-32-chars",
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_me_rejects_token_without_type_claim(auth_client):
    client, active_user_id, _ = auth_client
    now = datetime.now(timezone.utc)

    token = jwt.encode(
        {
            "sub": str(active_user_id),
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
