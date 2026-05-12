import os
from dotenv import load_dotenv

load_dotenv()

# Google returns scope strings normalized (e.g., 'email' → full URL). Without this,
# oauthlib raises a Warning that aborts the OAuth code exchange in google_auth().
os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', '1')

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
