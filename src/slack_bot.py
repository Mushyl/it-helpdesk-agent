"""
Slack bot front-end for the IT Help Desk agent.

A `/helpdesk <question>` slash command routes the message through the same
SupportAgent pipeline used by the web UI and CLI, then posts a formatted
Block Kit reply back to Slack.

Design:
- The message-formatting logic (`build_slack_blocks`, `_to_slack_mrkdwn`) is
  pure and unit-tested offline.
- The Slack wiring (slack_bolt App + Socket Mode) is created lazily inside
  `main()`, so importing this module for tests pulls in neither slack_bolt
  nor the heavy embedding stack.

Run it with:  python src/slack_bot.py   (needs SLACK_BOT_TOKEN + SLACK_APP_TOKEN)
"""

import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

logger = logging.getLogger(__name__)

# Slack section blocks accept at most 3000 characters of text.
_SECTION_LIMIT = 3000
_URGENCY_EMOJI = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟢"}

_agent = None  # lazily-built SupportAgent singleton


def _to_slack_mrkdwn(text: str) -> str:
    """
    Convert the small subset of Markdown that Claude emits into Slack mrkdwn.

    Slack uses *single asterisks* for bold and has no heading syntax, whereas
    Claude tends to use **double asterisks** and `#` headings.
    """
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)              # **bold** -> *bold*
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)  # # head -> *head*
    return text


def build_slack_blocks(result) -> list[dict]:
    """
    Build a Slack Block Kit message from an AgentResult.

    Pure function (no Slack SDK needed), so it is fully unit-testable.

    Args:
        result: An object exposing label, urgency, summary, reply, top_k,
                security_flag, low_confidence and response_time_ms.

    Returns:
        A list of Block Kit blocks, respecting Slack's size limits.
    """
    reply = _to_slack_mrkdwn(result.reply)
    if len(reply) > _SECTION_LIMIT:
        reply = reply[: _SECTION_LIMIT - 1] + "…"

    urgency = f"{_URGENCY_EMOJI.get(result.urgency, '')} {result.urgency}".strip()

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🛠️ IT Help Desk", "emoji": True},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Categoria:*\n{result.label}"},
                {"type": "mrkdwn", "text": f"*Urgenza:*\n{urgency}"},
            ],
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": reply}},
    ]

    if result.security_flag:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":rotating_light: *Incidente di sicurezza* — segnalato per escalation.",
                },
            }
        )
    if result.low_confidence:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":warning: *Confidenza bassa* — verifica manuale consigliata.",
                },
            }
        )

    sources = ", ".join(result.top_k) if result.top_k else "nessuna"
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Generata in {result.response_time_ms / 1000:.1f}s · fonti: {sources}",
                }
            ],
        }
    )
    return blocks


def _get_agent():
    """Build the SupportAgent once (lazy import keeps module load light)."""
    global _agent
    if _agent is None:
        from agent import SupportAgent

        _agent = SupportAgent()
    return _agent


def run_query(text: str, agent=None) -> list[dict]:
    """Run a question through the agent and return Slack blocks.

    Args:
        text:  The employee question.
        agent: Optional agent instance (injected in tests); defaults to the
               shared singleton.
    """
    agent = agent or _get_agent()
    result = agent.run(text)
    return build_slack_blocks(result)


def main() -> None:
    """Start the Slack bot in Socket Mode (blocks until interrupted)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    if not config.SLACK_BOT_TOKEN or not config.SLACK_APP_TOKEN:
        raise SystemExit(
            "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in key.env to run "
            "the Slack bot. See key.env.example."
        )

    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = App(token=config.SLACK_BOT_TOKEN)

    @app.command("/helpdesk")
    def handle_helpdesk(ack, command, respond):  # pragma: no cover - needs Slack
        ack()
        text = (command.get("text") or "").strip()
        if not text:
            respond(
                "Scrivi la tua richiesta, es. "
                "`/helpdesk non riesco a connettermi alla VPN`"
            )
            return
        try:
            blocks = run_query(text)
            respond(blocks=blocks, response_type="in_channel")
        except Exception as exc:
            logger.error("Slack query failed: %s", exc, exc_info=True)
            respond("Si è verificato un errore nell'elaborazione della richiesta.")

    logger.info("Starting Slack bot (Socket Mode)...")
    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()


if __name__ == "__main__":
    main()
