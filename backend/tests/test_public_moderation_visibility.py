import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app
from app.models.company import Company
from app.models.email import Email
from app.models.phone_number import PhoneNumber
from app.models.recruiter import Recruiter


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
def public_client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    records = [
        (
            "companies",
            Company,
            {"name": "Pending Visibility Company"},
            "/api/companies",
        ),
        (
            "recruiters",
            Recruiter,
            {"name": "Pending Visibility Recruiter"},
            "/api/recruiters",
        ),
        (
            "emails",
            Email,
            {"email_address": "pending-visibility@example.com"},
            "/api/emails",
        ),
        (
            "phone_numbers",
            PhoneNumber,
            {"phone_number": "+15550123458"},
            "/api/phone-numbers",
        ),
    ]

    record_ids = {}
    try:
        with TestSessionLocal() as db:
            for category, model, data, _ in records:
                pending = model(**data, moderation_status="pending")
                db.add(pending)
                db.flush()
                record_ids[(category, "pending")] = pending.id

                rejected_data = dict(data)
                if category == "companies":
                    rejected_data["name"] = "Rejected Visibility Company"
                elif category == "recruiters":
                    rejected_data["name"] = "Rejected Visibility Recruiter"
                elif category == "emails":
                    rejected_data["email_address"] = "rejected-visibility@example.com"
                else:
                    rejected_data["phone_number"] = "+15550123459"

                rejected = model(
                    **rejected_data,
                    moderation_status="rejected",
                )
                db.add(rejected)
                db.flush()
                record_ids[(category, "rejected")] = rejected.id

            db.commit()

        with TestClient(app) as client:
            yield client, records, record_ids
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.mark.parametrize(
    ("category", "state"),
    [
        (category, state)
        for category in (
            "companies",
            "recruiters",
            "emails",
            "phone_numbers",
        )
        for state in ("pending", "rejected")
    ],
)
def test_unapproved_records_are_hidden_from_public_lists(
    public_client, category, state
):
    client, records, record_ids = public_client
    _, _, _, base_path = next(
        record for record in records if record[0] == category
    )

    response = client.get(base_path)

    assert response.status_code == 200
    body = response.json()
    items = body.get("items", [])
    hidden_id = record_ids[(category, state)]

    assert all(item["id"] != hidden_id for item in items)


@pytest.mark.parametrize(
    ("category", "state"),
    [
        (category, state)
        for category in (
            "companies",
            "recruiters",
            "emails",
            "phone_numbers",
        )
        for state in ("pending", "rejected")
    ],
)
def test_unapproved_record_details_return_404(
    public_client, category, state
):
    client, records, record_ids = public_client
    _, _, _, base_path = next(
        record for record in records if record[0] == category
    )

    record_id = record_ids[(category, state)]
    response = client.get(f"{base_path}/{record_id}")

    assert response.status_code == 404
