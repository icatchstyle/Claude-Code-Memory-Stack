# vault-mcp — reference MCP server

A small, working MCP server for a Markdown knowledge base. It is a **reference implementation of
the patterns**, not a feature-complete product: read it, then build the server your vault needs.

Stdlib only apart from the MCP SDK. No database, no persistent index — a few thousand notes
re-index in well under a second, which is cheaper than the operational cost of a persistent index
and immune to the stale-index failure it brings with it.

## Tools

| Tool | Purpose |
|---|---|
| `status` | Server + vault health. **Call this first when anything looks wrong.** |
| `search` | Ranked full-text search, capped |
| `gotcha_check` | Warnings relevant to a context — the payoff tool |
| `read_note` | One note: frontmatter, body, links, callouts |
| `create_note` | Create with consistent frontmatter, optional auto-indexing |
| `update_note` | Append or replace the body, preserving frontmatter |
| `list_directory` | Structure without content |
| `vault_health` | Gotchas without a callout, broken links, orphans, missing indexes |

## Run

```bash
pip install -e .

# stdio (simplest — one process per session)
VAULT_PATH=~/vault python -m vault_mcp

# HTTP daemon (recommended — one process for all sessions)
VAULT_PATH=~/vault MCP_TRANSPORT=http MCP_PORT=8765 python -m vault_mcp
```

Register it:

```bash
claude mcp add vault --env VAULT_PATH=$HOME/vault -- python -m vault_mcp          # stdio
claude mcp add --transport http vault http://127.0.0.1:8765/mcp                    # http
```

## Docker + the single-daemon pattern

```bash
docker build -t vault-mcp .
VAULT_PATH=~/vault ./scripts/ensure-up.sh
```

`ensure-up.sh` is **idempotent**: it reuses a running container, starts a stopped one, creates one
if absent, and — importantly — probes that the container can actually *see* the vault content, not
merely that it is running. Wire it to `SessionStart`.

> **The trap that follows:** because the script reuses a running container, changing a mount or an
> environment variable has no effect until you replace it:
> `docker rm -f vault-mcp && ./scripts/ensure-up.sh`

## What it deliberately does not do

Embeddings and semantic search, a graph API, file watching, multi-vault support, write locking.
Each is a reasonable next step; none is needed to make a vault useful, and every one of them is a
thing that can break at three in the morning.

## Design decisions worth copying

1. **One job per tool, enforced at the boundary.** `read_note` refuses a non-note. Two tools that
   both "read something" invite the agent to pick the one without the validation.
2. **Guardrails in code.** Path traversal is refused in `Vault.resolve`, where the model cannot
   argue with it. A `create_note` marked `type: gotcha` without a callout is rejected outright.
3. **Bounded output everywhere.** One unbounded response fills the context and makes every turn
   after it worse.
4. **Errors that say what to do next.** A missing note returns the closest matches; a zero-note
   status returns the stale-mount hint.
5. **Severity-first ranking in `gotcha_check`.** A `danger` you half-match beats an `info` you
   fully match — because the cost of the two mistakes is not the same.
