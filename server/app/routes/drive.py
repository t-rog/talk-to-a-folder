import os
import logging
from flask import Blueprint, request, jsonify, session
from ..service import drive_service, vector_service

logger = logging.getLogger(__name__)
bp = Blueprint('drive', __name__, url_prefix='/api/drive')


@bp.route('/process-folder', methods=['POST'])
def process_folder():
    """Process a Google Drive folder: list files, extract text, chunk, and store in vector DB."""
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
        # Process the folder
        result = drive_service.process_folder(folder_url_or_id, credentials)

        if result['status'] == 'error':
            logger.error(f"Folder processing failed: {result.get('error')}")
            return jsonify(result), 400

        # Tag every chunk with the authenticated user_id before storing.
        # Required so queries can be scoped per-user and never leak across accounts.
        chunks = result.pop('chunks', [])
        for chunk in chunks:
            chunk['metadata']['user_id'] = user_id

        if chunks:
            vector_result = vector_service.store_documents(chunks)
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


@bp.route('/test')
def test():
    return {'status': 'ok'}