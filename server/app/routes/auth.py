import os
import anthropic
from flask import Blueprint, request, jsonify, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

bp = Blueprint('api', __name__, url_prefix='/api')

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


def _build_flow():
    return Flow.from_client_config(
        client_config={
            'web': {
                'client_id': os.environ['GOOGLE_CLIENT_ID'],
                'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=SCOPES,
        redirect_uri='postmessage',  # special value for SPA popup flow
    )


@bp.route('/health')
def health():
    return {'status': 'ok'}


@bp.route('/auth/google', methods=['POST'])
def google_auth():
    data = request.get_json(silent=True) or {}
    print('Received auth request with data:', data)
    code = data.get('code', '').strip()

    if not code:
        return jsonify({'error': 'authorization code is required'}), 400

    flow = _build_flow()
    flow.fetch_token(code=code)
    credentials = flow.credentials

    oauth2 = build('oauth2', 'v2', credentials=credentials)
    user_info = oauth2.userinfo().get().execute()

    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes or SCOPES),
    }
    session['user'] = {
        'id': user_info['id'],
        'email': user_info['email'],
        'name': user_info.get('name'),
        'picture': user_info.get('picture'),
    }

    print('User authenticated and stored in session:', session['user'])
    return jsonify({
        'user': session['user'],
        'name': user_info.get('name')
        })


@bp.route('/auth/me')
def auth_me():
    user = session.get('user')
    print('Auth check, user in session:', user)
    if not user:
        return jsonify({'user': None}), 401
    return jsonify({'user': user, 'name': user.get('name')})


@bp.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})


@bp.route('/chat', methods=['POST'])
def chat():
    from ..service import vector_service

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not authenticated. Please sign in with Google.'}), 401

    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    context = data.get('context', '').strip()
    folder_id = data.get('folder_id') or None

    if not message:
        return jsonify({'error': 'message is required'}), 400

    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    # Always scope retrieval to the authenticated user. folder_id narrows further.
    relevant_chunks = vector_service.query_with_metadata(
        message, n_results=5, user_id=user['id'], folder_id=folder_id
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

            # Track unique files for sources
            if file_id not in seen_files:
                sources.append({
                    'file_name': file_name,
                    'file_id': file_id,
                    'chunk_index': chunk_index,
                })
                seen_files.add(file_id)

    # Build system prompt with both metadata and document context
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
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        system=system_prompt,
        messages=[{'role': 'user', 'content': message}],
    )

    return jsonify({
        'reply': response.content[0].text,
        'sources': sources,
    })