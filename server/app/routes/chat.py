"""Chat endpoint — RAG-style: vector retrieval + Claude generation."""
import anthropic
from flask import Blueprint, jsonify, request, session

from ..config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from ..service import vector_store

bp = Blueprint('chat', __name__, url_prefix='/api')


@bp.route('/chat', methods=['POST'])
def chat():
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not authenticated. Please sign in with Google.'}), 401

    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    context = data.get('context', '').strip()
    folder_id = data.get('folder_id') or None

    if not message:
        return jsonify({'error': 'message is required'}), 400

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Always scope retrieval to the authenticated user. folder_id narrows further.
    relevant_chunks = vector_store.query_with_metadata(
        message, n_results=7, user_id=user['id'], folder_id=folder_id,
    )

    # Build document context from retrieved chunks
    document_context = ''
    sources = []
    if relevant_chunks:
        document_context = 'DOCUMENT EXCERPTS:\n'
        seen_files = set()
        for chunk_text, metadata in relevant_chunks:
            file_name = metadata.get('file_name', 'Unknown')
            file_id = metadata.get('file_id')
            chunk_index = metadata.get('chunk_index', 0)

            document_context += f"\nFrom {file_name} (chunk {chunk_index}):\n{chunk_text}\n"

            if file_id not in seen_files:
                sources.append({
                    'file_name': file_name,
                    'file_id': file_id,
                    'chunk_index': chunk_index,
                })
                seen_files.add(file_id)

    system_prompt = (
        'You are an AI agent that can read and understand Google Drive folder contents. '
        'You can see file metadata (names, extensions, sizes, modified dates) AND the text contents of documents. '
        'When answering questions, refer to specific documents, filenames, and relevant quotes when available. '
        'Be concise and helpful. Use plain text, no markdown headers. Keep responses to 2-4 short sentences unless a list is needed.\n\n'
        f'FOLDER METADATA:\n{context}'
    )
    if document_context:
        system_prompt += f'\n\n{document_context}'

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{'role': 'user', 'content': message}],
    )

    return jsonify({
        'reply': response.content[0].text,
        'sources': sources,
    })
