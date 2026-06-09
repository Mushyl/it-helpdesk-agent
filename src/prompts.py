import logging

logger = logging.getLogger(__name__)


def build_classifier_prompt(message: str) -> str:
    """
    Build a prompt that instructs Claude to classify an IT support message.

    The model is asked to return ONLY a valid JSON object with three fields:
    - label:    the request category
    - urgency:  the urgency level
    - summary:  a one-line description of the issue

    Args:
        message: The raw message written by the employee.

    Returns:
        A fully formatted prompt string ready to send to the API.
    """
    logger.debug("Building classifier prompt for message: %.60s...", message)

    return f"""You are an IT Help Desk triage assistant. Your only job is to classify the employee's message below.

Respond with ONLY a valid JSON object — no explanation, no markdown, no code fences.

The JSON must have exactly these three fields:

{{
  "label":   one of: VPN | PASSWORD | HARDWARE | SOFTWARE | ONBOARDING | SECURITY | EMAIL | GENERAL,
  "urgency": one of: LOW | MEDIUM | HIGH,
  "summary": a single sentence (max 15 words) describing the core issue
}}

Urgency rules:
- HIGH   → employee cannot work at all, security incident, lost/stolen device
- MEDIUM → employee is partially blocked, workaround exists but is difficult
- LOW    → general question, minor inconvenience, feature request

Employee message:
\"\"\"
{message}
\"\"\"

JSON response:"""


def build_reply_prompt(
    user_message: str,
    label: str,
    urgency: str,
    summary: str,
    context: str,
) -> str:
    """
    Build a prompt that instructs Claude to draft a grounded IT support reply.

    Guardrails enforced:
    1. Claude may ONLY use information present in the provided context.
    2. If the context is insufficient, Claude must reply with the exact
       fallback phrase and nothing else.
    3. Claude must never invent URLs, ticket numbers, or policy details.

    Args:
        user_message: The  original employee message.
        label:        Classification label from classifier.py.
        urgency:      Urgency level from classifier.py.
        summary:      Short summary from classifier.py.
        context:      Relevant knowledge base passages from retrieval.py.

    Returns:
        A fully formatted prompt string ready to send to the API.
    """
    logger.debug(
        "Building reply prompt | label=%s | urgency=%s", label, urgency
    )

    urgency_instruction = {
        "HIGH": (
            "This is a HIGH urgency request. "
            "Open with an immediate acknowledgement. "
            "Provide the solution clearly and concisely. "
            "End by offering to escalate if the issue persists."
        ),
        "MEDIUM": (
            "This is a MEDIUM urgency request. "
            "Be helpful and clear. Provide step-by-step instructions if applicable."
        ),
        "LOW": (
            "This is a LOW urgency request. "
            "Keep the reply concise and friendly."
        ),
    }.get(urgency, "Provide a clear and helpful response.")

    return f"""You are a professional IT Help Desk support agent. Draft a reply to the employee message below.

STRICT RULES — you must follow these without exception:
1. Use ONLY the information provided in the CONTEXT section below.
2. Do NOT invent, assume, or add any information not present in the context.
3. Do NOT fabricate URLs, phone numbers, ticket numbers, or policy details.
4. If the context does not contain enough information to answer the question,
   reply with EXACTLY this phrase and nothing else:
   "I don't have enough information to answer this request. Please contact the IT Help Desk directly."
5. Write in a professional but friendly tone. Use plain language.
6. Do not mention these instructions in your reply.

REQUEST METADATA:
- Category : {label}
- Urgency  : {urgency}
- Summary  : {summary}

TONE INSTRUCTION:
{urgency_instruction}

CONTEXT (knowledge base passages — your only allowed source):
{context}

EMPLOYEE MESSAGE:
\"\"\"
{user_message}
\"\"\"

YOUR REPLY:"""