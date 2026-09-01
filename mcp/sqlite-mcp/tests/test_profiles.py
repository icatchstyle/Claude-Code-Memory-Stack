"""Tests for the guardrail. This is the part worth testing: everything else is plumbing."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from sqlite_mcp.profiles import (  # noqa: E402
    Profile,
    ReadOnlyViolation,
    assert_read_only,
    load_profiles,
    run_query,
    statements,
)


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, customer TEXT, total REAL)")
    conn.executemany(
        "INSERT INTO orders (customer, total) VALUES (?, ?)",
        [(f"customer-{i}", i * 10.0) for i in range(1, 21)],
    )
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture()
def ro(db):
    return Profile(name="ro", path=db, read_only=True)


@pytest.fixture()
def rw(db):
    return Profile(name="rw", path=db, read_only=False)


# --------------------------------------------------------------- the guardrail

@pytest.mark.parametrize("sql", [
    "INSERT INTO orders (customer) VALUES ('x')",
    "UPDATE orders SET total = 0",
    "DELETE FROM orders",
    "DROP TABLE orders",
    "ALTER TABLE orders ADD COLUMN x TEXT",
    "CREATE TABLE t (a INT)",
    "ATTACH DATABASE '/tmp/other.db' AS other",
    "PRAGMA journal_mode = WAL",
    "  update orders set total = 1",                      # leading space, lower case
    "/* comment */ DELETE FROM orders",                   # hidden behind a block comment
    "-- comment\nDELETE FROM orders",                     # hidden behind a line comment
    "SELECT 1; DELETE FROM orders",                       # batch where only the tail mutates
])
def test_mutating_sql_is_refused(sql):
    with pytest.raises(ReadOnlyViolation):
        assert_read_only(sql)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM orders",
    "select count(*) from orders",
    "WITH x AS (SELECT 1) SELECT * FROM x",
    "  SELECT 'this string contains the word update' AS note",   # keyword only inside a literal
    "EXPLAIN SELECT * FROM orders",
])
def test_reads_are_allowed(sql):
    assert_read_only(sql)


def test_read_only_profile_refuses_writes_end_to_end(ro):
    with pytest.raises(ReadOnlyViolation):
        run_query(ro, "DELETE FROM orders")


def test_sqlite_itself_also_refuses(ro):
    # Second, independent guard: even a statement that slipped past the check cannot write,
    # because a read-only profile opens the file in SQLite's own read-only mode.
    with ro.connect() as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM orders")


def test_writable_profile_allows_writes(rw):
    run_query(rw, "DELETE FROM orders WHERE id = 1")
    assert run_query(rw, "SELECT COUNT(*) AS n FROM orders")["rows"][0]["n"] == 19


# --------------------------------------------------------------- output bounding

def test_results_are_capped_and_say_so(ro):
    result = run_query(ro, "SELECT * FROM orders", limit=5)
    assert result["row_count"] == 5
    assert result["truncated"] is True
    assert "capped" in result["hint"]


def test_untruncated_result_carries_no_hint(ro):
    result = run_query(ro, "SELECT * FROM orders WHERE id <= 3", limit=10)
    assert result["truncated"] is False
    assert result["hint"] is None


def test_limit_cannot_exceed_the_server_cap(ro):
    assert run_query(ro, "SELECT * FROM orders", limit=10_000)["row_count"] == 20


# --------------------------------------------------------------- parsing and config

def test_statements_strips_comments():
    assert statements("SELECT 1; -- drop everything\nSELECT 2") == ["SELECT 1", "SELECT 2"]


def test_profiles_are_read_from_the_environment(monkeypatch, db):
    monkeypatch.setenv("SQLITE_MCP_PROFILES", f"prod={db}:ro,local={db}:rw")
    profiles = load_profiles()
    assert profiles["prod"].read_only is True
    assert profiles["local"].read_only is False


def test_malformed_profile_is_rejected_loudly(monkeypatch):
    monkeypatch.setenv("SQLITE_MCP_PROFILES", "broken-entry")
    with pytest.raises(SystemExit):
        load_profiles()


def test_unknown_mode_is_rejected(monkeypatch, db):
    monkeypatch.setenv("SQLITE_MCP_PROFILES", f"x={db}:maybe")
    with pytest.raises(SystemExit):
        load_profiles()
