# SQL Copilot ⚡

An AI-powered SQL assistant that converts natural language to SQL using **Gemini 2.5 Pro**, with a beautiful dark-themed React UI and a FastAPI backend.

## Features

- 🤖 **Natural language → SQL** via Gemini 2.5 Pro
- 🗄️ **Multi-database support** — PostgreSQL, MySQL, SQLite
- 🌳 **Schema explorer** — live tree view of tables and columns
- 🔍 **Syntax-highlighted SQL** display with copy button
- 📊 **Paginated results table** for large result sets
- ✏️ **Edit & re-run** generated SQL directly
- ⚠️ **Confirmation modal** for destructive operations (DELETE, UPDATE, DROP, TRUNCATE)
- 🔄 **Mode toggle** — switch between Natural Language and Raw SQL mode
- 🔐 **Session-based connections** — credentials sent once on connect, never again in subsequent requests

---

## Project Structure

```
sql-copilot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── requirements.txt     # Python deps
│   ├── pytest.ini           # Test configuration
│   ├── .env.example         # Environment variable template
│   └── tests/
│       └── test_main.py     # pytest test suite
└── frontend/
    ├── src/
    │   ├── App.tsx           # Main application
    │   ├── index.css         # Global design system
    │   ├── api/
    │   │   └── client.ts     # Axios API client (session-aware)
    │   └── components/
    │       ├── ConnectionForm.tsx  # DB connection panel
    │       ├── QueryInput.tsx      # NL/SQL input + mode toggle
    │       ├── ResultsTable.tsx    # SQL block + data table
    │       └── SchemaViewer.tsx    # Schema sidebar tree
    ├── index.html
    ├── vite.config.ts
    └── package.json
```

---

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Gemini API Key** — get one free at https://aistudio.google.com/

For PostgreSQL: `psycopg2-binary` is included (no extra install needed)  
For MySQL: `pymysql` is included  
For SQLite: built-in, no extra server needed

---

## Installation & Setup

### 1. Clone / open the project

```bash
cd "sql-copilot"
```

### 2. Backend Setup

```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux

# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=AIza...
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

---

## Running the App

### Start the Backend (Terminal 1)

```bash
cd backend
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux
uvicorn main:app --reload --port 8000
```

Backend will be at: http://localhost:8000  
API docs (Swagger): http://localhost:8000/docs

### Start the Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Frontend will be at: http://localhost:5173

---

## Running Tests

```bash
cd backend
venv\Scripts\activate
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## API Reference

| Method | Endpoint                | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/api/health`           | Health check                             |
| POST   | `/api/connect`          | Connect to DB, returns `session_id`      |
| DELETE | `/api/session/{id}`     | Invalidate a session (disconnect)        |
| POST   | `/api/query`            | NL → SQL via Gemini, then execute        |
| POST   | `/api/execute`          | Execute raw SQL directly                 |

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

**Response includes `session_id`** — use this for all subsequent requests. Credentials are never sent again.

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

## SQLite Quick Start (no server needed)

1. Create a test SQLite database:

```python
import sqlite3
conn = sqlite3.connect("test.db")
conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, score REAL)")
conn.execute("INSERT INTO users VALUES (1,'Alice','alice@example.com',98.5)")
conn.execute("INSERT INTO users VALUES (2,'Bob','bob@example.com',82.1)")
conn.commit()
conn.close()
print("Created test.db")
```

2. In the app, select **SQLite**, enter the full path to `test.db`, and click **Connect**.
3. Try: *"Show me all users sorted by score"*

---

## Environment Variables

| Variable        | Required | Description            |
|-----------------|----------|------------------------|
| `GEMINI_API_KEY`| ✅ Yes   | Your Gemini API key    |

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | FastAPI + Uvicorn                   |
| AI       | Google Gemini 2.5 Pro (via google-genai SDK) |
| Database | SQLAlchemy + psycopg2 / pymysql     |
| Frontend | React 18 + TypeScript + Vite        |
| Styling  | Vanilla CSS (dark design system)    |
| HTTP     | Axios                               |
| Syntax   | react-syntax-highlighter            |
| Testing  | pytest + httpx + pytest-cov         |

---

## Security Design

Credentials travel over the wire **only once** — in the `POST /api/connect` request. The server stores the connection URL in a server-side session (1-hour TTL) and returns a UUID `session_id`. All subsequent query and execute requests carry only the `session_id`. This means:

- Passwords never appear in browser network logs for normal query traffic
- Sessions auto-expire after 1 hour of inactivity
- Clients can explicitly disconnect via `DELETE /api/session/{id}`

---

## Troubleshooting

**`ModuleNotFoundError`** → Make sure your venv is activated and `pip install -r requirements.txt` was run.

**`401 Unauthorized` from the API** → Your session may have expired (1-hour TTL). Click Connect again.

**`401 Unauthorized` from Gemini** → Check your `GEMINI_API_KEY` in `.env`.

**CORS errors** → Backend must be running on port 8000. Frontend proxy in `vite.config.ts` handles this automatically in dev.

**PostgreSQL connection refused** → Check that your PostgreSQL server is running and credentials are correct.

**SQLite path errors** → Use an absolute path, e.g. `C:\Users\you\mydb.sqlite` on Windows.
