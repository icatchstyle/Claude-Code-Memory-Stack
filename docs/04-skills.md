# 4 — Skills: procedures that fire when they should

A skill is a Markdown file with frontmatter that Claude Code loads **on demand** when its
description matches the situation. It is the right home for anything that is a repeatable
sequence of steps.

The whole craft is in two places: **the description** (which decides *whether* it loads) and
**the body** (which decides whether it *helps* once loaded). Most broken skills are broken in the
description.

**In this chapter:** [Anatomy](#anatomy) · [When this runs](#when-this-runs) · [Steps](#steps) · [Writing a description that triggers correctly](#writing-a-description-that-triggers-correctly) · [Single source of truth: vault + symlink](#single-source-of-truth-vault-symlink) · [Structuring the body](#structuring-the-body) · [Categories](#categories) · [A quality bar](#a-quality-bar) · [Two worked examples](#two-worked-examples)

## Anatomy

```markdown
---
name: ship-ticket
description: >
  Ships the work on the current ticket — commits, pushes, opens a merge request against the
  requested stage, posts the MR link as a ticket comment and watches the pipeline. Trigger on
  "/ship-ticket", "ship this", "open an MR for the ticket", "this can go to QA". Do NOT trigger
  for creating a working environment (that is `worktree`), for merging the MR itself, or for
  deploy jobs and tags (that is `git-mcp`).
argument-hint: "[stage]"
allowed-tools: Bash, Read, mcp__git__*
---

# Ship ticket

## When this runs
…

## Steps
1. …
```

| Field | Meaning |
|---|---|
| `name` | The slash command: `/ship-ticket` |
| `description` | The trigger contract. See below — this is the whole game. |
| `argument-hint` | Shown in the UI; documents what arguments do |
| `allowed-tools` | Narrows what the skill may touch while it is active |
| `disable-model-invocation` | `true` = user-invoked only, never auto-triggered |

## Writing a description that triggers correctly

The description is matched against the situation. It has to be **precise in both directions**:
what fires it, and what must not.

**The three-part shape:**

1. **What it does**, in one or two concrete sentences — mechanism, not marketing.
2. **Trigger on:** the literal phrases users actually say, including the slash command, in the
   language they say them in.
3. **Do NOT trigger for:** the adjacent cases, each pointing at the right alternative.

The negative clause is what people skip, and it is the reason for the two classic failures:

- **Over-triggering** — a skill named `check` with description "checks things" fires on every
  prompt containing "check". Cure: name the exact adjacent cases it must *not* claim.
- **Under-triggering** — a perfectly good skill that never loads because its description
  describes the implementation instead of the request. Cure: write the *user's* words, not yours.

For skills that must only ever run when explicitly asked, be blunt in the text **and** set the
frontmatter flag:

```
Trigger ONLY on an explicit "/audit-security" invocation. Do NOT trigger on casual mentions of
security, audits, or scanning. Without the explicit call, this skill stays asleep.
```

Rule of thumb: **a description shorter than three lines is almost certainly under-specified.**
Being verbose here is cheap — descriptions are cheap to load, wrong triggering is not.

## Single source of truth: vault + symlink

Skills belong in the vault (`SKILLS/<category>/<name>.md` or `SKILLS/<category>/<name>/`), where
they are searchable, versioned and linkable to the knowledge they depend on. They are then
**symlinked** into the active directory:

```bash
# single-file skill
ln -sfn "$VAULT/SKILLS/ops/ship-ticket.md" ~/.claude/skills/ship-ticket/SKILL.md

# multi-file skill (references/, scripts/, assets/) — link the directory
ln -sfn "$VAULT/SKILLS/ops/ship-ticket" ~/.claude/skills/ship-ticket
```

**Never copy.** A copy drifts, and drift is undetectable until it bites: you edit the vault
version, nothing changes, and you spend an hour before noticing the active file is a stale twin.
Symlinks load live — edit the source, the next invocation uses it, no restart.

One exception worth knowing: if a skill's scripts are invoked from *outside* Claude Code (a
scheduler calling them by absolute path), keep those scripts local and symlink only the
`SKILL.md`. External callers should not depend on your vault being mounted.

## Structuring the body

Keep the `SKILL.md` at the level of **decisions and sequence**. Push reference material into
`references/` and executable steps into `scripts/`, and name them from the body. This keeps the
loaded skill small while the details stay one read away.

```
SKILLS/ops/ship-ticket/
├── SKILL.md              the procedure: steps, decisions, guardrails
├── references/
│   └── mr-template.md    long-form material, read only when needed
└── scripts/
    └── watch-pipeline.sh deterministic work — a script does it better than prose
```

Anything that is *pure mechanism* — polling, parsing, formatting — belongs in a script or an MCP
server, not in skill prose. A model asked to follow ten deterministic steps will occasionally
follow nine. This is also the cleanest division of labour in the whole stack:

> **The MCP server owns the mechanism. The skill owns the domain knowledge.**

The server knows *how* to run a query safely. The skill knows *which* query answers this
question, and what the result means.

## Categories

Group skills by what they are *for*, and keep the tree shallow:

| Category | Contains |
|---|---|
| `analysis/` | Investigation and reporting: log analysis, audits, health checks |
| `ops/` | Operational procedures: shipping, cleanup, worktrees, maintenance |
| `communication/` | Anything written in your name: tickets, wiki pages, comments |
| `tools/<area>/` | Tool-specific know-how: a dashboard system, a second-opinion agent |

Maintain a `SKILLS/_INDEX.md` listing every skill with its one-line purpose and its symlink
command. When a skill mysteriously stops appearing, that index is where you find out that its
symlink was never created.

## A quality bar

A skill is good when it:

- **Names its exclusions.** Half of triggering correctly is refusing to trigger.
- **Fails loudly.** If a precondition is missing, say so and stop — do not improvise around it.
- **Is idempotent where it can be.** Running it twice should not double anything.
- **States its guardrails inline.** "Never push to a protected branch" belongs *in* the skill,
  not only in `CLAUDE.md`, because a loaded skill is what the model is looking at.
- **Ends by writing back.** If it discovers something durable, it puts it in the vault.

## Two worked examples

Both live in the vault template, where the convention above says they belong:

- [`SKILLS/ops/capture-knowledge.md`](../vault-template/SKILLS/ops/capture-knowledge.md) — a
  single-file skill with a tightly scoped description.
- [`SKILLS/analysis/review-changes/`](../vault-template/SKILLS/analysis/review-changes/SKILL.md) —
  a skill with `references/` and `scripts/`, showing the split between prose and mechanism.
- [`SKILLS/INSTALLING.md`](../vault-template/SKILLS/INSTALLING.md) — the symlink commands and how
  to find a skill whose link was never created.

Next: [`05-mcp.md`](05-mcp.md).
