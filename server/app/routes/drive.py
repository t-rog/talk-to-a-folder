"""Drive folder processing endpoint."""
import logging

from flask import Blueprint, jsonify, request, session

from ..service import folder_processor, vector_store

logger = logging.getLogger(__name__)
bp = Blueprint('drive', __name__, url_prefix='/api/drive')


@bp.route('/process-folder', methods=['POST'])
def process_folder():
    """Process a Drive folder: list files, extract text, chunk, and store in vector DB."""
    data = request.get_json(silent=True) or {}
    folder_url_or_id = data.get('folder_url', '').strip()

    if not folder_url_or_id:
        return jsonify({'error': 'folder_url is required'}), 400

    credentials = session.get('credentials')
    user = session.get('user')
    if not credentials or not user:
        return jsonify({'error': 'Not authenticated. Please sign in with Google.'}), 401

    user_id = user['id']

    try:
        result = folder_processor.process_folder(folder_url_or_id, credentials)

        if result['status'] == 'error':
            code = result.get('error_code', 'unknown')
            logger.error(f"Folder processing failed: {code} — {result.get('message')}")
            http_status = {
                'folder_not_found': 404,
                'access_denied': 403,
                'not_a_folder': 400,
            }.get(code, 500)
            return jsonify(result), http_status

        # Tag every chunk with the authenticated user_id before storing.
        # Required so queries can be scoped per-user and never leak across accounts.
        chunks = result.pop('chunks', [])
        for chunk in chunks:
            chunk['metadata']['user_id'] = user_id

        if chunks:
            vector_result = vector_store.store_documents(chunks)
            result['vector_store_status'] = vector_result['status']
            result['chunks_indexed'] = vector_result['chunks_stored']
        else:
            result['vector_store_status'] = 'no_chunks'
            result['chunks_indexed'] = 0

        logger.info(f"Successfully processed folder: {result}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error processing folder: {e}")
        return jsonify({'error': str(e)}), 500
