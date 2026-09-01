# 6 — Hooks: turning instructions into reflexes

A hook is a shell command Claude Code runs on a lifecycle event. Hooks are the only layer in this
stack that is **deterministic**: the model can forget an instruction, drift from it under a long
context, or reason its way around it. A hook just runs.

Use hooks for anything that must happen *every* time. Use instructions for anything that needs
judgement. Getting that split right is most of the value.

**In this chapter:** [Events](#events) · [The rules of hook writing](#the-rules-of-hook-writing) · [The three hooks in this template](#the-three-hooks-in-this-template) · [Wiring](#wiring) · [Ideas worth stealing](#ideas-worth-stealing) · [Debugging](#debugging)

## Events

| Event | Fires | Typical use |
|---|---|---|
| `SessionStart` | New session | Start MCP daemons, health-check the environment |
| `UserPromptSubmit` | Each user message | Inject standing context; observe the prompt |
| `PreToolUse` | Before a tool call | Block or warn on dangerous operations |
| `PostToolUse` | After a tool call | Lint, format, log |
| `Stop` | Turn ends | Notify |
| `Notification` | Input needed | Notify differently |

## The rules of hook writing

1. **Never break the turn.** `set -uo pipefail`, not `-e`. Every failure path exits `0`. A hook
   that dies takes your session with it, and it will die on the day a dependency is missing.
2. **Be fast.** `UserPromptSubmit` and `SessionStart` are on the critical path of every
   interaction. Set a `timeout`, and background anything slow with `nohup … &`.
3. **Mind stdout.** For `UserPromptSubmit`, stdout is injected into the context. If your hook is
   not meant to speak to the model, redirect it: `exec 1>/dev/null`.
4. **Be idempotent.** Hooks fire more often than you expect, sometimes twice for one event.
5. **Fail silently, log loudly.** Write diagnostics to a file, not to the conversation.

## The three hooks in this template

### `memory-recall-reminder.sh` — the one that matters

`CLAUDE.md` states the recall rule once, at session start. Sixty turns later that instruction is
far away and competing with everything since. This hook restates the obligation **every turn**,
right next to the prompt it applies to.

It skips bare acknowledgements ("yes", "ok", "stop") so the reminder does not fire on messages
with no task in them.

```bash
payload="$(cat)"
prompt="$(printf '%s' "$payload" | jq -r '.prompt // ""')"

normalized="$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]' | tr -d '[:punct:][:space:]')"
case "$normalized" in
  yes|no|ok|okay|go|continue|thanks|stop|"") exit 0 ;;
esac

jq -n '{
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: "MEMORY RECALL (binding, this turn): before answering …"
  },
  suppressOutput: true
}'
```

`suppressOutput: true` keeps it invisible to you while remaining visible to the model.

This single hook is the difference between a vault that gets consulted and one that does not. If
you adopt nothing else from this chapter, adopt this.

### `session-name-ticket.sh` — naming sessions after the work

Detects a ticket key in the prompt and renames the session, so a screen full of sessions is
readable. Three safeguards make it safe:

- **Only rename interactive sessions.** Background and subagent sessions must not touch a title
  a human is looking at.
- **Never overwrite a manual rename.** The hook records the titles it set; if the current title is
  not one of them, it stands down. A human decision is final.
- **Fail soft everywhere.** It depends on transcript internals that may change. Every unexpected
  state exits `0` in silence.

The pattern generalises: *touch only what you created, and stop the moment reality disagrees.*

### `notify.sh` — audible turn completion

Plays a sound when a turn ends or input is needed. Genuinely useful for long runs. Worth reading
for two techniques it demonstrates:

- **A mute switch outside the code.** A flag file in the vault turns sounds off globally or per
  event, so silencing them is a one-line edit, not a settings hunt.
- **Debouncing with an atomic lock.** The same event can fire twice in quick succession;
  `mkdir` is atomic, so exactly one of two racing calls wins and the other bails.

## Wiring

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [
        { "type": "command", "command": "/path/to/mcp/vault/scripts/ensure-up.sh >/tmp/vault-mcp.log 2>&1" },
        { "type": "command", "command": "nohup /path/to/mcp/logs/scripts/ensure-up.sh >/tmp/logs-mcp.log 2>&1 &" }
      ]}
    ],
    "UserPromptSubmit": [
      { "hooks": [
        { "type": "command", "command": "$HOME/.claude/hooks/memory-recall-reminder.sh", "timeout": 5 },
        { "type": "command", "command": "$HOME/.claude/hooks/session-name-ticket.sh", "timeout": 5 }
      ]}
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "$HOME/.claude/hooks/notify.sh done" } ] }
    ]
  }
}
```

Note the mix: the vault daemon is **blocking** (the first prompt needs it), the others are
**backgrounded** (nothing in the first turn depends on them). That is deliberate — a session that
takes four seconds to start is a session you stop opening.

## Ideas worth stealing

- **`PreToolUse` guard** on destructive commands against production-named targets — a hard block
  is better than a rule the model might rationalise past.
- **`PostToolUse` formatter** after every edit, so style never reaches review.
- **`SessionStart` health check** that warns when a daemon is up but its data source is empty —
  catching the stale-mount failure before it wastes an hour.

## Debugging

Hooks are silent by design, which makes them confusing when wrong. Test them by hand:

```bash
echo '{"prompt":"test","session_id":"x","transcript_path":"/dev/null"}' \
  | ~/.claude/hooks/memory-recall-reminder.sh
```

If nothing comes out and you expected JSON, check that `jq` exists, the file is executable, and
the path in `settings.json` is absolute. Those three account for nearly every broken hook.

Next: [`07-scale.md`](07-scale.md).
