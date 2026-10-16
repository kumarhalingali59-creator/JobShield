
from sqlalchemy.orm import Session

from app.engines.risk_rules import normalize_evidence_source
from app.models.risk_score import RiskScore
from app.models.risk_signal import RiskSignal
from app.services.risk_scoring import calculate_risk


def assess_and_save(
    db: Session,
    *,
    target_type: str,
    target_value: str,
    signals: list[dict],
    has_sufficient_evidence: bool,
) -> RiskScore:
    """Calculate an assessment and save it with its supporting signals."""

    normalized_signals = []

    for signal in signals:
        points = int(signal["points"])

        if not -100 <= points <= 100:
            raise ValueError(
                "Each signal's points must be between -100 and 100."
            )

        source = normalize_evidence_source(
            str(signal.get("source", "automated_detection"))
        )

        normalized_signals.append(
            {
                "signal_type": str(signal["signal_type"]),
                "severity": str(signal["severity"]),
                "points": points,
                "description": str(signal["description"]),
                "source": source,
            }
        )

    assessment = calculate_risk(
        [signal["points"] for signal in normalized_signals],
        has_sufficient_evidence=has_sufficient_evidence,
    )

    record = RiskScore(
        target_type=target_type.strip().lower(),
        target_value=target_value.strip(),
        score=assessment.score,
        risk_level=assessment.risk_level,
        explanation=assessment.explanation,
    )

    db.add(record)

    try:
        db.flush()

        for signal in normalized_signals:
            db.add(
                RiskSignal(
                    risk_score_id=record.id,
                    **signal,
                )
            )

        db.commit()
        db.refresh(record)
        return record

    except Exception:
        db.rollback()
        raise
