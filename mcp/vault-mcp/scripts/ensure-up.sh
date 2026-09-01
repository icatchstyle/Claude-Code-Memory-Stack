#!/usr/bin/env bash
# Ensure exactly ONE vault-mcp daemon is running.
#
# Idempotent: reuse a running container, start a stopped one, create it if absent. Every Claude
# session then connects to this single process over HTTP — no per-session container, no
# contention over a shared resource.
#
# Uses the plain `docker` CLI on purpose, not `docker compose`: this runs as a SessionStart hook
# in environments where compose may not exist.
set -euo pipefail

NAME="${VAULT_MCP_NAME:-vault-mcp}"
IMAGE="${VAULT_MCP_IMAGE:-vault-mcp:latest}"
PORT="${MCP_PORT:-8765}"
VAULT_PATH="${VAULT_PATH:?VAULT_PATH must be set}"
# A file you know exists. Probing for CONTENT catches a partially visible mount, which a
# non-empty listing does not.
SENTINEL="${VAULT_SENTINEL:-HOME.md}"

log() { echo "[ensure-up] $*" >&2; }

command -v docker >/dev/null 2>&1 || { log "ERROR: docker CLI not found"; exit 1; }

# True when the container actually sees the vault CONTENT, not just the mount point.
mount_ok() {
  if [ -n "$SENTINEL" ] && [ -e "$VAULT_PATH/$SENTINEL" ]; then
    docker exec "$NAME" sh -c "test -e '/vault/$SENTINEL'" >/dev/null 2>&1
    return $?
  fi
  local c h
  c="$(docker exec "$NAME" sh -c 'ls -A /vault 2>/dev/null | wc -l' 2>/dev/null || echo 0)"
  h="$(ls -A "$VAULT_PATH" 2>/dev/null | wc -l || echo 0)"
  [ "${c:-0}" -gt 0 ] || [ "${h:-0}" -eq 0 ]
}

state="$(docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null || echo absent)"
case "$state" in
  true)
    log "already running ($NAME)"
    # The stale-mount failure: running and healthy, seeing nothing. Only a restart fixes it.
    if ! mount_ok; then
      log "WARNING: container cannot see the vault content — restarting"
      docker restart "$NAME" >/dev/null
      sleep 4
      mount_ok || log "ERROR: /vault still empty after restart — check the host path"
    fi
    ;;
  false)
    log "starting existing container ($NAME)"
    docker start "$NAME" >/dev/null
    ;;
  *)
    log "creating container ($NAME) on 127.0.0.1:$PORT"
    docker run -d --name "$NAME" --restart unless-stopped \
      -p "127.0.0.1:$PORT:$PORT" \
      -v "$VAULT_PATH:/vault:rw" \
      -e VAULT_PATH=/vault -e MCP_PORT="$PORT" \
      "$IMAGE" >/dev/null
    ;;
esac
