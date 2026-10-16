
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
) -> RiskAssessment:
    """Calculate a transparent preliminary risk assessment."""

    if not has_sufficient_evidence or not signal_points:
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

    return RiskAssessment(
        score=score,
        risk_level=risk_level,
        explanation=(
            f"Preliminary score: {score}/100, based on "
            f"{len(signal_points)} risk signal(s). "
            "Review the individual signals and their sources."
        ),
    )
