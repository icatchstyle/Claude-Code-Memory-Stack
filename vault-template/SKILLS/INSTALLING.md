---
title: Installing skills — symlink, never copy
type: guideline
tags: [skills, symlink, installation]
---

# Installing skills — symlink, never copy

Skills live here, in the vault, where they are searchable, versioned and linkable to the knowledge
they depend on. The active location `~/.claude/skills/` holds only **symlinks**.

> [!danger] Never copy a skill into the active location
> A copy drifts. You edit the vault version, nothing changes, and you lose an hour before noticing
> the active file is a stale twin. Symlinks load live — edit the source, the next invocation uses
> it, no restart.

## Commands

```bash
VAULT=~/vault

# Single-file skill: link the file as SKILL.md inside a folder named after the skill.
mkdir -p ~/.claude/skills/capture-knowledge
ln -sfn "$VAULT/SKILLS/ops/capture-knowledge.md" ~/.claude/skills/capture-knowledge/SKILL.md

# Multi-file skill (references/, scripts/, assets/): link the whole directory.
ln -sfn "$VAULT/SKILLS/analysis/review-changes" ~/.claude/skills/review-changes
```

## Verify

A dangling symlink is a skill that silently does not exist — no error, it simply never triggers.

```bash
find ~/.claude/skills -maxdepth 2 -xtype l    # prints broken links; empty output is good
```

Check **both** shapes when auditing: a skill may be linked as a file
(`~/.claude/skills/<name>/SKILL.md`) or as a directory (`~/.claude/skills/<name>`). Looking only
for the first misses every multi-file skill.

## One exception

If a skill's scripts are invoked from **outside** the agent — a scheduler calling them by absolute
path — keep those scripts local and symlink only the `SKILL.md`. External callers should not depend
on your vault being mounted.

## The two example skills

- [[SKILLS/ops/capture-knowledge|capture-knowledge]] — single file, tightly scoped description
- [[SKILLS/analysis/review-changes/SKILL|review-changes]] — `references/` and `scripts/`, showing
  the split between prose and mechanism

## Navigation

- [[SKILLS/_INDEX|Skills]] · [[HOME|Home]]
