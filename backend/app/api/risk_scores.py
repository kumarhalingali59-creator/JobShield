
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db_errors import commit_or_raise
from app.core.dependencies import get_db
from app.engines.risk_rules import build_risk_signal
from app.models.risk_signal import RiskSignal
from app.schemas.risk_score import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    RiskSignalResponse,
)
from app.services.automated_detector import (
    analyze_target_for_osint_signals,
    analyze_text_for_scam_signals,
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Target type and target value cannot be blank.",
        )

    # Validate supplied signal names for backward compatibility.
    # Client-provided signals are never trusted as evidence or saved.
    for signal_type in request.signal_types:
        if build_risk_signal(signal_type) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Unknown risk signal type: {signal_type}",
            )

    text_target_types = {
        "message",
        "job description",
        "job_description",
        "recruitment text",
        "recruitment message",
    }

    try:
        # Generate risk signals from backend detection only.
        if target_type in text_target_types:
            signals = analyze_text_for_scam_signals(target_value)
        else:
            signals = analyze_target_for_osint_signals(
                target_type,
                target_value,
            )

        record = assess_and_save(
            db,
            target_type=target_type,
            target_value=target_value,
            signals=signals,
            # Client input cannot establish verified evidence.
            has_sufficient_evidence=False,
            # Allow a preliminary score for backend-detected signals.
            preliminary=True,
        )

        # This endpoint owns the database transaction.
        commit_or_raise(db)
        db.refresh(record)

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

    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The risk assessment could not be saved.",
        ) from exc
