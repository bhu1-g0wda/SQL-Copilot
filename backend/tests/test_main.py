"""
test_main.py — pytest test suite for SQL Copilot backend

Run from the backend/ directory:
    pytest tests/ -v --cov=. --cov-report=term-missing

Covers:
  - Health endpoint
  - /api/connect  (SQLite happy path + bad path)
  - /api/execute  (SELECT, DML undo capture)
  - /api/query    (mocked Gemini)
  - /api/session  (DELETE endpoint)
  - build_connection_url helpers
  - schema_to_prompt formatting
  - _quote() for all Python types
  - generate_undo_sql for UPDATE / DELETE / INSERT
  - generate_insert_undo for SQLite
  - _extract_where regex
  - Pydantic validator on db_type
"""

import os
import sqlite3
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

# ── make sure we pick up .env if present ──────────────────────────────────────
os.environ.setdefault("GEMINI_API_KEY", "test-key-not-used-in-unit-tests")

from main import (
    app,
    build_connection_url,
    schema_to_prompt,
    get_schema,
    execute_sql,
    generate_undo_sql,
    generate_insert_undo,
    _quote,
    _extract_where,
    _sessions,
)

client = TestClient(app)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db():
    """Creates a temporary SQLite DB with a small products table."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE products (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL,
            price REAL    NOT NULL
        )
    """)
    conn.execute("INSERT INTO products (name, price) VALUES ('Widget', 9.99)")
    conn.execute("INSERT INTO products (name, price) VALUES ('Gadget', 49.99)")
    conn.commit()
    conn.close()
    yield path
    os.unlink(path)


@pytest.fixture()
def tmp_engine(tmp_db):
    """SQLAlchemy engine pointing at tmp_db."""
    engine = create_engine(f"sqlite:///{tmp_db}")
    yield engine
    engine.dispose()


