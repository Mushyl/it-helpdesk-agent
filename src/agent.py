import logging
import time
from dataclasses import dataclass

from classifier import classify_message
from draft_reply import draft_reply
from reporting import save_run_report
from retrieval import retrieve_context

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Structured outcome of a single end-to-end agent run."""

    label: str
    urgency: str
    summary: str
    context: str
    reply: str
    top_k: list[str]
    scores: list[float]
    report_paths: dict  # {"report_json": "...", "reply_txt": "..."}


class SupportAgent:
    """
    Orchestrates the full IT Help Desk pipeline:
    classify -> retrieve context (RAG) -> draft reply -> save report.
    """

    def __init__(self, top_k: int = 3) -> None:
        self.top_k = top_k

    def run(self, user_message: str) -> AgentResult:
        """
        Execute the complete pipeline for a single employee message.

        Args:
            user_message: The raw message written by the employee.

        Returns:
            An AgentResult with the classification, RAG context,
            drafted reply, and the paths of the persisted report.

        Raises:
            Exception: Any unrecoverable pipeline error is logged and
                       re-raised so the caller can fail loudly rather
                       than acting on a partial result.
        """
        start = time.perf_counter()
        logger.info("=== Agent run started ===")

        try:
            logger.info("Step 1/4 — Classifying message...")
            classification = classify_message(user_message)

            logger.info("Step 2/4 — Retrieving context (top_k=%d)...", self.top_k)
            retrieval = retrieve_context(user_message, top_k=self.top_k)

            logger.info("Step 3/4 — Drafting reply...")
            reply = draft_reply(
                user_message=user_message,
                label=classification["label"],
                urgency=classification["urgency"],
                summary=classification["summary"],
                context=retrieval["context"],
            )

            response_time_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info("Step 4/4 — Saving run report...")
            report_paths = save_run_report(
                user_message=user_message,
                classification=classification,
                context=retrieval["context"],
                reply=reply,
                top_k=retrieval["top_k"],
                scores=retrieval["scores"],
                response_time_ms=response_time_ms,
            )

            logger.info(
                "=== Agent run completed in %.2f ms ===", response_time_ms
            )

            return AgentResult(
                label=classification["label"],
                urgency=classification["urgency"],
                summary=classification["summary"],
                context=retrieval["context"],
                reply=reply,
                top_k=retrieval["top_k"],
                scores=retrieval["scores"],
                report_paths=report_paths,
            )

        except Exception as exc:
            logger.error("Agent run failed: %s", exc, exc_info=True)
            raise
