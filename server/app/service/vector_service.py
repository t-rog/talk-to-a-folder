import os
import chromadb
from typing import List, Dict, Tuple, Optional

client = chromadb.PersistentClient(path=os.environ.get('CHROMA_PATH', './chroma_data'))
collection = client.get_or_create_collection(name="my_collection")


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
