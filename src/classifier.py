import json
import logging
import re

from api_client import chat
from prompts import build_classifier_prompt

logger = logging.getLogger(__name__)

VALID_LABELS = {
    "VPN", "PASSWORD", "HARDWARE", "SOFTWARE",
    "ONBOARDING", "SECURITY", "EMAIL", "GENERAL",
}
VALID_URGENCIES = {"LOW", "MEDIUM", "HIGH"}

_KEYWORD_RULES: list[tuple[str, str, str]] = [
    # SECURITY first — highest-priority signals must win before generic words.
    ("phishing", "SECURITY", "HIGH"),
    ("malware", "SECURITY", "HIGH"),
    ("virus", "SECURITY", "HIGH"),
    ("stolen", "SECURITY", "HIGH"),
    ("rubato", "SECURITY", "HIGH"),
    ("rubata", "SECURITY", "HIGH"),
    ("sospetto", "SECURITY", "HIGH"),
    ("sospetta", "SECURITY", "HIGH"),
    ("link strano", "SECURITY", "HIGH"),
    # English keywords
    ("vpn", "VPN", "MEDIUM"),
    ("password", "PASSWORD", "MEDIUM"),
    ("reset", "PASSWORD", "MEDIUM"),
    ("locked", "PASSWORD", "HIGH"),
    ("laptop", "HARDWARE", "MEDIUM"),
    ("screen", "HARDWARE", "MEDIUM"),
    ("monitor", "HARDWARE", "LOW"),
    ("broken", "HARDWARE", "HIGH"),
    ("install", "SOFTWARE", "LOW"),
    ("license", "SOFTWARE", "LOW"),
    ("slack", "SOFTWARE", "LOW"),
    ("zoom", "SOFTWARE", "LOW"),
    ("onboard", "ONBOARDING", "LOW"),
    ("new employee", "ONBOARDING", "LOW"),
    ("first day", "ONBOARDING", "MEDIUM"),
    ("email", "EMAIL", "LOW"),
    ("gmail", "EMAIL", "LOW"),
    ("outlook", "EMAIL", "LOW"),
    # Italian keywords
    ("portatile", "HARDWARE", "MEDIUM"),
    ("schermo", "HARDWARE", "MEDIUM"),
    ("rotto", "HARDWARE", "HIGH"),
    ("rotta", "HARDWARE", "HIGH"),
    ("guasto", "HARDWARE", "HIGH"),
    ("guasta", "HARDWARE", "HIGH"),
    ("bloccato", "PASSWORD", "HIGH"),
    ("bloccata", "PASSWORD", "HIGH"),
    ("reimposta", "PASSWORD", "MEDIUM"),
    ("ripristina", "PASSWORD", "MEDIUM"),
    ("installare", "SOFTWARE", "LOW"),
    ("installazione", "SOFTWARE", "LOW"),
    ("licenza", "SOFTWARE", "LOW"),
    ("nuovo dipendente", "ONBOARDING", "LOW"),
    ("primo giorno", "ONBOARDING", "MEDIUM"),
    ("posta", "EMAIL", "LOW"),
]


def _extract_json_from_text(text: str) -> dict:
    """
    Attempt to parse a JSON object from a string that may contain
    extra text, markdown fences, or whitespace around the JSON.

    Raises:
        json.JSONDecodeError: If no valid JSON object can be extracted.
    """
    text = text.strip()

    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
    if match:
        return json.loads(match.group())

    raise json.JSONDecodeError("No JSON object found in response", text, 0)


def _validate_classification(data: dict) -> dict:
    """
    Validate and normalise the classification dict returned by Claude.
    Unknown labels or urgencies are replaced with safe defaults.

    Args:
        data: Raw dict parsed from Claude's JSON response.

    Returns:
        A clean dict with guaranteed label, urgency, and summary keys.
    """
    label = str(data.get("label", "GENERAL")).upper().strip()
    urgency = str(data.get("urgency", "LOW")).upper().strip()
    summary = str(data.get("summary", "No summary provided.")).strip()

    if label not in VALID_LABELS:
        logger.warning("Unknown label '%s' — defaulting to GENERAL.", label)
        label = "GENERAL"

    if urgency not in VALID_URGENCIES:
        logger.warning("Unknown urgency '%s' — defaulting to LOW.", urgency)
        urgency = "LOW"

    return {"label": label, "urgency": urgency, "summary": summary}


def _keyword_fallback(message: str) -> dict:
    """
    Rule-based classifier used when the Claude API call fails or returns
    unparseable output. Scans the message for known IT keywords.

    Args:
        message: The original employee message (lowercased internally).

    Returns:
        A classification dict with label, urgency, and summary.
    """
    logger.warning("Using keyword fallback classifier.")
    lower = message.lower()

    for keyword, label, urgency in _KEYWORD_RULES:
        if keyword in lower:
            return {
                "label": label,
                "urgency": urgency,
                "summary": f"Keyword match: '{keyword}' detected in message.",
            }

    return {
        "label": "GENERAL",
        "urgency": "LOW",
        "summary": "Unable to classify automatically. Manual review recommended.",
    }


def classify_message(message: str) -> dict:
    """
    Classify an employee IT support message using Claude.

    Attempts to call the Anthropic API and parse the JSON response.
    Falls back to keyword-based rules if the API call fails or the
    response cannot be parsed as valid JSON.

    Args:
        message: The raw message written by the employee.

    Returns:
        A dict with three guaranteed keys:
        {
            "label":   str,  # e.g. "VPN"
            "urgency": str,  # e.g. "HIGH"
            "summary": str,  # e.g. "Employee cannot connect to VPN."
        }
    """
    logger.info("Classifying message: %.60s...", message)

    prompt = build_classifier_prompt(message)
    messages = [{"role": "user", "content": prompt}]

    try:
        raw_response = chat(messages, temperature=0.0)
        logger.debug("Raw classifier response: %s", raw_response)

        data = _extract_json_from_text(raw_response)
        result = _validate_classification(data)

        logger.info(
            "Classification result — label=%s | urgency=%s",
            result["label"],
            result["urgency"],
        )
        return result

    except json.JSONDecodeError as exc:
        logger.error("JSON parsing failed: %s — switching to keyword fallback.", exc)
        return _keyword_fallback(message)

    except Exception as exc:
        logger.error("Classifier API call failed: %s — switching to keyword fallback.", exc)
        return _keyword_fallback(message)