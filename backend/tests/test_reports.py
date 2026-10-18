
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.report import Report
from app.models.risk_score import RiskScore
from app.models.user import User

# Register related models and their foreign-key dependencies.
from app.models import evidence  # noqa: F401


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


def test_report_submission_and_private_report_visibility():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    target_value = (
        "Test message asking for a registration fee "
        "before joining a job"
    )

    try:
        with TestSessionLocal() as db:
            user = User(
                email="report-test@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            other_user = User(
                email="other-report-test@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )

            db.add_all([user, other_user])
            db.commit()
            db.refresh(user)
            db.refresh(other_user)

            user_id = user.id
            other_user_id = other_user.id

        token = create_access_token(subject=str(user_id))
        other_token = create_access_token(
            subject=str(other_user_id)
        )

        with TestClient(app) as client:
            # Submit a report as the first user.
            response = client.post(
                "/api/reports",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "report_type": "message",
                    "target_value": target_value,
                    "description": (
                        "The sender requests an upfront registration "
                        "payment before employment."
                    ),
                },
            )

            assert response.status_code == 201, response.text
            assert response.json()["status"] == "pending"

            report_id = response.json()["id"]

            # Pending reports must not be publicly visible.
            public_list = client.get("/api/reports")
            public_detail = client.get(
                f"/api/reports/{report_id}"
            )

            assert public_list.status_code == 200
            assert all(
                item["id"] != report_id
                for item in public_list.json()["items"]
            )

            assert public_detail.status_code == 404

            # The submitting user can see their own pending report.
            my_reports = client.get(
                "/api/reports/mine",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert my_reports.status_code == 200, my_reports.text
            assert my_reports.json()["total"] == 1
            assert my_reports.json()["items"][0]["id"] == report_id
            assert my_reports.json()["items"][0]["status"] == "pending"

            # A different authenticated user cannot see that report.
            other_reports = client.get(
                "/api/reports/mine",
                headers={
                    "Authorization": f"Bearer {other_token}"
                },
            )

            assert other_reports.status_code == 200
            assert other_reports.json()["total"] == 0
            assert other_reports.json()["items"] == []

            # The private endpoint requires authentication.
            anonymous_reports = client.get("/api/reports/mine")

            assert anonymous_reports.status_code in (401, 403)

        # Confirm the report and its UNKNOWN risk assessment persist.
        with TestSessionLocal() as db:
            report = db.query(Report).filter(
                Report.target_value == target_value
            ).first()

            assert report is not None
            assert report.user_id == user_id

            assessment = (
                db.query(RiskScore)
                .filter(
                    RiskScore.target_value == target_value,
                    RiskScore.target_type == "message",
                )
                .order_by(RiskScore.id.desc())
                .first()
            )

            assert assessment is not None
            assert assessment.risk_level == "UNKNOWN"
            assert assessment.score is None

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_public_report_filters_never_expose_unapproved_reports():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestSessionLocal() as db:
            user = User(
                email="report-visibility@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            pending_report = Report(
                user_id=user.id,
                report_type="message",
                target_value="PENDING-VISIBILITY-TEST",
                description="Pending test report.",
                status="pending",
            )
            rejected_report = Report(
                user_id=user.id,
                report_type="message",
                target_value="REJECTED-VISIBILITY-TEST",
                description="Rejected test report.",
                status="rejected",
            )
            approved_report = Report(
                user_id=user.id,
                report_type="message",
                target_value="APPROVED-VISIBILITY-TEST",
                description="Approved test report.",
                status="approved",
            )

            db.add_all([
                pending_report,
                rejected_report,
                approved_report,
            ])
            db.commit()

            pending_id = pending_report.id
            rejected_id = rejected_report.id
            approved_id = approved_report.id

        with TestClient(app) as client:
            # Ordinary public listing only returns approved reports.
            response = client.get("/api/reports")
            assert response.status_code == 200, response.text

            public_ids = {
                item["id"] for item in response.json()["items"]
            }
            assert approved_id in public_ids
            assert pending_id not in public_ids
            assert rejected_id not in public_ids

            # Explicit status filters must not bypass approval rules.
            for requested_status in ("pending", "rejected"):
                filtered = client.get(
                    "/api/reports",
                    params={"status": requested_status},
                )
                assert filtered.status_code == 200, filtered.text
                assert filtered.json()["total"] == 0

            # Direct lookup must also hide unapproved reports.
            assert client.get(
                f"/api/reports/{pending_id}"
            ).status_code == 404

            assert client.get(
                f"/api/reports/{rejected_id}"
            ).status_code == 404

            # The approved report remains publicly accessible.
            approved_detail = client.get(
                f"/api/reports/{approved_id}"
            )
            assert approved_detail.status_code == 200, (
                approved_detail.text
            )

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_user_cannot_access_another_users_pending_report():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestSessionLocal() as db:
            owner = User(
                email="pending-owner@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            other_user = User(
                email="pending-other@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            db.add_all([owner, other_user])
            db.commit()
            db.refresh(owner)
            db.refresh(other_user)

            report = Report(
                user_id=owner.id,
                report_type="message",
                target_value="PRIVATE-PENDING-REPORT-TEST",
                description="Private pending report.",
                status="pending",
            )
            db.add(report)
            db.commit()
            db.refresh(report)

            report_id = report.id
            owner_id = owner.id
            other_user_id = other_user.id

        owner_token = create_access_token(subject=str(owner_id))
        other_token = create_access_token(subject=str(other_user_id))

        with TestClient(app) as client:
            # Owner can see the pending report in their own list.
            owner_response = client.get(
                "/api/reports/mine",
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert owner_response.status_code == 200
            assert any(
                item["id"] == report_id
                for item in owner_response.json()["items"]
            )

            # Another user cannot see it in their own list.
            other_response = client.get(
                "/api/reports/mine",
                headers={"Authorization": f"Bearer {other_token}"},
            )
            assert other_response.status_code == 200
            assert all(
                item["id"] != report_id
                for item in other_response.json()["items"]
            )

            # Direct public lookup must not expose the pending report.
            direct_response = client.get(
                f"/api/reports/{report_id}",
                headers={"Authorization": f"Bearer {other_token}"},
            )
            assert direct_response.status_code == 404

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
