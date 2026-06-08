import os
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="SQL Copilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Models ──────────────────────────────────────────────────────────────────

class ConnectionRequest(BaseModel):
    db_type: str
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None

class QueryRequest(BaseModel):
    natural_language_query: str
    db_type: str
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None
    schema_info: Optional[dict] = None

class ExecuteRequest(BaseModel):
    sql: str
    db_type: str
    host: Optional[str] = "localhost"
    port: Optional[int] = None
    database: str
    username: Optional[str] = None
    password: Optional[str] = None

# ── Regex patterns ───────────────────────────────────────────────────────────

_DML_RE      = re.compile(r"^\s*(INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_INSERT_TBL  = re.compile(r"INSERT\s+INTO\s+[`\"'\[]?(\w+)[`\"'\]]?", re.IGNORECASE)
_UPDATE_TBL  = re.compile(r"UPDATE\s+[`\"'\[]?(\w+)[`\"'\]]?", re.IGNORECASE)
_DELETE_TBL  = re.compile(r"DELETE\s+FROM\s+[`\"'\[]?(\w+)[`\"'\]]?", re.IGNORECASE)
_WHERE_RE    = re.compile(
    r"\bWHERE\b(.+?)(?:\bORDER\s+BY\b|\bLIMIT\b|\bGROUP\s+BY\b|\bHAVING\b|$)",
    re.IGNORECASE | re.DOTALL,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def build_connection_url(req) -> str:
    db_type = req.db_type.lower()
    if db_type == "sqlite":
        return f"sqlite:///{req.database}"
    elif db_type == "postgresql":
        port = req.port or 5432
        return f"postgresql+psycopg2://{req.username}:{req.password}@{req.host}:{port}/{req.database}"
    elif db_type == "mysql":
        port = req.port or 3306
        return f"mysql+pymysql://{req.username}:{req.password}@{req.host}:{port}/{req.database}"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported db_type: {req.db_type}")


def get_schema(engine) -> dict:
    inspector = inspect(engine)
    schema = {}
    for table_name in inspector.get_table_names():
        columns = [
            {"name": col["name"], "type": str(col["type"]), "nullable": col.get("nullable", True)}
            for col in inspector.get_columns(table_name)
        ]
        pk  = inspector.get_pk_constraint(table_name)
        fks = inspector.get_foreign_keys(table_name)
        schema[table_name] = {
            "columns": columns,
            "primary_keys": pk.get("constrained_columns", []),
            "foreign_keys": [
                {
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": fk["referred_table"],
                    "referred_columns": fk["referred_columns"],
                }
                for fk in fks
            ],
        }
    return schema


def schema_to_prompt(schema: dict) -> str:
    lines = ["Database Schema:"]
    for table, info in schema.items():
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in info["columns"])
        lines.append(f"  Table `{table}`: {cols}")
        if info["primary_keys"]:
            lines.append(f"    Primary Keys: {', '.join(info['primary_keys'])}")
        if info["foreign_keys"]:
            for fk in info["foreign_keys"]:
                lines.append(f"    FK: {fk['constrained_columns']} -> {fk['referred_table']}({fk['referred_columns']})")
    return "\n".join(lines)


def execute_sql(engine, sql: str) -> dict:
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        conn.commit()
        if result.returns_rows:
            columns = list(result.keys())
            rows    = [list(row) for row in result.fetchall()]
            return {"columns": columns, "rows": rows, "rowcount": len(rows)}
        else:
            return {"columns": [], "rows": [], "rowcount": result.rowcount}


def nl_to_sql(natural_language: str, schema: dict, db_type: str) -> str:
    schema_text = schema_to_prompt(schema)
    system_prompt = f"""You are an expert SQL assistant. Convert natural language queries into accurate SQL statements.

{schema_text}

Target database: {db_type}

Rules:
1. Return ONLY the SQL statement — no explanations, no markdown code fences, no commentary.
2. Use proper SQL syntax for the target database ({db_type}).
3. Always alias columns for clarity when using aggregation.
4. For potentially destructive operations (DELETE, DROP, TRUNCATE), include a comment warning.
5. Never use SELECT * unless the user specifically asks for all columns.
6. If the request is ambiguous, make a reasonable assumption and generate the best SQL you can.
"""
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": natural_language}],
    )
    sql = message.content[0].text.strip()
    if sql.startswith("```"):
        lines = sql.split("\n")
        sql = "\n".join(lines[1:-1]).strip()
    return sql


# ── Undo SQL generation ──────────────────────────────────────────────────────