@pytest.fixture()
def session_id(tmp_db):
    """Calls /api/connect and returns the session_id."""
    resp = client.post("/api/connect", json={"db_type": "sqlite", "database": tmp_db})
    assert resp.status_code == 200
    return resp.json()["session_id"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Health endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "SQL Copilot" in body["message"]


# ─────────────────────────────────────────────────────────────────────────────
# 2. /api/connect
# ─────────────────────────────────────────────────────────────────────────────

def test_connect_sqlite_happy(tmp_db):
    resp = client.post("/api/connect", json={"db_type": "sqlite", "database": tmp_db})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "session_id" in body
    assert "schema" in body
    assert "products" in body["schema"]


def test_connect_sqlite_bad_path():
    resp = client.post("/api/connect", json={
        "db_type": "sqlite",
        "database": "/nonexistent/path/db.sqlite",
    })
    # SQLite creates the file on connect — the SELECT 1 should still pass,
    # but get_schema will return an empty schema (no tables).
    # What matters is the endpoint doesn't 500.
    assert resp.status_code in (200, 400)


def test_connect_unsupported_db_type():
    resp = client.post("/api/connect", json={
        "db_type": "oracle",
        "database": "mydb",
    })
    # Pydantic field_validator raises 422 Unprocessable Entity (FastAPI standard)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    # detail is a list of validation errors from Pydantic
    assert any("db_type" in str(d) or "must be one of" in str(d) for d in detail)


def test_connect_returns_session_in_store(tmp_db):
    _sessions.clear()
    resp = client.post("/api/connect", json={"db_type": "sqlite", "database": tmp_db})
    sid = resp.json()["session_id"]
    assert sid in _sessions


# ─────────────────────────────────────────────────────────────────────────────
# 3. /api/session DELETE
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_session(session_id):
    resp = client.delete(f"/api/session/{session_id}")
    assert resp.status_code == 200
    assert session_id not in _sessions


def test_delete_session_not_found():
    resp = client.delete("/api/session/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 4. /api/execute
# ─────────────────────────────────────────────────────────────────────────────

def test_execute_select_via_session(session_id):
    resp = client.post("/api/execute", json={
        "session_id": session_id,
        "sql": "SELECT id, name, price FROM products ORDER BY id",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["columns"] == ["id", "name", "price"]
    assert len(body["rows"]) == 2
    assert body["rows"][0][1] == "Widget"


def test_execute_bad_sql(session_id):
    resp = client.post("/api/execute", json={
        "session_id": session_id,
        "sql": "SELECT * FROM nonexistent_table_xyz",
    })
    assert resp.status_code == 400


def test_execute_invalid_session():
    resp = client.post("/api/execute", json={
        "session_id": "00000000-0000-0000-0000-000000000000",
        "sql": "SELECT 1",
    })
    assert resp.status_code == 401


def test_execute_insert_produces_undo(session_id):
    resp = client.post("/api/execute", json={
        "session_id": session_id,
        "sql": "INSERT INTO products (name, price) VALUES ('Doohickey', 1.99)",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    # undo_sql should be a DELETE statement
    assert body["undo_sql"] is not None
    assert "DELETE" in body["undo_sql"].upper()


def test_execute_delete_produces_undo(session_id):
    resp = client.post("/api/execute", json={
        "session_id": session_id,
        "sql": "DELETE FROM products WHERE name = 'Widget'",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["undo_sql"] is not None
    assert "INSERT" in body["undo_sql"].upper()


def test_execute_update_produces_undo(session_id):
    resp = client.post("/api/execute", json={
        "session_id": session_id,
        "sql": "UPDATE products SET price = 99.99 WHERE name = 'Gadget'",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["undo_sql"] is not None
    assert "UPDATE" in body["undo_sql"].upper()


# ─────────────────────────────────────────────────────────────────────────────
# 5. /api/query (monkeypatched — no real Gemini call)
# ─────────────────────────────────────────────────────────────────────────────

def test_query_nl_to_sql(session_id, monkeypatch):
    import main as m
    monkeypatch.setattr(m, "nl_to_sql",
        lambda nl, schema, db_type: "SELECT id, name, price FROM products ORDER BY id")

    resp = client.post("/api/query", json={
        "session_id": session_id,
        "natural_language_query": "show me all products",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "SELECT" in body["sql"].upper()
    assert len(body["rows"]) == 2


def test_query_invalid_session(monkeypatch):
    import main as m
    monkeypatch.setattr(m, "nl_to_sql", lambda *a, **kw: "SELECT 1")
    resp = client.post("/api/query", json={
        "session_id": "00000000-0000-0000-0000-000000000000",
        "natural_language_query": "anything",
    })
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 6. build_connection_url
# ─────────────────────────────────────────────────────────────────────────────

class _Req:
    """Minimal stand-in for a Pydantic request model."""
    def __init__(self, db_type, database, host="localhost", port=None, username=None, password=None):
        self.db_type  = db_type
        self.database = database
        self.host     = host
        self.port     = port
        self.username = username
        self.password = password


def test_build_url_sqlite():
    url = build_connection_url(_Req("sqlite", "/tmp/test.db"))
    assert url == "sqlite:////tmp/test.db"


def test_build_url_postgresql():
    url = build_connection_url(_Req("postgresql", "mydb", host="pg-host", port=5432,
                                    username="admin", password="secret"))
    assert "postgresql+psycopg2" in url
    assert "pg-host:5432" in url
    assert "mydb" in url


def test_build_url_mysql():
    url = build_connection_url(_Req("mysql", "shop", host="my-host", port=3306,
                                    username="root", password="pass"))
    assert "mysql+pymysql" in url
    assert "my-host:3306" in url


def test_build_url_unsupported():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        build_connection_url(_Req("oracle", "mydb"))
    assert exc_info.value.status_code == 400


def test_build_url_postgresql_default_port():
    url = build_connection_url(_Req("postgresql", "mydb", username="u", password="p"))
    assert ":5432/" in url


def test_build_url_mysql_default_port():
    url = build_connection_url(_Req("mysql", "mydb", username="u", password="p"))
    assert ":3306/" in url


# ─────────────────────────────────────────────────────────────────────────────
# 7. schema_to_prompt
# ─────────────────────────────────────────────────────────────────────────────

def test_schema_to_prompt_basic():
    schema = {
        "users": {
            "columns": [
                {"name": "id",    "type": "INTEGER", "nullable": False},
                {"name": "email", "type": "TEXT",    "nullable": True},
            ],
            "primary_keys": ["id"],
            "foreign_keys": [],
        }
    }
    prompt = schema_to_prompt(schema)
    assert "Table `users`" in prompt
    assert "id (INTEGER)" in prompt
    assert "Primary Keys: id" in prompt


def test_schema_to_prompt_with_fk():
    schema = {
        "orders": {
            "columns": [{"name": "user_id", "type": "INTEGER", "nullable": False}],
            "primary_keys": [],
            "foreign_keys": [{
                "constrained_columns": ["user_id"],
                "referred_table": "users",
                "referred_columns": ["id"],
            }],
        }
    }
    prompt = schema_to_prompt(schema)
    assert "FK:" in prompt
    assert "users" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# 8. _quote helper
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, expected", [
    (None,         "NULL"),
    (True,         "1"),
    (False,        "0"),
    (42,           "42"),
    (3.14,         "3.14"),
    ("hello",      "'hello'"),
    ("it's a test","'it''s a test'"),   # single-quote escaping
    ("",           "''"),
])
def test_quote(value, expected):
    assert _quote(value) == expected


# ─────────────────────────────────────────────────────────────────────────────
# 9. _extract_where
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("sql, expected", [
    ("DELETE FROM t WHERE id = 1",                   "id = 1"),
    ("UPDATE t SET x=1 WHERE y > 2 ORDER BY z",      "y > 2"),
    ("SELECT * FROM t WHERE a = 'b' LIMIT 10",       "a = 'b'"),
    ("SELECT * FROM t",                               None),
    ("DELETE FROM t WHERE id = 1 AND name = 'foo'",  "id = 1 AND name = 'foo'"),
])
def test_extract_where(sql, expected):
    assert _extract_where(sql) == expected


# ─────────────────────────────────────────────────────────────────────────────
# 10. generate_undo_sql (unit — uses real in-memory SQLite)
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_undo_update(tmp_engine):
    undo = generate_undo_sql(
        tmp_engine,
        "UPDATE products SET price = 0.01 WHERE name = 'Widget'",
        "sqlite",
    )
    assert undo is not None
    assert "UPDATE products SET" in undo
    assert "9.99" in undo          # original price must be preserved


def test_generate_undo_delete(tmp_engine):
    undo = generate_undo_sql(
        tmp_engine,
        "DELETE FROM products WHERE name = 'Gadget'",
        "sqlite",
    )
    assert undo is not None
    assert "INSERT INTO products" in undo
    assert "Gadget" in undo


def test_generate_undo_insert_sentinel(tmp_engine):
    undo = generate_undo_sql(
        tmp_engine,
        "INSERT INTO products (name, price) VALUES ('NewItem', 5.0)",
        "sqlite",
    )
    assert undo == "__POST_INSERT__"


def test_generate_undo_select_returns_none(tmp_engine):
    undo = generate_undo_sql(tmp_engine, "SELECT * FROM products", "sqlite")
    assert undo is None


# ─────────────────────────────────────────────────────────────────────────────
# 11. generate_insert_undo (post-insert capture)
# ─────────────────────────────────────────────────────────────────────────────

def test_generate_insert_undo_sqlite(tmp_engine):
    with tmp_engine.connect() as conn:
        conn.execute(text("INSERT INTO products (name, price) VALUES ('TempItem', 7.77)"))
        conn.commit()

    undo = generate_insert_undo(
        tmp_engine,
        "INSERT INTO products (name, price) VALUES ('TempItem', 7.77)",
        "sqlite",
    )
    assert undo is not None
    assert "DELETE FROM products WHERE" in undo


# ─────────────────────────────────────────────────────────────────────────────
# 12. get_schema integrity
# ─────────────────────────────────────────────────────────────────────────────

def test_get_schema(tmp_engine):
    schema = get_schema(tmp_engine)
    assert "products" in schema
    col_names = [c["name"] for c in schema["products"]["columns"]]
    assert "id" in col_names
    assert "name" in col_names
    assert "price" in col_names
    assert schema["products"]["primary_keys"] == ["id"]


# ─────────────────────────────────────────────────────────────────────────────
# 13. execute_sql
# ─────────────────────────────────────────────────────────────────────────────

def test_execute_sql_select(tmp_engine):
    result = execute_sql(tmp_engine, "SELECT name, price FROM products ORDER BY id")
    assert result["columns"] == ["name", "price"]
    assert result["rowcount"] == 2
    assert result["rows"][0][0] == "Widget"


def test_execute_sql_insert_rowcount(tmp_engine):
    result = execute_sql(tmp_engine, "INSERT INTO products (name, price) VALUES ('X', 1.0)")
    assert result["rowcount"] == 1
    assert result["columns"] == []
