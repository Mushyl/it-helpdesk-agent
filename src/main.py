import logging
import sys

from agent import SupportAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger("main")

_BANNER = """
============================================================
   IT HELP DESK SUPPORT AGENT  (RAG + Claude)
   Type your IT request below.
   Finish your message with an EMPTY line to send.
   Send an empty message (or Ctrl+C) to quit.
============================================================
"""


def _read_message() -> str:
    """
    Read a possibly multi-line message from stdin.

    Lines are collected until the user enters an empty line,
    which acts as the "send" signal.

    Returns:
        The full message with surrounding whitespace stripped.
    """
    print("\nYour IT request (empty line to send):")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _print_result(result) -> None:
    """Print the agent result to stdout, clearly separated from logs."""
    print("\n" + "=" * 60)
    print(f"  CATEGORY : {result.label}")
    print(f"  URGENCY  : {result.urgency}")
    print(f"  SUMMARY  : {result.summary}")
    print(f"  TIME     : {result.response_time_ms:.0f} ms")
    if result.security_flag:
        print("  FLAG     : SECURITY incident — escalation recommended")
    if result.low_confidence:
        print("  FLAG     : LOW CONFIDENCE — knowledge base may lack coverage")
    print("-" * 60)
    print("  REPLY:")
    print("-" * 60)
    print(result.reply)
    print("=" * 60)
    print(f"  Report JSON : {result.report_paths['report_json']}")
    print(f"  Reply  TXT  : {result.report_paths['reply_txt']}")
    print("=" * 60 + "\n")


def main() -> None:
    """Interactive entry point. Serves requests until the user quits."""
    print(_BANNER)
    agent = SupportAgent()

    while True:
        message = _read_message()

        if not message:
            print("No message entered. Goodbye!")
            return

        try:
            result = agent.run(message)
        except Exception as exc:
            logger.error("The request could not be processed: %s", exc)
            print(
                "\n[ERROR] Sorry, the request could not be processed. "
                "Please check the logs above and try again.\n"
            )
            continue

        _print_result(result)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
        sys.exit(0)
