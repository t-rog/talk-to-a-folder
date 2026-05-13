import os
from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ['FLASK_SECRET_KEY']

    # Session cookie hardening only applies in production (HTTPS). Locally we
    # need Secure=False so cookies are accepted over plain http://localhost.
    is_prod = os.environ.get('FLASK_PRODUCTION') == '1'
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=is_prod,
        SESSION_COOKIE_SAMESITE='None' if is_prod else 'Lax',
    )

    CORS(
        app,
        supports_credentials=True,
        origins=os.environ.get('FRONTEND_ORIGIN', 'http://localhost:5173'),
        allow_headers=['Content-Type'],
        methods=['GET', 'POST', 'OPTIONS'],
    )

    from .routes import auth, drive
    app.register_blueprint(drive.bp)
    app.register_blueprint(auth.bp)

    return app
