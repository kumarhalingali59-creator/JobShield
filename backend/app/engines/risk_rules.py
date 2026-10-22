from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class RiskRule:
    signal_type: str
    severity: str
    points: int
    description: str


RISK_RULES: dict[str, RiskRule] = {
    # Core Deterministic Signals
    "upfront_registration_fee": RiskRule(
        signal_type="upfront_registration_fee",
        severity="high",
        points=35,
        description="The job message requests an upfront registration payment before employment.",
    ),
    "payment_for_job_offer": RiskRule(
        signal_type="payment_for_job_offer",
        severity="high",
        points=40,
        description="The job offer requests payment as a condition of receiving employment.",
    ),
    "unverified_company_details": RiskRule(
        signal_type="unverified_company_details",
        severity="medium",
        points=10,
        description="The company's identity or public details could not be independently verified.",
    ),

    # OSINT & Domain Intelligence Signals
    "suspicious_free_email_domain": RiskRule(
        signal_type="suspicious_free_email_domain",
        severity="medium",
        points=20,
        description="Recruiter uses a free webmail address (Gmail/Yahoo/Hotmail) for corporate communication.",
    ),
    "suspicious_domain_tld": RiskRule(
        signal_type="suspicious_domain_tld",
        severity="medium",
        points=25,
        description="Domain uses a top-level domain frequently associated with low-cost spam or phishing hosting.",
    ),
    "recently_created_domain": RiskRule(
        signal_type="recently_created_domain",
        severity="high",
        points=30,
        description="Domain was registered very recently and lacks established operational history.",
    ),
    "lookalike_domain_impersonation": RiskRule(
        signal_type="lookalike_domain_impersonation",
        severity="high",
        points=35,
        description="Domain closely mimics a legitimate brand or enterprise company domain.",
    ),

    # AI/NLP Scam Pattern Signals
    "training_equipment_reimbursement_scheme": RiskRule(
        signal_type="training_equipment_reimbursement_scheme",
        severity="high",
        points=40,
        description="Directs candidate to buy equipment from a specific vendor using a promised check/wire reimbursement.",
    ),
    "security_deposit_demand": RiskRule(
        signal_type="security_deposit_demand",
        severity="high",
        points=35,
        description="Demands a security deposit for hardware, badge, or remote work training materials.",
    ),
    "overpayment_refund_scam": RiskRule(
        signal_type="overpayment_refund_scam",
        severity="high",
        points=45,
        description="Mentions overpayment refunding via check, wire transfer, cryptocurrency, or gift cards.",
    ),
    "telegram_whatsapp_interview_only": RiskRule(
        signal_type="telegram_whatsapp_interview_only",
        severity="medium",
        points=20,
        description="Conducts hiring process exclusively over informal chat platforms like Telegram or WhatsApp.",
    ),
    "guaranteed_high_pay_no_skills": RiskRule(
        signal_type="guaranteed_high_pay_no_skills",
        severity="medium",
        points=25,
        description="Promises guaranteed high daily/weekly pay with no required prior experience or skill verification.",
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