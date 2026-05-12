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
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    context = data.get('context', '').strip()

    if not message:
        return jsonify({'error': 'message is required'}), 400

    client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

    response = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        system=(
            'You are an AI agent that can read and summarize the contents of a Google Drive folder. '
            'You can ONLY see file metadata (names, extensions, sizes, modified dates), NOT file contents. '
            'Be concise and helpful. If asked about content you cannot see, say what you would do to find out. '
            'Use plain text, no markdown headers. Keep responses to 2-4 short sentences unless a list is needed.\n\n'
            f'FOLDER CONTEXT:\n{context}'
        ),
        messages=[{'role': 'user', 'content': message}],
    )

    return jsonify({'reply': response.content[0].text})