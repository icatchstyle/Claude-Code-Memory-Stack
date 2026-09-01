---
name: vault-lint
description: >
  Checks the knowledge base for the defects that make notes unfindable — gotchas without a
  severity callout, notes missing from their folder index, frontmatter drift, broken and
  table-cell wikilinks, and skills whose symlink was never created. Reports findings grouped by
  severity and fixes only what the user approves. Trigger on "/vault-lint", "check the knowledge
  base", "lint the vault", "vault health", "find broken links in my notes". Do NOT trigger for
  writing new knowledge (that is `capture-knowledge`), for searching the vault (no skill needed),
  or for linting source code.
argument-hint: "[folder to restrict to, e.g. PROJECTS/acme]"
allowed-tools: Read, Grep, Glob, Bash
---

# Vault lint

The counterpart to [[SKILLS/ops/capture-knowledge|capture-knowledge]]: one writes, this one keeps
the result usable. A knowledge base decays quietly — nothing errors, notes simply stop being
found.

## When this runs

Weekly, or after a burst of writing. Also before adopting someone else's vault, to see what you
are inheriting.

## The checks, in order of value

### 1. Gotchas without a severity callout — the highest-value check

A note of type `gotcha` whose body has no `> [!severity]` line is **invisible to retrieval**. It
exists, it is correct, and it will never surface at the moment it would have saved you. This is
the single most damaging defect in a vault because it produces no symptom.

```bash
grep -rLl '^> \[!' --include='*.md' "$VAULT"/*/gotchas "$VAULT"/*/*/gotchas 2>/dev/null
```

Report every hit. Offer to add the callout, deriving it from the note's first paragraph — but
never invent a severity: ask which of `danger`/`warning`/`tip`/`info` applies.

### 2. Notes missing from their folder's `_INDEX.md`

An unindexed note is findable only by full-text luck. For each folder, compare its `*.md` files
against the links in its `_INDEX.md`.

Exempt: `_INDEX.md` itself, the vault's entry points, and skill payload folders
(`references/`, `scripts/`, `assets/`) — those are read by a skill, not browsed.

### 3. Frontmatter drift

- Mixed date keys (`date:` vs `created:` vs a localised spelling). Pick one; a query over time
  silently misses half the vault otherwise.
- Date format other than `YYYY-MM-DD`.
- Unknown `type:` values, or capitalised enum values — `Behoben` and `behoben` are different
  strings to every query engine.
- Missing `title:`, which makes the note appear untitled in search results.

### 4. Broken wikilinks

Distinguish **broken** from **intentionally dangling**. A planned target on a roadmap page and an
append-only maintenance log are supposed to look like errors. Keep an allow-list, or the report
becomes noise you learn to ignore — which is worse than not running it.

### 5. Piped wikilinks inside table cells

`[[path|alias]]` in a table cell breaks in many renderers: the pipe is also the column separator,
and the escape ends up inside the link target. Worse, the resulting broken link often does **not**
appear in a link check, because the mangled target looks syntactically valid.

```bash
grep -rn '^|.*\[\[[^]]*|' --include='*.md' "$VAULT"
```

Fix by moving navigation links out of the table into a bullet list.

### 6. Skills without a symlink, and symlinks without a skill

```bash
find ~/.claude/skills -maxdepth 2 -xtype l          # dangling links: a skill that silently does not exist
```

Then compare both directions against `SKILLS/` in the vault. A skill present in one place and not
the other is a skill you will wonder about for an hour.

## Reporting

Group by severity, most damaging first, and give the count before the list. For each finding: the
path, what is wrong, and the concrete fix.

End with the two numbers that matter: **how many notes, how many defects**. A vault that grows
while its defect count stays flat is healthy.

## Guardrails

- **Report first, fix second.** Never rewrite notes unasked — especially not other people's.
- **Never guess a severity.** Ask.
- **Do not "fix" intentional exceptions.** Check the allow-list before touching anything.
- **Vault-wide cleanup is this skill's job, not a knowledge-writing run's.** Leave pre-existing
  defects to a deliberate lint pass rather than fixing them in passing.
