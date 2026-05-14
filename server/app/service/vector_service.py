import os
import chromadb
from chromadb.utils.embedding_functions import VoyageAIEmbeddingFunction
from typing import List, Dict, Tuple, Optional

# Ensure the ChromaDB data dir exists before instantiating. ChromaDB's Rust
# layer can fail with EACCES if the subdirectory under a mounted disk hasn't
# been created yet (common on first deploy to Render with a persistent disk).
_chroma_path = os.environ.get('CHROMA_PATH', './chroma_data')
os.makedirs(_chroma_path, exist_ok=True)

# Use Voyage AI for embeddings when VOYAGE_API_KEY is set. Offloads the
# CPU/memory-heavy embedding work off the Flask server (free tier covers ~50M
# tokens, far more than this app uses). When unset, ChromaDB falls back to its
# built-in sentence-transformers embedder — fine for local dev but too slow
# on small cloud instances.
_voyage_key = os.environ.get('VOYAGE_API_KEY')
_embedding_fn = (
    VoyageAIEmbeddingFunction(
        api_key=_voyage_key,
        model_name=os.environ.get('VOYAGE_MODEL', 'voyage-3-lite'),
    )
    if _voyage_key
    else None
)

client = chromadb.PersistentClient(path=_chroma_path)
collection = client.get_or_create_collection(
    name="my_collection",
    embedding_function=_embedding_fn,
)


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

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        where=where,
    )

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]

    return list(zip(documents, metadatas))


def batch_add_vectors(chunks_with_metadata: List[Dict]) -> List[str]:
    """
    Upsert document chunks. IDs are deterministic ({user_id}:{file_id}:{chunk_index})
    so re-processing a folder overwrites existing chunks instead of duplicating them.
    """
    ids = [
        f"{item['metadata']['user_id']}:{item['metadata']['file_id']}:{item['metadata']['chunk_index']}"
        for item in chunks_with_metadata
    ]
    documents = [item['document_text'] for item in chunks_with_metadata]
    metadatas = [item['metadata'] for item in chunks_with_metadata]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )
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
