# 10 — Anti-patterns: how these setups actually fail

Each of these is a real failure mode with a real cost. They are ordered roughly by how often they
happen.

**The twelve:** [The `CLAUDE.md` that ate the vault](#1-the-claudemd-that-ate-the-vault) · [Advisory recall](#2-advisory-recall) · [The read-only vault](#3-the-read-only-vault) · [Copies instead of symlinks](#4-copies-instead-of-symlinks) · [Descriptions without exclusions](#5-descriptions-without-exclusions) · [Notes titled by topic](#6-notes-titled-by-topic) · [Gotchas without the marker](#7-gotchas-without-the-marker) · [Guardrails in the prompt instead of the server](#8-guardrails-in-the-prompt-instead-of-the-server) · [Unbounded tool output](#9-unbounded-tool-output) · [Subagents as the first move](#10-subagents-as-the-first-move) · [Agents that never saw your rules](#11-agents-that-never-saw-your-rules) · [Building for a team before it works for one person](#12-building-for-a-team-before-it-works-for-one-person)

---

### 1. The `CLAUDE.md` that ate the vault

**Looks like:** 800+ lines. Service inventories, host lists, database profiles, architecture
notes, a step-by-step deploy procedure.

**Costs:** every line, on every prompt, forever — plus degraded instruction-following, because
rules are diluted by facts.

**Fix:** for each line ask *"does this change what the agent does, or only what it knows?"*
Knowledge goes to the vault with a one-line pointer left behind. Target 150–300 lines.

---

### 2. Advisory recall

**Looks like:** *"Consult the knowledge base when relevant."*

**Costs:** the vault is never read. The agent cannot know a lookup was relevant until it has
done it, and missing knowledge leaves no visible gap.

**Fix:** mandatory by default, with a short closed exemption list, plus a `UserPromptSubmit` hook
that restates it every turn. Explicitly forbid the "this seems trivial" rationalisation.

---

### 3. The read-only vault

**Looks like:** a good structure, built in one enthusiastic weekend, unchanged since.

**Costs:** it goes stale, retrieval starts returning wrong answers, trust collapses, and then
nobody reads it either.

**Fix:** a write-back skill and the five-minutes-a-day habit. If writing feels like a chore, the
write path has too much friction — reduce the friction, do not rely on discipline.

---

### 4. Copies instead of symlinks

**Looks like:** a skill in the vault *and* a copy in `~/.claude/skills/`.

**Costs:** silent drift. You edit the vault version, nothing changes, and you lose an hour before
realising the active file is a stale twin.

**Fix:** symlink, always. `ln -sfn "$VAULT/SKILLS/..." ~/.claude/skills/<name>`. Lint for skills
that exist in one place and not the other.

---

### 5. Descriptions without exclusions

**Looks like:** `description: Checks things.`

**Costs:** either the skill fires constantly on unrelated prompts, or a good skill never loads.

**Fix:** the three-part shape — what it does, "trigger on" with literal phrases, "do NOT trigger
for" with the adjacent cases named and redirected.

---

### 6. Notes titled by topic

**Looks like:** `docker-notes.md`, `database-stuff.md`, `misc-findings.md`.

**Costs:** unfindable. Search matches titles heavily, and a topic title matches everything and
answers nothing.

**Fix:** the title states the conclusion. `mount-goes-stale-after-resync.md`. One idea per note;
if the title needs an "and", split it.

---

### 7. Gotchas without the marker

**Looks like:** a well-written trap note with no severity callout.

**Costs:** invisible to structured retrieval. The note exists and never surfaces at the moment it
would have saved you.

**Fix:** the callout is mandatory. Lint for it — this is the single highest-value lint check.

---

### 8. Guardrails in the prompt instead of the server

**Looks like:** *"Never run mutating SQL against production."*

**Costs:** it holds until the day it does not. An instruction is a strong suggestion; the model
can reason its way past one under pressure.

**Fix:** enforce server-side. A read-only profile that rejects mutating SQL in code cannot be
talked around. If it must never happen, make it impossible, not forbidden.

---

### 9. Unbounded tool output

**Looks like:** a query tool that returns whatever the query matched.

**Costs:** one call fills the context; everything after it is worse and more expensive.

**Fix:** cap server-side, push the limit into the query itself, offer an `out_file` for large
results. This is a server responsibility, not a prompting problem.

---

### 10. Subagents as the first move

**Looks like:** reaching for a fan-out before the vault has anything in it.

**Costs:** several agents, each re-deriving context nobody wrote down, at several times the price.

**Fix:** knowledge first, then procedures, then scale. Subagents multiply what you have — make
sure that is worth multiplying.

---

### 11. Agents that never saw your rules

**Looks like:** a research subagent reading your vault directly off disk, bypassing the server.

**Costs:** skipped validation and indexing, plus writes that break your conventions.

**Fix:** subagents do not inherit `CLAUDE.md`. Put the rules that matter **in their prompt**, and
prefer read-only agent types for anything exploratory.

---

### 12. Building for a team before it works for one person

**Looks like:** governance, a review process, and a taxonomy committee, on day three.

**Costs:** the friction kills the habit before the value appears.

**Fix:** make it work for you first. Conventions that survive one person's daily use are the only
ones worth standardising on. Share the shape, not the content.

---

## The meta-lesson

Every failure above is the same shape: **the system asked a human (or a model) to remember
something, instead of making it structural.**

Structure the rule so it cannot be skipped. Structure the note so it can be found. Structure the
guardrail so it cannot be argued with. Then the discipline you need to sustain it is almost none —
which is the only amount that lasts.
