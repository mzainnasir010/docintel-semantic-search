"""Unit tests for normalized document/query embeddings."""

import numpy as np
import pytest

from quillseek.embeddings import Embedder
from quillseek.embeddings import embedder as embedder_module


class FakeSentenceTransformer:
    def get_sentence_embedding_dimension(self):
        return 3

    def encode(self, texts, **kwargs):
        return np.asarray(
            [[len(text), text.lower().count("a") + 1, text.lower().count("e") + 1] for text in texts],
            dtype=np.float32,
        )


@pytest.fixture
def fake_embedder(monkeypatch):
    load_calls = []

    def load_model(model_name, device):
        load_calls.append((model_name, device))
        return FakeSentenceTransformer()

    monkeypatch.setattr(embedder_module, "_load_model", load_model)
    return Embedder(model_name="test-model", batch_size=2, device="cpu"), load_calls


def test_model_load_is_lazy_and_exposes_name_and_dimension(fake_embedder) -> None:
    embedder, load_calls = fake_embedder

    assert embedder.model_name == "test-model"
    assert load_calls == []
    assert embedder.dimension == 3
    assert load_calls == [("test-model", "cpu")]


def test_embeddings_have_expected_shape_and_l2_normalization(fake_embedder) -> None:
    embedder, _ = fake_embedder
    vectors = embedder.embed_documents(["alpha", "beta"])

    assert vectors.shape == (2, 3)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)


def test_query_and_document_encoding_share_normalized_model(fake_embedder) -> None:
    embedder, load_calls = fake_embedder
    document_vector = embedder.embed_documents(["same text"])[0]
    query_vector = embedder.embed_query("same text")

    assert query_vector.shape == (3,)
    assert np.allclose(document_vector, query_vector)
    assert len(load_calls) == 1


def test_batch_output_matches_single_encodings_and_is_deterministic(fake_embedder) -> None:
    embedder, _ = fake_embedder
    batch = embedder.embed_documents(["alpha", "beta"])
    singles = np.vstack([embedder.embed_documents([text])[0] for text in ["alpha", "beta"]])

    assert np.allclose(batch, singles)
    assert np.allclose(batch, embedder.embed_documents(["alpha", "beta"]))


def test_empty_document_batch_has_correct_dimension(fake_embedder) -> None:
    embedder, _ = fake_embedder

    assert embedder.embed_documents([]).shape == (0, 3)


def test_model_embeddings_capture_vacation_and_leave_semantics() -> None:
    embedder = Embedder()
    vectors = embedder.embed_documents(
        [
            "annual leave days",
            "twenty paid vacation days per year",
            "the chemical composition of distant stars",
        ]
    )
    vacation_similarity = float(vectors[0] @ vectors[1])
    unrelated_similarity = float(vectors[0] @ vectors[2])

    assert vacation_similarity > unrelated_similarity


def test_invalid_batch_size_is_rejected() -> None:
    with pytest.raises(ValueError, match="batch_size must be positive"):
        Embedder(batch_size=0)


@pytest.mark.parametrize(("cuda_available", "expected"), [(True, "cuda"), (False, "cpu")])
def test_device_selection_prefers_gpu_when_available(monkeypatch, cuda_available, expected) -> None:
    monkeypatch.setattr(embedder_module.torch.cuda, "is_available", lambda: cuda_available)

    assert embedder_module.select_device() == expected
