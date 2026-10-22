from app.services.automated_detector import (
    analyze_text_for_scam_signals,
    analyze_target_for_osint_signals,
)


def test_detector_identifies_registration_fee():
    signals = analyze_text_for_scam_signals(
        "Please send a  registration fee to secure your position."
    )
    assert any(s["signal_type"] == "upfront_registration_fee" for s in signals)


def test_detector_identifies_telegram_interview():
    signals = analyze_text_for_scam_signals(
        "Your interview will be conducted via Telegram chat only with our HR manager."
    )
    assert any(s["signal_type"] == "telegram_whatsapp_interview_only" for s in signals)


def test_detector_identifies_free_email():
    signals = analyze_target_for_osint_signals("email", "recruiter@gmail.com")
    assert any(s["signal_type"] == "suspicious_free_email_domain" for s in signals)


def test_detector_identifies_suspicious_tld():
    signals = analyze_target_for_osint_signals("website", "https://hiring-secure-portal.xyz")
    assert any(s["signal_type"] == "suspicious_domain_tld" for s in signals)


def test_detector_returns_empty_for_clean_text():
    signals = analyze_text_for_scam_signals(
        "We are looking for a senior software engineer with 5 years of experience."
    )
    assert len(signals) == 0