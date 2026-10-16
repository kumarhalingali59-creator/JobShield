
from sqlalchemy.orm import Session

from app.engines.risk_rules import build_risk_signal
from app.models.report import Report
from app.models.risk_score import RiskScore
from app.models.risk_signal import RiskSignal
from app.services.risk_engine import assess_and_save


def assess_report(
    db: Session,
    report: Report,
) -> RiskScore:
    """
    Create a preliminary assessment for a report.

    A user-submitted report is an allegation, not verified proof.
    Therefore, this service never marks evidence as sufficient.
    """

    signals = []

    # Add only a registered signal when the report describes
    # a known risk indicator. Do not infer guilt from a report alone.
    description_and_target = (
        f"{report.target_value} {report.description}"
    ).lower()

    if (
        "registration fee" in description_and_target
        or "registration payment" in description_and_target
    ):
        signal = build_risk_signal(
            "upfront_registration_fee",
            source="user_report",
        )
        if signal is not None:
            signals.append(signal)

    elif (
        "pay for job" in description_and_target
        or "payment for employment" in description_and_target
        or "payment to get a job" in description_and_target
    ):
        signal = build_risk_signal(
            "payment_for_job_offer",
            source="user_report",
        )
        if signal is not None:
            signals.append(signal)

    return assess_and_save(
        db,
        target_type=report.report_type,
        target_value=report.target_value,
        signals=signals,
        has_sufficient_evidence=False,
    )
