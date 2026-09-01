---
name: capture-knowledge
description: >
  Captures the durable, generalisable knowledge from the current session into the knowledge base —
  gotchas, insights, decisions and snippets, each in the right folder with the right template and
  the mandatory severity callout. Deduplicates against existing notes before writing and updates
  the folder index afterwards. Trigger on "/capture-knowledge", "write that down", "save this to
  the knowledge base", "capture the session", "add a gotcha for this". Do NOT trigger for reading
  or searching the knowledge base (that needs no skill), for documenting a codebase (that is
  `document-project`), or for writing a ticket or wiki page in the user's name (that is
  `write-as-me`).
argument-hint: "[optional focus, e.g. 'only the docker finding']"
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Capture knowledge

Closes the loop. A knowledge base that is only read goes stale; this skill is the return path.

## When this runs

At the end of a session that discovered something non-obvious. Also mid-session, the moment a
trap is found — a gotcha written while the surprise is fresh is worth three written from memory.

## Preconditions

- The knowledge base path is known and writable.
- `TEMPLATES/` exists. If it does not, stop and say so — inventing a layout per note is exactly
  what makes a vault unsearchable.

## Steps

### 0. Go through the session in episodes

Split the conversation into work episodes — one episode is one task or topic — and apply this
grid to each. Questions 1–4 are the point of the skill; 5–8 only when the episode yields
something.

| # | Question | Category |
|---|---|---|
| 1 | **Where** was the relevant code, config, table, dashboard? | orientation |
| 2 | Which **dependency or coupling** became visible (service → database, repo → service)? | coupling |
| 3 | **How was a piece of information obtained** — which tool, query, log source? | access path |
| 4 | Which **command or query** is reusable once parameterised? | snippet |
| 5 | Which **procedure** was worked out that will be repeated? | runbook |
| 6 | What **went wrong**, as a transferable pattern? | gotcha |
| 7 | Which **decision** was made, including rejected alternatives? | decision |
| 8 | What stayed **open**? | open item |

Couplings are the most valuable answer here — they only become visible when working across system
boundaries, and nothing else in the stack records them.

### 0b. Three sources that fall through the grid

These happen *in passing*, are never part of the task, and are therefore never reported. Go
through them deliberately.

| Source | What to look for |
|---|---|
| **Failed tool calls** | Every rejected call: wrong parameter name, missing permission, timeout, "not found", a 4xx. Including the ones that worked on the second try. Worked around in the moment and never discussed — and the richest source of gotchas there is. |
| **Subagent replies** | What came back: locations, query recipes, dead ends. The main transcript keeps only the conclusion; the route to it is in the reply. |
| **Tooling friction** | Where a tool was missing or awkward, and what was built instead. This does not belong in the knowledge base — route it to wherever you track improvements. |

### 1. Classify

For each candidate, decide what it is. Be strict:

| Kind | Destination | Marker |
|---|---|---|
| A trap that costs time | `GLOBAL/gotchas/<tech>/` or `PROJECTS/<p>/gotchas/` | severity callout, **mandatory** |
| A non-obvious mechanism | `GLOBAL/insights/` or `PROJECTS/<p>/architecture/` | — |
| A choice and its cost | `DECISIONS/` or `PROJECTS/<p>/decisions/` | status in frontmatter |
| A reusable command | `GLOBAL/snippets/` | a "when you want this" line |
| Nothing durable | nowhere | — |

**"Nothing" is a valid outcome.** A session of dead ends writes nothing. Say so and stop.

### 2. Generalise — the quality bar

Save the transferable core, never the incident.

- ❌ "Order 4711 was rejected as a duplicate."
- ✅ "Duplicate detection normalises e-mail case in SQL but not in the application, so the two
  disagree."

Test each candidate: *would this help someone who never saw this case?* If not, drop it.

### 3. Deduplicate

Search the knowledge base for each candidate **before** writing. If a note already covers it,
**update that note** rather than adding a fourth near-copy. Prefer merging to appending — a note
that grew by accretion is unreadable.

### 4. Write

- Use the matching template.
- Title states the **conclusion**, not the topic: `mount-goes-stale-after-resync.md`, never
  `docker-notes.md`.
- One idea per note.
- Gotchas open with `> [!severity] Title` — without it the note is invisible to retrieval.
- Link to related notes, including ones that do not exist yet.

### 5. Index and verify

- Add one line to the folder's `_INDEX.md` saying what the note answers.
- Check: callout present? No piped wikilinks inside table cells? No unintended broken links?

### 6. Report

Open with the count — episodes reviewed, candidates found, new, updated, discarded at the
generalisation gate, skipped as already present. The statistic is the evidence that the grid ran
on every episode, and it is mandatory even when everything is zero.

Then list what was written, updated, and deliberately skipped — with the reason for the skips.
The skips are the part the user needs to be able to veto.

End the reply with this line, literally, and only if something was actually written:

```
KNOWLEDGE_CAPTURED new=<n> updated=<n>
```

The scheduled harvest ([`automation/`](../../../automation/)) uses it to skip the part of the
session already filed. Leave it out on an abort or a zero harvest — then the session stays intact
for the next run and nothing is lost. See [[SKILLS/ops/mining-stop|mining-stop]] for declining
without harvesting.

## Guardrails

- **Never write secrets, tokens or credentials.** A knowledge base is not a password manager.
- **Never write what the code or git history already says.**
- **Never invent a folder** outside the established taxonomy.
- **Never overwrite an existing note wholesale** — merge, and preserve what was already there.
