# 8 — Operations: keeping the stack alive

A memory stack is a garden. Left alone it does not stay as you found it — it decays: duplicate
notes, dead links, skills whose symlinks were never made, a `CLAUDE.md` full of paths that moved.

None of this maintenance is hard. It just has to be scheduled.

**In this chapter:** [The maintenance rhythm](#the-maintenance-rhythm) · [The write-back skill](#the-write-back-skill) · [Linting](#linting) · [Backups](#backups) · [Health checks worth having](#health-checks-worth-having) · [Troubleshooting](#troubleshooting) · [Measuring whether it works](#measuring-whether-it-works)

## The maintenance rhythm

| Cadence | Task | How |
|---|---|---|
| Per session | Write back what was non-obvious | A write-back skill, invoked at the end |
| Weekly | Health check: broken links, orphans, missing indexes | `vault_health` / a lint skill |
| Weekly | Deduplicate: search before writing; merge near-copies | Manual, guided by search |
| Monthly | Audit `CLAUDE.md` — cut every fact, verify every path | Manual, 20 minutes |
| Monthly | Prune `WORKBENCH/` — promote or delete | Manual |
| Quarterly | Review skills: which never triggered? which over-triggered? | Manual |
| Continuous | Back up the vault | Version control or sync |

## The write-back skill

The most valuable maintenance skill you will own. It should:

1. **Classify** what the session produced: gotcha, insight, decision, snippet, runbook, nothing.
2. **Discard case detail.** Save the transferable core, never the incident.
3. **Deduplicate.** Search first; update an existing note rather than adding a fourth near-copy.
4. **Write to the right place** with the right template and the mandatory markers.
5. **Re-index** so the new note is findable immediately.
6. **Report** what changed, so you can veto it.

Step 2 is the quality bar of the whole vault. "Customer 4711 could not log in" is worthless.
"The login gate compares e-mail case-sensitively in SQL and case-insensitively in PHP, so the two
disagree and the one-time code is consumed before authorisation" is a gotcha you will thank
yourself for.

**Nothing is a valid classification.** A session of dead ends should write nothing. A vault that
records every session is a log, not a knowledge base.

## Linting

Automate the checks that are mechanical:

- Gotchas without a severity callout — **invisible to retrieval**, the highest-value check.
- Notes missing from their folder's `_INDEX.md`.
- Frontmatter drift: mixed date keys, unknown `type` values, missing titles.
- Broken wikilinks and orphan notes.
- Piped wikilinks inside table cells.
- Skills in the vault with no symlink in the active directory, and vice versa.

Distinguish **broken** from **intentionally dangling**. Planned targets on a roadmap page and
append-only maintenance logs are supposed to look like errors. Keep a short allow-list, or the
lint output becomes noise you learn to ignore — which is worse than no lint at all.

## Backups

The vault is plain Markdown, so this is easy and there is no excuse.

- **Version control it.** Git gives you history and a diff of what the agent changed — which is
  also the best review mechanism you will get for automated writes.
- **Or sync it** (any cloud folder). Be aware that sync clients and container bind mounts
  interact badly; see the stale-mount failure in [`05-mcp.md`](05-mcp.md).
- **Back up `~/.claude/` too** — `settings.json`, hooks, and any skills that are not symlinks.

## Health checks worth having

- **Is the vault visible to the server?** Compare host file count with container file count. This
  catches the failure mode where everything reports healthy and nothing is found.
- **Do all skills resolve?** A dangling symlink means a skill that silently does not exist.
- **Did the scheduled jobs run?** Write their output into `GLOBAL/maintenance/` and glance at it.
- **Is `CLAUDE.md` still true?** The paths in it are the fastest thing to go stale.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Server healthy, zero notes, re-index inserts nothing | Stale bind mount — `docker restart`, not `ensure-up.sh` |
| A skill never triggers | Description too narrow, or the symlink was never created |
| A skill triggers constantly | No "do NOT trigger for" clause |
| Agent bypasses the MCP and reads files directly | Access rule missing from `CLAUDE.md`, or a subagent that never saw it |
| Every outbound server fails on TLS | Corporate interception — mount the host CA bundle |
| Recall happens sometimes | The rule is advisory; make it mandatory and add the hook |
| Context fills after a few turns | A tool returns unbounded output — cap it server-side |
| Vault search returns nothing useful | Titles name topics instead of conclusions |

## Measuring whether it works

Not with dashboards. With three questions, once a month:

1. **How often did you re-explain something you had explained before?** Should trend to zero.
2. **How often did the agent warn you about a trap before you hit it?** Should trend up.
3. **How often did you skip writing something down because it was inconvenient?** If often, the
   write path has too much friction — fix the friction, not your discipline.

Next: [`09-adoption.md`](09-adoption.md).
