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

List what was written, updated, and deliberately skipped — with the reason for the skips. The
skips are the part the user needs to be able to veto.

## Guardrails

- **Never write secrets, tokens or credentials.** A knowledge base is not a password manager.
- **Never write what the code or git history already says.**
- **Never invent a folder** outside the established taxonomy.
- **Never overwrite an existing note wholesale** — merge, and preserve what was already there.
