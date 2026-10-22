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


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(
    bind=engine,
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
def search_client():
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestSessionLocal() as db:
            records = [
                (
                    Company,
                    "companies",
                    "Visibility Search Company",
                    {"name": "Visibility Search Company"},
                ),
                (
                    Recruiter,
                    "recruiters",
                    "Visibility Search Recruiter",
                    {"name": "Visibility Search Recruiter"},
                ),
                (
                    Email,
                    "emails",
                    "visibility-search@example.com",
                    {"email_address": "visibility-search@example.com"},
                ),
                (
                    PhoneNumber,
                    "phone_numbers",
                    "+15550123458",
                    {"phone_number": "+15550123458"},
                ),
            ]

            for model, category, query, fields in records:
                for state in ("pending", "rejected", "approved"):
                    data = dict(fields)

                    if category == "emails":
                        data["email_address"] = f"{state}-visibility@example.com"
                    elif category == "phone_numbers":
                        data["phone_number"] = {
                            "pending": "+15550123451",
                            "rejected": "+15550123452",
                            "approved": "+15550123453",
                        }[state]

                    data["description"] = f"{query} moderation visibility test"
                    db.add(model(**data, moderation_status=state))

            db.commit()

        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.mark.parametrize(
    ("search_type", "query"),
    [
        ("companies", "Visibility Search Company"),
        ("recruiters", "Visibility Search Recruiter"),
        ("emails", "visibility-search"),
        ("phone_numbers", "155501234"),
    ],
)
def test_search_returns_only_approved_moderated_records(
    search_client, search_type, query
):
    response = search_client.post(
        "/api/search",
        json={"search_type": search_type, "query": query},
    )

    assert response.status_code == 200, response.text

    results = response.json()["results"]
    assert results
    assert all(result["type"] == search_type for result in results)
    assert len(results) == 1
