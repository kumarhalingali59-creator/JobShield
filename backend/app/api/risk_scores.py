
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.engines.risk_rules import build_risk_signal
from app.models.risk_signal import RiskSignal
from app.schemas.risk_score import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    RiskSignalResponse,
)
from app.services.risk_engine import assess_and_save

router = APIRouter(
    prefix="/api/risk-assessments",
    tags=["Risk Assessments"],
)


@router.post(
    "",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_assessment(
    request: RiskAssessmentRequest,
    db: Session = Depends(get_db),
):
    target_type = request.target_type.strip().lower()
    target_value = request.target_value.strip()

    if not target_type or not target_value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Target type and target value cannot be blank.",
        )

    signals = []

    for signal_type in request.signal_types:
        signal = build_risk_signal(signal_type)

        if signal is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown risk signal type: {signal_type}",
            )

        signals.append(signal)

    try:
        record = assess_and_save(
            db,
            target_type=target_type,
            target_value=target_value,
            signals=signals,
            # Client input cannot establish evidence sufficiency.
            # Keep assessments UNKNOWN until trusted evaluation exists.
            has_sufficient_evidence=False,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    saved_signals = (
        db.query(RiskSignal)
        .filter(RiskSignal.risk_score_id == record.id)
        .order_by(RiskSignal.id.asc())
        .all()
    )

    return RiskAssessmentResponse(
        id=record.id,
        target_type=record.target_type,
        target_value=record.target_value,
        score=record.score,
        risk_level=record.risk_level,
        explanation=record.explanation,
        signals=[
            RiskSignalResponse(
                signal_type=signal.signal_type,
                severity=signal.severity,
                points=signal.points,
                description=signal.description,
                source=signal.source,
            )
            for signal in saved_signals
        ],
    )
