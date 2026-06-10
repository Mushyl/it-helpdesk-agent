import json
import logging
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def save_run_report(
    user_message: str,
    classification: dict,
    context: str,
    reply: str,
    top_k: list[str],
    scores: list[float],
    out_dir: str = "runs",
    response_time_ms: float | None = None,
) -> dict:
    """
    Persist a full record of a single agent run to disk for auditing.

    Two artefacts are written into the runs/ directory:
    - run_TIMESTAMP.json : the complete structured report
    - reply_TIMESTAMP.txt : the reply text only (for quick reading)

    The JSON report includes three audit signals:
    - security_flag    : True when the request was classified as SECURITY
    - low_confidence   : True when the best RAG score is below 0.3
                         (the knowledge base likely has a coverage gap)
    - response_time_ms : end-to-end pipeline latency, when provided

    Args:
        user_message:     The original employee message.
        classification:   The dict returned by classifier.classify_message().
        context:          The formatted RAG context string.
        reply:            The drafted reply text.
        top_k:            IDs of the retrieved KB documents.
        scores:           Similarity scores for the retrieved documents.
        out_dir:          Directory name, resolved relative to src/.
        response_time_ms: Optional end-to-end pipeline latency in milliseconds.

    Returns:
        A dict with the paths of the two written files:
        {"report_json": "...", "reply_txt": "..."}
    """
    runs_dir = Path(__file__).parent / out_dir
    runs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    label = str(classification.get("label", "GENERAL")).upper()
    security_flag = label == "SECURITY"
    top_score = scores[0] if scores else 0.0
    low_confidence = top_score < config.LOW_CONFIDENCE_THRESHOLD

    if security_flag:
        logger.warning(
            "SECURITY request detected — security_flag set on report %s.",
            timestamp,
        )
    if low_confidence:
        logger.warning(
            "Low retrieval confidence (top score %.4f < %.2f) — "
            "possible knowledge base gap for: %.60s...",
            top_score,
            config.LOW_CONFIDENCE_THRESHOLD,
            user_message,
        )

    report = {
        "user_message": user_message,
        "classification": classification,
        "context": context,
        "reply": reply,
        "security_flag": security_flag,
        "low_confidence": low_confidence,
        "meta": {
            "timestamp": timestamp,
            "top_k": top_k,
            "scores": scores,
            "top_score": round(float(top_score), 4),
            "response_time_ms": response_time_ms,
        },
    }

    report_json = runs_dir / f"run_{timestamp}.json"
    reply_txt = runs_dir / f"reply_{timestamp}.txt"

    with open(report_json, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    with open(reply_txt, "w", encoding="utf-8") as fh:
        fh.write(reply)

    logger.info(
        "Run report saved | json=%s | txt=%s",
        report_json.name,
        reply_txt.name,
    )

    return {
        "report_json": str(report_json),
        "reply_txt": str(reply_txt),
    }
