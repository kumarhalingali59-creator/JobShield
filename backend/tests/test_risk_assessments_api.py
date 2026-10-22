
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app
from app.models import evidence  # noqa: F401
from app.models.risk_score import RiskScore
from app.models.risk_signal import RiskSignal


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


def test_blank_target_value_is_rejected():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/risk-assessments",
                json={
                    "target_type": "website",
                    "target_value": "   ",
                    "signal_types": [],
                },
            )

        assert response.status_code == 422

        with TestSessionLocal() as db:
            assert db.query(RiskScore).count() == 0
            assert db.query(RiskSignal).count() == 0

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_unknown_signal_type_is_rejected_without_saving():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/risk-assessments",
                json={
                    "target_type": "website",
                    "target_value": "example.com",
                    "signal_types": ["unknown_signal"],
                },
            )

        assert response.status_code == 422

        with TestSessionLocal() as db:
            assert db.query(RiskScore).count() == 0
            assert db.query(RiskSignal).count() == 0

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_client_cannot_force_sufficient_evidence():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/risk-assessments",
                json={
                    "target_type": "website",
                    "target_value": "example.com",
                    "signal_types": ["payment_for_job_offer"],
                    "has_sufficient_evidence": True,
                },
            )

        assert response.status_code == 201, response.text
        data = response.json()

        # The client-provided signal must not be trusted or saved.
        assert data["risk_level"] == "UNKNOWN"
        assert data["score"] is None
        assert data["signals"] == []

        with TestSessionLocal() as db:
            saved = db.query(RiskScore).filter_by(
                target_value="example.com",
                target_type="website",
            ).one()

            assert saved.risk_level == "UNKNOWN"
            assert saved.score is None

            assert (
                db.query(RiskSignal)
                .filter_by(risk_score_id=saved.id)
                .count()
                == 0
            )

    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()
