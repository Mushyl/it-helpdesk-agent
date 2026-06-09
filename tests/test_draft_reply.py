"""Unit tests for draft_reply.py — the grounded reply generator.

The Anthropic call is monkeypatched, so we test the wrapper logic
(stripping, graceful fallback) without any network access.
"""

import draft_reply


def test_draft_reply_returns_stripped_text(monkeypatch):
    monkeypatch.setattr(draft_reply, "chat", lambda *a, **k: "  Hello world  ")
    out = draft_reply.draft_reply("msg", "VPN", "LOW", "summary", "context")
    assert out == "Hello world"


def test_draft_reply_falls_back_on_api_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("overloaded")

    monkeypatch.setattr(draft_reply, "chat", boom)
    out = draft_reply.draft_reply("msg", "VPN", "LOW", "summary", "context")
    # Safe fallback instead of a crash.
    assert "contact the IT Help Desk" in out
