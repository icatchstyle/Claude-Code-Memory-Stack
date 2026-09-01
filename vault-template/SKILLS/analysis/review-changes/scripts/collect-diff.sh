#!/usr/bin/env bash
# Collect the current diff in a shape the review skill can work with.
# Deterministic mechanism belongs in a script, not in skill prose.
#
#   collect-diff.sh [--staged] [--max-lines N]
set -euo pipefail

STAGED=""
MAX_LINES=2000

while [ $# -gt 0 ]; do
  case "$1" in
    --staged)    STAGED="--staged"; shift ;;
    --max-lines) MAX_LINES="${2:-2000}"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "error: not a git repository" >&2; exit 1; }

echo "=== files ==="
git diff $STAGED --stat

lines="$(git diff $STAGED | wc -l)"
echo
echo "=== diff (${lines} lines) ==="
if [ "$lines" -gt "$MAX_LINES" ]; then
  echo "TRUNCATED: ${lines} lines exceeds --max-lines ${MAX_LINES}."
  echo "Review per file instead: git diff $STAGED -- <path>"
  git diff $STAGED --stat
  exit 0
fi
git diff $STAGED
