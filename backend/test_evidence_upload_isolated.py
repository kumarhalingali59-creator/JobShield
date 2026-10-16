
from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.main import app as fastapi_app
from app.models.user import User
from app.models.report import Report
from app.models.evidence import Evidence
from app.models.risk_score import RiskScore
from app.models.risk_signal import RiskSignal

# Register all SQLAlchemy models.
import app.models.company
import app.models.email
import app.models.job
import app.models.message
import app.models.phone_number
import app.models.recruiter
import app.models.website

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

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = override_get_db


# Fake storage: never connect to Supabase.
def fake_upload_evidence_file(report_id, file):
    content = file.file.read(5 * 1024 * 1024 + 1)

    if not content:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if len(content) > 5 * 1024 * 1024:
        from fastapi import HTTPException
        raise HTTPException(status_code=413, detail="File size must not exceed 5 MB.")

    return {
        "file_name": file.filename,
        "storage_path": f"isolated-test/{report_id}/mock-upload.txt",
        "content_type": file.content_type,
        "file_size": len(content),
    }


try:
    with TestSessionLocal() as db:
        user_a = User(
            email="upload-user-a@example.invalid",
            password_hash=hash_password("Isolated-Upload-Password-A-2026!"),
            is_active=True,
        )
        user_b = User(
            email="upload-user-b@example.invalid",
            password_hash=hash_password("Isolated-Upload-Password-B-2026!"),
            is_active=True,
        )
        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        report_a = Report(
            user_id=user_a.id,
            report_type="company",
            target_value="Upload Test Company A",
            description="Isolated upload test report A.",
        )
        report_b = Report(
            user_id=user_b.id,
            report_type="company",
            target_value="Upload Test Company B",
            description="Isolated upload test report B.",
        )
        db.add_all([report_a, report_b])
        db.commit()
        db.refresh(report_a)
        db.refresh(report_b)

        user_a_id = user_a.id
        user_b_id = user_b.id
        report_a_id = report_a.id
        report_b_id = report_b.id

    headers_a = {
        "Authorization": f"Bearer {create_access_token(str(user_a_id))}"
    }

    with TestClient(fastapi_app) as client:
        # 1. Unauthenticated upload must be rejected.
        with patch(
            "app.api.evidence.upload_evidence_file",
            side_effect=AssertionError("Storage must not be called"),
        ) as storage_mock:
            response = client.post(
                "/api/evidence/upload",
                data={"report_id": str(report_a_id)},
                files={"file": ("proof.txt", b"safe test", "text/plain")},
            )
            assert response.status_code == 401, (
                response.status_code, response.text
            )
            storage_mock.assert_not_called()
        print("PASS: unauthenticated upload rejected (401)")

        # 2. A user cannot upload to another user's report.
        with patch(
            "app.api.evidence.upload_evidence_file",
            side_effect=AssertionError("Storage must not be called"),
        ) as storage_mock:
            response = client.post(
                "/api/evidence/upload",
                headers=headers_a,
                data={"report_id": str(report_b_id)},
                files={"file": ("proof.txt", b"safe test", "text/plain")},
            )
            assert response.status_code == 404, (
                response.status_code, response.text
            )
            storage_mock.assert_not_called()
        print("PASS: cross-user upload rejected before storage (404)")

        # 3. Unsupported MIME type is rejected by the real storage service.
        from app.services.evidence_storage import upload_evidence_file

        with patch(
            "app.services.evidence_storage.get_storage_client",
            side_effect=AssertionError("Supabase must not be called"),
        ):
            response = client.post(
                "/api/evidence/upload",
                headers=headers_a,
                data={"report_id": str(report_a_id)},
                files={
                    "file": (
                        "malware.exe",
                        b"not a real executable",
                        "application/octet-stream",
                    )
                },
            )
            assert response.status_code == 415, (
                response.status_code, response.text
            )
        print("PASS: unsupported file type rejected (415)")

        # 4. Empty files are rejected by the real storage service.
        with patch(
            "app.services.evidence_storage.get_storage_client",
            side_effect=AssertionError("Supabase must not be called"),
        ):
            response = client.post(
                "/api/evidence/upload",
                headers=headers_a,
                data={"report_id": str(report_a_id)},
                files={"file": ("empty.txt", b"", "text/plain")},
            )
            assert response.status_code == 400, (
                response.status_code, response.text
            )
        print("PASS: empty file rejected (400)")

        # 5. Files exceeding 5 MB are rejected by the real storage service.
        with patch(
            "app.services.evidence_storage.get_storage_client",
            side_effect=AssertionError("Supabase must not be called"),
        ):
            response = client.post(
                "/api/evidence/upload",
                headers=headers_a,
                data={"report_id": str(report_a_id)},
                files={
                    "file": (
                        "large.txt",
                        b"x" * (5 * 1024 * 1024 + 1),
                        "text/plain",
                    )
                },
            )
            assert response.status_code == 413, (
                response.status_code, response.text
            )
        print("PASS: oversized file rejected (413)")

        # 6. A valid upload uses the mock and saves only to SQLite.
        with patch(
            "app.api.evidence.upload_evidence_file",
            side_effect=fake_upload_evidence_file,
        ) as storage_mock:
            response = client.post(
                "/api/evidence/upload",
                headers=headers_a,
                data={
                    "report_id": str(report_a_id),
                    "description": "Isolated successful upload test",
                },
                files={
                    "file": (
                        "proof.txt",
                        b"safe test content",
                        "text/plain",
                    )
                },
            )
            assert response.status_code == 201, (
                response.status_code, response.text
            )
            storage_mock.assert_called_once()

            saved = response.json()
            assert saved["report_id"] == report_a_id, saved
            assert saved["file_name"] == "proof.txt", saved
        print("PASS: mocked valid upload saved in isolated SQLite (201)")

        # 7. If database commit fails, the API should attempt storage cleanup.
        # The upload itself is mocked; cleanup is mocked too.
        class FakeStorageBucket:
            def __init__(self):
                self.removed_paths = []

            def remove(self, paths):
                self.removed_paths.extend(paths)
                return []

        class FakeStorage:
            def __init__(self, bucket):
                self.bucket = bucket

            def from_(self, bucket_name):
                assert bucket_name == "jobshield-evidence", bucket_name
                return self.bucket

        class FakeStorageClient:
            def __init__(self, bucket):
                self.storage = FakeStorage(bucket)

        fake_bucket = FakeStorageBucket()

        def fail_commit_after_upload(db_session):
            raise RuntimeError("Unexpected commit hook reached")

        # Force a database SQLAlchemy error at commit and check cleanup.
        from sqlalchemy.exc import SQLAlchemyError

        def fail_commit(*args, **kwargs):
            raise SQLAlchemyError("Isolated simulated database failure")

        with (
            patch(
                "app.api.evidence.upload_evidence_file",
                side_effect=fake_upload_evidence_file,
            ),
            patch(
                "app.api.evidence.get_storage_client",
                return_value=FakeStorageClient(fake_bucket),
            ),
            patch.object(
                TestSessionLocal.class_,
                "commit",
                autospec=True,
                side_effect=fail_commit,
            ),
        ):
            response = client.post(
                "/api/evidence/upload",
                headers=headers_a,
                data={"report_id": str(report_a_id)},
                files={
                    "file": (
                        "cleanup.txt",
                        b"cleanup test",
                        "text/plain",
                    )
                },
            )
            assert response.status_code == 500, (
                response.status_code, response.text
            )
            assert len(fake_bucket.removed_paths) == 1, (
                fake_bucket.removed_paths
            )
        print("PASS: database failure triggers mocked storage cleanup")

        # 8. Unauthenticated evidence downloads must be rejected.
        evidence_id = saved["id"]

        with patch(
            "app.api.evidence.create_evidence_signed_url",
            side_effect=AssertionError("Signed URL must not be created"),
        ) as signed_url_mock:
            response = client.get(
                f"/api/evidence/{evidence_id}/download"
            )
            assert response.status_code == 401, (
                response.status_code, response.text
            )
            signed_url_mock.assert_not_called()
        print("PASS: unauthenticated download rejected (401)")

        # 9. Another user must not download this evidence.
        headers_b = {
            "Authorization": (
                f"Bearer {create_access_token(str(user_b_id))}"
            )
        }

        with patch(
            "app.api.evidence.create_evidence_signed_url",
            side_effect=AssertionError("Signed URL must not be created"),
        ) as signed_url_mock:
            response = client.get(
                f"/api/evidence/{evidence_id}/download",
                headers=headers_b,
            )
            assert response.status_code == 404, (
                response.status_code, response.text
            )
            signed_url_mock.assert_not_called()
        print("PASS: cross-user download rejected (404)")

        # 10. The owner can receive a temporary signed URL.
        with patch(
            "app.api.evidence.create_evidence_signed_url",
            return_value="https://example.invalid/mock-signed-download",
        ) as signed_url_mock:
            response = client.get(
                f"/api/evidence/{evidence_id}/download",
                headers=headers_a,
            )
            assert response.status_code == 200, (
                response.status_code, response.text
            )

            download_data = response.json()
            assert download_data["download_url"] == (
                "https://example.invalid/mock-signed-download"
            ), download_data
            assert download_data["expires_in"] == 60, download_data

            signed_url_mock.assert_called_once_with(
                saved["storage_path"],
                report_id=report_a_id,
            )

        print("PASS: owner receives temporary signed URL (200)")


finally:
    fastapi_app.dependency_overrides.pop(get_db, None)
    engine.dispose()

print("SUCCESS: isolated evidence upload security tests passed")
