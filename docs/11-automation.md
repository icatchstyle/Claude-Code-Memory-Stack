# 11 — Automating the write-back loop

Every other layer in this stack is structural. A hook fires or it does not. A guardrail is in code
or it is not. Retrieval is mandatory or it is advisory, and if it is advisory it does not happen.

The write-back loop is the exception, and that is why it is the part that fails.

**In this chapter:** [Why this needs automating](#why-this-needs-automating) · [What a machine collects that you never would](#what-a-machine-collects-that-you-never-would) · [The safety rails](#the-safety-rails) · [Proving the run happened](#proving-the-run-happened) · [The cut marker](#the-cut-marker) · [What will break](#what-will-break) · [Running it](#running-it)

## Why this needs automating

Chapter 9 puts the honest cost at *five minutes a day*, and calls it "the only line in the table
that fails quietly if you skip it". That is the whole problem in one sentence.

Skipping it produces no error. The vault does not shrink; it simply stops growing while your
systems keep changing. Six weeks later retrieval starts returning answers that were true in
spring, you stop trusting it, and then you stop reading it — at which point every other layer is
still working perfectly and delivering nothing.

Discipline is not a fix for a structural problem. It is a fix that works until the week you are
busy, which is also the week that produces the most worth writing down.

So: schedule it. Read yesterday's sessions, extract what a person would have written down, file
it. The reference implementation is [`automation/`](../automation/).

## What a machine collects that you never would

This is the part that makes automation worth more than a reminder, and it is easy to miss.

**Failed tool calls.** A wrong parameter name, a missing permission, a timeout, a "not found".
You work around it in the moment and never mention it again. It is not in your summary because it
was not the point of the task — and it is, reliably, the richest source of gotchas you have.

A person cannot report these: nobody remembers the eleven small frictions of a working day. A
collector reading transcripts finds them mechanically, every time, without judgement.

**Subagent replies.** The main transcript keeps the conclusion, because that is what the parent
session needed. But the *route* — where the thing lived, which query answered it, which dead end
was excluded — is in the agent's own reply, and that is orientation knowledge, the highest-value
category in the vault.

**Tooling friction.** Where a tool was missing or awkward, and what got built instead. Unlike the
two above this is *not* extracted mechanically — recognising it takes judgement, not pattern
matching. The harvesting skill looks for it while reading the digest. It does not belong in the
knowledge base either; route it to whatever list you keep of things to improve.

What is deliberately *not* collected: thinking blocks. Internal reasoning is not knowledge, and
filing it as if it were is how a vault fills with plausible noise.

## The safety rails

This points an unsupervised agent at your knowledge base with write access. Five rails, in order
of how much they matter.

### 1. State advances only on success

If the run fails, the cursor stays where it was and the next run covers the same window again.

The alternative — advancing a cursor past work that was never done — loses that window
permanently, and produces no error at any point. It is the worst failure mode available here,
precisely because it looks like success.

### 2. The conventions must load before anything is written

The runner asks the agent to read the write procedure and confirm it mentions the mandatory
severity callout. If that probe fails, the run refuses to continue.

This is not ceremony. An unattended agent that cannot read the conventions does not stop — it
invents its own, consistently, across every note it files. Gotchas land without callouts, which
makes them **invisible to retrieval** (chapter 2), and you discover it at the next lint, after
dozens exist. A run that writes nothing is recoverable in a minute; a run that writes eighty
malformed notes is an afternoon.

### 3. The run must be able to authenticate

Checked with a trivial prompt before the harvest, and never retried.

An expired login is the failure this chapter would otherwise not survive, because it is the one
that looks like nothing. The scheduler starts the job on time. The collector runs, finds its
sessions, writes its digests. Then the agent call dies in about three seconds, and the log ends
with a line that reads like an authentication detail rather than an outage. Tomorrow the same
thing happens, and the day after.

Two decisions follow from that:

- **Fail before the work, not during it.** The check is a separate call with its own error, so
  the log says *the login expired* rather than *the write procedure did not load* — which is what
  an auth failure looks like when the convention probe is the first thing to touch the network.
- **Never retry an auth failure.** A second attempt fails identically within seconds and pushes
  the real cause further up the log. A retry loop is for flaky things; a missing credential is
  not flaky.

### 4. One run at a time

An atomic lock, with a staleness window so a crashed run does not block tomorrow forever.

### 5. Version-control the vault

The script cannot enforce this, so the chapter says it instead: **put the vault in git before you
enable writing.** Not as a backup. As a review mechanism — `git diff` is how you read what an
agent wrote while you slept, and the only realistic way to catch it drifting.

Start in dry run. Stay there a week. Read the digests it collects and the reports it would have
acted on. Only then add `--write`.

## Proving the run happened

A scheduler tells you that it started a process. That is all it tells you.

Every scheduler surface — last run time, next run time, exit code, "missed runs: 0" — describes
the wrapper, not the work. A harvest that authenticates, collects nothing usable and dies looks
identical to one that filed nine gotchas, and both look identical to a run that wrote eighty
malformed notes. So the runner keeps its own account, and you read that instead:

```bash
python3 automation/run.py --status
```

```
cursor (window starts here) : 2024-05-06T07:08:09Z
last attempt                : 2024-05-20T07:20:03Z
last successful harvest     : 2024-05-06T07:20:01Z
status                      : auth_failed
consecutive failures        : 12 (since 2024-05-07T07:20:02Z)
```

Three things in that output do work no scheduler does:

- **`status`** is why the run ended, in the runner's own words: `ok`, `ok_empty`,
  `collector_failed`, `auth_failed`, `failed`.
- **`consecutive_failures`** turns a series into one fact. A single failure is bad luck; twelve
  in a row is a broken system, and the difference is invisible if you only ever see the newest
  log.
- **The gap between `last attempt` and `last successful harvest`** is the window that is still
  waiting to be collected. It grows every day the job fails, which is also why the next
  successful run announces itself as a catch-up.

`--status` exits non-zero while runs are failing, so it composes into whatever already watches
your machine, without needing to parse a log.

## The cut marker

A session that has already been harvested must not be harvested again — duplicates are the one
defect a knowledge base does not recover from on its own, because retrieval cannot tell you which
of three near-identical notes is current.

So a session carries a marker, and the collector starts after the latest one:

| Marker | Emitted by | Meaning |
|---|---|---|
| `KNOWLEDGE_CAPTURED` | [`capture-knowledge`](../vault-template/SKILLS/ops/capture-knowledge.md) | The earlier part is filed. |
| `MINING_STOP` | [`mining-stop`](../vault-template/SKILLS/ops/mining-stop.md) | The earlier part is not worth filing. |

The second exists because a lot of real work is experimentation and dead ends. Pushing that
through a model nightly costs tokens and yields nothing. `mining-stop` writes nothing, reads
nothing, and emits one line — it has to be cheap enough to use mid-task.

Both cuts are irreversible: what precedes them is never seen again. That is the point, and it is
worth being deliberate about.

## What will break

One function. `parse_line` in `collect_sessions.py` reads Claude Code's transcript format, which
is an internal detail that can change without notice.

That fragility is contained rather than accepted:

- It is the **only** function that knows the format. Everything downstream works on `Event`
  objects.
- It is covered by **fixture tests**. When the format moves, `pytest` fails loudly — instead of
  the collector quietly producing empty digests, which is the failure nobody notices for weeks.
- The failure mode is *no knowledge captured*, never *wrong knowledge captured*.

Adapt that one function and the rest keeps working. This is the only part of this template that
depends on something outside its control, and it is worth knowing that going in.

## Running it

```bash
cd automation
python3 run.py                           # dry run — the default
ls ~/.claude/knowledge-miner/staging/    # read what it would hand over
python3 run.py --write                   # once you trust it
python3 run.py --status                  # what the last runs actually did
```

The runner is Python and standard library only, so it runs the same way on Linux, macOS and
Windows. That is not tidiness: this is the one part of the stack that runs while nobody is
watching, and a harvest that depends on a shell being installed silently stops existing on the
machine that does not have one. `run.sh` is kept as a thin wrapper for crontabs and Makefile
targets that already point at it.

Scheduling examples for cron, launchd and Windows Task Scheduler are in
[`automation/schedule/`](../automation/schedule/). All three start **without** `--write`. The
Task Scheduler script registers a native Python run by default and takes `-UseWsl` for setups
where the knowledge base lives inside WSL.

## Where this sits in the stack

Worth noticing, because it is the first thing in this repository that uses every layer at once:

| Layer | Part |
|---|---|
| **Skill** | `capture-knowledge` decides *what* is worth filing |
| **Script** | `collect_sessions.py` does the mechanical work a model should not |
| **Reflex** | the scheduler entry, so it happens without anyone deciding to |
| **Capability** | the vault MCP server, through which everything is written |
| **Rules** | the write procedure, which the run verifies before it writes |

That is the argument of chapter 1, running unattended at 07:20.
