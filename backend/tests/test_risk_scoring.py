
from app.services.risk_scoring import calculate_risk
from app.engines.risk_rules import (
    build_risk_signal,
    normalize_evidence_source,
)


def test_insufficient_evidence_returns_unknown():
    result = calculate_risk(
        [35],
        has_sufficient_evidence=False,
    )

    assert result.score is None
    assert result.risk_level == "UNKNOWN"


def test_no_signals_returns_unknown():
    result = calculate_risk(
        [],
        has_sufficient_evidence=True,
    )

    assert result.score is None
    assert result.risk_level == "UNKNOWN"


def test_low_risk_score():
    result = calculate_risk(
        [10],
        has_sufficient_evidence=True,
    )

    assert result.score == 10
    assert result.risk_level == "LOW"


def test_suspicious_risk_score():
    result = calculate_risk(
        [40],
        has_sufficient_evidence=True,
    )

    assert result.score == 40
    assert result.risk_level == "SUSPICIOUS"


def test_high_risk_score():
    result = calculate_risk(
        [70],
        has_sufficient_evidence=True,
    )

    assert result.score == 70
    assert result.risk_level == "HIGH RISK"


def test_score_is_capped_at_100():
    result = calculate_risk(
        [70, 50],
        has_sufficient_evidence=True,
    )

    assert result.score == 100
    assert result.risk_level == "HIGH RISK"


def test_generated_risk_signal_uses_valid_default_source():
    signal = build_risk_signal("upfront_registration_fee")

    assert signal is not None
    assert signal["source"] == "automated_detection"
    assert normalize_evidence_source(signal["source"]) == "automated_detection"


def test_invalid_evidence_source_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="Unsupported evidence source"):
        normalize_evidence_source("system")
