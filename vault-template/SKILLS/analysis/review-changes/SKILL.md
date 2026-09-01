---
name: review-changes
description: >
  Reviews the current diff across several independent dimensions (correctness, security,
  performance, tests), verifies each candidate finding adversarially before reporting it, and
  returns only what survives. Trigger on "/review-changes", "review my changes", "review the
  diff", "check this before I push", "is this ready for review". Do NOT trigger for committing,
  pushing or opening a PR (that is `ship-ticket`), for reviewing someone else's already-open PR
  (that is `review-pr`), or for a general code question with no diff involved.
argument-hint: "[dimension, e.g. 'security only']"
allowed-tools: Read, Grep, Glob, Bash(git diff:*), Bash(git status:*)
---

# Review changes

Multi-dimensional review of uncommitted work, with adversarial verification.

## Why this shape

A single review pass mixes concerns and produces a list dominated by whichever dimension the
model happened to think about first. Splitting by dimension gives each one full attention.

And a finding that has not survived an attempt to disprove it is a **candidate**, not a finding.
Most raw candidates do not survive. Reporting them unverified trains the user to ignore the
output, which costs more than the review was worth.

## Preconditions

- A git repository with uncommitted changes. If the diff is empty, say so and stop.
- If the diff exceeds ~2,000 lines, ask whether to narrow it. A review that skims is worse than
  no review, because it looks like assurance.

## Steps

### 1. Scope

```bash
git status --short
git diff --stat
```

Restrict to a dimension if one was given as an argument.

### 2. Review, one dimension at a time

For each dimension in [`references/dimensions.md`](references/dimensions.md), work through the
diff with that dimension's checklist and produce **candidates**: file, line, claim, and a
concrete failure scenario.

A candidate without a failure scenario — *these inputs produce this wrong output* — is an
opinion. Drop it here rather than making the user drop it later.

### 3. Verify adversarially

For each candidate, actively try to disprove it. Read the surrounding code, the callers, the
tests. Ask: *is there a guard elsewhere that already prevents this?*

Keep only what survives, and mark each survivor `CONFIRMED` (a failure path was traced) or
`PLAUSIBLE` (it looks wrong but could not be fully traced).

### 4. Report

Most severe first. For each: file:line, one sentence on the defect, the concrete failure
scenario, and the verdict. If nothing survived, say exactly that — a clean review is a result,
not a failure to find something.

## Guardrails

- **Read-only.** This skill never edits. Fixing is a separate, explicitly requested step.
- **No style opinions** unless the project has a written convention that the change violates.
- **Do not report the absence of a test as a bug.** Report it as missing coverage, separately.

## Layout

```
review-changes/
├── SKILL.md                    this file — decisions and sequence
├── references/
│   └── dimensions.md           the per-dimension checklists (read on demand)
└── scripts/
    └── collect-diff.sh         deterministic collection — a script does it better than prose
```

The split is the point: **the skill holds judgement, the script holds mechanism.** A model asked
to follow ten deterministic steps will occasionally follow nine.
