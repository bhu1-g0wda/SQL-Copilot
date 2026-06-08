# SQL Copilot ⚡

An AI-powered SQL assistant that converts natural language to SQL using **Claude Sonnet 4**, with a beautiful dark-themed React UI and a FastAPI backend.

## Features

- 🤖 **Natural language → SQL** via Claude Sonnet 4
- 🗄️ **Multi-database support** — PostgreSQL, MySQL, SQLite
- 🌳 **Schema explorer** — live tree view of tables and columns
- 🔍 **Syntax-highlighted SQL** display with copy button
- 📊 **Paginated results table** for large result sets
- ✏️ **Edit & re-run** generated SQL directly
- ⚠️ **Confirmation modal** for destructive operations (DELETE, UPDATE, DROP, TRUNCATE)
- 🔄 **Mode toggle** — switch between Natural Language and Raw SQL mode

---

## Project Structure

```
sql-copilot/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── requirements.txt     # Python deps
│   └── .env.example         # Environment variable template
└── frontend/
    ├── src/
    │   ├── App.tsx           # Main application
    │   ├── index.css         # Global design system
    │   ├── api/
    │   │   └── client.ts     # Axios API client
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
- **Anthropic API Key** — get one at https://console.anthropic.com

For PostgreSQL: `psycopg2-binary` is included (no extra install needed)  
For MySQL: `pymysql` is included  
For SQLite: built-in, no extra server needed

---

## Installation & Setup

### 1. Clone / open the project

```bash
cd "sql copliot"
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

# Edit .env and add your Anthropic API key:
# ANTHROPIC_API_KEY=sk-ant-...
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

## API Reference

| Method | Endpoint        | Description                          |
|--------|-----------------|--------------------------------------|
| GET    | `/api/health`   | Health check                         |
| POST   | `/api/connect`  | Connect to DB and retrieve schema    |
| POST   | `/api/query`    | NL → SQL via Claude, then execute    |
| POST   | `/api/execute`  | Execute raw SQL directly             |

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

### POST /api/query

```json
{
  "natural_language_query": "Show me the top 10 customers by revenue",
  "db_type": "postgresql",
  "host": "localhost",
  "port": 5432,
  "database": "mydb",
  "username": "postgres",
  "password": "secret"
}
```

### POST /api/execute

```json
{
  "sql": "SELECT * FROM customers LIMIT 5;",
  "db_type": "sqlite",
  "database": "/path/to/db.sqlite"
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

| Variable           | Required | Description               |
|--------------------|----------|---------------------------|
| `ANTHROPIC_API_KEY`| ✅ Yes   | Your Anthropic API key    |

---

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | FastAPI + Uvicorn                   |
| AI       | Anthropic SDK (Claude Sonnet 4)     |
| Database | SQLAlchemy + psycopg2 / pymysql     |
| Frontend | React 18 + TypeScript + Vite        |
| Styling  | Vanilla CSS (dark design system)    |
| HTTP     | Axios                               |
| Syntax   | react-syntax-highlighter            |

---

## Troubleshooting

**`ModuleNotFoundError`** → Make sure your venv is activated and `pip install -r requirements.txt` was run.

**`401 Unauthorized` from Anthropic** → Check your `ANTHROPIC_API_KEY` in `.env`.

**CORS errors** → Backend must be running on port 8000. Frontend proxy in `vite.config.ts` handles this automatically in dev.

**PostgreSQL connection refused** → Check that your PostgreSQL server is running and credentials are correct.

**SQLite path errors** → Use an absolute path, e.g. `C:\Users\you\mydb.sqlite` on Windows.
