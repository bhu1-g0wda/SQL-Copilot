# SQL Copilot ⚡

An AI-powered SQL assistant that converts natural language to SQL using **Gemini 2.5 Pro**, with a beautiful dark-themed React UI and a FastAPI backend.

## Features

- 🤖 **Natural language → SQL** — powered by Gemini 2.5 Pro
- 🗄️ **Multi-database support** — PostgreSQL, MySQL, SQLite
- 🌳 **Schema explorer** — live tree view of your tables and columns
- 🔍 **Syntax-highlighted SQL** display with one-click copy
- 📊 **Paginated results table** for large result sets
- ✏️ **Edit & re-run** AI-generated SQL directly in the editor
- ↩️ **Undo stack** — revert INSERT / UPDATE / DELETE operations
- ⚠️ **Confirmation modal** for destructive operations (DELETE, UPDATE, DROP, TRUNCATE)
- 🔄 **Mode toggle** — switch between Natural Language and Raw SQL mode
- 🔐 **Session-based connections** — credentials sent once on connect, never in subsequent requests
- ↔️ **Resizable panels** — drag to resize the sidebar and query panel

---

## Project Structure

```
sql-copilot/
├── backend/
│   ├── main.py              # FastAPI application (all routes + logic)
│   ├── requirements.txt     # Python dependencies
│   ├── pytest.ini           # Pytest configuration
│   ├── sample_store.db      # Sample SQLite database for quick demo
│   └── .env                 # Environment variables (not committed)
└── frontend/
    ├── src/
    │   ├── App.tsx                    # Root component, state & layout
    │   ├── index.css                  # Global dark design system
    │   ├── main.tsx                   # React entry point
    │   ├── api/
    │   │   └── client.ts              # Axios API client (session-aware)
    │   └── components/
    │       ├── ConnectionForm.tsx     # Database connection panel
    │       ├── QueryInput.tsx         # NL / SQL input + mode toggle
    │       ├── ResultsTable.tsx       # Syntax-highlighted SQL + data table
    │       └── SchemaViewer.tsx       # Schema sidebar tree
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    └── package.json
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10 or newer |
| Node.js | 18 or newer |
| Gemini API Key | Free at https://aistudio.google.com/ |

> **Database drivers** — `psycopg2-binary` (PostgreSQL) and `pymysql` (MySQL) are included in `requirements.txt`. SQLite is built into Python — no extra install needed.

---

## Installation & Setup

### Step 1 — Get a Gemini API Key

Go to https://aistudio.google.com/, sign in, and create a free API key.

---

### Step 2 — Backend Setup

Open a terminal and run:

```bash
cd backend
```

**Create and activate a virtual environment:**

```bash
# Create
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS / Linux)
source venv/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Configure your API key:**

Open `backend\.env` and set your key:

```
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

---

### Step 3 — Frontend Setup

Open a **second terminal** and run:

```bash
cd frontend
npm install
```

---

## Running the App

### Terminal 1 — Start the Backend

```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

- API base URL: http://localhost:8000
- Interactive Swagger docs: http://localhost:8000/docs

### Terminal 2 — Start the Frontend

```bash
cd frontend
npm run dev
```

- App URL: http://localhost:5173

Open http://localhost:5173 in your browser and you're ready to go.

---

## Quick Start with the Sample Database

A ready-to-use SQLite database (`backend/sample_store.db`) is included. To connect:

1. Open the app at http://localhost:5173
2. In the **Connection** panel, select **SQLite**
3. Enter the full path to `sample_store.db`, e.g.:
   ```
   C:\Users\YourName\Desktop\sql copliot\backend\sample_store.db
   ```
4. Click **Connect**
5. Try asking: *"Show me all products sorted by price"*

---

## Creating Your Own SQLite Database

```python
import sqlite3

conn = sqlite3.connect("mydb.db")
conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, score REAL)")
conn.execute("INSERT INTO users VALUES (1, 'Alice', 'alice@example.com', 98.5)")
conn.execute("INSERT INTO users VALUES (2, 'Bob',   'bob@example.com',   82.1)")
conn.commit()
conn.close()
print("Created mydb.db")
```

Then connect using the full path to `mydb.db`.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/connect` | Connect to a database — returns `session_id` |
| DELETE | `/api/session/{id}` | Invalidate a session (disconnect) |
| POST | `/api/query` | Natural language → SQL via Gemini, then execute |
| POST | `/api/execute` | Execute raw SQL directly |

### POST /api/connect

```json
{
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "username": "postgres",
  "password": "secret"
}
```

For SQLite, only `db_type` and `database` (file path) are required.

**Response** includes a `session_id` — pass this in all subsequent requests. Credentials are never sent again.

### POST /api/query

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "natural_language_query": "Show me the top 10 customers by revenue"
}
```

### POST /api/execute

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "sql": "SELECT id, name FROM customers LIMIT 5;"
}
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Your Gemini API key from Google AI Studio |

The `.env` file lives at `backend\.env` and is excluded from version control by `.gitignore`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| AI | Google Gemini 2.5 Pro (google-genai SDK) |
| Database | SQLAlchemy + psycopg2 / pymysql |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Vanilla CSS (dark design system) |
| HTTP Client | Axios |
| Syntax Highlighting | react-syntax-highlighter |

---

## Security Design

Credentials travel over the wire **only once** — in the `POST /api/connect` request. The server stores the connection URL in a server-side session (1-hour TTL) and returns a UUID `session_id`. All subsequent query and execute requests carry only the `session_id`. This means:

- Passwords never appear in browser network logs for normal query traffic
- Sessions auto-expire after 1 hour of inactivity
- Clients can explicitly disconnect via `DELETE /api/session/{id}`

---

## Troubleshooting

**`ModuleNotFoundError` on startup**
→ Make sure your venv is activated (`venv\Scripts\activate`) and `pip install -r requirements.txt` has been run.

**`401 Unauthorized` from the API**
→ Your session has expired (1-hour TTL). Click **Connect** in the app to start a new session.

**`401 Unauthorized` / Gemini errors**
→ Check that `GEMINI_API_KEY` is set correctly in `backend\.env`.

**CORS errors in the browser**
→ The backend must be running on port 8000. The Vite proxy in `vite.config.ts` handles CORS automatically during development.

**PostgreSQL connection refused**
→ Check that your PostgreSQL server is running and that the host, port, and credentials are correct.

**SQLite path not found**
→ Use the full absolute path, e.g. `C:\Users\YourName\Desktop\sql copliot\backend\sample_store.db`. Backslashes are fine on Windows.

**Frontend shows blank page / network errors**
→ Make sure both the backend (port 8000) and frontend dev server (port 5173) are running at the same time.
