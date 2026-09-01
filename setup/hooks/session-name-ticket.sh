#!/usr/bin/env bash
# UserPromptSubmit hook: name the session after the ticket key the user just mentioned,
# as long as the session still carries an auto-generated name.
#
# WHY
#   A screen full of sessions called "Refactoring the thing" is unreadable. Named after the
#   ticket, it is a work queue.
#
# THREE SAFEGUARDS — the reason this is safe to run on every prompt:
#   1. Only interactive sessions are renamed. Background/subagent runs must never touch a
#      title a human is looking at.
#   2. A manual rename is final. The hook records the titles it set; if the current title is
#      not one of its own, it stands down.
#   3. Fail soft everywhere. It relies on transcript internals that may change; every
#      unexpected state exits 0 in silence rather than breaking the turn.
#
# NOTE: the transcript mechanics below are host internals and may differ in your version.
#       Treat this as a pattern to adapt, not an API to depend on.
set -uo pipefail

# UserPromptSubmit stdout is injected as context — this hook must never speak to the model.
exec 1>/dev/null

STATE_DIR="$HOME/.claude/session-name"
TICKET_RE='(PROJ|OPS|SUP)-[0-9]{1,6}'     # <-- adapt to your ticket prefixes
MAX_DESC_WORDS=5

payload="$(cat)" || exit 0
sid="$(printf '%s' "$payload"        | jq -r '.session_id // ""'      2>/dev/null)"
transcript="$(printf '%s' "$payload" | jq -r '.transcript_path // ""' 2>/dev/null)"
prompt="$(printf '%s' "$payload"     | jq -r '.prompt // ""'          2>/dev/null)"

[ -n "$sid" ] && [ -n "$transcript" ] && [ -f "$transcript" ] || exit 0

# Guard 1: interactive sessions only.
session_file="$(grep -l "\"sessionId\":\"$sid\"" "$HOME"/.claude/sessions/*.json 2>/dev/null | head -1)"
[ -n "$session_file" ] || exit 0
[ "$(jq -r '.kind // ""' "$session_file" 2>/dev/null)" = "interactive" ] || exit 0

ticket="$(printf '%s' "$prompt" | grep -oiE "$TICKET_RE" | head -1 | tr '[:lower:]' '[:upper:]')"
[ -n "$ticket" ] || exit 0

current="$(grep '"type":"custom-title"' "$transcript" 2>/dev/null | tail -1 \
           | jq -r '.customTitle // ""' 2>/dev/null)"
owned="$(cat "$STATE_DIR/$sid" 2>/dev/null || true)"

# Guard 2: leave alone anything this hook did not write itself.
if [ -n "$current" ] && [ "$current" != "$owned" ]; then exit 0; fi

# Description: reuse the host's own auto-generated title, trimmed to a few words.
desc="$(grep '"type":"ai-title"' "$transcript" 2>/dev/null | tail -1 \
        | jq -r '.aiTitle // ""' 2>/dev/null | tr '\n' ' ' \
        | awk -v n="$MAX_DESC_WORDS" '{for(i=1;i<=NF&&i<=n;i++)printf "%s%s",(i>1?" ":""),$i}')"

title="$ticket"
[ -n "$desc" ] && title="$ticket $desc"
[ "$title" != "$current" ] || exit 0

line="$(jq -cn --arg t "$title" --arg s "$sid" \
        '{type:"custom-title",customTitle:$t,sessionId:$s}')" || exit 0
printf '%s\n' "$line" >>"$transcript" || exit 0

mkdir -p "$STATE_DIR" 2>/dev/null && printf '%s' "$title" >"$STATE_DIR/$sid" 2>/dev/null
exit 0
