#!/usr/bin/env bash
# Unattended harvest run: collect yesterday's sessions, hand them to an agent, file the result.
#
#   ./run.sh                 # DRY RUN — collects and reports, writes nothing. The default.
#   ./run.sh --write         # actually let the agent write to the knowledge base
#   ./run.sh --write --since-days 7
#
# Environment:
#   MINER_VAULT_DIR         path to the vault; if it is a git repository, the run verifies that
#                           reported writes actually landed instead of trusting the report
#   MINER_PERMISSION_MODE   permission mode for the headless agent (default: acceptEdits)
#   MINER_PROJECTS_DIR      where transcripts live (default: ~/.claude/projects)
#   MINER_STATE_DIR         where state, staging and logs live (default: ~/.claude/knowledge-miner)
#
# DRY RUN IS THE DEFAULT ON PURPOSE. This script points an unsupervised agent at your notes with
# write access. Nobody should get that by forgetting a flag.
#
# THE SAFETY RAILS, in order of importance:
#
#   1. State advances only on success. If the run fails, the next one covers the same window
#      again. Advancing a cursor past work that was never done loses it permanently, silently.
#   2. The write procedure must load before anything is written. An agent that cannot read the
#      conventions writes notes that violate them — at scale, unattended, and you find out at
#      the next lint, after dozens of them exist.
#   3. One run at a time. A second run harvesting the same window creates duplicates.
#   4. Version-control your vault. Not as a backup: so you can read the diff of what an agent
#      wrote while you slept. This script cannot enforce it; do it anyway.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${MINER_STATE_DIR:-$HOME/.claude/knowledge-miner}"
STATE_FILE="$STATE_DIR/last-run"
STAGING="$STATE_DIR/staging"
LOG_DIR="$STATE_DIR/logs"
LOCK="$STATE_DIR/lock"

WRITE=0
SINCE_DAYS=""
SKILL="${MINER_SKILL:-capture-knowledge}"

while [ $# -gt 0 ]; do
  case "$1" in
    --write)      WRITE=1; shift ;;
    --since-days) SINCE_DAYS="${2:-1}"; shift 2 ;;
    --skill)      SKILL="${2:-}"; shift 2 ;;
    -h|--help)    sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$STATE_DIR" "$LOG_DIR"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$LOG_DIR/$RUN_ID.log"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$LOG"; }
fail() { log "FAILED: $*"; log "State not advanced — the next run covers this window again."; exit 1; }

# --- 3. one run at a time -----------------------------------------------------------------
if ! mkdir "$LOCK" 2>/dev/null; then
  if [ -n "$(find "$LOCK" -maxdepth 0 -mmin -120 2>/dev/null)" ]; then
    log "Another run is in progress (lock younger than 2h). Exiting."
    exit 0
  fi
  log "Stale lock found, taking over."
  touch "$LOCK"          # refresh, or a second run started moments later takes over too
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

# --- window -------------------------------------------------------------------------------
if [ -n "$SINCE_DAYS" ]; then
  SINCE_ARGS=(--since-days "$SINCE_DAYS")
  log "Window: last $SINCE_DAYS day(s), explicitly requested."
elif [ -f "$STATE_FILE" ]; then
  SINCE_ARGS=(--since-iso "$(cat "$STATE_FILE")")
  log "Window: since $(cat "$STATE_FILE") (last successful run)."
else
  SINCE_ARGS=(--since-days 1)
  log "Window: last 24h (no previous run recorded)."
fi

# The timestamp the state would advance to. Captured BEFORE the work, so sessions written
# during the run are picked up next time rather than skipped.
NEW_STATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# --- collect ------------------------------------------------------------------------------
rm -rf "$STAGING"
COLLECT_ARGS=(--out "$STAGING" "${SINCE_ARGS[@]}")
[ -n "${CLAUDE_SESSION_ID:-}" ] && COLLECT_ARGS+=(--self-session "$CLAUDE_SESSION_ID")
[ -n "${MINER_PROJECTS_DIR:-}" ] && COLLECT_ARGS+=(--projects-dir "$MINER_PROJECTS_DIR")

log "Collecting…"
python3 "$HERE/collect_sessions.py" "${COLLECT_ARGS[@]}" 2>&1 | tee -a "$LOG" || fail "collector"

