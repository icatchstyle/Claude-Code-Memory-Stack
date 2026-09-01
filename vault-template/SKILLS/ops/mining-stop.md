---
name: mining-stop
description: >
  Marks the conversation so far as not worth harvesting, so the scheduled harvest skips it. Writes
  nothing, changes nothing, analyses nothing — it only emits the marker line. For sessions whose
  history is experimentation, dead ends or throwaway work that the harvester would otherwise push
  through a model for no gain. Trigger ONLY on an explicit "/mining-stop". Do NOT trigger on
  "save this", "update the knowledge base" or "capture the session" — that is `capture-knowledge`,
  which actually harvests.
---

# Mining stop

The abstaining counterpart to [[SKILLS/ops/capture-knowledge|capture-knowledge]]. Both cut the
session for the scheduled harvest; they differ in what happens first.

- `capture-knowledge` says: *the earlier part is filed.*
- `mining-stop` says: *the earlier part is not worth filing.*

## What to do

Exactly two things:

1. Print one short confirmation line, so the cut is visible in the transcript.
2. As the **very last line** of the reply, literally:

   ```
   MINING_STOP
   ```

## What must not happen

No search, no reading back over the conversation, no harvest table, **no write of any kind**, no
re-index, no summary. And no asking whether something should be saved after all — the invocation
*is* that decision.

The value of this skill is that it costs nothing. It has to be usable mid-task without loading
context.

## Why the marker must be last and literal

The collector looks for it as a substring in assistant messages. Text after it is harmless; the
marker missing entirely means no cut happens. Unlike `capture-knowledge` there is no fallback
signal — that one can also be detected by its writes, and this one writes nothing by design.

> [!warning] The cut is not reversible
> Everything before the marker is never seen by the harvest again. That is the purpose, but be
> deliberate: if the history does contain something generalisable, call `capture-knowledge`
> instead. It cuts just the same, but files the knowledge first.

## Related

- [[SKILLS/ops/capture-knowledge|capture-knowledge]] — harvests, then cuts
- [[SKILLS/ops/vault-lint|vault-lint]] — finds what a careless harvest left behind
