# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`automation/`** — the scheduled harvest that closes the write-back loop without relying on
  discipline: a collector turning past sessions into digests, a runner that is dry-run by default,
  and schedule examples for cron, launchd and Task Scheduler. It deliberately extracts what a
  person never reports — failed tool calls, subagent replies — and refuses to write unless the
  conventions load first, advances its state only on success, and never harvests a session twice.
  Documented in `docs/11-automation.md`, with the one format-dependent function isolated and
  covered by fixtures.
- **`mining-stop`** — the abstaining counterpart to `capture-knowledge`: marks a session as not
  worth harvesting, writes nothing.
- **`capture-knowledge`** now works through the session in episodes against an eight-question
  grid, and deliberately mines the three sources that fall through it.
- **`mcp/sqlite-mcp/`** — a second reference server demonstrating guardrails enforced in code:
  named profiles where read-only is checked twice, independently (statement inspection after
  comment stripping, plus SQLite's own read-only mode), bounded output, and errors that name the
  next step. It exists to prove the central claim of `docs/05-mcp.md`, which was previously
  asserted but not demonstrated.
- **Two more example skills** — `vault-lint`, the maintenance counterpart to `capture-knowledge`,
  and `multi`, the opt-in keyword for parallel execution. Both were described in the
  documentation without being shipped.
- GitHub Actions updated to `checkout@v7` and `setup-python@v7`.
- Dependabot version updates for GitHub Actions and the reference server's Python dependencies,
  grouped into one pull request per ecosystem and scheduled monthly.

### Fixed

- **Both servers were broken against the current MCP SDK.** `mcp>=1.2.0` now resolves to 2.x,
  where `FastMCP` was renamed to `MCPServer` and transport parameters moved from
  `mcp.settings` onto `run()`. Anyone installing them today would have hit an ImportError.
  Migrated to the 2.x API and pinned to `mcp>=2.0,<3`. The tests never caught it because they
  cover the dependency-free layer; the CI import check added in this release did, on its first
  run.
- **Path traversal in `Vault.resolve`.** It compared path strings by prefix, so a sibling
  directory got through: for a vault at `/data/vault`, `../vault-secrets/x.md` resolved to
  `/data/vault-secrets/x.md`, which starts with the vault's path and was accepted — readable and
  writable, since `create_note` and `update_note` go through the same function. Now compared as
  paths, with the sibling case covered by a test.
- **The cron example shipped `--write`**, contradicting its own comment and the documentation's
  claim that all three schedules start in dry run. An unattended agent would have had write
  access on day one.
- **The harvest run granted no write permission and still reported success.** Headless runs have
  nobody to answer a permission prompt, so writes were refused while the marker still appeared
  and the state advanced — losing the window silently. The permission mode is now explicit, and a
  reported write is verified against the vault when it is a git repository.
- `gotcha_check` returned navigational callouts from indexes and entry points as if they were
  warnings, and callout extraction was not code-aware.
- `make check` did not run ShellCheck although CI does, breaking the guarantee that a green local
  run predicts a green pipeline — the same drift the shared vault check was introduced to end.
- SQLite connections were committed but never closed, leaking a descriptor per query in exactly
  the long-lived daemon this project recommends; profile paths were not percent-encoded; profile
  descriptions were never populated.
- Documentation corrections: a stale filename in the README's worked example, "two example
  skills" where five ship, a `vault_health` capability that does not exist, "tooling friction"
  described as mechanically extracted when it needs judgement, and the notification mute switch
  located in the vault rather than in `~/.claude/`.
- Portability: the notification debounce used GNU-only `find -newermt` and failed silently on
  macOS.

- Wikilink extraction now ignores fenced and inline code, so a note documenting link syntax no
  longer produces phantom broken links. Any vault that describes its own conventions hits this.
- The vault health assertions live in one script used by both `make vault` and CI. They had
  drifted apart — the Makefile checked three rules, CI four — so a change could pass locally and
  fail in the pipeline, breaking the guarantee CONTRIBUTING.md makes.

## [0.1.0] — 2026-09-01

First public release.

### Added

- **An architecture diagram and a worked example** in the README: real `gotcha_check` output
  against the vault skeleton, showing severity-ranked warnings surfaced from a context line.

- **Documentation** — ten chapters covering the layered architecture, the vault, `CLAUDE.md`,
  skills, MCP servers, hooks, scaling with subagents, operations, an adoption path, and the
  anti-patterns these setups fail on.
- **`setup/`** — `bootstrap.sh` (idempotent, never overwrites, supports `--dry-run`), an annotated
  `CLAUDE.md` template, a `settings.json` template, and three working hooks: a per-turn memory
  recall reminder, ticket-based session naming, and turn-completion notifications.
- **`vault-template/`** — a knowledge-base skeleton with the folder taxonomy, an `_INDEX.md` per
  folder, seven note templates, a worked example gotcha, and the write procedure that
  knowledge-writing skills follow.
- **Two annotated example skills**, inside the vault template rather than beside it, so the
  repository follows the convention it teaches: a single-file skill (`SKILLS/ops/`) and one split
  across `references/` and `scripts/` (`SKILLS/analysis/`).
- **`mcp/vault-mcp/`** — a reference MCP server for the vault (`search`, `gotcha_check`,
  `read_note`, `create_note`, `update_note`, `list_directory`, `vault_health`, `status`), with a
  Dockerfile, an idempotent `ensure-up.sh` implementing the single-daemon pattern, and tests.
- **`Makefile`** — `make check` runs exactly what CI runs, plus individual `test`, `links`,
  `shell`, `vault` and `demo` targets.
- **CI** — tests on Python 3.10–3.13, a package build and import check, ShellCheck and syntax
  checks on every shell script plus a guard that their executable bit is actually committed, a
  relative-link check across all documentation, an end-to-end `bootstrap.sh` run including an
  idempotency check, and a health check asserting that the vault template passes the rules it
  teaches — no gotcha without a severity callout, no orphans, no folder without an index.

[Unreleased]: https://github.com/icatchstyle/Claude-Code-Memory-Stack/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/icatchstyle/Claude-Code-Memory-Stack/releases/tag/v0.1.0
