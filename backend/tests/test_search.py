
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


def test_search_rejects_unsupported_type(client):
    test_client, _ = client

    response = test_client.post(
        "/api/search",
        json={"search_type": "unknown", "query": "engineer"},
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"search_type": "companies", "query": ""},
        {"search_type": "companies", "query": "   "},
        {"search_type": "", "query": "engineer"},
    ],
)
def test_search_rejects_empty_input(client, payload):
    test_client, _ = client

    response = test_client.post("/api/search", json=payload)

    assert response.status_code == 422


def test_search_returns_empty_results_when_no_matches(client):
    test_client, db = client

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    response = test_client.post(
        "/api/search",
        json={"search_type": "companies", "query": "Example Corp"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["total"] == 0
    assert response.json()["results"] == []


def test_search_accepts_singular_alias(client):
    test_client, db = client

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    response = test_client.post(
        "/api/search",
        json={"search_type": "company", "query": "Example"},
    )

    assert response.status_code == 200
    assert response.json()["search_type"] == "companies"
    db.query.assert_called_once()


def test_recruiter_search_does_not_expose_contact_details(client):
    test_client, db = client

    recruiter = MagicMock()
    recruiter.id = 7
    recruiter.name = "Example Recruiter"
    recruiter.email = "private@example.com"
    recruiter.phone = "+91-9876543210"
    recruiter.company_name = "Example Company"
    recruiter.profile_url = "https://example.com/profile"
    recruiter.description = "Recruitment profile"

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        recruiter
    ]

    response = test_client.post(
        "/api/search",
        json={"search_type": "recruiters", "query": "Example"},
    )

    assert response.status_code == 200

    result = response.json()["results"][0]

    assert "email" not in result["record"]
    assert "phone" not in result["record"]
    assert "private@example.com" not in response.text
    assert "+91-9876543210" not in response.text


def test_email_search_does_not_expose_email_address(client):
    test_client, db = client

    email = MagicMock()
    email.id = 8
    email.email_address = "private@example.com"
    email.description = "Suspicious recruitment email"

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        email
    ]

    response = test_client.post(
        "/api/search",
        json={"search_type": "emails", "query": "private@example.com"},
    )

    assert response.status_code == 200

    result = response.json()["results"][0]

    assert result["title"] == "Email record #8"
    assert "email_address" not in result["record"]
    assert "private@example.com" not in response.text


def test_message_search_does_not_expose_raw_message(client):
    test_client, db = client

    message = MagicMock()
    message.id = 9
    message.message_text = "Send your password to scammer@example.com"

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        message
    ]

    response = test_client.post(
        "/api/search",
        json={"search_type": "messages", "query": "password"},
    )

    assert response.status_code == 200

    result = response.json()["results"][0]

    assert result["title"] == "Messages #9"
    assert result["record"] == {}
    assert message.message_text not in response.text
    assert "scammer@example.com" not in response.text

def test_all_search_does_not_echo_sensitive_query(client):
    test_client, db = client

    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    sensitive_query = "private.person@example.com"

    response = test_client.post(
        "/api/search",
        json={"search_type": "all", "query": sensitive_query},
    )

    assert response.status_code == 200
    assert response.json()["query"] == "All"
    assert sensitive_query not in response.text
