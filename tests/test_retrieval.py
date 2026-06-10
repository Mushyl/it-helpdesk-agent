"""Unit tests for retrieval.py — top-k selection, scoring and formatting.

The real SentenceTransformer is replaced with a deterministic stub and the
knowledge base with a 3-document fixture, so these tests run offline and
without downloading any model.
"""

import numpy as np
import pytest

pytest.importorskip("sentence_transformers")

import retrieval  # noqa: E402


class FakeModel:
    """Deterministic stand-in for SentenceTransformer.

    Maps each text to a 3-dim vector based on keyword presence, then
    L2-normalises it — mirroring normalize_embeddings=True behaviour.
    """

    def __init__(self) -> None:
        self.encode_calls = 0

    def encode(self, texts, **kwargs):
        self.encode_calls += 1
        vectors = []
        for text in texts:
            lower = text.lower()
            v = np.array(
                [
                    1.0 if "vpn" in lower else 0.0,
                    1.0 if "password" in lower else 0.0,
                    1.0 if "printer" in lower else 0.0,
                ]
            )
            norm = np.linalg.norm(v)
            vectors.append(v / norm if norm else v)
        return np.array(vectors)


FAKE_KB = [
    {"id": "doc_vpn", "text": "VPN setup guide"},
    {"id": "doc_pwd", "text": "Password reset portal"},
    {"id": "doc_prn", "text": "Printer configuration"},
]


@pytest.fixture()
def fake_model(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(retrieval, "_get_model", lambda: model)
    monkeypatch.setattr(retrieval, "load_kb", lambda: FAKE_KB)
    # Reset the module-level embedding cache for test isolation;
    # monkeypatch restores the original value on teardown.
    monkeypatch.setattr(retrieval, "_kb_embeddings", None)
    return model


def test_top_match_is_most_similar_document(fake_model):
    out = retrieval.retrieve_context("the vpn is not working", top_k=2)
    assert out["top_k"][0] == "doc_vpn"
    assert len(out["top_k"]) == 2


def test_scores_are_sorted_descending(fake_model):
    out = retrieval.retrieve_context("vpn and password issues", top_k=3)
    assert out["scores"] == sorted(out["scores"], reverse=True)


def test_context_is_formatted_with_doc_ids(fake_model):
    out = retrieval.retrieve_context("printer trouble", top_k=1)
    assert out["context"] == "[doc_prn] Printer configuration"


def test_top_k_larger_than_kb_returns_all_docs(fake_model):
    out = retrieval.retrieve_context("vpn", top_k=10)
    assert len(out["top_k"]) == len(FAKE_KB)


def test_kb_embeddings_computed_once_then_cached(fake_model):
    retrieval.retrieve_context("vpn", top_k=1)
    # First call: 1 encode for the KB + 1 for the query.
    assert fake_model.encode_calls == 2
    retrieval.retrieve_context("password", top_k=1)
    # Second call: only the query is encoded (KB embeddings are cached).
    assert fake_model.encode_calls == 3
