from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.risk_score import RiskScore
from app.models import evidence as evidence_model  # noqa: F401


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


def test_evidence_access_requires_report_ownership(monkeypatch):
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestSessionLocal() as db:
            owner = User(
                email="evidence-owner@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            other_user = User(
                email="evidence-other@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            db.add_all([owner, other_user])
            db.commit()
            db.refresh(owner)
            db.refresh(other_user)

            report = Report(
                user_id=owner.id,
                report_type="other",
                target_value="EVIDENCE-API-TEST",
                description="Test report for evidence API authorization.",
                status="pending",
            )
            db.add(report)
            db.commit()
            db.refresh(report)

            evidence = Evidence(
                report_id=report.id,
                file_name="test.txt",
                storage_path=f"{report.id}/test-evidence-object",
                content_type="text/plain",
                file_size=4,
                description="Test-only evidence.",
            )
            db.add(evidence)
            db.commit()
            db.refresh(evidence)

            owner_id = owner.id
            other_user_id = other_user.id
            report_id = report.id
            evidence_id = evidence.id

        owner_token = create_access_token(subject=str(owner_id))
        other_token = create_access_token(subject=str(other_user_id))

        # Mock signed URL creation: no real storage access occurs.
        monkeypatch.setattr(
            "app.api.evidence.create_evidence_signed_url",
            lambda storage_path, report_id: (
                "https://example.invalid/test-signed-url"
            ),
        )

        with TestClient(app) as client:
            # Anonymous users cannot access private evidence.
            anonymous_detail = client.get(
                f"/api/evidence/{evidence_id}"
            )
            assert anonymous_detail.status_code in (401, 403)

            anonymous_download = client.get(
                f"/api/evidence/{evidence_id}/download"
            )
            assert anonymous_download.status_code in (401, 403)

            # The report owner can view the evidence metadata.
            owner_detail = client.get(
                f"/api/evidence/{evidence_id}",
                headers={
                    "Authorization": f"Bearer {owner_token}"
                },
            )
            assert owner_detail.status_code == 200, owner_detail.text
            assert owner_detail.json()["id"] == evidence_id

            # Another authenticated user cannot view or download it.
            other_detail = client.get(
                f"/api/evidence/{evidence_id}",
                headers={
                    "Authorization": f"Bearer {other_token}"
                },
            )
            assert other_detail.status_code == 404

            other_download = client.get(
                f"/api/evidence/{evidence_id}/download",
                headers={
                    "Authorization": f"Bearer {other_token}"
                },
            )
            assert other_download.status_code == 404

            # The owner receives a mocked, short-lived download URL.
            owner_download = client.get(
                f"/api/evidence/{evidence_id}/download",
                headers={
                    "Authorization": f"Bearer {owner_token}"
                },
            )
            assert owner_download.status_code == 200, owner_download.text
            assert (
                owner_download.json()["download_url"]
                == "https://example.invalid/test-signed-url"
            )
            assert owner_download.json()["expires_in"] == 60

            # The evidence list must only include the owner's reports.
            owner_list = client.get(
                f"/api/evidence?report_id={report_id}",
                headers={
                    "Authorization": f"Bearer {owner_token}"
                },
            )
            assert owner_list.status_code == 200, owner_list.text
            assert owner_list.json()["total"] == 1

            other_list = client.get(
                f"/api/evidence?report_id={report_id}",
                headers={
                    "Authorization": f"Bearer {other_token}"
                },
            )
            assert other_list.status_code == 404

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_other_user_cannot_create_evidence_metadata():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestSessionLocal() as db:
            owner = User(
                email="metadata-owner@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            other_user = User(
                email="metadata-other@example.com",
                password_hash="test-password-hash",
                is_active=True,
            )
            db.add_all([owner, other_user])
            db.commit()
            db.refresh(owner)
            db.refresh(other_user)

            report = Report(
                user_id=owner.id,
                report_type="other",
                target_value="METADATA-OWNERSHIP-TEST",
                description="Test report for evidence metadata ownership.",
                status="pending",
            )
            db.add(report)
            db.commit()
            db.refresh(report)

            owner_id = owner.id
            other_user_id = other_user.id
            report_id = report.id

        other_token = create_access_token(subject=str(other_user_id))

        with TestClient(app) as client:
            response = client.post(
                "/api/evidence",
                headers={
                    "Authorization": f"Bearer {other_token}"
                },
                json={
                    "report_id": report_id,
                    "file_name": "unauthorized.txt",
                    "storage_path": f"{report_id}/unauthorized-object",
                    "content_type": "text/plain",
                    "file_size": 4,
                    "description": "Unauthorized evidence metadata.",
                },
            )

        # The endpoint must hide reports owned by another user.
        assert response.status_code == 404, response.text

        # No evidence metadata should have been created.
        with TestSessionLocal() as db:
            evidence_count = (
                db.query(Evidence)
                .filter(Evidence.report_id == report_id)
                .count()
            )
            assert evidence_count == 0

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
