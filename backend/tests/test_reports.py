
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.main import app
from app.models.risk_score import RiskScore

client = TestClient(app)


def test_report_submission_creates_unknown_risk_assessment():
    target_value = (
        "Test message asking for a registration fee "
        "before joining a job"
    )

    response = client.post(
        "/api/reports",
        json={
            "report_type": "message",
            "target_value": target_value,
            "description": (
                "The sender requests an upfront registration "
                "payment before employment."
            ),
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending"

    with SessionLocal() as db:
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
