
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAssessment:
    score: int | None
    risk_level: str
    explanation: str


def calculate_risk(
    signal_points: list[int],
    *,
    has_sufficient_evidence: bool,
    preliminary: bool = False,
) -> RiskAssessment:
    """Calculate a transparent risk assessment.

    Preliminary scoring is permitted for detected automated indicators.
    It does not mean that the target or allegation has been verified.
    """

    if not signal_points or (
        not has_sufficient_evidence and not preliminary
    ):
        return RiskAssessment(
            score=None,
            risk_level="UNKNOWN",
            explanation="Insufficient evidence to assess this target.",
        )

    score = max(0, min(100, sum(signal_points)))

    if score < 20:
        risk_level = "LOW"
    elif score < 40:
        risk_level = "CAUTION"
    elif score < 70:
        risk_level = "SUSPICIOUS"
    else:
        risk_level = "HIGH RISK"

    explanation = (
        f"Preliminary score: {score}/100, based on "
        f"{len(signal_points)} risk signal(s). "
        "These indicators are not proof of fraud. "
        "Review the individual signals and their sources."
    )

    return RiskAssessment(
        score=score,
        risk_level=risk_level,
        explanation=explanation,
    )
