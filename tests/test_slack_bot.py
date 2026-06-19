"""Unit tests for slack_bot.py — Block Kit formatting and query routing.

These run fully offline: build_slack_blocks is pure, and run_query is tested
with an injected fake agent, so neither slack_bolt nor the embedding model is
imported.
"""

import json
from types import SimpleNamespace

import slack_bot


def _fake_result(**overrides):
    base = dict(
        label="VPN",
        urgency="HIGH",
        summary="VPN down",
        reply="Here is the answer.",
        top_k=["vpn_setup_windows"],
        scores=[0.71],
        security_flag=False,
        low_confidence=False,
        response_time_ms=1234.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_blocks_basic_structure():
    blocks = slack_bot.build_slack_blocks(_fake_result())
    assert isinstance(blocks, list) and blocks
    assert blocks[0]["type"] == "header"
    assert "section" in [b["type"] for b in blocks]
    assert blocks[-1]["type"] == "context"


def test_blocks_include_category_and_urgency():
    payload = json.dumps(slack_bot.build_slack_blocks(_fake_result(label="SECURITY")))
    assert "SECURITY" in payload
    assert "HIGH" in payload


def test_blocks_security_flag_adds_warning():
    payload = json.dumps(
        slack_bot.build_slack_blocks(_fake_result(security_flag=True))
    ).lower()
    assert "sicurezza" in payload


def test_blocks_low_confidence_adds_notice():
    payload = json.dumps(
        slack_bot.build_slack_blocks(_fake_result(low_confidence=True))
    ).lower()
    assert "confidenza bassa" in payload


def test_blocks_respect_section_char_limit():
    blocks = slack_bot.build_slack_blocks(_fake_result(reply="x" * 5000))
    for b in blocks:
        if b.get("type") == "section" and "text" in b:
            assert len(b["text"]["text"]) <= 3000


def test_blocks_within_total_block_limit():
    assert len(slack_bot.build_slack_blocks(_fake_result())) <= 50


def test_markdown_bold_converted_to_slack_mrkdwn():
    out = slack_bot._to_slack_mrkdwn("This is **bold** and more")
    assert "*bold*" in out
    assert "**" not in out


def test_markdown_heading_converted_to_bold():
    out = slack_bot._to_slack_mrkdwn("## Title\nbody")
    assert out.startswith("*Title*")


def test_run_query_uses_injected_agent_and_formats_result():
    fake_agent = SimpleNamespace(run=lambda text: _fake_result(summary="routed"))
    blocks = slack_bot.run_query("vpn down", agent=fake_agent)
    assert any("Here is the answer." in json.dumps(b) for b in blocks)
