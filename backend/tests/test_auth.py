
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.core.request_rate_limit import RequestRateLimitMiddleware
from app.core.security import hash_password, verify_password
from app.main import app as fastapi_app
from app.models.user import User

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
def auth_routes_client():
    Base.metadata.create_all(bind=test_engine)
    fastapi_app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(fastapi_app) as client:
            # Find the live middleware instance and reset its test counters.
            middleware = client.app.middleware_stack

            while middleware is not None:
                if isinstance(middleware, RequestRateLimitMiddleware):
                    with middleware.lock:
                        middleware.requests.clear()
                    break

                middleware = getattr(middleware, "app", None)
            else:
                pytest.fail("RequestRateLimitMiddleware was not found.")

            yield client

    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_register_creates_user_with_hashed_password(auth_routes_client):
    response = auth_routes_client.post(
        "/api/auth/register",
        json={
            "email": "NewUser@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert body["email"] == "newuser@example.com"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body

    with TestSessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == "newuser@example.com")
        )

        assert user is not None
        assert user.password_hash != "Strong-Test-Password-2026!"
        assert verify_password(
            "Strong-Test-Password-2026!",
            user.password_hash,
        )


def test_register_rejects_duplicate_email(auth_routes_client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Strong-Test-Password-2026!",
    }

    first = auth_routes_client.post("/api/auth/register", json=payload)
    second = auth_routes_client.post("/api/auth/register", json=payload)

    assert first.status_code == 201, first.text
    assert second.status_code == 409


def test_register_normalizes_email(auth_routes_client):
    response = auth_routes_client.post(
        "/api/auth/register",
        json={
            "email": "MixedCase@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["email"] == "mixedcase@example.com"


def test_register_rejects_short_password(auth_routes_client):
    response = auth_routes_client.post(
        "/api/auth/register",
        json={
            "email": "short-password@example.com",
            "password": "short",
        },
    )

    assert response.status_code == 422


def test_register_rejects_invalid_email(auth_routes_client):
    response = auth_routes_client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert response.status_code == 422


def test_login_returns_access_token(auth_routes_client):
    registration = auth_routes_client.post(
        "/api/auth/register",
        json={
            "email": "login@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert registration.status_code == 201, registration.text

    response = auth_routes_client.post(
        "/api/auth/login",
        json={
            "email": "LOGIN@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()

    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900

    me_response = auth_routes_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "login@example.com"


def test_login_rejects_wrong_password(auth_routes_client):
    registration = auth_routes_client.post(
        "/api/auth/register",
        json={
            "email": "wrong-password@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert registration.status_code == 201, registration.text

    response = auth_routes_client.post(
        "/api/auth/login",
        json={
            "email": "wrong-password@example.com",
            "password": "Wrong-Password-2026!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_unknown_email(auth_routes_client):
    response = auth_routes_client.post(
        "/api/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_inactive_account(auth_routes_client):
    with TestSessionLocal() as db:
        user = User(
            email="inactive-login@example.com",
            password_hash=hash_password("Strong-Test-Password-2026!"),
            is_active=False,
        )
        db.add(user)
        db.commit()

    response = auth_routes_client.post(
        "/api/auth/login",
        json={
            "email": "inactive-login@example.com",
            "password": "Strong-Test-Password-2026!",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "This account is inactive."


def test_login_rejects_empty_password(auth_routes_client):
    response = auth_routes_client.post(
        "/api/auth/login",
        json={
            "email": "empty-password@example.com",
            "password": "",
        },
    )

    assert response.status_code == 422
