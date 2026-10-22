
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
from app.models.report import Report
from app.models.report_moderation_log import ReportModerationLog
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
def report_moderation_client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    with TestSessionLocal() as db:
        regular_user = User(
            email="report-review-user@example.com",
            password_hash=hash_password("Test-Password-2026!"),
            is_active=True,
            is_admin=False,
        )
        admin_user = User(
            email="report-review-admin@example.com",
            password_hash=hash_password("Test-Password-2026!"),
            is_active=True,
            is_admin=True,
        )
        db.add_all([regular_user, admin_user])
        db.commit()
        db.refresh(regular_user)
        db.refresh(admin_user)

        report = Report(
            user_id=regular_user.id,
            report_type="company",
            target_value="Example Recruitment Ltd",
            description="The recruiter requested an upfront payment.",
            status="pending",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        user_id = regular_user.id
        admin_id = admin_user.id
        report_id = report.id

    try:
        with TestClient(app) as client:
            yield client, user_id, admin_id, report_id
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def auth_headers(user_id):
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def test_report_queue_requires_admin(report_moderation_client):
    client, user_id, _, _ = report_moderation_client

    anonymous = client.get(
        "/api/admin/moderation/reports/pending"
    )
    regular_user = client.get(
        "/api/admin/moderation/reports/pending",
        headers=auth_headers(user_id),
    )

    assert anonymous.status_code == 401
    assert regular_user.status_code == 403


def test_admin_can_list_pending_reports(report_moderation_client):
    client, _, admin_id, report_id = report_moderation_client

    response = client.get(
        "/api/admin/moderation/reports/pending",
        headers=auth_headers(admin_id),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == report_id
    assert body["items"][0]["status"] == "pending"
    assert "evidence" in body["items"][0]
    assert "storage_path" not in body["items"][0]


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_admin_can_decide_report(
    report_moderation_client, decision
):
    client, _, admin_id, report_id = report_moderation_client

    response = client.patch(
        f"/api/admin/moderation/reports/{report_id}/decision",
        headers=auth_headers(admin_id),
        json={
            "status": decision,
            "notes": "Reviewed the submitted information.",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == decision

    with TestSessionLocal() as db:
        report = db.get(Report, report_id)
        assert report.status == decision

        logs = (
            db.query(ReportModerationLog)
            .filter(ReportModerationLog.report_id == report_id)
            .all()
        )
        assert len(logs) == 1
        assert logs[0].actor_user_id == admin_id
        assert logs[0].actor_type == "admin"
        assert logs[0].action == decision


def test_request_evidence_requires_notes(report_moderation_client):
    client, _, admin_id, report_id = report_moderation_client

    response = client.patch(
        f"/api/admin/moderation/reports/{report_id}/decision",
        headers=auth_headers(admin_id),
        json={"status": "needs_evidence"},
    )

    assert response.status_code == 422


def test_admin_can_request_evidence_and_view_history(
    report_moderation_client,
):
    client, _, admin_id, report_id = report_moderation_client
    headers = auth_headers(admin_id)

    decision = client.patch(
        f"/api/admin/moderation/reports/{report_id}/decision",
        headers=headers,
        json={
            "status": "needs_evidence",
            "notes": "Please provide the original job offer.",
        },
    )

    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "needs_evidence"

    history = client.get(
        f"/api/admin/moderation/reports/{report_id}/history",
        headers=headers,
    )

    assert history.status_code == 200, history.text
    body = history.json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == "needs_evidence"
    assert (
        body["items"][0]["notes"]
        == "Please provide the original job offer."
    )
    assert body["items"][0]["actor_user_id"] == admin_id


def test_regular_user_cannot_view_moderation_history(
    report_moderation_client,
):
    client, user_id, _, report_id = report_moderation_client

    response = client.get(
        f"/api/admin/moderation/reports/{report_id}/history",
        headers=auth_headers(user_id),
    )

    assert response.status_code == 403


def test_admin_cannot_moderate_report_twice(
    report_moderation_client,
):
    client, _, admin_id, report_id = report_moderation_client
    url = f"/api/admin/moderation/reports/{report_id}/decision"
    headers = auth_headers(admin_id)

    first = client.patch(
        url,
        headers=headers,
        json={
            "status": "approved",
            "notes": "Evidence reviewed.",
        },
    )
    second = client.patch(
        url,
        headers=headers,
        json={
            "status": "rejected",
            "notes": "Second decision attempt.",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_moderation_returns_404_for_unknown_report(
    report_moderation_client,
):
    client, _, admin_id, _ = report_moderation_client

    response = client.patch(
        "/api/admin/moderation/reports/999999/decision",
        headers=auth_headers(admin_id),
        json={
            "status": "approved",
            "notes": "Review.",
        },
    )

    assert response.status_code == 404


def test_public_report_detail_hides_unapproved_report(
    report_moderation_client,
):
    client, _, _, report_id = report_moderation_client

    response = client.get(f"/api/reports/{report_id}")

    assert response.status_code == 404

def test_invalid_moderation_decision_does_not_change_report(
    report_moderation_client,
):
    client, _, admin_id, report_id = report_moderation_client

    response = client.patch(
        f"/api/admin/moderation/reports/{report_id}/decision",
        headers=auth_headers(admin_id),
        json={
            "status": "invalid_status",
            "notes": "This decision should not be accepted.",
        },
    )

    assert response.status_code == 422

    with TestSessionLocal() as db:
        report = db.get(Report, report_id)
        assert report is not None
        assert report.status == "pending"

        logs = (
            db.query(ReportModerationLog)
            .filter(ReportModerationLog.report_id == report_id)
            .all()
        )
        assert len(logs) == 0

def test_complete_evidence_resubmission_lifecycle(
    report_moderation_client, monkeypatch
):
    from app.models.evidence import Evidence

    client, user_id, admin_id, report_id = report_moderation_client

    admin_headers = auth_headers(admin_id)
    user_headers = auth_headers(user_id)

    # 1. Admin requests additional evidence.
    decision = client.patch(
        f"/api/admin/moderation/reports/{report_id}/decision",
        headers=admin_headers,
        json={
            "status": "needs_evidence",
            "notes": "Please provide the original job offer.",
        },
    )

    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "needs_evidence"

    # 2. Mock storage so the test does not upload to Supabase.
    monkeypatch.setattr(
        "app.api.evidence.upload_evidence_file",
        lambda report_id, file: {
            "file_name": "job_offer.txt",
            "storage_path": f"{report_id}/test-job-offer.txt",
            "content_type": "text/plain",
            "file_size": 20,
        },
    )

    # 3. The report owner submits additional evidence.
    upload = client.post(
        "/api/evidence/upload",
        headers=user_headers,
        data={
            "report_id": str(report_id),
            "description": "Additional job offer evidence",
        },
        files={
            "file": (
                "job_offer.txt",
                b"Mock job offer evidence",
                "text/plain",
            )
        },
    )

    assert upload.status_code == 201, upload.text
    assert upload.json()["file_name"] == "job_offer.txt"

    # 4. Verify the report returns to pending and evidence is saved.
    with TestSessionLocal() as db:
        report = db.get(Report, report_id)
        assert report is not None
        assert report.status == "pending"

        evidence_items = (
            db.query(Evidence)
            .filter(Evidence.report_id == report_id)
            .all()
        )
        assert len(evidence_items) == 1
        assert evidence_items[0].file_name == "job_offer.txt"

        logs = (
            db.query(ReportModerationLog)
            .filter(ReportModerationLog.report_id == report_id)
            .order_by(ReportModerationLog.id)
            .all()
        )

        assert len(logs) == 2
        assert logs[0].actor_user_id == admin_id
        assert logs[0].action == "needs_evidence"
        assert logs[1].actor_user_id == user_id
        assert logs[1].actor_type == "user"
        assert logs[1].action == "evidence_submitted"

    # 5. Verify the report appears in the admin's pending queue again.
    queue = client.get(
        "/api/admin/moderation/reports/pending",
        headers=admin_headers,
    )

    assert queue.status_code == 200, queue.text
    body = queue.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == report_id
    assert body["items"][0]["status"] == "pending"
    assert len(body["items"][0]["evidence"]) == 1
