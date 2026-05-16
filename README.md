# talk-to-a-folder

Chat with the contents of a Google Drive folder using Claude. The app embeds the documents in the folder you connect, then answers questions grounded in their content with linked source citations.

## Stack

```
client/   React + Vite + TypeScript (port 5173)
server/   Python + Flask            (port 5000)
```

External services:
- **Google OAuth + Drive API** — user sign-in and document fetch
- **Voyage AI** (`voyage-3-lite`) — text embeddings
- **Pinecone Serverless** — vector storage and similarity search
- **Anthropic Claude Haiku 4.5** — chat generation

Supported file types: Google Docs, Google Slides, Google Sheets, `.docx`, `.pptx`, `.xlsx`, `.pdf`, plain text, source code, JSON, YAML, CSV, Markdown.

## Prerequisites

You need accounts and API keys from four providers. All have free tiers that cover personal use.

| Service | Where to sign up | What you need |
|---|---|---|
| **Google Cloud** | [console.cloud.google.com](https://console.cloud.google.com) | OAuth 2.0 Client ID + Secret, Drive API enabled |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) | API key (starts with `sk-ant-`), $5+ credit |
| **Voyage AI** | [voyageai.com](https://www.voyageai.com) | API key (starts with `pa-`) |
| **Pinecone** | [pinecone.io](https://www.pinecone.io) | API key + index name (see setup below) |

### Google OAuth client setup

1. In [Google Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials), create an OAuth 2.0 Client ID of type **Web application**.
2. Add `http://localhost:5173` under **Authorized JavaScript origins**.
3. Enable the **Google Drive API** for the project (Google Cloud Console → APIs & Services → Library).
4. Note the **Client ID** and **Client secret** — you'll paste them into `.env` files below.

### Pinecone index setup

1. Sign in to [pinecone.io](https://www.pinecone.io) and create a **Serverless** index:
   - **Name**: `talk-to-a-folder` (or whatever — match what you set in `PINECONE_INDEX`)
   - **Dimensions**: `512` (matches `voyage-3-lite`)
   - **Metric**: `cosine`
   - **Cloud / region**: AWS `us-east-1` (free-tier-eligible)
2. Copy the **API key** from the Pinecone dashboard.

## Local setup

### 1. Backend

```bash
cd server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `server/.env` with your keys:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_CLIENT_ID=604215321895-xxxxxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
FLASK_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
VOYAGE_API_KEY=pa-...
PINECONE_API_KEY=pcsk-...
PINECONE_INDEX=talk-to-a-folder

# Optional tuning
# VOYAGE_MODEL=voyage-3-lite          # embedding model
# VECTOR_SCORE_THRESHOLD=0.4          # cosine threshold for retrieval

# Production-only (leave unset locally)
# FLASK_PRODUCTION=1
# FRONTEND_ORIGIN=https://your-prod-frontend.com
```

Start the server:

```bash
flask run
```

### 2. Frontend

```bash
cd client
npm install
```

Create `client/.env`:

```env
VITE_GOOGLE_CLIENT_ID=604215321895-xxxxxxxx.apps.googleusercontent.com
# Optional — only needed for cross-origin prod deploys
# VITE_API_BASE_URL=https://your-backend.onrender.com
```

`VITE_GOOGLE_CLIENT_ID` **must match** `GOOGLE_CLIENT_ID` in `server/.env`.

Start the dev server:

```bash
npm run dev
```

### 3. Open the app

[http://localhost:5173](http://localhost:5173)

Sign in with Google, paste a Drive folder URL (e.g. `https://drive.google.com/drive/folders/...`), and start asking questions.

The Vite dev server proxies `/api/*` requests to Flask on port 5000, so frontend and backend behave as same-origin during development.

## Testing

```bash
cd server
pip install -r requirements-dev.txt
pytest
```

Six tests cover the security-critical user/folder isolation in the vector retrieval layer.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `KeyError: 'FLASK_SECRET_KEY'` at boot | Missing or unset env var in `server/.env` |
| Sign-in popup closes but UI stays signed out | `VITE_GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_ID` don't match, or `http://localhost:5173` isn't in OAuth client's Authorized JavaScript origins |
| `Error 403: Google Drive API has not been used` | Drive API not enabled for the OAuth project; visit the URL printed in the error |
| `WARNING: PINECONE_API_KEY or PINECONE_INDEX not set` in backend logs | Missing env vars; or the Pinecone index doesn't exist |
| Chat returns `Not authenticated` after working previously | Access token expired (~1 hr); sign out and back in |
| `Folder not found` / `access denied` | Folder URL is wrong, points to a file instead of a folder, or the signed-in account doesn't have access |

## Project layout

```
server/
├── wsgi.py                       # Gunicorn entry / dev server bootstrap
├── app/
│   ├── __init__.py               # Flask factory, CORS, session config
│   ├── routes/
│   │   ├── auth.py               # /api/auth/*, /api/chat, /api/health
│   │   └── drive.py              # /api/drive/process-folder
│   └── service/
│       ├── drive_service.py      # Drive listing, downloads, text extraction, chunking
│       └── vector_service.py     # Voyage embedding + Pinecone storage/retrieval
└── tests/                        # pytest with FakeIndex stub for Pinecone

client/
└── src/
    ├── App.tsx                   # Top-level state, auth, folder connect, localStorage
    ├── components/
    │   ├── Header.tsx            # Sign-in / user avatar
    │   ├── UrlPanel.tsx          # Drive URL input + status (panel 1)
    │   ├── AnalyticsPanel.tsx    # Folder breakdown, file types, recent activity (panel 2)
    │   ├── ChatPanel.tsx         # Chat wrapper (panel 3)
    │   ├── Chat.tsx              # Message list, input, source citations
    │   └── TypeGlyph.tsx         # File-type SVG icons
    └── lib/
        ├── folderData.ts         # Types, categorization, sample folders (unused by default)
        └── api.ts                # apiUrl helper for prod cross-origin deploys
```
