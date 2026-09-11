#!/usr/bin/env bash
# Wrapper around run.py, kept so existing crontabs, launchd jobs and Makefile targets that
# point at run.sh keep working.
#
#   ./run.sh                 # DRY RUN — collects and reports, writes nothing. The default.
#   ./run.sh --write         # actually let the agent write to the knowledge base
#   ./run.sh --status        # what the last runs did, without running anything
#
# The runner itself is Python and standard library only, so the harvest also runs where no
# POSIX shell does — Windows without WSL, in particular. Read run.py for the safety rails and
# the environment variables; every argument here is passed straight through.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    exec "$candidate" "$HERE/run.py" "$@"
  fi
done

echo "No python3 on PATH. The harvest runner needs Python 3.10 or newer." >&2
exit 1
