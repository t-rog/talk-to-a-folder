import os
import time
import voyageai
from pinecone import Pinecone
from typing import List, Dict, Tuple, Optional


def _log(msg: str) -> None:
    print(f"[vector] {msg}", flush=True)


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
    """
    if _voyage is None:
        raise RuntimeError("VOYAGE_API_KEY is not set; cannot embed")
    t = time.time()
    result = _voyage.embed(texts, model=_voyage_model, input_type=input_type)
    _log(f"  voyage.embed({input_type}, {len(texts)} items) took {time.time() - t:.2f}s")
    return result.embeddings


def query_with_metadata(
    query: str,
    n_results: int = 5,
    user_id: Optional[str] = None,
    folder_id: Optional[str] = None,
) -> List[Tuple[str, Dict]]:
    """
    Query the vector store and return tuples of (document_text, metadata).
    `user_id` is required in production to prevent cross-user data leaks; when
    omitted, the query is unscoped (use only for trusted internal callers).
    `folder_id` further narrows to a single folder within the user's chunks.
    """
    if _index is None:
        raise RuntimeError("Pinecone is not configured")

    # Pinecone implicitly ANDs top-level filter keys
    pinecone_filter: Dict[str, str] = {}
    if user_id:
        pinecone_filter['user_id'] = user_id
    if folder_id:
        pinecone_filter['folder_id'] = folder_id

    _log(f"query START, filter={pinecone_filter}")
    t = time.time()
    query_embedding = _embed([query], input_type='query')[0]
    result = _index.query(
        vector=query_embedding,
        top_k=n_results,
        filter=pinecone_filter if pinecone_filter else None,
        include_metadata=True,
    )
    _log(f"query END, {time.time() - t:.2f}s, {len(result.matches)} matches")

    pairs: List[Tuple[str, Dict]] = []
    for match in result.matches:
        meta = dict(match.metadata or {})
        text = meta.pop('text', '')
        pairs.append((text, meta))
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

    _index.upsert(vectors=vectors)
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
