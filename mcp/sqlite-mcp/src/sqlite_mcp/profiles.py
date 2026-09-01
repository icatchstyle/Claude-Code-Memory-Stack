"""Named connection profiles with read-only enforced in code.

This is the whole point of the module, and the claim the documentation rests on: a profile marked
read-only rejects mutating SQL *server-side*. The model cannot argue with it, cannot rephrase its
way past it, and cannot be persuaded that this once it is fine — because the refusal is not a
judgement call, it is a branch.

The same rule written in CLAUDE.md is a strong suggestion. That difference is the entire argument
for putting a server in front of a system instead of handing over a shell.
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Statements that change data or schema. Matched on the first keyword of each statement, so a
# SELECT that merely contains the word "update" in a string literal is unaffected.
MUTATING = {
    "insert", "update", "delete", "replace", "drop", "create", "alter", "truncate",
    "attach", "detach", "vacuum", "reindex", "pragma", "begin", "commit", "rollback",
}

# Strip comments before inspecting, so `/* harmless */ DELETE FROM t` cannot slip through.
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT = re.compile(r"--[^\n]*")

MAX_ROWS = 500


class ReadOnlyViolation(Exception):
    """Raised when a mutating statement is sent to a read-only profile."""


@dataclass(frozen=True)
class Profile:
    name: str
    path: str
    read_only: bool
    description: str = ""

    def connect(self) -> sqlite3.Connection:
        """Open the database.

        Belt and braces: read-only profiles are opened through SQLite's own read-only URI mode as
        well. Even a statement that slipped past the check above cannot write, because the engine
        itself refuses. One guard is a rule; two independent guards is a property.
        """
        if self.read_only:
            uri = f"file:{Path(self.path).as_posix()}?mode=ro"
            conn = sqlite3.connect(uri, uri=True)
        else:
            conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn


def statements(sql: str) -> list[str]:
    """Split into statements, with comments removed."""
    cleaned = LINE_COMMENT.sub(" ", BLOCK_COMMENT.sub(" ", sql))
    return [s.strip() for s in cleaned.split(";") if s.strip()]


def assert_read_only(sql: str) -> None:
    """Raise if the SQL contains anything that could change data or schema.

    Note what this does NOT do: it does not try to be clever about intent. Anything whose first
    keyword is not a read is refused, including multi-statement batches where only one part
    mutates. Refusing too much is recoverable; allowing too much is not.
    """
    for stmt in statements(sql):
        first = re.split(r"\W+", stmt.lstrip("( \t\n"), maxsplit=1)[0].lower()
        if first in MUTATING:
            raise ReadOnlyViolation(
                f"Statement '{first.upper()}' is not allowed on a read-only profile. "
                f"Use a writable profile, or rewrite the query as a SELECT."
            )
        if not first:
            raise ReadOnlyViolation("Empty statement.")


def load_profiles() -> dict[str, Profile]:
    """Read profiles from the environment.

    Format: SQLITE_MCP_PROFILES="name=/path/to.db:ro,other=/path/other.db:rw"

    Deliberately not a config file the agent could edit: the set of things it may touch is
    defined outside its reach, by whoever starts the server.
    """
    raw = os.environ.get("SQLITE_MCP_PROFILES", "").strip()
    if not raw:
        raise SystemExit(
            "SQLITE_MCP_PROFILES is not set. Example:\n"
            '  SQLITE_MCP_PROFILES="prod=/data/app.db:ro,local=/data/dev.db:rw"'
        )

    profiles: dict[str, Profile] = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            name, rest = entry.split("=", 1)
            path, mode = rest.rsplit(":", 1)
        except ValueError:
            raise SystemExit(f"Malformed profile entry: {entry!r} (expected name=/path.db:ro)")
        if mode not in ("ro", "rw"):
            raise SystemExit(f"Profile {name!r}: mode must be 'ro' or 'rw', got {mode!r}")
        profiles[name.strip()] = Profile(
            name=name.strip(), path=path.strip(), read_only=(mode == "ro")
        )
    return profiles


def run_query(profile: Profile, sql: str, limit: int = MAX_ROWS) -> dict:
    """Execute a query and return rows, capped.

    The cap is not advice. An uncapped result is how one tool call fills the context and makes
    every turn after it worse and more expensive.
    """
    if profile.read_only:
        assert_read_only(sql)

    limit = max(1, min(limit, MAX_ROWS))
    with profile.connect() as conn:
        cur = conn.execute(sql)
        rows = cur.fetchmany(limit + 1)
        truncated = len(rows) > limit
        rows = rows[:limit]
        columns = [d[0] for d in cur.description] if cur.description else []

    return {
        "profile": profile.name,
        "columns": columns,
        "rows": [dict(r) for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
        "hint": (
            f"Result capped at {limit} rows. Narrow it with WHERE, or aggregate."
            if truncated else None
        ),
    }
