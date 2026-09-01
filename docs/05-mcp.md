# 5 — MCP servers: typed capabilities and where they break

An MCP server gives the agent **typed, guarded access** to a system. The point is not that it
*can* reach the database — a shell could do that. The point is that the server decides what
"reaching the database" is allowed to mean, in code, where the model cannot negotiate.

**In this chapter:** [Why a server instead of shell commands](#why-a-server-instead-of-shell-commands) · [A sensible server set](#a-sensible-server-set) · [The single-daemon pattern](#the-single-daemon-pattern) · [Failure modes worth knowing before they happen](#failure-modes-worth-knowing-before-they-happen) · [Designing good tools](#designing-good-tools) · [Reference implementation](#reference-implementation) · [Running without an MCP server](#running-without-an-mcp-server)

## Why a server instead of shell commands

| | Shell | MCP server |
|---|---|---|
| Guardrails | In the prompt — advisory | In code — enforced |
| Output | Whatever the tool printed | Shaped, capped, paginated |
| Discovery | The agent must know the invocation | Typed schema, self-describing |
| Auditing | Scattered across transcripts | One place |
| Failure | Silent or cryptic | Structured, with a remedy |

A read-only database profile that rejects mutating SQL **server-side** cannot be talked around.
The same rule in `CLAUDE.md` is a strong suggestion. That difference is the entire argument.

## A sensible server set

Start with one and grow. In rough order of payoff:

1. **Vault** — the knowledge layer. Highest value, because every other layer leans on it.
2. **Issue tracker** — tickets and wiki pages are where the *why* lives.
3. **Git / forge** — branches, MRs, pipelines, with protected-branch guards.
4. **Database** — named profiles, read-only enforced per profile.
5. **Logs** — production observability with row caps and windowed output.
6. **Domain server** — your own business objects, if the vocabulary is stable enough.

Each server should own one system. A server that does three things has three reasons to break.

## The single-daemon pattern

The most important operational decision, and the one that is easy to get wrong.

If every Claude session spawns its own server process, and those processes share a SQLite index or
any other single-writer resource, you get lock contention, corrupted indexes, and failures that
only appear when you happen to have two sessions open.

**Run exactly one long-lived process per server, and have every session connect to it over HTTP.**

```bash
#!/usr/bin/env bash
# ensure-up.sh — idempotent: reuse a running container, start a stopped one, create if absent.
set -euo pipefail
NAME="${SERVER_NAME:-vault-mcp}"
PORT="${MCP_PORT:-8765}"

state="$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null || echo absent)"
case "$state" in
  true)  echo "[ensure-up] already running" ;;
  false) docker start "$NAME" >/dev/null ;;
  *)     docker run -d --name "$NAME" -p "127.0.0.1:$PORT:$PORT" \
           -v "$VAULT_PATH:/vault:rw" -e VAULT_PATH=/vault "$IMAGE" >/dev/null ;;
esac
```

Wire it to `SessionStart` in `settings.json`. Make it **idempotent** (safe to run a hundred times)
and **fast** (it runs before every session — background the slow ones with `nohup … &`).

Bind to `127.0.0.1`, never `0.0.0.0`. This server reads your notes and can reach your systems.

### The trap that follows from it

`ensure-up.sh` reuses a running container **by design**. That means changing a mount or an
environment variable has no effect until you actually replace the container:

```bash
docker rm -f vault-mcp && ./scripts/ensure-up.sh
```

And if you keep a `docker-compose.yml` alongside a script that uses `docker run`, the compose file
is *not what is running*. Either delete it or keep it in sync deliberately — a stale compose file
is a reliable way to spend an hour debugging a config change that was never applied.

## Failure modes worth knowing before they happen

**The stale mount.** On WSL2 with Docker Desktop and a cloud-synced folder, a container's bind
mount can survive a host-side re-sync while pointing at nothing. Symptom: the server is healthy,
reports zero notes, and a re-index inserts nothing, while the host directory is visibly full.

Diagnose by comparing both sides, and fix with a real restart:

```bash
docker exec vault-mcp sh -c 'ls /vault | wc -l'   # 0 → mount is orphaned
ls "$VAULT_PATH" | wc -l                          # >0 → host is fine
docker restart vault-mcp                          # ensure-up.sh will NOT do this
```

`ensure-up.sh` cannot fix it — the container *is* running, so an idempotent script correctly does
nothing. Better still, build a **sentinel check** into the script: probe for one file you know
exists (`MAP.md`) rather than for a non-empty listing, so a partially visible mount is caught too.
Write this whole procedure into your `CLAUDE.md` as a self-healing rule, so the agent recognises
and repairs it without you.

**TLS interception.** On a corporate network with a security gateway, every outbound server fails
with `CERTIFICATE_VERIFY_FAILED` while the host works fine — the container lacks the gateway CA.
Mount the host CA bundle and set `SSL_CERT_FILE`.

**Context flooding.** A tool that returns 5,000 rows has just consumed your context. Cap results
server-side, push limits into the query itself, and offer an `out_file` parameter for anything
large. This is a server responsibility, not a prompting problem.

## Designing good tools

- **One job per tool**, with a schema-level guarantee. `read_note` should refuse a binary asset;
  `read_file` should refuse a note. Two tools that both "read something" invite the agent to
  bypass the one with the validation.
- **Names that read as intent**: `list_profiles`, `query`, `gotcha_check`. Not `execute`.
- **Errors that tell the agent what to do next**: *"Profile 'prod' is read-only; use 'qa' or an
  explicit `SELECT`."*
- **Server-side enforcement.** If it must never happen, make it impossible, not forbidden.
- **Stable output shapes.** The agent learns your JSON. Changing keys silently breaks skills.

## Reference implementation

[`mcp/vault-mcp/`](../mcp/vault-mcp/) is a small, real MCP server for the vault. It implements the
pattern rather than everything you might want:

| Tool | Purpose |
|---|---|
| `search` | Full-text search across the vault, ranked, capped |
| `read_note` | Read one note with frontmatter parsed and links extracted |
| `create_note` | Create from a template, with optional auto-linking into `_INDEX.md` |
| `update_note` | Replace or append, preserving frontmatter |
| `gotcha_check` | Return callout-marked warnings matching a context — the payoff tool |
| `list_directory` | Structural overview without reading content |
| `vault_health` | Broken links, orphans, missing indexes, frontmatter drift |

`gotcha_check` is the one that changes daily life: it turns "notes about problems" into a warning
system that fires *before* the mistake.

### The second server: guardrails in code

[`mcp/sqlite-mcp/`](../mcp/sqlite-mcp/) exists to prove the claim this chapter opens with. It
implements named profiles where read-only is enforced **twice, independently**: mutating
statements are refused after comments are stripped, and a read-only profile opens the database in
SQLite's own read-only mode, so even a statement that slipped past the first check cannot write.

One guard is a rule. Two independent guards is a property — and a property is what you want
between an agent and your production data.

## Running without an MCP server

The design degrades gracefully. Without a server, Claude reads the vault with `Read`, `Glob` and
`Grep`. You lose ranked search, structured gotcha retrieval, and write validation; you keep the
structure, the conventions, and most of the value.

If you go this route, add to `CLAUDE.md`:

```markdown
The knowledge base lives at `<path>`. Search it with Grep before starting a task; read the
`_INDEX.md` of the relevant folder first, then only the notes that matter. Never dump whole
folders into context.
```

Adopt the server when grep-based recall starts costing you more context than it saves — for most
people that is somewhere north of a few hundred notes.

Next: [`06-hooks.md`](06-hooks.md).