COUNT="$(find "$STAGING" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
if [ "$COUNT" -eq 0 ]; then
  log "Nothing to harvest. Advancing state."
  printf '%s' "$NEW_STATE" >"$STATE_FILE"
  exit 0
fi
log "$COUNT digest(s) in $STAGING"

# --- dry run stops here -------------------------------------------------------------------
if [ "$WRITE" -eq 0 ]; then
  log "DRY RUN — no agent invoked, nothing written, state not advanced."
  log "Inspect the digests in $STAGING, then re-run with --write."
  exit 0
fi

command -v claude >/dev/null 2>&1 || fail "the 'claude' CLI is not on PATH"

# --- 2. the conventions must load ---------------------------------------------------------
# Checked BEFORE granting write access. An unattended agent that cannot read the write
# procedure will invent its own — consistently, quietly, and across every note it files.
log "Verifying the write procedure is reachable…"
PROBE="$(claude -p 'Read the knowledge base note describing the write procedure for
knowledge-writing skills. Reply with exactly OK if it loaded and mentions the mandatory
severity callout for gotchas, otherwise reply MISSING.' 2>&1)" || fail "probe call"
case "$PROBE" in
  *OK*) log "Write procedure loaded." ;;
  *)    fail "write procedure did not load (got: ${PROBE:0:200}). Refusing to write." ;;
esac

# --- harvest ------------------------------------------------------------------------------
# Headless runs have no one to answer a permission prompt, so a write is simply refused unless
# the mode says otherwise. Without this the run looks successful and files nothing.
PERMISSION_MODE="${MINER_PERMISSION_MODE:-acceptEdits}"

# Is the vault a git repository? If it is, we can prove afterwards that something was actually
# written, rather than trusting the agent's own report. This is the functional reason the
# documentation asks you to version-control the vault.
VAULT_DIR="${MINER_VAULT_DIR:-}"
vault_dirty() {
  [ -n "$VAULT_DIR" ] || return 2
  git -C "$VAULT_DIR" rev-parse --git-dir >/dev/null 2>&1 || return 2
  [ -n "$(git -C "$VAULT_DIR" status --porcelain 2>/dev/null)" ]
}
vault_dirty; BEFORE=$?

log "Harvesting with /$SKILL (permission mode: $PERMISSION_MODE)…"
PROMPT="Run /$SKILL over the session digests in $STAGING.

Each file is one past session. Work through them and file what is durable and generalisable.
Pay particular attention to the 'Failed tool calls' sections: they are the richest source of
gotchas and nobody reports them, which is why they are collected mechanically.

Discard case detail. Save the transferable core, never the incident. Deduplicate against what
already exists before writing anything new. If a session yielded nothing durable, say so and
write nothing — that is a valid outcome, not a failure.

End your reply with: MINER_RESULT new=<n> updated=<n> skipped=<n>"

REPLY="$(claude -p --permission-mode "$PERMISSION_MODE" "$PROMPT" 2>&1 | tee -a "$LOG")"

RESULT="$(printf '%s' "$REPLY" | grep -o 'MINER_RESULT.*' | tail -1)"
[ -n "$RESULT" ] || fail "no MINER_RESULT marker in the reply — treating the run as incomplete"

NEW_COUNT="$(printf '%s' "$RESULT" | sed -n 's/.*new=\([0-9]*\).*/\1/p')"
UPD_COUNT="$(printf '%s' "$RESULT" | sed -n 's/.*updated=\([0-9]*\).*/\1/p')"
WROTE=$(( ${NEW_COUNT:-0} + ${UPD_COUNT:-0} ))
log "Reported: ${RESULT}"

# The marker alone is not proof. An agent whose writes were refused still reports a result —
# with zeroes, or worse, with counts for writes that never landed.
if [ "$WROTE" -gt 0 ]; then
  vault_dirty; AFTER=$?
  case "$BEFORE:$AFTER" in
    2:*) log "NOTE: the vault is not a git repository, so the report could not be verified." ;;
    *:0) log "Verified: the vault changed on disk." ;;
    *:1) fail "reported $WROTE write(s) but the vault is unchanged — writes were refused" ;;
  esac
fi

printf '%s' "$NEW_STATE" >"$STATE_FILE"
log "Done. State advanced to $NEW_STATE."
