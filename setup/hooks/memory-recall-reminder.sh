#!/usr/bin/env bash
# UserPromptSubmit hook: re-inject the knowledge-recall obligation every turn.
#
# WHY THIS EXISTS
#   CLAUDE.md states the recall rule once, at session start. Sixty turns later that
#   instruction is far away and competing with everything since. This hook restates the
#   obligation next to the prompt it applies to, which is the difference between a knowledge
#   base that gets consulted and one that does not.
#
# CONTRACT
#   stdin  : JSON payload with .prompt
#   stdout : JSON with hookSpecificOutput.additionalContext  (injected into the model's context)
#   exit   : ALWAYS 0 — a hook must never break the turn.
set -uo pipefail

payload="$(cat)" || exit 0
prompt="$(printf '%s' "$payload" | jq -r '.prompt // ""' 2>/dev/null)" || exit 0

# Skip pure acknowledgements: no task in them, nothing to recall.
normalized="$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]' | tr -d '[:punct:][:space:]')"
case "$normalized" in
  yes|no|ok|okay|yep|go|continue|next|thanks|thx|stop|abort|"") exit 0 ;;
esac

# Edit the text below to match your own tooling and wording.
jq -n '{
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: "MEMORY RECALL (binding, applies to this turn): before you answer or start working, consult the knowledge base — a gotcha check with the context (project, technologies, paths) AND a search with one or two precise terms. Skip only for a pure follow-up about the running conversation, a bare confirmation, or a search already run this session. Do not talk yourself out of it as trivial: questions that sound like general knowledge often have a project-specific answer here. If the search finds nothing, carry on normally. Write new insights back at the end."
  },
  suppressOutput: true
}' 2>/dev/null || exit 0
