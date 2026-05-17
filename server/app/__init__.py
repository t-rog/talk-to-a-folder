from flask import Flask
from flask_cors import CORS

from . import config


def create_app():
    app = Flask(__name__)
    app.secret_key = config.FLASK_SECRET_KEY

    # Session cookie hardening only applies in production (HTTPS). Locally we
    # need Secure=False so cookies are accepted over plain http://localhost.
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=config.IS_PROD,
        SESSION_COOKIE_SAMESITE='None' if config.IS_PROD else 'Lax',
    )

    CORS(
        app,
        supports_credentials=True,
        origins=config.FRONTEND_ORIGIN,
        allow_headers=['Content-Type'],
        methods=['GET', 'POST', 'OPTIONS'],
    )

    from .routes import auth, chat, drive
    app.register_blueprint(auth.bp)
    app.register_blueprint(chat.bp)
    app.register_blueprint(drive.bp)

    return app
