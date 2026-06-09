"""Unit tests for classifier.py — no API calls, no model downloads.

The Anthropic call is replaced with a monkeypatched stub, so these tests
run offline, deterministically, and in milliseconds.
"""

import json

import pytest

import classifier


# --------------------------------------------------------------------------
# _extract_json_from_text — the defensive JSON parser
# --------------------------------------------------------------------------
def test_extract_json_plain():
    assert classifier._extract_json_from_text('{"label": "VPN"}') == {"label": "VPN"}


def test_extract_json_with_markdown_fences():
    raw = '```json\n{"label": "VPN", "urgency": "HIGH"}\n```'
    assert classifier._extract_json_from_text(raw)["label"] == "VPN"


def test_extract_json_embedded_in_prose():
    raw = 'Sure! Here is the JSON:\n{"label": "PASSWORD"}\nHope it helps.'
    assert classifier._extract_json_from_text(raw)["label"] == "PASSWORD"


def test_extract_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        classifier._extract_json_from_text("there is no json here at all")


# --------------------------------------------------------------------------
# _validate_classification — normalisation & safe defaults
# --------------------------------------------------------------------------
def test_validate_normalises_to_uppercase_and_strips():
    out = classifier._validate_classification(
        {"label": "vpn", "urgency": "high", "summary": "  spaced  "}
    )
    assert out["label"] == "VPN"
    assert out["urgency"] == "HIGH"
    assert out["summary"] == "spaced"


def test_validate_unknown_label_defaults_to_general():
    out = classifier._validate_classification({"label": "BANANA", "urgency": "LOW"})
    assert out["label"] == "GENERAL"


def test_validate_unknown_urgency_defaults_to_low():
    out = classifier._validate_classification({"label": "VPN", "urgency": "SUPER"})
    assert out["urgency"] == "LOW"


# --------------------------------------------------------------------------
# _keyword_fallback — offline classifier (English + Italian)
# --------------------------------------------------------------------------
def test_keyword_fallback_english_vpn():
    assert classifier._keyword_fallback("I cannot connect to the vpn")["label"] == "VPN"


def test_keyword_fallback_italian_security_regression():
    """Regression: an Italian phishing message must map to SECURITY/HIGH
    even when the API is down (previously returned GENERAL/LOW)."""
    out = classifier._keyword_fallback("Ho cliccato su un link sospetto, e' una truffa?")
    assert out["label"] == "SECURITY"
    assert out["urgency"] == "HIGH"


def test_keyword_fallback_italian_hardware():
    assert classifier._keyword_fallback("Il mio portatile non si accende")["label"] == "HARDWARE"


def test_keyword_fallback_unknown_returns_general_low():
    out = classifier._keyword_fallback("xyzzy qwerty foobar")
    assert out["label"] == "GENERAL"
    assert out["urgency"] == "LOW"


# --------------------------------------------------------------------------
# classify_message — orchestration with a mocked API
# --------------------------------------------------------------------------
def test_classify_message_parses_valid_api_response(monkeypatch):
    monkeypatch.setattr(
        classifier, "chat",
        lambda *a, **k: '{"label":"VPN","urgency":"HIGH","summary":"x"}',
    )
    out = classifier.classify_message("vpn is down")
    assert out["label"] == "VPN"
    assert out["urgency"] == "HIGH"


def test_classify_message_falls_back_on_api_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("API overloaded")

    monkeypatch.setattr(classifier, "chat", boom)
    out = classifier.classify_message("I cannot connect to the vpn")
    # Graceful degradation: keyword fallback kicks in, never crashes.
    assert out["label"] == "VPN"
    assert set(out.keys()) == {"label", "urgency", "summary"}
