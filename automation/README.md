# Automating the write-back loop

The scheduled harvest: read yesterday's sessions, extract what a person would have written
down, file it. This is the answer to the one line in the adoption table that fails quietly —
*"five minutes a day"* — because it is the only part that depends on human discipline rather
than on structure.

Read [`docs/11-automation.md`](../docs/11-automation.md) for the reasoning. This file is how to
run it.

> [!WARNING]
> This points an **unsupervised agent at your knowledge base with write access**. Dry run is the
> default and you should stay there for a week. Put the vault under version control first — not
> as a backup, but so you can read the diff of what was written while you slept.

## Quick start

```bash
./run.sh                          # dry run: collect and report, write nothing
ls ~/.claude/knowledge-miner/staging/    # read what it would have handed over

./run.sh --write                  # once you trust it
./run.sh --write --since-days 7   # catch up after a gap
```

Then schedule it — examples for [cron](schedule/crontab.example),
[launchd](schedule/com.example.knowledge-miner.plist) and
[Task Scheduler](schedule/register-task.ps1).

## What it collects

Three things a human never reports, because they happen in passing:

| Source | Why it matters |
|---|---|
| **Failed tool calls** | Worked around in the moment and never discussed. The richest source of gotchas there is — and mechanically collectable, which is exactly why a machine should do it. |
| **Subagent replies** | The main transcript keeps the conclusion; the route to it — where things live, which query answered what — is in the agent's reply. |
| **Prompts and reports** | The narrative that gives the other two their context. |

Thinking blocks are deliberately excluded: internal reasoning is not knowledge, and filing it as
if it were is how a vault fills up with plausible noise.

## The safety rails

**State advances only on success.** A failed run leaves the cursor where it was, so the next run
covers the same window. Advancing past work that was never done loses it permanently and without
a symptom.

**The write procedure must load before anything is written.** The runner asks the agent to read
the conventions and confirm; if that probe fails, it refuses to continue. An unattended agent
that cannot read the conventions invents its own — consistently, across every note it files, and
you find out at the next lint after dozens exist.

**One run at a time.** An atomic lock, with a two-hour staleness window so a crashed run does not
block the next day forever.

**A cut marker, so nothing is harvested twice.** A session already handled carries a marker; the
collector starts after the latest one. Re-harvesting is how duplicates get created, and duplicates
are the one defect a knowledge base does not recover from on its own.

## Files

| File | Purpose |
|---|---|
| `collect_sessions.py` | Transcripts → digests. Contains the one format-dependent function. |
| `run.sh` | The runner: window, collection, probe, harvest, state. |
| `schedule/` | cron, launchd and Task Scheduler examples |
| `tests/` | Fixture tests for the parsing and the cut marker |

## The part that will break

`parse_line` in `collect_sessions.py` reads Claude Code's transcript format, which is an internal
detail and can change without notice. It is deliberately the **only** function that knows the
format, and it is covered by fixtures in `tests/`.

When the format changes, `pytest tests/` fails loudly — instead of the collector quietly
producing empty digests, which is the failure you would not notice for weeks. Adapt that one
function; everything else works on `Event` objects and is unaffected.

```bash
pytest tests/ -v
```
