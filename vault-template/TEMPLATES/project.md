---
title: "<Project name>"
type: project-index
tags: [project]
project: <slug>
status: active
repo: <local checkout path>
git_repo: <forge project URL, https, no .git suffix>
date: <YYYY-MM-DD>
---

# <Project name>

One paragraph: what this system does and who depends on it.

## Source

- **Local path:** `<repo from frontmatter>`
- **Repository:** `<git_repo from frontmatter>`
- **Stack:** `<languages, frameworks, datastores>`

> [!info] Convention
> Every project `_INDEX.md` carries the local checkout path (`repo:`) and the repository URL
> (`git_repo:`) in its frontmatter. Tooling that opens a project relies on those two fields;
> a project note without them is invisible to it.

## Environments

| Environment | URL | Notes |
|---|---|---|
| Dev | | |
| QA | | |
| Prod | | |

## Where things are

The most valuable section in this note. Answer the questions you ask on every return visit:

| Question | Answer |
|---|---|
| Entry point | |
| Configuration | |
| Database access | |
| Build / test command | |
| Deployment | |
| Logs | |

## Coupling

Who does this system talk to, and how? Link the shared contracts rather than restating them.

- upstream: …
- downstream: …

## Subfolders

| Folder | Contents |
|---|---|
| `gotchas/` | Project-specific traps |
| `architecture/` | How it is built |
| `analyses/` | Investigations |
| `decisions/` | ADRs scoped to this project |

## Navigation

- [[PROJECTS/_INDEX|All projects]] · [[MAP|System map]]
