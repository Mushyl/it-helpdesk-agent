import logging
import os

import anthropic

import config

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    # Return a shared Anthropic client, creating it on first call.
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY not found. "
                "Make sure key.env exists in the project root and contains the key."
            )
        _client = anthropic.Anthropic(
            api_key=api_key,
            timeout=config.LLM_TIMEOUT_SECONDS,
            max_retries=config.LLM_MAX_RETRIES,
        )
        logger.debug("Anthropic client initialised successfully.")
    return _client


def chat(
    messages: list[dict],
    model: str = config.ANTHROPIC_MODEL,
    max_tokens: int = 1024,
    temperature: float = 0.2,
) -> str:
    """
    Send a list of messages to Claude and return the text response.

    Args:
        messages:    List of dicts in Anthropic format:
                     [{"role": "user", "content": "..."}]
        model:       Claude model identifier (default: config.ANTHROPIC_MODEL).
        max_tokens:  Maximum tokens in the response.
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative).

    Returns:
        The assistant's reply as a plain string.

    Raises:
        anthropic.APIError: If the API call fails after the configured retries.
        EnvironmentError:   If the API key is missing.
    """
    client = _get_client()

    logger.debug(
        "Calling Claude | model=%s | messages=%d | temperature=%s",
        model,
        len(messages),
        temperature,
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=messages,
    )

    reply = response.content[0].text
    logger.debug("Claude replied with %d characters.", len(reply))
    return reply
