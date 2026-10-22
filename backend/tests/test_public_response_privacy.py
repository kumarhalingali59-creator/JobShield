
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.dependencies import get_db


@pytest.fixture
def client():
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app) as test_client:
        yield test_client, db

    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("endpoint", "model_fields", "sensitive_fields", "record_id"),
    [
        (
            "/api/recruiters",
            {
                "id": 7,
                "name": "Example Recruiter",
                "email": "private@example.com",
                "phone": "+91-9876543210",
                "company_name": "Example Company",
                "profile_url": "https://example.com/profile",
                "description": "Recruitment profile",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "moderation_status": "approved",
            },
            ("email", "phone"),
            7,
        ),
        (
            "/api/emails",
            {
                "id": 8,
                "email_address": "private@example.com",
                "description": "Suspicious recruitment email",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
                "moderation_status": "approved",
            },
            ("email_address",),
            8,
        ),
        (
            "/api/messages",
            {
                "id": 9,
                "message_text": "Send your password to scammer@example.com",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            },
            ("message_text",),
            9,
        ),
    ],
)
@pytest.mark.parametrize("detail", [False, True])
def test_public_get_endpoints_hide_sensitive_fields(
    client,
    endpoint,
    model_fields,
    sensitive_fields,
    record_id,
    detail,
):
    test_client, db = client

    record = MagicMock()

    for field, value in model_fields.items():
        setattr(record, field, value)

    if detail:
        if endpoint in ("/api/recruiters", "/api/emails"):
            # Moderated detail endpoints use filtered database queries.
            db.query.return_value.filter.return_value.first.return_value = (
                record
            )
        else:
            db.get.return_value = record

        response = test_client.get(f"{endpoint}/{record_id}")

        assert response.status_code == 200, response.text
        returned_records = [response.json()]

    else:
        query = db.query.return_value

        if endpoint == "/api/recruiters":
            # Recruiter listing applies moderation and optional search filters.
            query.filter.return_value.count.return_value = 1
            (
                query.filter.return_value
                .order_by.return_value
                .offset.return_value
                .limit.return_value
                .all.return_value
            ) = [record]

        elif endpoint == "/api/emails":
            # Email listing applies the approved-status filter and pagination.
            query.filter.return_value.count.return_value = 1
            (
                query.filter.return_value
                .order_by.return_value
                .offset.return_value
                .limit.return_value
                .all.return_value
            ) = [record]

        else:
            query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
                record
            ]
            query.count.return_value = 1

        response = test_client.get(endpoint)

        assert response.status_code == 200, response.text
        returned_records = response.json()["items"]

    response_data = response.text

    for returned_record in returned_records:
        for field in sensitive_fields:
            assert field not in returned_record

    for field in sensitive_fields:
        value = model_fields[field]
        assert value not in response_data


@pytest.mark.parametrize(
    ("endpoint", "payload", "model_fields", "sensitive_values"),
    [
        (
            "/api/recruiters",
            {
                "name": "Example Recruiter",
                "email": "private@example.com",
                "phone": "+91-9876543210",
                "company_name": "Example Company",
                "profile_url": "https://example.com/profile",
                "description": "Recruitment profile",
            },
            {
                "id": 7,
                "name": "Example Recruiter",
                "email": "private@example.com",
                "phone": "+91-9876543210",
                "company_name": "Example Company",
                "profile_url": "https://example.com/profile",
                "description": "Recruitment profile",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            },
            ("private@example.com", "+91-9876543210"),
        ),
        (
            "/api/emails",
            {
                "email_address": "private@example.com",
                "description": "Suspicious recruitment email",
            },
            {
                "id": 8,
                "email_address": "private@example.com",
                "description": "Suspicious recruitment email",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            },
            ("private@example.com",),
        ),
        (
            "/api/messages",
            {
                "message_text": "Send your password to scammer@example.com",
            },
            {
                "id": 9,
                "message_text": "Send your password to scammer@example.com",
                "created_at": "2026-01-01T00:00:00",
                "updated_at": "2026-01-01T00:00:00",
            },
            ("Send your password to scammer@example.com",),
        ),
    ],
)
def test_public_create_endpoints_hide_sensitive_fields(
    client,
    endpoint,
    payload,
    model_fields,
    sensitive_values,
):
    test_client, db = client

    # Simulate a new record that does not already exist.
    db.query.return_value.filter.return_value.first.return_value = None

    db.add.return_value = None
    db.commit.return_value = None

    # Populate the actual SQLAlchemy model instance on refresh.
    def populate_created_record(instance):
        instance.id = model_fields["id"]
        instance.created_at = datetime.fromisoformat(
            model_fields["created_at"]
        )
        instance.updated_at = datetime.fromisoformat(
            model_fields["updated_at"]
        )

    db.refresh.side_effect = populate_created_record

    response = test_client.post(endpoint, json=payload)

    assert response.status_code == 201, response.text

    response_data = response.json()

    # Sensitive values must not be exposed in the response.
    for sensitive_value in sensitive_values:
        assert sensitive_value not in response.text

    for field in (
        "email",
        "phone",
        "email_address",
        "message_text",
    ):
        assert field not in response_data
