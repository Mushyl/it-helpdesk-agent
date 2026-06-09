import json
import logging
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_KB_PATH = Path(__file__).parent / "kb" / "knowledge.json"

_model: SentenceTransformer | None = None
_kb_cache: list[dict] | None = None
_kb_embeddings: np.ndarray | None = None


def _get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it (Singleton pattern)."""
    global _model
    if _model is None:
        logger.info("Loading embedding model (first call — may take a few seconds)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded successfully.")
    return _model


def load_kb() -> list[dict]:
    """
    Read the knowledge base from kb/knowledge.json.

    Returns:
        A list of dicts, each with 'id' and 'text' keys.

    Raises:
        FileNotFoundError: If knowledge.json does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    global _kb_cache
    if _kb_cache is not None:
        logger.debug("Returning cached knowledge base (%d docs).", len(_kb_cache))
        return _kb_cache

    logger.info("Loading knowledge base from %s", _KB_PATH)

    if not _KB_PATH.exists():
        raise FileNotFoundError(
            f"Knowledge base not found at {_KB_PATH}. "
            "Make sure kb/knowledge.json exists inside the src/ folder."
        )

    with open(_KB_PATH, encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in knowledge base: %s", exc)
            raise

    if not isinstance(data, list) or not data:
        raise ValueError("knowledge.json must be a non-empty JSON array.")

    _kb_cache = data
    logger.info("Knowledge base loaded: %d documents.", len(data))
    return data


def _get_kb_embeddings() -> np.ndarray:
    """
    Compute and cache the embedding vectors for every KB document.
    Called once on first retrieval, then reused for all subsequent queries.
    """
    global _kb_embeddings
    if _kb_embeddings is not None:
        return _kb_embeddings

    kb = load_kb()
    model = _get_model()

    texts = [doc["text"] for doc in kb]
    logger.info("Computing embeddings for %d KB documents...", len(texts))
    _kb_embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    logger.info("KB embeddings computed — shape: %s", _kb_embeddings.shape)

    return _kb_embeddings


def retrieve_context(query: str, top_k: int = 3) -> dict:
    """
    Find the most relevant knowledge base documents for the given query.

    How it works:
    1. Encode the query into an embedding vector.
    2. Compute dot-product similarity against every KB document embedding.
    3. Select the top_k highest-scoring documents.
    4. Format them into a context string for the reply prompt.

    Args:
        query: The employee's message or a search string.
        top_k: Number of documents to retrieve (default: 3).

    Returns:
        A dict with three keys:
        {
            "context": str,            # Formatted text for the reply prompt
            "top_k":   list[str],      # IDs of the selected documents
            "scores":  list[float],    # Similarity scores (highest first)
        }
    """
    logger.info("Retrieving context for query: %.60s...", query)

    kb = load_kb()
    kb_embeddings = _get_kb_embeddings()
    model = _get_model()

    query_embedding = model.encode([query], convert_to_numpy=True, show_progress_bar=False)

    scores = np.dot(kb_embeddings, query_embedding.T).flatten()

    top_indices = np.argsort(scores)[::-1][:top_k]

    selected_ids = []
    selected_scores = []
    context_parts = []

    for idx in top_indices:
        doc = kb[idx]
        score = float(scores[idx])

        selected_ids.append(doc["id"])
        selected_scores.append(round(score, 4))
        context_parts.append(f"[{doc['id']}] {doc['text']}")

        logger.debug(
            "  Match: id=%s | score=%.4f", doc["id"], score
        )

    context_string = "\n\n".join(context_parts)

    logger.info(
        "Retrieved %d documents — top match: %s (%.4f)",
        len(selected_ids),
        selected_ids[0] if selected_ids else "none",
        selected_scores[0] if selected_scores else 0.0,
    )

    return {
        "context": context_string,
        "top_k": selected_ids,
        "scores": selected_scores,
    }