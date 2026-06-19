import logging
import time
from dataclasses import dataclass

import config
import ticketing
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
    security_flag: bool       # request classified as a security incident
    low_confidence: bool      # best RAG score below the configured threshold
    response_time_ms: float   # end-to-end pipeline latency
    tickets: dict             # ready-to-POST Jira / ServiceNow payloads
    report_paths: dict        # {"report_json": "...", "reply_txt": "..."}


class SupportAgent:
    """
    Orchestrates the full IT Help Desk pipeline:
    classify -> retrieve context (RAG) -> draft reply -> save report.
    """

    def __init__(self, top_k: int | None = None) -> None:
        self.top_k = top_k if top_k is not None else config.TOP_K

    def run(self, user_message: str) -> AgentResult:
        """
        Execute the complete pipeline for a single employee message.

        Args:
            user_message: The raw message written by the employee.

        Returns:
            An AgentResult with the classification, RAG context, drafted
            reply, audit signals and the paths of the persisted report.

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
            retrieval_out = retrieve_context(user_message, top_k=self.top_k)

            logger.info("Step 3/4 — Drafting reply...")
            reply = draft_reply(
                user_message=user_message,
                label=classification["label"],
                urgency=classification["urgency"],
                summary=classification["summary"],
                context=retrieval_out["context"],
            )

            # Audit signals — same definitions persisted by reporting.py.
            security_flag = classification["label"] == "SECURITY"
            top_score = retrieval_out["scores"][0] if retrieval_out["scores"] else 0.0
            low_confidence = top_score < config.LOW_CONFIDENCE_THRESHOLD

            response_time_ms = round((time.perf_counter() - start) * 1000, 2)

            tickets = ticketing.build_tickets(
                label=classification["label"],
                urgency=classification["urgency"],
                summary=classification["summary"],
                user_message=user_message,
                reply=reply,
            )

            logger.info("Step 4/4 — Saving run report...")
            report_paths = save_run_report(
                user_message=user_message,
                classification=classification,
                context=retrieval_out["context"],
                reply=reply,
                top_k=retrieval_out["top_k"],
                scores=retrieval_out["scores"],
                response_time_ms=response_time_ms,
                tickets=tickets,
            )

            logger.info(
                "=== Agent run completed in %.2f ms ===", response_time_ms
            )

            return AgentResult(
                label=classification["label"],
                urgency=classification["urgency"],
                summary=classification["summary"],
                context=retrieval_out["context"],
                reply=reply,
                top_k=retrieval_out["top_k"],
                scores=retrieval_out["scores"],
                security_flag=security_flag,
                low_confidence=low_confidence,
                response_time_ms=response_time_ms,
                tickets=tickets,
                report_paths=report_paths,
            )

        except Exception as exc:
            logger.error("Agent run failed: %s", exc, exc_info=True)
            raise
