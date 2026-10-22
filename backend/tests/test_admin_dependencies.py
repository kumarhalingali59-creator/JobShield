
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth_dependencies import get_current_user
from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.core.admin_dependencies import require_admin
from app.models.user import User


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
def admin_test_client():
    Base.metadata.create_all(bind=test_engine)

    app = FastAPI()
    app.dependency_overrides[get_db] = override_get_db

    @app.get("/admin-check")
    def admin_check(
        current_user: User = Depends(require_admin),
    ):
        return {"admin": current_user.is_admin}

    with TestSessionLocal() as db:
        regular_user = User(
            email="regular-admin-test@example.com",
            password_hash=hash_password("Test-Password-2026!"),
            is_active=True,
            is_admin=False,
        )
        admin_user = User(
            email="admin-test@example.com",
            password_hash=hash_password("Test-Password-2026!"),
            is_active=True,
            is_admin=True,
        )
        db.add_all([regular_user, admin_user])
        db.commit()
        db.refresh(regular_user)
        db.refresh(admin_user)

        regular_user_id = regular_user.id
        admin_user_id = admin_user.id

    try:
        with TestClient(app) as client:
            yield client, regular_user_id, admin_user_id
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_admin_route_rejects_anonymous_user(admin_test_client):
    client, _, _ = admin_test_client

    response = client.get("/admin-check")

    assert response.status_code == 401


def test_admin_route_rejects_regular_user(admin_test_client):
    client, regular_user_id, _ = admin_test_client
    token = create_access_token(subject=str(regular_user_id))

    response = client.get(
        "/admin-check",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator privileges required."


def test_admin_route_accepts_admin_user(admin_test_client):
    client, _, admin_user_id = admin_test_client
    token = create_access_token(subject=str(admin_user_id))

    response = client.get(
        "/admin-check",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"admin": True}
