# 7 — Scale: subagents, workflows, and the economics of context

Once the stack works, the binding constraint stops being knowledge and becomes **context**. A
session that has read forty files is slower, more expensive, and measurably worse at following
instructions than one that has read four.

Subagents and workflows exist to solve exactly that. They are not a way to be clever; they are a
way to keep the main session clean.

**In this chapter:** [The real argument for subagents](#the-real-argument-for-subagents) · [Make it opt-in](#make-it-opt-in) · [Fleet sizing](#fleet-sizing) · [Workflows vs. ad-hoc agents](#workflows-vs-ad-hoc-agents) · [Division of labour when writing back](#division-of-labour-when-writing-back) · [Agent hygiene](#agent-hygiene) · [Cost awareness](#cost-awareness)

## The real argument for subagents

Not parallelism. **Context isolation.**

A subagent gets its own window, reads what it needs, and returns a conclusion. Ten thousand tokens
of searching become three hundred tokens of answer in your session. The parallelism is a bonus;
the isolation is the point.

Which means the decision rule is simple:

| Situation | Do |
|---|---|
| You know the file and the symbol | Read it yourself — delegation costs more than it saves |
| The answer requires sweeping many files | Delegate; keep the conclusion, not the dumps |
| Several independent questions | Delegate in parallel, one message, several agents |
| Deterministic multi-stage pipeline | A workflow, not ad-hoc agents |
| Parallel *writes* to one repo | Isolate each agent in its own worktree |

## Make it opt-in

Subagents burn tokens fast, and a setup that spawns them on its own judgement will surprise you.
The cleanest fix is a **keyword the user must say**.

Pick a word — this template uses `multi` — and give it a skill whose only job is to state that
permission has been granted and to set the rules for spending it:

```markdown
---
name: multi
description: >
  The user's explicit opt-in keyword for parallel execution. When triggered, the user has granted
  permission to use several subagents and/or multi-stage orchestration — but only where it
  genuinely speeds up or improves the task. Trigger ONLY on the word "multi": "/multi", "do it
  multi", "plan it multi". Do NOT trigger on casual mentions of "parallel" or "several agents".
---
```

Two properties make this work. The permission is **explicit** — no guessing. And it is a
permission, **not an obligation**: if the task is genuinely serial, the right answer is to say so
in one line and work serially.

## Fleet sizing

More agents is not better. Each one costs tokens, adds coordination, and can return something
subtly wrong that you then have to verify.

| Task | Agents |
|---|---|
| Focused search across a codebase | 1–2 |
| Multi-dimensional review (bugs, perf, security) | 3–5, one per dimension |
| Broad audit across many services | 5–10, one per service |
| Anything larger | Ask first — it is the user's budget |

**Always verify adversarially.** An agent that reports a finding is not evidence that the finding
is real. The strongest pattern is two-stage: agents find candidates, a second pass tries to
disprove each one, and only survivors are reported. Most raw findings do not survive.

## Workflows vs. ad-hoc agents

Use a **workflow** when the shape is fixed and the value is in determinism: the same stages every
time, results cached, resumable after a failure. Use **ad-hoc agents** when the shape depends on
what you find.

Rule of thumb: if you would draw it as a diagram before running it, it is a workflow.

## Division of labour when writing back

Parallel agents writing to the same knowledge base is a merge conflict waiting to happen. Split it
by *kind of output*:

- **Subagents write knowledge.** Gotchas, insights, findings — small, additive, independent notes.
- **The top-level session writes the deliverable.** The report, the summary, the decision — the
  one artefact that needs a single coherent voice.

This keeps writes non-overlapping and keeps the thing you actually hand over consistent.

## Agent hygiene

- **Subagents do not inherit `CLAUDE.md`.** Read-only research agents in particular start without
  your rules. If a rule matters — *"reach the vault only through the MCP server"* — **put it in
  the prompt you give them.** This is the single most common cause of an agent quietly bypassing
  your access rules.
- **Give them a narrow brief.** "Find where X is configured" beats "look into X".
- **Ask for a conclusion, not a transcript.** Otherwise you have moved the context problem, not
  solved it.
- **Never fabricate a pending agent's result.** If it has not reported, say it is still running.

## Cost awareness

A ten-agent fan-out can cost more than a day of normal interactive work. That is fine when it
replaces a day of your work. It is not fine as a default. Two habits keep this honest:

- For anything large, **state the rough cost before starting** and let the user decide.
- For anything small, **just do it serially** — the overhead of coordination exceeds the win
  below a few genuinely independent units of work.

Next: [`08-operations.md`](08-operations.md).
