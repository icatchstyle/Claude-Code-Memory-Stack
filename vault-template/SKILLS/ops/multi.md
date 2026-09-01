---
name: multi
description: >
  The user's explicit opt-in keyword for parallel execution. When this triggers, the user has
  granted permission to use several subagents and/or deterministic multi-stage orchestration —
  but only where it genuinely speeds up or improves the task. Also governs fleet size, agent-type
  choice, worktree isolation for parallel writes, and who writes what back to the knowledge base.
  Trigger ONLY on the word itself: "/multi", "do it multi", "plan it multi", "make that multi".
  Do NOT trigger on casual mentions of "parallel", "several agents" or "at the same time" without
  the keyword — and never infer the permission from a task merely looking parallelisable.
argument-hint: "[the task to parallelise]"
---

# Multi — the parallel-execution opt-in

## What this skill is

A **permission marker**, not a procedure. Its entire job is to make one thing unambiguous: the
user has agreed to spend tokens on parallelism for this task.

## Why a keyword at all

Subagents burn tokens fast — a ten-agent fan-out can cost more than a day of ordinary interactive
work. An agent that decides on its own when to fan out will surprise its user, and unpleasant
surprises about cost are how a good setup gets switched off.

Making the permission a word the user types removes the guesswork entirely. There is nothing to
infer: either the word is there or it is not.

## It is a permission, not an obligation

If the task is genuinely serial, say so in one line and work serially. Fanning out because you
were allowed to is the failure mode this skill exists to prevent — the second one, after fanning
out without being allowed to.

## Fleet sizing

| Task | Agents |
|---|---|
| Focused search across a codebase | 1–2 |
| Multi-dimensional review (bugs, performance, security) | 3–5, one per dimension |
| Broad audit across many services | 5–10, one per service |
| Anything larger | Ask first — it is the user's budget |

## Rules while parallel

**Subagents do not inherit `CLAUDE.md`.** Read-only research agents in particular start without
your rules. Any rule that matters — *"reach the knowledge base only through its MCP server"* —
must be written into the prompt you give them. This is the most common cause of an agent quietly
bypassing an access rule.

**Give each agent a narrow brief and ask for a conclusion, not a transcript.** The point of a
subagent is context isolation: ten thousand tokens of searching become three hundred tokens of
answer. Returning the raw material moves the problem instead of solving it.

**Verify adversarially.** An agent reporting a finding is not evidence the finding is real. Have
a second pass try to disprove each candidate and report only survivors. Most do not survive.

**Isolate parallel writes.** Several agents writing in one working tree collide. Give each its own
worktree, or serialise the writes.

## Division of labour when writing back

- **Subagents write knowledge** — gotchas, insights, findings: small, additive, independent notes.
- **The top-level session writes the deliverable** — the report or summary, which needs one voice.

This keeps writes non-overlapping and the handover coherent.

## Related

- [[SKILLS/analysis/review-changes/SKILL|review-changes]] — the shape this enables: one agent per
  dimension, each finding verified before it is reported.
