"""MCP server exposing SQLite databases through named, permission-scoped profiles.

A companion to vault-mcp, demonstrating the one pattern that server does not: **a guardrail
enforced in code rather than in a prompt.** Everything else here is deliberately minimal.

Read docs/05-mcp.md alongside this file — the argument it makes is what this implements.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .profiles import MAX_ROWS, ReadOnlyViolation, load_profiles, run_query

PROFILES = load_profiles()
mcp = FastMCP("sqlite")


def _get(name: str):
    if name not in PROFILES:
        raise ValueError(
            f"Unknown profile {name!r}. Available: {sorted(PROFILES)}. "
            "Call list_profiles first — the set of profiles is defined by whoever started the "
            "server and can change without notice."
        )
    return PROFILES[name]


@mcp.tool()
def list_profiles() -> dict:
    """List the databases this server may reach, and whether each is writable.

    Call this before anything else. Which profiles exist, and which are read-only, is decided
    outside the agent's reach — never assume a name or a permission.
    """
    return {
        "profiles": [
            {
                "name": p.name,
                "read_only": p.read_only,
                "description": p.description,
                "exists": os.path.exists(p.path),
            }
            for p in PROFILES.values()
        ],
        "row_cap": MAX_ROWS,
    }


@mcp.tool()
def query(profile: str, sql: str, limit: int = 100) -> dict:
    """Run SQL against a profile. Read-only profiles reject mutating statements server-side.

    Args:
        profile: a name from list_profiles.
        sql: the statement. On a read-only profile anything but a read is refused.
        limit: maximum rows (capped at 500 regardless).
    """
    p = _get(profile)
    try:
        return run_query(p, sql, limit)
    except ReadOnlyViolation as exc:
        # An error that says what to do next, not a stack trace.
        writable = [n for n, q in PROFILES.items() if not q.read_only]
        raise ValueError(
            f"{exc} Profile {profile!r} is read-only."
            + (f" Writable profiles: {writable}." if writable else " No writable profile exists.")
        ) from None


@mcp.tool()
def list_tables(profile: str) -> dict:
    """List the tables and views in a profile."""
    result = run_query(
        _get(profile),
        "SELECT name, type FROM sqlite_master "
        "WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name",
    )
    return {"profile": profile, "tables": result["rows"]}


@mcp.tool()
def describe_table(profile: str, table: str) -> dict:
    """Show a table's columns, types and keys.

    Args:
        profile: a name from list_profiles.
        table: the table name, as returned by list_tables.
    """
    p = _get(profile)
    # The table name cannot be a bound parameter in PRAGMA, so it is validated against the
    # catalogue instead of interpolated blindly — the injection route this shape invites.
    known = {r["name"] for r in run_query(
        p, "SELECT name FROM sqlite_master WHERE type IN ('table','view')")["rows"]}
    if table not in known:
        raise ValueError(f"Unknown table {table!r} in profile {p.name!r}. Call list_tables first.")

    with p.connect() as conn:
        cols = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
    return {
        "profile": p.name,
        "table": table,
        "columns": [
            {
                "name": c["name"],
                "type": c["type"],
                "not_null": bool(c["notnull"]),
                "default": c["dflt_value"],
                "primary_key": bool(c["pk"]),
            }
            for c in cols
        ],
    }


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        mcp.settings.host = os.environ.get("MCP_HOST", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("MCP_PORT", "8766"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