def _quote(v) -> str:
    """Safely quote a Python value for inclusion in SQL."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    # String — escape single quotes by doubling them
    return "'" + str(v).replace("'", "''") + "'"


def _get_pk_cols(engine, table: str) -> list[str]:
    try:
        inspector = inspect(engine)
        return inspector.get_pk_constraint(table).get("constrained_columns", [])
    except Exception:
        return []


def _fetch_rows(engine, table: str, where_clause: str | None) -> tuple[list[str], list[dict]]:
    """SELECT * from table with optional WHERE; returns (cols, list_of_dicts)."""
    sql = f"SELECT * FROM {table}"
    if where_clause:
        sql += f" WHERE {where_clause}"
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        cols = list(result.keys())
        rows = [dict(zip(cols, row)) for row in result.fetchall()]
    return cols, rows


def _extract_where(sql: str) -> str | None:
    m = _WHERE_RE.search(sql)
    return m.group(1).strip() if m else None


def generate_undo_sql(engine, sql: str, db_type: str) -> str | None:
    """
    Generate inverse SQL for a DML statement.
    Must be called BEFORE execution for UPDATE/DELETE.
    Returns None if undo is not possible, or the sentinel '__POST_INSERT__' for INSERTs.
    """
    dml_match = _DML_RE.match(sql)
    if not dml_match:
        return None

    dml = dml_match.group(1).upper()

    # ── UPDATE → capture old values, generate reverse UPDATE ────────────────
    if dml == "UPDATE":
        m = _UPDATE_TBL.search(sql)
        if not m:
            return None
        table = m.group(1)
        pk_cols = _get_pk_cols(engine, table)
        where = _extract_where(sql)
        try:
            cols, rows = _fetch_rows(engine, table, where)
        except Exception:
            return None
        if not rows:
            return None

        parts = []
        for row in rows:
            non_pk = [c for c in cols if c not in pk_cols]
            set_clause = ", ".join(f"{c} = {_quote(row[c])}" for c in non_pk)
            if not set_clause:
                continue
            if pk_cols:
                pk_where = " AND ".join(f"{pk} = {_quote(row[pk])}" for pk in pk_cols)
            else:
                # No PK — use all columns to identify the row
                pk_where = " AND ".join(f"{c} = {_quote(row[c])}" for c in cols)
            parts.append(f"UPDATE {table} SET {set_clause} WHERE {pk_where};")
        return "\n".join(parts) if parts else None

    # ── DELETE → capture rows first, generate INSERT to restore them ─────────
    elif dml == "DELETE":
        m = _DELETE_TBL.search(sql)
        if not m:
            return None
        table = m.group(1)
        where = _extract_where(sql)
        try:
            cols, rows = _fetch_rows(engine, table, where)
        except Exception:
            return None
        if not rows:
            return None

        parts = []
        for row in rows:
            col_list = ", ".join(cols)
            val_list = ", ".join(_quote(row[c]) for c in cols)
            parts.append(f"INSERT INTO {table} ({col_list}) VALUES ({val_list});")
        return "\n".join(parts) if parts else None

    # ── INSERT → handled post-execution ─────────────────────────────────────
    elif dml == "INSERT":
        return "__POST_INSERT__"

    return None


def generate_insert_undo(engine, sql: str, db_type: str) -> str | None:
    """
    Generate DELETE undo for an INSERT — called AFTER the INSERT has been executed.
    Uses last_insert_rowid() (SQLite) or LAST_INSERT_ID() (MySQL).
    """
    m = _INSERT_TBL.search(sql)
    if not m:
        return None
    table = m.group(1)
    pk_cols = _get_pk_cols(engine, table)

    try:
        with engine.connect() as conn:
            db = db_type.lower()
            if db == "sqlite":
                result = conn.execute(text(
                    f"SELECT * FROM {table} WHERE rowid = last_insert_rowid()"
                ))
            elif db == "mysql":
                if not pk_cols:
                    return None
                result = conn.execute(text(
                    f"SELECT * FROM {table} WHERE {pk_cols[0]} = LAST_INSERT_ID()"
                ))
            else:
                # PostgreSQL: RETURNING clause needed in original INSERT to capture easily;
                # fall back to None rather than guessing
                return None

            row_data = result.fetchone()
            if not row_data:
                return None
            cols     = list(result.keys())
            row_dict = dict(zip(cols, row_data))

        if pk_cols:
            where = " AND ".join(f"{pk} = {_quote(row_dict[pk])}" for pk in pk_cols)
        else:
            where = " AND ".join(f"{c} = {_quote(row_dict[c])}" for c in cols)

        return f"DELETE FROM {table} WHERE {where};"
    except Exception:
        return None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "SQL Copilot API is running"}


@app.post("/api/connect")
def connect(req: ConnectionRequest):
    try:
        url    = build_connection_url(req)
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        schema = get_schema(engine)
        engine.dispose()
        return {"success": True, "schema": schema, "message": "Connected successfully"}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=f"Database connection failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
def query(req: QueryRequest):
    try:
        url    = build_connection_url(req)
        engine = create_engine(url, pool_pre_ping=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        schema = req.schema_info or get_schema(engine)
        sql    = nl_to_sql(req.natural_language_query, schema, req.db_type)

        # Generate undo BEFORE execution — fully isolated, never affects the query
        try:
            undo_sql = generate_undo_sql(engine, sql, req.db_type)
        except Exception:
            undo_sql = None

        result = execute_sql(engine, sql)

        # Generate undo AFTER execution (INSERT) — also isolated
        if undo_sql == "__POST_INSERT__":
            try:
                undo_sql = generate_insert_undo(engine, sql, req.db_type)
            except Exception:
                undo_sql = None

        return {
            "success":  True,
            "sql":      sql,
            "columns":  result["columns"],
            "rows":     result["rows"],
            "rowcount": result["rowcount"],
            "undo_sql": undo_sql,
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")
    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"AI error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) or "Internal server error")
    finally:
        engine.dispose()


@app.post("/api/execute")
def execute(req: ExecuteRequest):
    try:
        url    = build_connection_url(req)
        engine = create_engine(url, pool_pre_ping=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Generate undo BEFORE execution — fully isolated, never affects the query
        try:
            undo_sql = generate_undo_sql(engine, req.sql, req.db_type)
        except Exception:
            undo_sql = None

        result = execute_sql(engine, req.sql)

        # Generate undo AFTER execution (INSERT) — also isolated
        if undo_sql == "__POST_INSERT__":
            try:
                undo_sql = generate_insert_undo(engine, req.sql, req.db_type)
            except Exception:
                undo_sql = None

        return {
            "success":  True,
            "sql":      req.sql,
            "columns":  result["columns"],
            "rows":     result["rows"],
            "rowcount": result["rowcount"],
            "undo_sql": undo_sql,
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=400, detail=f"SQL execution failed: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) or "Internal server error")
    finally:
        engine.dispose()
