# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Dependabot version updates for GitHub Actions and the reference server's Python dependencies,
  grouped into one pull request per ecosystem and scheduled monthly.

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
