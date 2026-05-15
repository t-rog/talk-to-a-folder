"""
Shared test setup.

The vector_service module instantiates a PersistentClient at import time, so we
redirect it at a throwaway temp dir before any test code imports it. Each test
then receives a fresh in-memory ChromaDB collection via the `fresh_collection`
fixture — fast, hermetic, no cross-test contamination.
"""
import os
import tempfile
import uuid

# Must run before any `from app.service import vector_service` import.
os.environ.setdefault('CHROMA_PATH', tempfile.mkdtemp(prefix='chroma_test_'))

import chromadb
import pytest
from app.service import vector_service


@pytest.fixture
def fresh_collection(monkeypatch):
    """
    Replace the module-level collection with an isolated in-memory one.
    Uses a unique collection name per test because chromadb.Client() reuses
    cached collection state under the same name across fixture instantiations.

    Also stubs vector_service._embed so tests don't need a real Voyage API
    key — we're testing filter logic, not embedding quality.
    """
    client = chromadb.Client()
    name = f'test_{uuid.uuid4().hex}'
    collection = client.get_or_create_collection(name=name)
    monkeypatch.setattr(vector_service, 'collection', collection)

    def fake_embed(texts, input_type):
        # Distinct deterministic vector per text so ChromaDB accepts them as
        # unique points. Quality doesn't matter — filter logic is what we test.
        return [[float((hash(t) + i) % 1000) / 1000 for i in range(384)] for t in texts]

    monkeypatch.setattr(vector_service, '_embed', fake_embed)

    yield collection
    try:
        client.delete_collection(name=name)
    except Exception:
        pass


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
