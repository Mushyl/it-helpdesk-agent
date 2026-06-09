"""Unit test for agent.py — verifies the orchestration wiring.

Every pipeline stage is monkeypatched, so this test runs offline and
checks only that SupportAgent.run() calls the stages and assembles a
complete AgentResult.
"""

import pytest

# The agent module imports retrieval, which imports sentence-transformers.
# Skip cleanly if that heavy dependency is not installed in the environment.
pytest.importorskip("sentence_transformers")

import agent  # noqa: E402


def test_support_agent_run_orchestrates_pipeline(monkeypatch):
    monkeypatch.setattr(
        agent, "classify_message",
        lambda m: {"label": "VPN", "urgency": "HIGH", "summary": "s"},
    )
    monkeypatch.setattr(
        agent, "retrieve_context",
        lambda q, top_k=3: {"context": "ctx", "top_k": ["doc1"], "scores": [0.9]},
    )
    monkeypatch.setattr(agent, "draft_reply", lambda **k: "the reply")
    monkeypatch.setattr(
        agent, "save_run_report",
        lambda **k: {"report_json": "run.json", "reply_txt": "reply.txt"},
    )

    result = agent.SupportAgent(top_k=3).run("vpn is down")

    assert result.label == "VPN"
    assert result.urgency == "HIGH"
    assert result.reply == "the reply"
    assert result.top_k == ["doc1"]
    assert result.scores == [0.9]
    assert result.report_paths["report_json"] == "run.json"
