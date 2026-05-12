import os
from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ['FLASK_SECRET_KEY']
    CORS(
        app,
        supports_credentials=True,
        origins='http://localhost:5173',
        allow_headers=['Content-Type'],
        methods=['GET', 'POST', 'OPTIONS'],
    )

    from .routes import auth, drive
    app.register_blueprint(drive.bp)
    app.register_blueprint(auth.bp)

    return app
