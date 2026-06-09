"""Unit tests for reporting.py — verifies the three audit signals
(security_flag, low_confidence, response_time_ms) and file output.

Reports are written into pytest's tmp_path, so no real runs/ folder is
touched and tests leave no artefacts behind.
"""

import json
from pathlib import Path

import reporting


def _classification(label: str = "VPN") -> dict:
    return {"label": label, "urgency": "MEDIUM", "summary": "test summary"}


def _load(out: dict) -> dict:
    return json.loads(Path(out["report_json"]).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# security_flag — the security policy enforcer
# --------------------------------------------------------------------------
def test_security_flag_true_for_security_label(tmp_path):
    out = reporting.save_run_report(
        "msg", _classification("SECURITY"), "ctx", "reply", ["a"], [0.9],
        out_dir=str(tmp_path),
    )
    assert _load(out)["security_flag"] is True


def test_security_flag_false_for_other_labels(tmp_path):
    out = reporting.save_run_report(
        "msg", _classification("VPN"), "ctx", "reply", ["a"], [0.9],
        out_dir=str(tmp_path),
    )
    assert _load(out)["security_flag"] is False


# --------------------------------------------------------------------------
# low_confidence — the knowledge-gap tracker (threshold 0.3)
# --------------------------------------------------------------------------
def test_low_confidence_true_below_threshold(tmp_path):
    out = reporting.save_run_report(
        "m", _classification(), "c", "r", ["a"], [0.1], out_dir=str(tmp_path),
    )
    assert _load(out)["low_confidence"] is True


def test_low_confidence_false_above_threshold(tmp_path):
    out = reporting.save_run_report(
        "m", _classification(), "c", "r", ["a"], [0.8], out_dir=str(tmp_path),
    )
    assert _load(out)["low_confidence"] is False


def test_low_confidence_true_for_empty_scores(tmp_path):
    out = reporting.save_run_report(
        "m", _classification(), "c", "r", [], [], out_dir=str(tmp_path),
    )
    assert _load(out)["low_confidence"] is True


# --------------------------------------------------------------------------
# response_time_ms — the SLA tracker
# --------------------------------------------------------------------------
def test_response_time_recorded_in_meta(tmp_path):
    out = reporting.save_run_report(
        "m", _classification(), "c", "r", ["a"], [0.5],
        out_dir=str(tmp_path), response_time_ms=1234.5,
    )
    assert _load(out)["meta"]["response_time_ms"] == 1234.5


# --------------------------------------------------------------------------
# File output
# --------------------------------------------------------------------------
def test_both_files_created_and_reply_txt_matches(tmp_path):
    out = reporting.save_run_report(
        "m", _classification(), "c", "the reply text", ["a"], [0.5],
        out_dir=str(tmp_path),
    )
    assert Path(out["report_json"]).exists()
    assert Path(out["reply_txt"]).exists()
    assert Path(out["reply_txt"]).read_text(encoding="utf-8") == "the reply text"


def test_report_json_has_expected_structure(tmp_path):
    out = reporting.save_run_report(
        "m", _classification(), "c", "r", ["a"], [0.5], out_dir=str(tmp_path),
    )
    data = _load(out)
    for key in ("user_message", "classification", "context", "reply",
                "security_flag", "low_confidence", "meta"):
        assert key in data
    for key in ("timestamp", "top_k", "scores", "top_score", "response_time_ms"):
        assert key in data["meta"]
