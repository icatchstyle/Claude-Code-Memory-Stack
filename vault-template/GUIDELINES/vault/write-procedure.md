---
title: Write procedure for knowledge-writing skills
type: guideline
tags: [vault, guidelines, write]
date: 2026-09-01
---

# Write procedure for knowledge-writing skills

The single source of truth for **how** anything gets written into this knowledge base. Every
skill that writes here follows this chain. Deviating from it is how a vault becomes unsearchable.

## The chain

### 1. Classify

What did this session actually produce?

| Kind | Goes to | Marker |
|---|---|---|
| A trap that costs time | `gotchas/` | severity callout, **mandatory** |
| A non-obvious mechanism | `insights/` | — |
| A choice and its cost | `decisions/` | status in frontmatter |
| A reusable command | `snippets/` | a "when you want this" line |
| A followable procedure | `WORKFLOWS/` or a skill | preconditions + verification |
| Nothing durable | nowhere | — |

> [!warning] "Nothing" is a valid classification
> A session of dead ends should write nothing. A vault that records every session is a log, not
> a knowledge base.

### 2. Generalise

Save the transferable core, never the incident.

- ❌ "Order 4711 was rejected as a duplicate."
- ✅ "Duplicate detection normalises e-mail case in SQL but not in the application, so the two
  disagree." → gotcha, `danger`.

Test: *would this note help someone who has never seen this case?* If not, it is a log entry.

### 3. Deduplicate

**Search before writing.** If a note already covers it, update that note. A vault with three
versions of a truth has none, and the newest is not reliably the one retrieval returns.

Merging beats appending: a note that grew by accretion over six sessions is unreadable.

### 4. Write

- Use the matching template from `TEMPLATES/`.
- Title states the **conclusion**, not the topic.
- One idea per note. If the title needs an "and", split it.
- Frontmatter: consistent `date:` key, correct `type:`, a `severity:` for gotchas.
- Link liberally, including to notes that do not exist yet — a dangling link is a to-do marker.

### 5. Index

Add a line to the folder's `_INDEX.md` saying what the note answers. An unindexed note is found
only by full-text luck.

### 6. Check

- Does the gotcha have its callout? (The single highest-value check.)
- Any piped wikilinks inside table cells? (They break.)
- Any new broken links that were not intended?

## Division of labour under parallelism

When several agents work at once:

- **Subagents write knowledge** — small, additive, independent notes.
- **The top-level session writes the deliverable** — the report or summary that needs one voice.

This keeps writes non-overlapping and the handover coherent.

## Navigation

- [[GUIDELINES/vault/_INDEX|Vault guidelines]] · [[HOME|Home]]
