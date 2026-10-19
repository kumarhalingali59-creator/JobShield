
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
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

# Register all models with SQLAlchemy.
import app.models.company
import app.models.email
import app.models.job
import app.models.message
import app.models.phone_number
import app.models.recruiter
import app.models.website

# Create an isolated, in-memory SQLite database.
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

try:
    # Create two users, each with their own report and evidence.
    with TestSessionLocal() as db:
        user_a = User(
            email="evidence-user-a@example.invalid",
            password_hash=hash_password(
                "Isolated-Test-Password-A-2026!"
            ),
            is_active=True,
        )
        user_b = User(
            email="evidence-user-b@example.invalid",
            password_hash=hash_password(
                "Isolated-Test-Password-B-2026!"
            ),
            is_active=True,
        )

        db.add_all([user_a, user_b])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)

        report_a = Report(
            user_id=user_a.id,
            report_type="company",
            target_value="Isolated Company A",
            description="Test report owned by user A.",
        )
        report_b = Report(
            user_id=user_b.id,
            report_type="company",
            target_value="Isolated Company B",
            description="Test report owned by user B.",
        )

        db.add_all([report_a, report_b])
        db.commit()
        db.refresh(report_a)
        db.refresh(report_b)

        evidence_a = Evidence(
            report_id=report_a.id,
            file_name="test-a.txt",
            storage_path=f"isolated-test/{report_a.id}/test-a.txt",
            content_type="text/plain",
            file_size=12,
            description="Isolated test evidence A.",
        )
        evidence_b = Evidence(
            report_id=report_b.id,
            file_name="test-b.txt",
            storage_path=f"isolated-test/{report_b.id}/test-b.txt",
            content_type="text/plain",
            file_size=12,
            description="Isolated test evidence B.",
        )

        db.add_all([evidence_a, evidence_b])
        db.commit()
        db.refresh(evidence_a)
        db.refresh(evidence_b)

        report_a_id = report_a.id
        report_b_id = report_b.id
        evidence_a_id = evidence_a.id
        evidence_b_id = evidence_b.id
        user_a_id = user_a.id

    token_a = create_access_token(subject=str(user_a_id))
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # IMPORTANT: use fastapi_app, not app.
    with TestClient(fastapi_app) as client:

        # 1. Unauthenticated access must be rejected.
        response = client.get("/api/evidence")
        assert response.status_code == 401, (
            response.status_code,
            response.text,
        )
        print("PASS: unauthenticated evidence listing rejected (401)")

        # 2. User A can list their own evidence.
        response = client.get(
            "/api/evidence",
            params={"report_id": report_a_id},
            headers=headers_a,
        )
        assert response.status_code == 200, (
            response.status_code,
            response.text,
        )

        listed_ids = [
            item["id"] for item in response.json()["items"]
        ]
        assert evidence_a_id in listed_ids, listed_ids
        assert evidence_b_id not in listed_ids, listed_ids
        print("PASS: user A can list their own evidence")

        # 3. User A can retrieve their own evidence.
        response = client.get(
            f"/api/evidence/{evidence_a_id}",
            headers=headers_a,
        )
        assert response.status_code == 200, (
            response.status_code,
            response.text,
        )
        print("PASS: user A can retrieve their own evidence")

        # 4. User A cannot retrieve user B's evidence.
        response = client.get(
            f"/api/evidence/{evidence_b_id}",
            headers=headers_a,
        )
        assert response.status_code == 404, (
            response.status_code,
            response.text,
        )
        print("PASS: user A cannot retrieve user B's evidence (404)")

        # 5. User A cannot attach evidence to user B's report.
        response = client.post(
            "/api/evidence",
            headers=headers_a,
            json={
                "report_id": report_b_id,
                "file_name": "unauthorized.txt",
                "storage_path": (
                    f"isolated-test/{report_b_id}/unauthorized.txt"
                ),
                "content_type": "text/plain",
                "file_size": 12,
                "description": "Should not be saved.",
            },
        )
        assert response.status_code == 405, (
            response.status_code,
            response.text,
        )
        print(
            "PASS: direct evidence metadata creation is disabled (405)"
        )

        # 6. User A cannot list evidence belonging to user B's report.
        response = client.get(
            "/api/evidence",
            params={"report_id": report_b_id},
            headers=headers_a,
        )
        assert response.status_code == 404, (
            response.status_code,
            response.text,
        )
        print(
            "PASS: user A cannot list user B's report evidence (404)"
        )

finally:
    fastapi_app.dependency_overrides.pop(get_db, None)
    engine.dispose()

print("SUCCESS: all isolated evidence ownership checks passed")
