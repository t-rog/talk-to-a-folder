"""Google OAuth + session management endpoints."""
from flask import Blueprint, jsonify, request, session
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from ..config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

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
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
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

    return jsonify({
        'user': session['user'],
        'name': user_info.get('name'),
    })


@bp.route('/auth/me')
def auth_me():
    user = session.get('user')
    if not user:
        return jsonify({'user': None}), 401
    return jsonify({'user': user, 'name': user.get('name')})


@bp.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})
