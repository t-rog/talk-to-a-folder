"""
Pinecone vector store — upsert/query/delete with user_id+folder_id filtering.
Uses embeddings.py for the actual vectorization; this module is pure storage
+ similarity-search concerns.
"""
import time
from typing import Dict, List, Optional, Tuple

from pinecone import Pinecone

from ..config import PINECONE_API_KEY, PINECONE_INDEX, VECTOR_SCORE_THRESHOLD
from .embeddings import _with_retry, embed


def _log(msg: str) -> None:
    print(f"[vector] {msg}", flush=True)


if PINECONE_API_KEY and PINECONE_INDEX:
    _pc = Pinecone(api_key=PINECONE_API_KEY)
    _index = _pc.Index(PINECONE_INDEX)
    _log(f"pinecone index ready: {PINECONE_INDEX}")
else:
    _index = None
    _log("WARNING: PINECONE_API_KEY or PINECONE_INDEX not set — vector ops will fail")


# Module-level alias so tests can monkeypatch the embedding function without
# reaching into another module. Same behavior as importing `embed` directly.
_embed = embed


def query_with_metadata(
    query: str,
    n_results: int = 7,
    user_id: Optional[str] = None,
    folder_id: Optional[str] = None,
) -> List[Tuple[str, Dict]]:
    """
    Query the vector store and return tuples of (document_text, metadata).
    `user_id` is required in production to prevent cross-user data leaks; when
    omitted, the query is unscoped (use only for trusted internal callers).
    `folder_id` further narrows to a single folder within the user's chunks.

    Chunks below VECTOR_SCORE_THRESHOLD are dropped — Pinecone's top_k always
    returns n_results matches regardless of relevance, so without this filter
    we'd feed Claude irrelevant text for off-topic queries.
    """
    if _index is None:
        raise RuntimeError("Pinecone is not configured")

    # Pinecone implicitly ANDs top-level filter keys
    pinecone_filter: Dict[str, str] = {}
    if user_id:
        pinecone_filter['user_id'] = user_id
    if folder_id:
        pinecone_filter['folder_id'] = folder_id

    _log(f"query START, filter={pinecone_filter}, top_k={n_results}, threshold={VECTOR_SCORE_THRESHOLD}")
    t = time.time()
    query_embedding = _embed([query], input_type='query')[0]
    result = _with_retry(lambda: _index.query(
        vector=query_embedding,
        top_k=n_results,
        filter=pinecone_filter if pinecone_filter else None,
        include_metadata=True,
    ))
    _log(f"query END, {time.time() - t:.2f}s, {len(result.matches)} matches raw")

    pairs: List[Tuple[str, Dict]] = []
    dropped = 0
    for match in result.matches:
        score = getattr(match, 'score', 0.0) or 0.0
        kept = score >= VECTOR_SCORE_THRESHOLD
        _log(f"  match {match.id} score={score:.3f} {'KEEP' if kept else 'DROP'}")
        if not kept:
            dropped += 1
            continue
        meta = dict(match.metadata or {})
        text = meta.pop('text', '')
        pairs.append((text, meta))
    _log(f"query result: {len(pairs)} kept, {dropped} dropped (threshold={VECTOR_SCORE_THRESHOLD})")
    return pairs


def batch_add_vectors(chunks_with_metadata: List[Dict]) -> List[str]:
    """
    Upsert document chunks into Pinecone. IDs are deterministic
    ({user_id}:{file_id}:{chunk_index}) so re-processing a folder overwrites
    existing chunks instead of duplicating them. The chunk text is stored in
    Pinecone metadata under the `text` key so it's returned at query time.
    """
    if _index is None:
        raise RuntimeError("Pinecone is not configured")

    documents = [item['document_text'] for item in chunks_with_metadata]

    _log(f"upsert START, {len(chunks_with_metadata)} chunks")
    t = time.time()
    embeddings = _embed(documents, input_type='document')

    vectors = []
    ids = []
    for item, embedding in zip(chunks_with_metadata, embeddings):
        meta = dict(item['metadata'])
        vec_id = f"{meta['user_id']}:{meta['file_id']}:{meta['chunk_index']}"
        ids.append(vec_id)
        meta['text'] = item['document_text']
        vectors.append({
            'id': vec_id,
            'values': embedding,
            'metadata': meta,
        })

    _with_retry(lambda: _index.upsert(vectors=vectors))
    _log(f"upsert END, {time.time() - t:.2f}s")
    return ids


def store_documents(chunks_with_metadata: List[Dict]) -> Dict:
    """Store a batch of document chunks. Wrapper around batch_add_vectors."""
    ids = batch_add_vectors(chunks_with_metadata)
    return {
        'status': 'success',
        'chunks_stored': len(ids),
        'ids': ids,
    }
