# talk-to-a-folder

Fullstack monorepo — React/Vite/TypeScript frontend + Python/Flask backend.

## Structure

```
client/   React + Vite + TypeScript (port 5173)
server/   Python + Flask             (port 5000)
```

## Getting started

### Backend

```bash
cd server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
flask run
```

### Frontend

```bash
cd client
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api/*` requests to Flask on port 5000.
