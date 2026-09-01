# 2 — The vault: structure, conventions, and why they are shaped that way

The vault is a folder of Markdown files. That is the whole technology. Everything useful about it
comes from **conventions**, not features — which is why it survives tool changes.

**In this chapter:** [Folder taxonomy](#folder-taxonomy) · [Naming](#naming) · [Frontmatter](#frontmatter) · [Gotchas: the one convention that pays for itself](#gotchas-the-one-convention-that-pays-for-itself) · [Problem](#problem) · [Cause](#cause) · [Fix](#fix) · [Prevention](#prevention) · [Linking](#linking) · [Note templates](#note-templates) · [What does *not* belong in the vault](#what-does-not-belong-in-the-vault) · [Sizing expectations](#sizing-expectations)

## Folder taxonomy

```
vault/
├── HOME.md                    entry point: what lives where
├── MAP.md                     the dependency graph between projects
├── GLOBAL/                    knowledge not owned by any single project
│   ├── gotchas/<tech>/        traps, by technology (docker/, git/, terraform/, …)
│   ├── architecture/          cross-system contracts and shared data formats
│   ├── insights/              non-obvious things learned that are not traps
│   ├── snippets/              reusable commands and code fragments
│   ├── config/                how your own tooling is configured and operated
│   └── maintenance/           logs from automated jobs, health reports
├── PROJECTS/<project>/        one folder per system you work on
│   ├── _INDEX.md              orientation: stack, repo path, environments, where things are
│   ├── gotchas/               traps specific to this project
│   ├── architecture/          how this system is built
│   ├── analyses/              deep dives, investigations
│   └── decisions/             ADRs scoped to this project
├── GUIDELINES/                binding conventions you and the agent both follow
│   ├── code/                  comment style, naming, review bar
│   ├── git/                   branching, commit messages, MR etiquette
│   ├── writing/               tone for tickets, wiki pages, comments
│   └── vault/                 the write procedure itself
├── SKILLS/<category>/         source of truth for skills (symlinked into ~/.claude/skills/)
├── TEMPLATES/                 note templates
├── DECISIONS/                 cross-cutting ADRs
├── WORKFLOWS/                 runbooks: deployment, incident, onboarding, release
└── WORKBENCH/<date>-<topic>/  time-boxed working material, not permanent knowledge
```

Four design choices in there are worth defending explicitly:

**`GLOBAL/` vs `PROJECTS/`.** The split is by *ownership*, not by topic. A Docker trap that would
bite you on any project is global. A Docker trap caused by one project's compose file is that
project's. When in doubt, ask: *if this project were deleted tomorrow, would the note still be
true?* Yes → global.

**`WORKBENCH/` exists so the rest stays clean.** Investigations produce a lot of intermediate
material that is valuable for two weeks and noise after that. Give it a dated folder and let it
age out. Without this, exploratory work either pollutes the permanent structure or gets thrown
away along with its conclusions.

**`GUIDELINES/` is separate from `GLOBAL/`.** Guidelines are *normative* — they say what you
should do. Everything in `GLOBAL/` is *descriptive* — it says what is true. Mixing them means the
agent cannot tell a rule from an observation.

**Every folder has an `_INDEX.md`.** It is a table of contents with one line per note, each line
saying what the note answers. This is what makes a vault navigable by an agent that has not read
it: it can read one index and know whether to open anything at all.

## Naming

- Files: `kebab-case.md`, lowercase, no dates in the name except in `WORKBENCH/`.
- **The filename states the conclusion, not the topic.** `mount-goes-stale-after-resync.md`, not
  `docker-notes.md`. You are naming for someone searching in a hurry.
- One idea per note. If the title needs an "and", it is two notes.
- Indexes are always `_INDEX.md`, so they sort first and are easy to glob.

## Frontmatter

Keep it small and consistent. Inconsistent frontmatter is worse than none, because tooling starts
lying to you.

```yaml
---
title: Editing the compiled CSS is silently overwritten
type: gotcha          # gotcha | insight | architecture | project-index | adr | snippet | index | skill
tags: [frontend, build]
project: acme-portal   # omit for GLOBAL notes
severity: danger       # gotchas only: danger | warning | tip | info
date: 2026-09-01       # pick ONE key name and never vary it
---
```

Pick one date key. Half `date:` and half `datum:`/`created:` means every query over time silently
misses half the vault.

## Gotchas: the one convention that pays for itself

A gotcha is a note about something that will waste your afternoon. They are the highest-value
notes in the vault, and they need a **machine-readable marker** so tooling can surface them
*before* the mistake, not after.

```markdown
---
title: Compiled CSS is regenerated on every deploy
type: gotcha
tags: [frontend, build]
severity: danger
---

# Compiled CSS is regenerated on every deploy

> [!danger] Edits to `dist/app.css` disappear at the next deploy
> The pipeline recompiles it from `src/less/`. Change the LESS source instead.

## Problem
A style fix applied directly to the compiled stylesheet works locally and vanishes in QA.

## Cause
`npm run build` regenerates `dist/` from `src/less/`; `dist/` is committed, which makes the file
look editable.

## Fix
Edit `src/less/<component>.less`, then `npm run build`.

## Prevention
Treat everything under `dist/` as generated. See [[GUIDELINES/code/generated-files]].
```

The callout line is **mandatory**. A gotcha without it is still a nice note and is invisible to
any "warn me about X" query. Severities:

| Severity | Use for |
|---|---|
| `danger` | Data loss, production breakage, silent corruption |
| `warning` | The standard trap: costs you an hour, no lasting damage |
| `tip` | A better way that is not obvious |
| `info` | Context that prevents a wrong assumption |

Why a callout and not a tag? Because it renders as a visible banner for the human *and* parses as
structured data for the machine, from the same text. One convention, two audiences.

## Linking

- Wikilinks with an alias: `[[PROJECTS/acme/architecture/auth-flow|the auth flow]]`.
- **Link liberally**, including to notes that do not exist yet — a dangling link is a to-do
  marker, not an error.
- **Never put a piped wikilink inside a table cell** if your renderer escapes it. Many Markdown
  pipelines turn `[[path|alias]]` in a table into a broken link because the pipe is also the
  column separator. Use a bullet list for navigation blocks:
  `- [[path|alias]] — what it answers`.
- Every note ends with a small **Navigation** section pointing at its `_INDEX.md` and one or two
  siblings. This is what turns a pile of files into a graph you can walk.

## Note templates

`TEMPLATES/` holds the shapes. Having them is not bureaucracy — it is how you get consistent
notes out of an agent that would otherwise invent a new layout each time.

| Template | For |
|---|---|
| `gotcha.md` | Traps, with the mandatory callout |
| `project.md` | A project `_INDEX.md`, with repo path and environments in frontmatter |
| `adr.md` | A decision: context, options, choice, consequences |
| `analysis.md` | An investigation, with a conclusion at the top |
| `snippet.md` | A reusable command, with the "when do I want this" line |
| `skill.md` | A skill, matching the `SKILL.md` frontmatter contract |
| `workflow.md` | A runbook |

## What does *not* belong in the vault

- Secrets, tokens, credentials. Ever. A knowledge base is not a password manager.
- Anything the code already says. Do not describe what a function does; the function does that
  better and never goes stale.
- Anything git history already says. "We fixed the login bug in March" is a commit, not a note.
- Case detail with no transferable core. Save the pattern, not the incident.

## Sizing expectations

A healthy vault after a year of one person's work is roughly **several hundred to a couple of
thousand notes**, dominated by gotchas and per-project orientation. If yours is much smaller, the
write-back loop is not running. If it is much larger, deduplication is not running.

Next: [`03-claude-md.md`](03-claude-md.md) — the rules layer that points into all of this.
