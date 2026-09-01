---
title: Skills — overview
type: index
tags: [index, skills]
---

# Skills — overview

Source of truth for skills. The active copies in `~/.claude/skills/` are **symlinks** into here —
never copies. See [[SKILLS/INSTALLING|INSTALLING]] for the exact commands.

| Skill | Category | Purpose |
|---|---|---|
| `capture-knowledge` | ops | Capture a session's durable knowledge into the vault |
| `vault-lint` | ops | Find the defects that make notes unfindable |
| `multi` | ops | The opt-in keyword for parallel execution |
| `review-changes` | analysis | Multi-dimensional review of the current diff, adversarially verified |

- [[SKILLS/ops/_INDEX|ops/]] — operational procedures
- [[SKILLS/analysis/_INDEX|analysis/]] — investigation and reporting
- [[SKILLS/communication/_INDEX|communication/]] — anything written in your name
- [[SKILLS/tools/_INDEX|tools/]] — tool-specific know-how

> [!warning] A skill with no symlink silently does not exist
> When a skill mysteriously never triggers, check this table against
> `find ~/.claude/skills -maxdepth 2 -xtype l` first — a dangling link produces no error.

## Navigation

- [[HOME|Home]]
