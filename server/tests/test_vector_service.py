"""
Security-critical tests for vector_service.

These guard the multi-tenant invariant: a user's query must only ever return
their own chunks. If any of these regress, there is a real privacy bug.
"""
from app.service import vector_service
from tests.conftest import make_chunk


def test_user_isolation_prevents_cross_user_retrieval(fresh_collection):
    """User A's query must never surface User B's chunks, even on identical text."""
    vector_service.batch_add_vectors([
        make_chunk(user_id='user_a', file_id='fA', chunk_index=0,
                   folder_id='folder_a', text='memo about quarterly earnings'),
        make_chunk(user_id='user_b', file_id='fB', chunk_index=0,
                   folder_id='folder_b', text='memo about quarterly earnings'),
    ])

    results = vector_service.query_with_metadata(
        'quarterly earnings', n_results=10, user_id='user_a'
    )

    assert len(results) == 1
    assert all(meta['user_id'] == 'user_a' for _, meta in results)


def test_folder_id_narrows_within_user(fresh_collection):
    """Within a single user, folder_id should further narrow the results."""
    vector_service.batch_add_vectors([
        make_chunk(user_id='user_a', file_id='f1', chunk_index=0,
                   folder_id='folder_one', text='cat facts'),
        make_chunk(user_id='user_a', file_id='f2', chunk_index=0,
                   folder_id='folder_two', text='cat facts'),
    ])

    results = vector_service.query_with_metadata(
        'cat facts', n_results=10, user_id='user_a', folder_id='folder_one'
    )

    assert len(results) == 1
    assert all(meta['folder_id'] == 'folder_one' for _, meta in results)


def test_folder_id_alone_does_not_bypass_user_filter(fresh_collection):
    """
    Guards against a regression where folder_id-only queries leak across users.
    User B passing User A's folder_id while scoping to user_b must return zero.
    """
    vector_service.batch_add_vectors([
        make_chunk(user_id='user_a', file_id='fA', chunk_index=0,
                   folder_id='shared_folder_id', text='confidential alpha'),
    ])

    results = vector_service.query_with_metadata(
        'confidential', n_results=10,
        user_id='user_b', folder_id='shared_folder_id',
    )

    assert results == []


def test_deterministic_ids_prevent_duplicates_on_reindex(fresh_collection):
    """Re-running batch_add_vectors with the same chunk must upsert, not duplicate."""
    chunk = make_chunk(user_id='user_a', file_id='f1', chunk_index=0,
                       folder_id='folder_a', text='original content')

    vector_service.batch_add_vectors([chunk])
    vector_service.batch_add_vectors([chunk])

    assert fresh_collection.count() == 1


def test_upsert_overwrites_chunk_text_in_place(fresh_collection):
    """
    Re-indexing with the same metadata but different text should replace the
    document content, not create a stale duplicate.
    """
    base_meta = dict(user_id='user_a', file_id='f1', chunk_index=0,
                     folder_id='folder_a')
    vector_service.batch_add_vectors([
        make_chunk(text='original content', **base_meta),
    ])
    vector_service.batch_add_vectors([
        make_chunk(text='updated content', **base_meta),
    ])

    results = vector_service.query_with_metadata(
        'content', n_results=5, user_id='user_a'
    )
    assert fresh_collection.count() == 1
    assert results[0][0] == 'updated content'


def test_deterministic_id_format(fresh_collection):
    """The ID scheme is `{user_id}:{file_id}:{chunk_index}`."""
    ids = vector_service.batch_add_vectors([
        make_chunk(user_id='alice', file_id='abc123', chunk_index=5,
                   folder_id='folder_a', text='x'),
    ])
    assert ids == ['alice:abc123:5']
