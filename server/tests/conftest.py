"""
Shared test setup.

vector_service initializes a real Pinecone client at import time if
PINECONE_API_KEY is set. To keep tests hermetic, the `fresh_collection`
fixture swaps in an in-memory FakeIndex that mirrors Pinecone's API surface
for upsert / query / delete with simple dict storage.
"""
from types import SimpleNamespace
from typing import Dict, List

import pytest
from app.service import vector_service


class FakeIndex:
    """Tiny in-memory stand-in for a Pinecone Index used by tests.

    Filters use exact-equality across all top-level filter keys (the subset of
    Pinecone's filter semantics we actually use in production code). Similarity
    isn't computed — matches are returned in insertion order, which is fine
    because our tests check filter behavior, not retrieval quality.
    """

    def __init__(self) -> None:
        self.vectors: Dict[str, Dict] = {}

    def upsert(self, vectors: List[Dict]) -> None:
        for v in vectors:
            self.vectors[v['id']] = v

    def query(self, vector, top_k, filter, include_metadata):
        candidates = list(self.vectors.values())
        if filter:
            candidates = [
                v for v in candidates
                if all(v.get('metadata', {}).get(k) == val for k, val in filter.items())
            ]
        return SimpleNamespace(matches=[
            SimpleNamespace(id=v['id'], score=1.0, metadata=v.get('metadata'))
            for v in candidates[:top_k]
        ])

    def delete(self, ids: List[str]) -> None:
        for i in ids:
            self.vectors.pop(i, None)

    def count(self) -> int:
        """Test helper — not part of Pinecone's API."""
        return len(self.vectors)


@pytest.fixture
def fresh_collection(monkeypatch):
    """
    Replace the module-level Pinecone index with an in-memory fake, and stub
    _embed so tests don't need a real Voyage API key. Filter logic is what
    matters for these tests; embedding quality is irrelevant.

    Named `fresh_collection` to keep test code unchanged from the ChromaDB era.
    """
    fake = FakeIndex()
    monkeypatch.setattr(vector_service, '_index', fake)

    def fake_embed(texts, input_type):
        # Distinct deterministic vector per text. Quality doesn't matter.
        return [[float((hash(t) + i) % 1000) / 1000 for i in range(512)] for t in texts]

    monkeypatch.setattr(vector_service, '_embed', fake_embed)
    yield fake


def make_chunk(*, user_id, file_id, chunk_index, folder_id, text):
    """Helper to build a chunk in the shape batch_add_vectors expects."""
    return {
        'document_text': text,
        'metadata': {
            'user_id': user_id,
            'file_id': file_id,
            'chunk_index': chunk_index,
            'folder_id': folder_id,
            'file_name': f'{file_id}.docx',
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        },
    }
