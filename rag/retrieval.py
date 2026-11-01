"""Local semantic vector search with no external vector database requirement."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from rag.documents import Chunk


@dataclass
class SearchHit:
    chunk: Chunk
    score: float


@dataclass
class VectorIndex:
    chunks: list[Chunk]
    vectors: np.ndarray  # normalized, shape (n_chunks, embedding_dim)


def _normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix[None, :]
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.clip(norms, 1e-12, None)


def build_index(chunks: list[Chunk], model) -> VectorIndex:
    if not chunks:
        raise ValueError("No searchable text found in PDFs")
    # Supports SentenceTransformer; isolate the embedding model for easy unit tests.
    vectors = model.encode(
        [chunk.text for chunk in chunks],
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return VectorIndex(chunks=chunks, vectors=_normalize(vectors))


def search(index: VectorIndex, question: str, model, *, top_k: int = 4) -> list[SearchHit]:
    if not question.strip() or top_k < 1:
        return []
    query_vec = _normalize(model.encode([question], convert_to_numpy=True))[0]
    similarity = index.vectors @ query_vec
    indices = np.argsort(-similarity, kind="stable")[:top_k]
    return [SearchHit(index.chunks[int(i)], float(similarity[int(i)])) for i in indices]
