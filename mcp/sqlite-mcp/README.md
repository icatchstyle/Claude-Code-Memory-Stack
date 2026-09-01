# sqlite-mcp — guardrails that cannot be argued with

A second reference server, existing to prove one claim from
[`docs/05-mcp.md`](../../docs/05-mcp.md):

> A read-only profile that rejects mutating SQL **server-side** cannot be talked around. The same
> rule in `CLAUDE.md` is a strong suggestion. That difference is the entire argument.

[`vault-mcp`](../vault-mcp/) shows structured retrieval. This one shows **permission scoping**.
It is deliberately small — SQLite, no dependencies beyond the MCP SDK, one idea.

## Tools

| Tool | Purpose |
|---|---|
| `list_profiles` | Which databases exist, and which are writable. **Call this first.** |
| `query` | Run SQL. Read-only profiles refuse anything that mutates. |
| `list_tables` | Tables and views in a profile |
| `describe_table` | Columns, types, keys |

## Run

```bash
pip install -e .

SQLITE_MCP_PROFILES="prod=/data/app.db:ro,local=/data/dev.db:rw" python -m sqlite_mcp
```

Register it:

```bash
claude mcp add sqlite -e SQLITE_MCP_PROFILES="prod=/data/app.db:ro" -- python -m sqlite_mcp
```

## The two guards

Read-only is enforced twice, independently. One guard is a rule; two is a property.

**1. Statement inspection.** Comments are stripped first, then the leading keyword of every
statement is checked. Anything that is not a read is refused — including a batch where only the
tail mutates:

```sql
SELECT 1; DELETE FROM orders          -- refused
/* harmless */ DELETE FROM orders     -- refused
SELECT 'contains the word update'     -- allowed: the keyword is inside a literal
```

It does not try to be clever about intent. Refusing too much is recoverable; allowing too much is
not.

**2. SQLite's own read-only mode.** A read-only profile opens the file as `file:...?mode=ro`, so
even a statement that slipped past the first guard cannot write — the engine refuses.

## Everything else it demonstrates

- **Profiles come from the environment**, not from a file the agent can edit. What it may touch is
  decided by whoever starts the server.
- **Output is bounded.** Results cap at 500 rows and say so, with a hint to narrow the query. One
  unbounded response fills the context and makes every turn after it worse.
- **Errors say what to do next.** A refused write names the writable profiles. An unknown profile
  lists the valid ones.
- **A table name is validated against the catalogue** rather than interpolated into a `PRAGMA`,
  because that shape is exactly where injection creeps into an otherwise careful server.

## Tests

```bash
pytest tests/ -v
```

The suite is mostly the guardrail, because that is the part with something to prove: mutating
statements in twelve shapes, reads that merely look like writes, the second SQLite-level guard,
the row cap, and malformed configuration.

## What it is not

Not a general database server. No connection pooling, no transactions, no other engines, no schema
migration. Adding those would obscure the one thing it is here to show.
