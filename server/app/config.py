"""
Centralized environment configuration.

Everything that reads from `os.environ` lives here so the full surface of
required + optional env vars is visible in one file. Modules import the
constants they need rather than calling `os.environ.get` ad-hoc.
"""
import os

# Required at startup
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

# Voyage AI — embeddings
VOYAGE_API_KEY = os.environ.get('VOYAGE_API_KEY')
VOYAGE_MODEL = os.environ.get('VOYAGE_MODEL', 'voyage-3-lite')

# Pinecone — vector store
PINECONE_API_KEY = os.environ.get('PINECONE_API_KEY')
PINECONE_INDEX = os.environ.get('PINECONE_INDEX')

# Retrieval tuning
VECTOR_SCORE_THRESHOLD = float(os.environ.get('VECTOR_SCORE_THRESHOLD', '0.4'))

# Deployment context
IS_PROD = os.environ.get('FLASK_PRODUCTION') == '1'
FRONTEND_ORIGIN = os.environ.get('FRONTEND_ORIGIN', 'http://localhost:5173')

# Anthropic model — pinned to current Haiku
CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
