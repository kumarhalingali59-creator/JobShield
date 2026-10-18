from io import BytesIO
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.user import User
from app.models.report import Report
from app.models.evidence import Evidence
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


def create_test_report(email, target):
    with TestSessionLocal() as db:
        user = User(
            email=email,
            password_hash="test-password-hash",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        report = Report(
            user_id=user.id,
            report_type="other",
            target_value=target,
            description="Test-only report.",
            status="pending",
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        user_id, report_id = user.id, report.id

    return create_access_token(subject=str(user_id)), report_id


def setup_test_database():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_test_database():
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_upload_saves_evidence_metadata(monkeypatch):
    setup_test_database()
    try:
        token, report_id = create_test_report(
            "upload-success@example.com",
            "UPLOAD-SUCCESS-TEST",
        )

        monkeypatch.setattr(
            "app.api.evidence.upload_evidence_file",
            lambda report_id, file: {
                "file_name": "test.txt",
                "storage_path": f"{report_id}/mock-object",
                "content_type": "text/plain",
                "file_size": 4,
            },
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/evidence/upload",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "report_id": str(report_id),
                    "description": "  test upload  ",
                },
                files={
                    "file": ("test.txt", BytesIO(b"test"), "text/plain"),
                },
            )

        assert response.status_code == 201, response.text
        body = response.json()
        assert body["file_name"] == "test.txt"
        assert body["storage_path"] == f"{report_id}/mock-object"
        assert body["content_type"] == "text/plain"
        assert body["file_size"] == 4
        assert body["description"] == "test upload"

        with TestSessionLocal() as db:
            saved = db.query(Evidence).filter_by(
                storage_path=f"{report_id}/mock-object"
            ).one()
            assert saved.report_id == report_id
    finally:
        teardown_test_database()


def test_upload_database_failure_attempts_storage_cleanup(monkeypatch):
    setup_test_database()
    listener_registered = False
    try:
        token, report_id = create_test_report(
            "upload-failure@example.com",
            "UPLOAD-FAILURE-TEST",
        )

        storage_client = Mock()
        storage_bucket = Mock()
        storage_client.storage.from_.return_value = storage_bucket

        monkeypatch.setattr(
            "app.api.evidence.upload_evidence_file",
            lambda report_id, file: {
                "file_name": "test.txt",
                "storage_path": f"{report_id}/mock-failed-object",
                "content_type": "text/plain",
                "file_size": 4,
            },
        )
        monkeypatch.setattr(
            "app.api.evidence.get_storage_client",
            lambda: storage_client,
        )

        def fail_evidence_flush(session, flush_context, instances):
            if any(isinstance(obj, Evidence) for obj in session.new):
                raise SQLAlchemyError("Simulated database failure")

        event.listen(
            TestSessionLocal,
            "before_flush",
            fail_evidence_flush,
        )
        listener_registered = True

        with TestClient(app) as client:
            response = client.post(
                "/api/evidence/upload",
                headers={"Authorization": f"Bearer {token}"},
                data={"report_id": str(report_id)},
                files={
                    "file": ("test.txt", BytesIO(b"test"), "text/plain"),
                },
            )

        assert response.status_code == 500, response.text
        assert response.json()["detail"] == (
            "Could not save evidence metadata."
        )
        storage_bucket.remove.assert_called_once_with(
            [f"{report_id}/mock-failed-object"]
        )

        with TestSessionLocal() as db:
            saved_count = db.query(Evidence).filter_by(
                report_id=report_id
            ).count()
            assert saved_count == 0
    finally:
        if listener_registered:
            event.remove(
                TestSessionLocal,
                "before_flush",
                fail_evidence_flush,
            )
        teardown_test_database()

def test_upload_rejects_report_owned_by_another_user(monkeypatch):
    setup_test_database()
    try:
        owner_token, report_id = create_test_report(
            "upload-owner@example.com",
            "UPLOAD-OWNERSHIP-TEST",
        )
        other_token, _ = create_test_report(
            "upload-other@example.com",
            "UPLOAD-OTHER-USER-TEST",
        )

        upload_mock = Mock(
            side_effect=AssertionError(
                "Storage upload must not run for an unowned report."
            )
        )
        monkeypatch.setattr(
            "app.api.evidence.upload_evidence_file",
            upload_mock,
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/evidence/upload",
                headers={
                    "Authorization": f"Bearer {other_token}"
                },
                data={"report_id": str(report_id)},
                files={
                    "file": (
                        "test.txt",
                        BytesIO(b"test"),
                        "text/plain",
                    ),
                },
            )

        assert response.status_code == 404, response.text
        upload_mock.assert_not_called()

        with TestSessionLocal() as db:
            saved_count = (
                db.query(Evidence)
                .filter_by(report_id=report_id)
                .count()
            )
            assert saved_count == 0

    finally:
        teardown_test_database()
