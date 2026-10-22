import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth_dependencies import get_current_user
from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.company import Company
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
def moderation_client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestSessionLocal() as db:
        regular_user = User(
            email="moderation-user@example.com",
            password_hash=hash_password("Test-Password-2026!"),
            is_active=True,
            is_admin=False,
        )
        admin_user = User(
            email="moderation-admin@example.com",
            password_hash=hash_password("Test-Password-2026!"),
            is_active=True,
            is_admin=True,
        )
        db.add_all([regular_user, admin_user])
        db.commit()
        db.refresh(regular_user)
        db.refresh(admin_user)

        regular_id = regular_user.id
        admin_id = admin_user.id

        company = Company(
            name="Pending Test Company",
            moderation_status="pending",
        )
        db.add(company)
        db.commit()
        db.refresh(company)
        company_id = company.id

    try:
        with TestClient(app) as client:
            yield client, regular_id, admin_id, company_id
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def auth_headers(user_id):
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_moderation_rejects_anonymous_user(moderation_client):
    client, _, _, _ = moderation_client

    response = client.get(
        "/api/admin/moderation/pending/companies"
    )

    assert response.status_code == 401


def test_moderation_rejects_regular_user(moderation_client):
    client, regular_id, _, _ = moderation_client

    response = client.get(
        "/api/admin/moderation/pending/companies",
        headers=auth_headers(regular_id),
    )

    assert response.status_code == 403


def test_admin_can_list_pending_companies(moderation_client):
    client, _, admin_id, company_id = moderation_client

    response = client.get(
        "/api/admin/moderation/pending/companies",
        headers=auth_headers(admin_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == company_id
    assert body["items"][0]["moderation_status"] == "pending"


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_admin_can_moderate_pending_company(
    moderation_client, decision
):
    client, _, admin_id, company_id = moderation_client

    response = client.patch(
        f"/api/admin/moderation/companies/{company_id}",
        headers=auth_headers(admin_id),
        json={"status": decision},
    )

    assert response.status_code == 200
    assert response.json()["moderation_status"] == decision

    with TestSessionLocal() as db:
        company = db.query(Company).filter(
            Company.id == company_id
        ).first()
        assert company.moderation_status == decision


def test_admin_cannot_moderate_company_twice(moderation_client):
    client, _, admin_id, company_id = moderation_client
    headers = auth_headers(admin_id)
    url = f"/api/admin/moderation/companies/{company_id}"

    first = client.patch(url, headers=headers, json={"status": "approved"})
    second = client.patch(url, headers=headers, json={"status": "rejected"})

    assert first.status_code == 200
    assert second.status_code == 409

from app.models.email import Email
from app.models.phone_number import PhoneNumber
from app.models.recruiter import Recruiter


@pytest.mark.parametrize(
    ("category", "model", "record_data"),
    [
        (
            "companies",
            Company,
            {"name": "Cross Category Company"},
        ),
        (
            "recruiters",
            Recruiter,
            {"name": "Cross Category Recruiter"},
        ),
        (
            "emails",
            Email,
            {"email_address": "cross-category@example.com"},
        ),
        (
            "phone_numbers",
            PhoneNumber,
            {"phone_number": "+15550123456"},
        ),
    ],
)
@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_admin_can_moderate_all_categories(
    moderation_client, category, model, record_data, decision
):
    client, _, admin_id, _ = moderation_client

    with TestSessionLocal() as db:
        record = model(**record_data, moderation_status="pending")
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id

    response = client.patch(
        f"/api/admin/moderation/{category}/{record_id}",
        headers=auth_headers(admin_id),
        json={"status": decision},
    )

    assert response.status_code == 200
    assert response.json()["moderation_status"] == decision
    assert response.json()["category"] == category

    with TestSessionLocal() as db:
        saved = db.query(model).filter(model.id == record_id).first()
        assert saved.moderation_status == decision


@pytest.mark.parametrize(
    ("category", "model", "record_data"),
    [
        (
            "companies",
            Company,
            {"name": "Pending Company Listing"},
        ),
        (
            "recruiters",
            Recruiter,
            {"name": "Pending Recruiter Listing"},
        ),
        (
            "emails",
            Email,
            {"email_address": "pending-listing@example.com"},
        ),
        (
            "phone_numbers",
            PhoneNumber,
            {"phone_number": "+15550123457"},
        ),
    ],
)
def test_admin_can_list_pending_all_categories(
    moderation_client, category, model, record_data
):
    client, _, admin_id, _ = moderation_client

    with TestSessionLocal() as db:
        record = model(**record_data, moderation_status="pending")
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id

    response = client.get(
        f"/api/admin/moderation/pending/{category}",
        headers=auth_headers(admin_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == category
    assert body["total"] >= 1
    assert any(item["id"] == record_id for item in body["items"])


def test_invalid_moderation_decision_is_rejected(moderation_client):
    client, _, admin_id, company_id = moderation_client

    response = client.patch(
        f"/api/admin/moderation/companies/{company_id}",
        headers=auth_headers(admin_id),
        json={"status": "pending"},
    )

    assert response.status_code == 422


def test_moderation_returns_404_for_unknown_record(moderation_client):
    client, _, admin_id, _ = moderation_client

    response = client.patch(
        "/api/admin/moderation/companies/999999",
        headers=auth_headers(admin_id),
        json={"status": "approved"},
    )

    assert response.status_code == 404


def test_moderation_rejects_unknown_category(moderation_client):
    client, _, admin_id, _ = moderation_client

    response = client.get(
        "/api/admin/moderation/pending/unknown",
        headers=auth_headers(admin_id),
    )

    assert response.status_code == 422
