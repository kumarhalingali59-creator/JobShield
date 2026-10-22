
import re

from app.engines.risk_rules import build_risk_signal


FREE_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "icloud.com",
}

SUSPICIOUS_TLDS = (
    ".xyz",
    ".top",
    ".tk",
    ".ml",
    ".ga",
    ".cf",
    ".gq",
    ".site",
    ".online",
)


def _add_signal(
    signals: list[dict],
    signal_type: str,
) -> None:
    """Add a registered signal only once."""
    signal = build_risk_signal(
        signal_type,
        source="automated_detection",
    )

    if signal is not None and not any(
        existing["signal_type"] == signal_type
        for existing in signals
    ):
        signals.append(signal)


def analyze_text_for_scam_signals(text: str) -> list[dict]:
    """
    Detect preliminary recruitment-scam indicators in message text.

    These rule-based matches are warning indicators, not proof of fraud.
    """
    if not text or not text.strip():
        return []

    lower_text = text.lower()
    normalized_text = re.sub(r"\s+", " ", lower_text)
    signals: list[dict] = []

    # 1. Registration, application, processing and training fees.
    registration_terms = (
        "registration",
        "register",
        "application fee",
        "processing fee",
        "onboarding",
        "training fee",
        "joining fee",
        "placement fee",
    )

    payment_terms = (
        "pay",
        "paid",
        "payment",
        "fee",
        "deposit",
        "â‚¹",
        "rs.",
        "inr",
        "rupees",
        "refundable",
    )

    has_registration_term = any(
        term in normalized_text for term in registration_terms
    )

    has_payment_term = any(
        term in normalized_text for term in payment_terms
    )

    if has_registration_term and has_payment_term:
        _add_signal(signals, "upfront_registration_fee")

    # Also recognize common fee wording without "registration".
    general_fee_phrases = (
        "processing fee",
        "application fee",
        "onboarding fee",
        "training fee",
        "joining fee",
        "placement fee",
        "pay to apply",
    )

    if any(
        phrase in normalized_text for phrase in general_fee_phrases
    ):
        _add_signal(signals, "upfront_registration_fee")

    # 2. Security deposits.
    deposit_terms = (
        "security deposit",
        "refundable deposit",
        "pay a deposit",
        "pay deposit",
        "deposit payment",
    )

    if any(term in normalized_text for term in deposit_terms):
        _add_signal(signals, "security_deposit_demand")

    # 3. Equipment-purchase and reimbursement schemes.
    equipment_terms = (
        "buy equipment",
        "purchase equipment",
        "buy a laptop",
        "purchase a laptop",
        "purchase software",
        "vendor kit",
        "company equipment kit",
        "equipment reimbursement",
    )

    if any(term in normalized_text for term in equipment_terms):
        _add_signal(
            signals,
            "training_equipment_reimbursement_scheme",
        )

    # 4. Overpayment, refund and suspicious payment instructions.
    overpayment_terms = (
        "overpayment",
        "overpaid",
        "wire transfer",
        "gift card",
        "cashier check",
        "cashier's check",
        "check reimbursement",
        "send the excess amount",
        "refund the difference",
        "crypto payment",
        "cryptocurrency payment",
    )

    if any(term in normalized_text for term in overpayment_terms):
        _add_signal(signals, "overpayment_refund_scam")

    # 5. Explicit payment required to obtain employment.
    job_payment_phrases = (
        "pay to get the job",
        "payment to get the job",
        "pay to secure the job",
        "payment to secure the job",
        "pay to receive the offer",
        "payment required for employment",
        "pay before joining",
        "pay us to get hired",
    )

    if any(
        phrase in normalized_text for phrase in job_payment_phrases
    ):
        _add_signal(signals, "payment_for_job_offer")

    # 6. Interviews conducted exclusively through messaging apps.
    messaging_interview_terms = (
        "telegram interview",
        "interview via telegram",
        "interview on telegram",
        "whatsapp interview",
        "interview via whatsapp",
        "interview on whatsapp",
        "chat only interview",
        "text interview only",
        "interview through text messages",
        "signal app interview",
    )

    has_known_messaging_phrase = any(
        phrase in normalized_text
        for phrase in messaging_interview_terms
    )

    # Handle natural wording such as:
    # "Your interview will be conducted via Telegram chat only."
    messaging_app_pattern = (
        r"\binterview\b"
        r".{0,100}?"
        r"\b(?:via|on|through|over)\s+"
        r"(?:telegram|whatsapp|signal(?:\s+app)?)\b"
        r".{0,50}?"
        r"\b(?:chat\s+only|chat-only|text\s+only|"
        r"text-only|chat|text\s+messages?)\b"
    )

    has_flexible_messaging_match = re.search(
        messaging_app_pattern,
        normalized_text,
    ) is not None

    if has_known_messaging_phrase or has_flexible_messaging_match:
        _add_signal(
            signals,
            "telegram_whatsapp_interview_only",
        )

    # 7. Unrealistic earnings or no-skill claims.
    unrealistic_pay_terms = (
        "no experience needed",
        "no experience required",
        "no skills required",
        "no skill required",
        "guaranteed income",
        "guaranteed earnings",
        "easy money",
        "high pay weekly",
        "earn daily",
        "earn money instantly",
    )

    if any(
        phrase in normalized_text for phrase in unrealistic_pay_terms
    ):
        _add_signal(signals, "guaranteed_high_pay_no_skills")

    return signals


def analyze_target_for_osint_signals(
    target_type: str,
    target_value: str,
) -> list[dict]:
    """
    Detect simple email-domain and website-TLD warning indicators.

    These checks are preliminary heuristics. A free email provider or
    unusual domain extension does not, by itself, prove fraud.
    """
    if not target_value or not target_value.strip():
        return []

    signals: list[dict] = []
    value = target_value.strip().lower()
    normalized_type = (target_type or "").strip().lower()

    # Email-domain check.
    if normalized_type == "email" or "@" in value:
        parts = value.rsplit("@", 1)

        if len(parts) == 2:
            domain = parts[1].split("/", 1)[0].split("?", 1)[0].strip()

            if domain in FREE_EMAIL_DOMAINS:
                _add_signal(
                    signals,
                    "suspicious_free_email_domain",
                )

    # Website/domain extension check.
    if normalized_type in {
        "website",
        "job url",
        "domain",
        "url",
        "company",
        "recruiter",
    } or "." in value:
        # Remove a path, query string and port before checking hostname.
        hostname = value.split("://")[-1]
        hostname = hostname.split("/", 1)[0]
        hostname = hostname.split("?", 1)[0]
        hostname = hostname.split("#", 1)[0]
        hostname = hostname.split(":", 1)[0].rstrip(".")

        if any(hostname.endswith(tld) for tld in SUSPICIOUS_TLDS):
            _add_signal(signals, "suspicious_domain_tld")

    return signals
