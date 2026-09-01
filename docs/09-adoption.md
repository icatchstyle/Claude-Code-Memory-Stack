# 9 — Adoption: what to do, in what order

The fastest way to fail at this is to build the whole thing in a weekend and then never feed it.
The stack pays off through **use**, not through construction. Build the smallest thing that
creates a habit, then let the habit pull the rest.

**In this chapter:** [Day 1 — rules only (30 minutes)](#day-1-rules-only-30-minutes) · [Week 1 — memory (half a day, then five minutes a day)](#week-1-memory-half-a-day-then-five-minutes-a-day) · [Week 2 — reflexes (1 hour)](#week-2-reflexes-1-hour) · [Weeks 3–6 — procedures (as they emerge)](#weeks-36-procedures-as-they-emerge) · [Month 2 — capabilities (a day, if the pain justifies it)](#month-2-capabilities-a-day-if-the-pain-justifies-it) · [Month 3+ — scale, and only then](#month-3-scale-and-only-then) · [The honest cost](#the-honest-cost) · [Signals you are doing it right](#signals-you-are-doing-it-right) · [Signals you are doing it wrong](#signals-you-are-doing-it-wrong)

## Day 1 — rules only (30 minutes)

Write `~/.claude/CLAUDE.md`. Nothing else. Start from
[`setup/CLAUDE.md.template`](../setup/CLAUDE.md.template) and fill in only:

- **Autonomy limits.** What must never happen unasked. Be specific and enumerate.
- **Output conventions.** Language of prose vs. code comments; comment style.
- **One or two things you are tired of repeating.**

Keep it under a page. Resist adding facts.

**You now have:** consistent behaviour. This alone is worth the half hour.

## Week 1 — memory (half a day, then five minutes a day)

```bash
./setup/bootstrap.sh --vault ~/vault
```

Then:

1. **Write `HOME.md`** — what lives where. Ten lines.
2. **Write one project `_INDEX.md`** for the system you touch most: stack, repo path,
   environments, where the important things are. This one note will earn its cost in a week.
3. **Add the recall rule** to `CLAUDE.md` (the exact wording is in
   [`03-claude-md.md`](03-claude-md.md)).
4. **Write gotchas as they happen.** Every time something surprises you, write it down
   immediately, with the callout. Do not batch this; batched notes never get written.

**Do not** try to backfill everything you know. It is a large effort with no feedback, and most of
it will be wrong or irrelevant. Write knowledge when it is fresh, provoked by real work.

**You now have:** facts that survive the session. This is the biggest single step in the whole
progression.

## Week 2 — reflexes (1 hour)

Install `memory-recall-reminder.sh` and wire it to `UserPromptSubmit`.

You will notice the difference immediately: recall stops depending on whether the model happened
to think of it. If you adopt exactly one hook, this is the one.

Optionally add the notification hook — small, and it changes how you work with long runs.

**You now have:** recall that is reliable rather than hopeful.

## Weeks 3–6 — procedures (as they emerge)

Do not sit down to "write skills". Instead: **the third time you explain the same multi-step
procedure, make it a skill.** Third time, not first — the first two teach you what the procedure
actually is.

Start with the two highest-value ones for almost everyone:

- **A write-back skill** — end a session by capturing what was durable. This closes the loop.
  A worked example ships with this template:
  [`capture-knowledge`](../vault-template/SKILLS/ops/capture-knowledge.md).
- **A maintenance skill** — the counterpart that keeps the result findable. Also included:
  [`vault-lint`](../vault-template/SKILLS/ops/vault-lint.md).
- **Your delivery procedure** — whatever "ship this" means in your world. This one you write
  yourself, and deliberately so: branching models, review conventions and ticket systems differ
  too much for a generic version to be anything but wrong or vacuous.

Put them in `SKILLS/` in the vault, symlink them, and keep `SKILLS/_INDEX.md` current.

**You now have:** repeatable procedures that fire on a word.

## Month 2 — capabilities (a day, if the pain justifies it)

Add the vault MCP server when grep-based recall starts costing more context than it saves.
[`mcp/vault-mcp/`](../mcp/vault-mcp/) runs as-is; the useful work is adapting `gotcha_check` to
how you actually phrase things.

Then add servers for the systems you touch daily, one at a time, each with real server-side
guardrails. Resist adding a server for something you touch monthly — the maintenance is constant
and the payoff is not.

**You now have:** typed, guarded access, and structured retrieval.

## Month 3+ — scale, and only then

Subagents and workflows are last for a reason: they multiply whatever you already have. Applied to
a good stack they save hours. Applied to a stack with no shared knowledge, they multiply confusion
and cost — several agents, each re-deriving the same context you never wrote down.

**You now have:** parallelism that does not flood your context.

## The honest cost

| Phase | Setup | Ongoing |
|---|---|---|
| Rules | 30 min | 20 min/month audit |
| Memory | 4 h | 5 min/day writing |
| Reflexes | 1 h | ~0 |
| Procedures | 1–2 h per skill | occasional revision |
| Capabilities | 1 day per server | occasional |
| Scale | 2 h | per-use judgement |

The five minutes a day is the part that matters. Everything else is one-off; that one is the
habit, and it is the only line in the table that fails quietly if you skip it.

## Signals you are doing it right

- You catch yourself thinking *"I should write that down"* — and it takes fifteen seconds.
- The agent warns you about something before you hit it.
- A new project gets its `_INDEX.md` on day one, unprompted.
- Your `CLAUDE.md` gets **shorter** over time, as facts migrate into the vault.

## Signals you are doing it wrong

- The vault only grows when you deliberately sit down to write it.
- `CLAUDE.md` is past 500 lines.
- You have skills you have never invoked.
- You cannot remember the last time a search returned something useful.

The last one is terminal: it means titles name topics instead of conclusions, or the write-back
loop stopped. Fix retrieval before adding anything new.

Next: [`10-antipatterns.md`](10-antipatterns.md).
