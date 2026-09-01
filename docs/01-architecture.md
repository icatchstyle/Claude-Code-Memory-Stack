# 1 — Architecture: six layers, and why they must stay separate

The single most common way these setups fail is **putting knowledge in the wrong layer**. A fact
in `CLAUDE.md` costs tokens forever. A behaviour rule in the vault is never read at the moment it
matters. A procedure written as prose in a note gets skipped. Getting the layer right is most of
the work.

**In this chapter:** [The layers](#the-layers) · [The routing test](#the-routing-test) · [Why not just one big CLAUDE.md?](#why-not-just-one-big-claudemd) · [Why not just RAG over everything?](#why-not-just-rag-over-everything) · [The write-back loop](#the-write-back-loop)

## The layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│  HOOKS — deterministic reflexes                                          │
│  Fire on lifecycle events. The model cannot forget them.                 │
│  SessionStart · UserPromptSubmit · PreToolUse · PostToolUse · Stop       │
└──────────────────────────────────────────────────────────────────────────┘
             │ inject context, block calls, enforce invariants
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  CLAUDE.md — standing behaviour rules                    (always loaded)  │
│  "How do I work here?" — autonomy limits, language, access paths,        │
│  the obligation to consult the vault.                                    │
│  NEVER facts. Keep it under ~300 lines.                                  │
└──────────────────────────────────────────────────────────────────────────┘
             │ points to
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  VAULT — durable facts                                    (on demand)    │
│  "What is true here?" — architecture, gotchas, decisions, runbooks,      │
│  snippets, per-project orientation. Retrieved by search, not by size.    │
└──────────────────────────────────────────────────────────────────────────┘
             │ referenced by
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  SKILLS — procedures                                       (on trigger)  │
│  "How do I do X, step by step?" — multi-step workflows with a            │
│  description precise enough to fire exactly when wanted.                 │
└──────────────────────────────────────────────────────────────────────────┘
             │ executed through
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  MCP SERVERS — typed capabilities                        (on tool call)  │
│  "What can I touch?" — vault, tickets, database, git, logs.              │
│  Guardrails live server-side, where the model cannot argue with them.    │
└──────────────────────────────────────────────────────────────────────────┘
             │ scaled by
             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  SUBAGENTS & WORKFLOWS — parallelism and context isolation  (opt-in)     │
│  "How do I do a lot of this at once, without flooding my context?"      │
└──────────────────────────────────────────────────────────────────────────┘
```

## The routing test

When you learn something new, ask in this order:

1. **Does it change how the agent behaves in every session?** → `CLAUDE.md`
   *"Never commit unless explicitly asked." "Always write code comments in English."*
2. **Must it happen every time, without exception, even if the model is distracted?** → **hook**
   *"Remind me to search the knowledge base." "Rename the session after the ticket."*
3. **Is it a fact about a system, a trap, or a decision?** → **vault**
   *"The QA database profile is read-only." "The mount goes stale after a re-sync; restart the container."*
4. **Is it a repeatable sequence of steps?** → **skill**
   *"Ship the current ticket: commit, push, open an MR, comment the link, watch the pipeline."*
5. **Is it access to a system, or an operation that needs guardrails?** → **MCP server**
   *"Query the database." "Read the vault." "Open a merge request."*
6. **Is it the same work repeated over many independent inputs?** → **subagent / workflow**

If something fits two layers, it usually belongs in the *lower* one, with a one-line pointer from
the layer above. `CLAUDE.md` should be full of pointers and empty of content.

## Why not just one big CLAUDE.md?

Because it does not scale, and the failure is quiet.

- **Cost.** Every line is re-read on every prompt, in every session, forever. A 3,000-line
  `CLAUDE.md` is a permanent tax on every interaction you will ever have.
- **Dilution.** Instruction-following degrades as instructions grow. The twelfth rule is obeyed
  less reliably than the second. Facts crowding out rules make the rules weaker.
- **Staleness.** Nobody reviews a 3,000-line file. Vault notes have dates, backlinks, and a lint
  pass; a bloated `CLAUDE.md` has none of those and rots silently.
- **No retrieval.** You cannot ask a `CLAUDE.md` "what do I need to know about Terraform here?"
  You can ask a vault exactly that.

The counter-intuitive result: **a smaller `CLAUDE.md` makes the agent smarter**, because what
remains is actually followed.

## Why not just RAG over everything?

Retrieval alone answers "what is relevant to this text?" It does not answer "what am I obliged to
do before I answer?" Behaviour rules must be *unconditionally present*; facts must be
*conditionally retrieved*. That is exactly why the two live in different layers.

The vault is also more than a corpus: it is **curated**. Notes are written for retrieval — one
idea per note, an explicit severity, a title that states the conclusion, links to related notes.
That curation is what makes a 1,500-note vault more useful than a 50,000-page wiki dump.

## The write-back loop

The architecture above is only half the system. It describes reading. Without the return path,
the vault decays into a snapshot of the week you built it.

```
        ┌─────────────┐   search / gotcha check   ┌──────────┐
        │   session   │ ────────────────────────► │  vault   │
        │  (working)  │ ◄──────────────────────── │          │
        └─────────────┘        relevant notes      └──────────┘
               │                                        ▲
               │  end of session:                       │
               │  what was non-obvious here?            │
               └────────────────────────────────────────┘
                        write it back, generalised
```

Two rules keep the return path healthy:

- **Generalise or discard.** Save the transferable pattern, never the incident. "Order 4711 was a
  duplicate" is noise. "Duplicate detection normalises e-mail case in SQL but not in PHP, so the
  two disagree" is knowledge.
- **Deduplicate before writing.** Search first. Update the existing note instead of adding a
  fourth near-copy. A vault with three versions of a truth has none.

See [`docs/02-vault.md`](02-vault.md) for the conventions, and
[`docs/08-operations.md`](08-operations.md) for keeping it clean over time.
