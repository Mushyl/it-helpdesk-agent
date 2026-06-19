"""Unit tests for agent.py — orchestration wiring and audit signals.

Every pipeline stage is monkeypatched, so these tests run offline and
check that SupportAgent.run() calls the stages, computes the audit flags
and assembles a complete AgentResult.
"""

import pytest

# The agent module imports retrieval, which imports sentence-transformers.
# Skip cleanly if that heavy dependency is not installed in the environment.
pytest.importorskip("sentence_transformers")

import agent  # noqa: E402


def _patch_pipeline(monkeypatch, label="VPN", urgency="HIGH", scores=None):
    scores = [0.9] if scores is None else scores
    monkeypatch.setattr(
        agent, "classify_message",
        lambda m: {"label": label, "urgency": urgency, "summary": "s"},
    )
    monkeypatch.setattr(
        agent, "retrieve_context",
        lambda q, top_k=3: {"context": "ctx", "top_k": ["doc1"], "scores": scores},
    )
    monkeypatch.setattr(agent, "draft_reply", lambda **k: "the reply")
    monkeypatch.setattr(
        agent, "save_run_report",
        lambda **k: {"report_json": "run.json", "reply_txt": "reply.txt"},
    )


def test_support_agent_run_orchestrates_pipeline(monkeypatch):
    _patch_pipeline(monkeypatch)

    result = agent.SupportAgent(top_k=3).run("vpn is down")

    assert result.label == "VPN"
    assert result.urgency == "HIGH"
    assert result.reply == "the reply"
    assert result.top_k == ["doc1"]
    assert result.scores == [0.9]
    assert result.report_paths["report_json"] == "run.json"
    # Audit signals for a confident, non-security run.
    assert result.security_flag is False
    assert result.low_confidence is False
    assert isinstance(result.response_time_ms, float)
    assert result.response_time_ms >= 0
    # Ticket payloads are built for both ITSM systems.
    assert set(result.tickets) == {"jira", "servicenow"}
    assert result.tickets["jira"]["fields"]["summary"] == "s"


def test_support_agent_flags_security_and_low_confidence(monkeypatch):
    _patch_pipeline(monkeypatch, label="SECURITY", scores=[0.1])

    result = agent.SupportAgent().run("phishing!")

    assert result.security_flag is True
    assert result.low_confidence is True


def test_support_agent_default_top_k_comes_from_config(monkeypatch):
    _patch_pipeline(monkeypatch)
    import config

    assert agent.SupportAgent().top_k == config.TOP_K
