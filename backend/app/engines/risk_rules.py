
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskRule:
    signal_type: str
    severity: str
    points: int
    description: str


RISK_RULES: dict[str, RiskRule] = {
    "upfront_registration_fee": RiskRule(
        signal_type="upfront_registration_fee",
        severity="high",
        points=35,
        description=(
            "The job message requests an upfront registration "
            "payment before employment."
        ),
    ),
    "payment_for_job_offer": RiskRule(
        signal_type="payment_for_job_offer",
        severity="high",
        points=40,
        description=(
            "The job offer requests payment as a condition "
            "of receiving employment."
        ),
    ),
    "unverified_company_details": RiskRule(
        signal_type="unverified_company_details",
        severity="medium",
        points=10,
        description=(
            "The company's identity or public details could "
            "not be independently verified."
        ),
    ),
}


def get_risk_rule(signal_type: str) -> RiskRule | None:
    """Return a known rule without treating unknown indicators as safe."""
    return RISK_RULES.get(signal_type)


def build_risk_signal(
    signal_type: str,
    *,
    source: str = "automated_detection",
) -> dict | None:
    """Build a database-ready signal from a registered rule."""

    rule = get_risk_rule(signal_type)

    if rule is None:
        return None

    return {
        "signal_type": rule.signal_type,
        "severity": rule.severity,
        "points": rule.points,
        "description": rule.description,
        "source": source,
    }


from enum import StrEnum


class EvidenceSource(StrEnum):
    USER_REPORT = "user_report"
    AUTOMATED_DETECTION = "automated_detection"
    PUBLIC_SOURCE = "public_source"
    VERIFIED_FACT = "verified_fact"


def validate_evidence_source(source: str) -> bool:
    """Check whether an evidence source category is recognized."""
    return source in {item.value for item in EvidenceSource}


def normalize_evidence_source(source: str) -> str:
    """Normalize and validate an evidence source category."""
    normalized = source.strip().lower()

    if not validate_evidence_source(normalized):
        raise ValueError(f"Unsupported evidence source: {source}")

    return normalized
