import os
import time
import voyageai
from pinecone import Pinecone
from typing import Any, Callable, List, Dict, Tuple, Optional


def _log(msg: str) -> None:
    print(f"[vector] {msg}", flush=True)


def _with_retry(fn: Callable[[], Any], attempts: int = 3, base_delay: float = 0.5) -> Any:
    """
    Retry a callable with exponential backoff. Covers transient failures from
    external APIs (Voyage, Pinecone): network blips, 429 rate limits, 503s.
    Doesn't distinguish retryable from non-retryable errors — at our scale,
    blanket retry is fine; a permanent error fails fast on its own (3 retries
    in under 4 seconds).
    """
    last_exc: Optional[Exception] = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                delay = base_delay * (2 ** i)
                _log(f"retry {i + 1}/{attempts} after {type(e).__name__}: {e} (sleep {delay}s)")
                time.sleep(delay)
    assert last_exc is not None
    raise last_exc


# ── Voyage AI (embeddings) ───────────────────────────────────────────────────
_voyage_key = os.environ.get('VOYAGE_API_KEY')
_voyage_model = os.environ.get('VOYAGE_MODEL', 'voyage-3-lite')

if _voyage_key:
    _voyage = voyageai.Client(api_key=_voyage_key)
    _log(f"voyage client ready, model={_voyage_model}")
else:
    _voyage = None
    _log("WARNING: VOYAGE_API_KEY not set — embedding calls will fail")


# ── Pinecone (vector store) ──────────────────────────────────────────────────
_pinecone_key = os.environ.get('PINECONE_API_KEY')
_pinecone_index_name = os.environ.get('PINECONE_INDEX')

if _pinecone_key and _pinecone_index_name:
    _pc = Pinecone(api_key=_pinecone_key)
    _index = _pc.Index(_pinecone_index_name)
    _log(f"pinecone index ready: {_pinecone_index_name}")
else:
    _index = None
    _log("WARNING: PINECONE_API_KEY or PINECONE_INDEX not set — vector ops will fail")


def _embed(texts: List[str], input_type: str) -> List[List[float]]:
    """
    Embed a list of texts via Voyage. input_type must be 'document' or 'query';
    Voyage uses different embeddings for each to improve retrieval quality.
    Retries with exponential backoff on transient failures.
    """
    if _voyage is None:
        raise RuntimeError("VOYAGE_API_KEY is not set; cannot embed")
    t = time.time()
    result = _with_retry(lambda: _voyage.embed(texts, model=_voyage_model, input_type=input_type))
    _log(f"  voyage.embed({input_type}, {len(texts)} items) took {time.time() - t:.2f}s")
    return result.embeddings


# Cosine similarity threshold below which a retrieved chunk is considered
# irrelevant and dropped before being passed to the LLM. Tune via env var if
# retrieval quality feels off — lower (0.3) for recall, higher (0.5) for precision.
SCORE_THRESHOLD = float(os.environ.get('VECTOR_SCORE_THRESHOLD', '0.4'))


def query_with_metadata(
    query: str,
    n_results: int = 3,
    user_id: Optional[str] = None,
    folder_id: Optional[str] = None,
) -> List[Tuple[str, Dict]]:
    """
    Query the vector store and return tuples of (document_text, metadata).
    `user_id` is required in production to prevent cross-user data leaks; when
    omitted, the query is unscoped (use only for trusted internal callers).
    `folder_id` further narrows to a single folder within the user's chunks.

    Chunks below SCORE_THRESHOLD are dropped — Pinecone's top_k always returns
    n_results matches regardless of relevance, so without this filter we'd
    feed Claude irrelevant text for off-topic queries.
    """
    if _index is None:
        raise RuntimeError("Pinecone is not configured")

    # Pinecone implicitly ANDs top-level filter keys
    pinecone_filter: Dict[str, str] = {}
    if user_id:
        pinecone_filter['user_id'] = user_id
    if folder_id:
        pinecone_filter['folder_id'] = folder_id

    _log(f"query START, filter={pinecone_filter}, top_k={n_results}, threshold={SCORE_THRESHOLD}")
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
        kept = score >= SCORE_THRESHOLD
        _log(f"  match {match.id} score={score:.3f} {'KEEP' if kept else 'DROP'}")
        if not kept:
            dropped += 1
            continue
        meta = dict(match.metadata or {})
        text = meta.pop('text', '')
        pairs.append((text, meta))
    _log(f"query result: {len(pairs)} kept, {dropped} dropped (threshold={SCORE_THRESHOLD})")
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
    """
    Store a batch of document chunks (wrapper around batch_add_vectors).
    Returns summary of what was stored.
    """
    ids = batch_add_vectors(chunks_with_metadata)
    return {
        'status': 'success',
        'chunks_stored': len(ids),
        'ids': ids,
    }
