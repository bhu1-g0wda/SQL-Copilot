"""
benchmark.py -- SQL Copilot performance evaluator

Runs a suite of natural-language queries against the live backend,
measures response time, and checks whether each generated SQL:
  1. Executes without error
  2. Returns a non-empty result (for SELECT queries)
  3. Contains expected keywords (correctness signal)

Usage:
    python benchmark.py

Requirements: backend must be running on http://localhost:8000
              and sample_store.db must be in the backend/ folder
"""

import os
import sys
import time
import json
import requests

# Force UTF-8 output so special chars don't crash on Windows cp1252 terminals
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# -- Config -------------------------------------------------------------------
BASE_URL    = "http://localhost:8000/api"
DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_store.db")
TIMEOUT_SEC = 60   # Gemini can take a while on complex queries

# -- Test suite ---------------------------------------------------------------
# Each entry:
#   "query"    : natural language string sent to /api/query
#   "level"    : "simple" | "medium" | "complex"
#   "must_have": keywords the generated SQL MUST contain (case-insensitive)
#   "must_run" : True = the SQL must execute without error
#   "must_rows": True = result must contain at least 1 row
TEST_SUITE = [
    # Simple
    {
        "query":     "Show me all products",
        "level":     "simple",
        "must_have": ["SELECT", "products"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "How many customers do we have?",
        "level":     "simple",
        "must_have": ["COUNT", "customers"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "List all product categories",
        "level":     "simple",
        "must_have": ["SELECT", "categories"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "Show me all orders with status cancelled",
        "level":     "simple",
        "must_have": ["SELECT", "orders", "cancelled"],
        "must_run":  True,
        "must_rows": False,
    },
    # Medium
    {
        "query":     "What are the top 5 most expensive products?",
        "level":     "medium",
        "must_have": ["SELECT", "products", "price", "LIMIT"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "Show me total revenue per product category",
        "level":     "medium",
        "must_have": ["SUM", "GROUP BY", "categories"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "Which customers joined in the last year?",
        "level":     "medium",
        "must_have": ["SELECT", "customers", "joined_at"],
        "must_run":  True,
        "must_rows": False,
    },
    {
        "query":     "Find products with less than 10 items in stock",
        "level":     "medium",
        "must_have": ["SELECT", "products", "stock"],
        "must_run":  True,
        "must_rows": False,
    },
    {
        "query":     "What is the average order value?",
        "level":     "medium",
        "must_have": ["AVG", "orders"],
        "must_run":  True,
        "must_rows": True,
    },
    # Complex
    {
        "query":     "Show me the top 5 customers by total amount spent, with their email",
        "level":     "complex",
        "must_have": ["JOIN", "customers", "orders", "SUM", "GROUP BY", "LIMIT"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "What is the total revenue per month for this year?",
        "level":     "complex",
        "must_have": ["SUM", "orders", "GROUP BY"],
        "must_run":  True,
        "must_rows": False,
    },
    {
        "query":     "Show me the average product rating per category",
        "level":     "complex",
        "must_have": ["AVG", "reviews", "categories", "JOIN", "GROUP BY"],
        "must_run":  True,
        "must_rows": True,
    },
    {
        "query":     "Which products have never been ordered?",
        "level":     "complex",
        "must_have": ["products", "order_items"],
        "must_run":  True,
        "must_rows": False,
    },
    {
        "query":     "Show month-over-month revenue growth as a percentage for the last 6 months",
        "level":     "complex",
        "must_have": ["strftime", "orders", "LAG"],
        "must_run":  True,
        "must_rows": False,
    },
    {
        "query":     "Find the top 3 best-selling products by total quantity sold, including category name",
        "level":     "complex",
        "must_have": ["SUM", "order_items", "products", "categories", "JOIN", "GROUP BY", "LIMIT"],
        "must_run":  True,
        "must_rows": True,
    },
]


# -- Helpers ------------------------------------------------------------------

def connect() -> str:
    resp = requests.post(f"{BASE_URL}/connect", json={
        "db_type":  "sqlite",
        "database": DB_PATH,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()["session_id"]


def run_query(session_id: str, nl_query: str) -> dict:
    t0 = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/query", json={
        "session_id":             session_id,
        "natural_language_query": nl_query,
    }, timeout=TIMEOUT_SEC)
    elapsed = time.perf_counter() - t0
    return {
        "status_code": resp.status_code,
        "elapsed_s":   round(elapsed, 2),
        "body":        resp.json() if resp.status_code == 200 else {"detail": resp.text},
    }


def check(result: dict, test: dict) -> dict:
    ok_http  = result["status_code"] == 200
    body     = result["body"]
    sql      = body.get("sql", "") if ok_http else ""
    rows     = body.get("rows", []) if ok_http else []

    sql_upper  = sql.upper()
    kw_hits    = [kw for kw in test["must_have"] if kw.upper() in sql_upper]
    kw_misses  = [kw for kw in test["must_have"] if kw.upper() not in sql_upper]
    kw_score   = len(kw_hits) / len(test["must_have"]) if test["must_have"] else 1.0

    run_ok  = ok_http if test["must_run"] else True
    rows_ok = (len(rows) > 0) if test["must_rows"] else True
    passed  = run_ok and rows_ok and kw_score == 1.0

    return {
        "query":     test["query"],
        "level":     test["level"],
        "elapsed_s": result["elapsed_s"],
        "http_ok":   ok_http,
        "run_ok":    run_ok,
        "rows_ok":   rows_ok,
        "kw_score":  round(kw_score * 100, 1),
        "kw_misses": kw_misses,
        "passed":    passed,
        "sql":       sql[:120] + ("..." if len(sql) > 120 else ""),
        "error":     body.get("detail", "") if not ok_http else "",
    }


# -- Main ---------------------------------------------------------------------

def main():
    SEP = "=" * 70
    print(SEP)
    print("  SQL Copilot -- Benchmark & Performance Evaluation")
    print(SEP)
    print(f"  Database : {DB_PATH}")
    print(f"  Queries  : {len(TEST_SUITE)}")
    print()

    print("Connecting to backend...", end=" ", flush=True)
    try:
        session_id = connect()
        print(f"OK (session: {session_id[:8]}...)")
    except Exception as e:
        print(f"FAILED -- {e}")
        print("Is the backend running on http://localhost:8000?")
        return

    reports   = []
    latencies = []

    for i, test in enumerate(TEST_SUITE, 1):
        tag     = f"[{test['level'].upper():<7}]"
        short_q = test["query"][:55] + ("..." if len(test["query"]) > 55 else "")
        print(f"  {i:02d}/{len(TEST_SUITE)} {tag} {short_q}", end=" ", flush=True)

        # Auto-reconnect up to 2 times on connection drop or session expiry
        result = None
        for attempt in range(3):
            try:
                result = run_query(session_id, test["query"])
                # 401 = session lost (server restarted); reconnect and retry
                if result["status_code"] == 401 and attempt < 2:
                    print(f"(reconnecting...)", end=" ", flush=True)
                    session_id = connect()
                    continue
                break
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as e:
                if attempt < 2:
                    time.sleep(2)
                    try:
                        session_id = connect()
                    except Exception:
                        pass
                    continue
                print(f"ERROR: {e}")
                result = None
                break

        if result is None:
            print("TIMEOUT")
            reports.append({**test, "elapsed_s": TIMEOUT_SEC, "http_ok": False,
                             "run_ok": False, "rows_ok": False,
                             "kw_score": 0, "kw_misses": test["must_have"],
                             "passed": False, "sql": "", "error": "Timeout"})
            continue
            print(f"ERROR: {e}")
            continue

        report = check(result, test)
        reports.append(report)
        latencies.append(report["elapsed_s"])

        status = "[PASS]" if report["passed"] else "[FAIL]"
        print(f"{status}  ({report['elapsed_s']}s)  kw:{report['kw_score']}%")

        if report["kw_misses"]:
            print(f"         ! Missing keywords: {', '.join(report['kw_misses'])}")
        if report["error"]:
            print(f"         x Error: {report['error'][:80]}")

    # -- Summary --------------------------------------------------------------
    print()
    print(SEP)
    print("  RESULTS SUMMARY")
    print(SEP)

    total  = len(reports)
    passed = sum(1 for r in reports if r["passed"])

    by_level: dict = {}
    for r in reports:
        lvl = r["level"]
        by_level.setdefault(lvl, {"pass": 0, "total": 0})
        by_level[lvl]["total"] += 1
        if r["passed"]:
            by_level[lvl]["pass"] += 1

    avg_lat = round(sum(latencies) / len(latencies), 2) if latencies else 0
    min_lat = round(min(latencies), 2) if latencies else 0
    max_lat = round(max(latencies), 2) if latencies else 0

    print(f"\n  Overall accuracy   : {passed}/{total}  ({round(passed/total*100, 1)}%)")
    print(f"  Avg response time  : {avg_lat}s")
    print(f"  Min / Max latency  : {min_lat}s / {max_lat}s")
    print()

    for lvl in ["simple", "medium", "complex"]:
        if lvl not in by_level:
            continue
        stats = by_level[lvl]
        pct   = round(stats["pass"] / stats["total"] * 100, 1)
        bar   = "#" * stats["pass"] + "-" * (stats["total"] - stats["pass"])
        print(f"  {lvl.capitalize():<8} accuracy  : {stats['pass']}/{stats['total']}  [{bar}]  {pct}%")

    print()
    for lvl in ["simple", "medium", "complex"]:
        lats = [r["elapsed_s"] for r in reports if r["level"] == lvl]
        if lats:
            print(f"  {lvl.capitalize():<8} avg latency: {round(sum(lats)/len(lats), 2)}s")

    print()
    print("  Failed queries:")
    any_failed = False
    for r in reports:
        if not r["passed"]:
            any_failed = True
            print(f"    x [{r['level']}] {r['query'][:60]}")
            if r["kw_misses"]:
                print(f"        Missing: {', '.join(r['kw_misses'])}")

    if not any_failed:
        print("    (none -- all passed!)")

    # Save JSON
    out_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "total":         total,
                "passed":        passed,
                "accuracy_pct":  round(passed / total * 100, 1),
                "avg_latency_s": avg_lat,
                "min_latency_s": min_lat,
                "max_latency_s": max_lat,
                "by_level":      by_level,
            },
            "results": reports,
        }, f, indent=2)

    print(f"\n  Full results saved to: benchmark_results.json")
    print(SEP)


if __name__ == "__main__":
    main()
