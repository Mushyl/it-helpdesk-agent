import logging

from api_client import chat
from prompts import build_reply_prompt

logger = logging.getLogger(__name__)

_FALLBACK_REPLY = (
    "I don't have enough information to answer this request. "
    "Please contact the IT Help Desk directly."
)


def draft_reply(
    user_message: str,
    label: str,
    urgency: str,
    summary: str,
    context: str,
) -> str:
    """
    Generate a grounded IT support reply using the retrieved RAG context.

    The reply is constrained by the guardrails defined in
    prompts.build_reply_prompt(): Claude may only use the provided
    context and must not fabricate URLs, ticket numbers, or policies.

    Args:
        user_message: The original employee message.
        label:        Classification label from classifier.py.
        urgency:      Urgency level from classifier.py.
        summary:      Short summary from classifier.py.
        context:      Relevant knowledge base passages from retrieval.py.

    Returns:
        The drafted reply as a plain string. On API failure a safe
        fallback message is returned instead of raising.
    """
    logger.info(
        "Drafting reply | label=%s | urgency=%s | context_chars=%d",
        label,
        urgency,
        len(context),
    )

    prompt = build_reply_prompt(user_message, label, urgency, summary, context)
    messages = [{"role": "user", "content": prompt}]

    try:
        reply = chat(messages, temperature=0.2)
        logger.info("Reply drafted successfully — %d characters.", len(reply))
        return reply.strip()

    except Exception as exc:
        logger.error(
            "Reply generation failed: %s — returning safe fallback message.",
            exc,
        )
        return _FALLBACK_REPLY
