import os
import time
import chromadb
import voyageai
from typing import List, Dict, Tuple, Optional


def _log(msg: str) -> None:
    print(f"[vector] {msg}", flush=True)


# Ensure the ChromaDB data dir exists before instantiating. ChromaDB's Rust
# layer can fail with EACCES if the subdirectory under a mounted disk hasn't
# been created yet (common on first deploy to Render with a persistent disk).
_chroma_path = os.environ.get('CHROMA_PATH', './chroma_data')
os.makedirs(_chroma_path, exist_ok=True)

# We call Voyage directly via its SDK instead of relying on ChromaDB's bundled
# VoyageAIEmbeddingFunction — that wrapper was hanging indefinitely on upsert
# in production. By pre-computing embeddings here and passing them to upsert()
# explicitly, ChromaDB never invokes any embedder of its own.
_voyage_key = os.environ.get('VOYAGE_API_KEY')
_voyage_model = os.environ.get('VOYAGE_MODEL', 'voyage-3-lite')

if not _voyage_key:
    _log("WARNING: VOYAGE_API_KEY not set — embedding calls will fail")
    _voyage = None
else:
    _voyage = voyageai.Client(api_key=_voyage_key)
    _log(f"voyage client ready, model={_voyage_model}")

client = chromadb.PersistentClient(path=_chroma_path)
# No embedding_function — we supply embeddings ourselves on every call.
collection = client.get_or_create_collection(name="my_collection")
_log(f"collection ready at {_chroma_path}")


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
    filters = []
    if user_id:
        filters.append({'user_id': user_id})
    if folder_id:
        filters.append({'folder_id': folder_id})

    if len(filters) > 1:
        where = {'$and': filters}
    elif filters:
        where = filters[0]
    else:
        where = None

    _log(f"query START, where={where}")
    t = time.time()
    query_embedding = _embed([query], input_type='query')[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )
    _log(f"query END, {time.time() - t:.2f}s")

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]

    return list(zip(documents, metadatas))


def batch_add_vectors(chunks_with_metadata: List[Dict]) -> List[str]:
    """
    Upsert document chunks. IDs are deterministic ({user_id}:{file_id}:{chunk_index})
    so re-processing a folder overwrites existing chunks instead of duplicating them.
    Embeddings are computed via Voyage SDK and passed in explicitly.
    """
    ids = [
        f"{item['metadata']['user_id']}:{item['metadata']['file_id']}:{item['metadata']['chunk_index']}"
        for item in chunks_with_metadata
    ]
    documents = [item['document_text'] for item in chunks_with_metadata]
    metadatas = [item['metadata'] for item in chunks_with_metadata]

    _log(f"upsert START, {len(ids)} chunks")
    t = time.time()
    embeddings = _embed(documents, input_type='document')
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )
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
