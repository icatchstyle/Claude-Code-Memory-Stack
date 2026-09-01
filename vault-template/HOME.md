---
title: Knowledge base — home
type: index
tags: [index, home]
---

# Knowledge base — home

The persistent memory. Everything durable that is not in the code and not in git history.

> [!tip] How to use this
> Search first, then read only the hits that matter. Read a folder's `_INDEX.md` before opening
> any note in it. Never dump a whole folder into context.

## Structure

- [[GLOBAL/_INDEX|GLOBAL]] — knowledge not owned by a single project: gotchas by technology,
  cross-system architecture, snippets, tooling config
- [[PROJECTS/_INDEX|PROJECTS]] — one folder per system: stack, repo path, environments,
  where things are, project-specific traps
- [[GUIDELINES/_INDEX|GUIDELINES]] — binding conventions (code, git, writing, this vault)
- [[SKILLS/_INDEX|SKILLS]] — source of truth for skills, symlinked into `~/.claude/skills/`
- [[WORKFLOWS/_INDEX|WORKFLOWS]] — runbooks: deployment, incident, onboarding, release
- [[DECISIONS/_INDEX|DECISIONS]] — cross-cutting ADRs
- [[TEMPLATES/_INDEX|TEMPLATES]] — note templates; use one for every new note
- [[WORKBENCH/_INDEX|WORKBENCH]] — dated working material, deliberately temporary
- [[MAP|MAP]] — how the systems depend on each other

## Where does a new note go?

| It is… | It goes to |
|---|---|
| A trap that will waste an afternoon | `GLOBAL/gotchas/<tech>/` or `PROJECTS/<p>/gotchas/` |
| True regardless of which project | `GLOBAL/` |
| Only true for one system | `PROJECTS/<p>/` |
| A rule about how we work | `GUIDELINES/` |
| A repeatable sequence of steps | `SKILLS/` (a skill, not a note) |
| A choice made and its consequences | `DECISIONS/` or `PROJECTS/<p>/decisions/` |
| Useful for two weeks | `WORKBENCH/<date>-<topic>/` |
| Already in the code or in git | Nowhere. Do not write it. |

## The write bar

Save the **transferable core**, never the incident.

- ❌ "Order 4711 was rejected as a duplicate."
- ✅ "Duplicate detection normalises e-mail case in SQL but not in the application, so the two
  disagree." → a gotcha, with a `danger` callout.
