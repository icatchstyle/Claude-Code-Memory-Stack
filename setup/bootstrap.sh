#!/usr/bin/env bash
# bootstrap.sh — lay down the memory stack: vault skeleton, hooks, CLAUDE.md, settings.
#
# Safe by design: never overwrites an existing file. Anything already present is reported
# as "skip" so you can merge it by hand. Run with --dry-run first.
#
#   ./setup/bootstrap.sh --vault ~/vault [--claude-dir ~/.claude] [--dry-run] [--force]
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VAULT=""
CLAUDE_DIR="$HOME/.claude"
DRY=0
FORCE=0

usage() { sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --vault)      VAULT="${2:-}"; shift 2 ;;
    --claude-dir) CLAUDE_DIR="${2:-}"; shift 2 ;;
    --dry-run)    DRY=1; shift ;;
    --force)      FORCE=1; shift ;;
    -h|--help)    usage 0 ;;
    *) echo "unknown option: $1" >&2; usage 1 ;;
  esac
done

[ -n "$VAULT" ] || { echo "error: --vault is required" >&2; usage 1; }

# Expand a leading ~ so --vault ~/vault works when quoted.
VAULT="${VAULT/#\~/$HOME}"
CLAUDE_DIR="${CLAUDE_DIR/#\~/$HOME}"

say()  { printf '%s\n' "$*"; }
act()  { [ "$DRY" -eq 1 ] && { say "  [dry-run] $*"; return 1; }; return 0; }

copy() {  # copy <src> <dst>
  local src="$1" dst="$2"
  if [ -e "$dst" ] && [ "$FORCE" -eq 0 ]; then
    say "  skip   $dst (exists — merge by hand)"; return 0
  fi
  act "copy   $src -> $dst" || return 0
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  say "  write  $dst"
}

say "==> Memory stack bootstrap"
say "    repo:        $REPO_DIR"
say "    vault:       $VAULT"
say "    claude dir:  $CLAUDE_DIR"
[ "$DRY" -eq 1 ] && say "    MODE:        dry run, nothing will be written"
say ""

# ---------------------------------------------------------------- vault skeleton
say "==> Vault skeleton"
if [ -d "$VAULT" ] && [ -n "$(ls -A "$VAULT" 2>/dev/null)" ] && [ "$FORCE" -eq 0 ]; then
  say "  note   $VAULT is not empty — copying only files that do not exist yet"
fi
if act "populate $VAULT from $REPO_DIR/vault-template"; then
  mkdir -p "$VAULT"
  # -n = never overwrite. cp -rn is not portable, so walk the tree explicitly.
  (cd "$REPO_DIR/vault-template" && find . -type d -exec mkdir -p "$VAULT/{}" \;)
  (cd "$REPO_DIR/vault-template" && find . -type f -print0 | while IFS= read -r -d '' f; do
      if [ -e "$VAULT/$f" ] && [ "$FORCE" -eq 0 ]; then
        printf '  skip   %s\n' "${f#./}"
      else
        cp "$f" "$VAULT/$f"; printf '  write  %s\n' "${f#./}"
      fi
    done)
fi
say ""

# ---------------------------------------------------------------- hooks
say "==> Hooks -> $CLAUDE_DIR/hooks"
for h in "$REPO_DIR"/setup/hooks/*.sh; do
  copy "$h" "$CLAUDE_DIR/hooks/$(basename "$h")"
done
if act "chmod +x $CLAUDE_DIR/hooks/*.sh"; then
  chmod +x "$CLAUDE_DIR"/hooks/*.sh 2>/dev/null || true
fi
say ""

# ---------------------------------------------------------------- CLAUDE.md + settings
say "==> Runtime files"
copy "$REPO_DIR/setup/CLAUDE.md.template"     "$CLAUDE_DIR/CLAUDE.md"
copy "$REPO_DIR/setup/settings.json.template" "$CLAUDE_DIR/settings.json.new"
say "  note   settings written as settings.json.new — merge it into your existing settings.json"
say ""

# ---------------------------------------------------------------- placeholders
say "==> Placeholders still to fill in"
if [ "$DRY" -eq 0 ]; then
  grep -rl '<VAULT_PATH>\|<ACCESS_METHOD>\|<DEFAULT_BRANCH>\|<KEYWORD>\|<MCP_REPO>' \
    "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/settings.json.new" 2>/dev/null \
    | sed 's/^/  edit   /' || say "  none"
fi
say ""

# ---------------------------------------------------------------- dependency check
say "==> Dependencies"
for tool in jq git; do
  if command -v "$tool" >/dev/null 2>&1; then say "  ok     $tool"
  else say "  MISSING $tool — hooks need it"; fi
done
say ""

cat <<EOF
==> Next steps

  1. \$EDITOR $CLAUDE_DIR/CLAUDE.md
     Replace every <PLACEHOLDER>. Delete every section you do not need.

  2. Merge $CLAUDE_DIR/settings.json.new into $CLAUDE_DIR/settings.json
     At minimum: permissions.additionalDirectories and the UserPromptSubmit hook.

  3. \$EDITOR $VAULT/HOME.md
     Ten lines: what lives where.

  4. Write ONE project _INDEX.md from $VAULT/TEMPLATES/project.md
     Pick the system you touch most. It earns its cost within a week.

  5. Optional: the reference MCP server
     cd $REPO_DIR/mcp/vault-mcp && pip install -e . && VAULT_PATH=$VAULT python -m vault_mcp

  Do NOT try to backfill everything you know. Write knowledge when it is fresh,
  provoked by real work. See docs/09-adoption.md.
EOF
