#!/usr/bin/env bash
# Stop / Notification hook: play a sound when a turn finishes or input is needed.
#
# Usage: notify.sh <event>       # event: done | input-needed
#
# Two techniques worth reusing:
#   1. A mute switch OUTSIDE the code — a flag file, so silencing is a one-line edit.
#   2. Debouncing with an atomic lock — the same event can fire twice in quick succession;
#      mkdir is atomic, so exactly one of two racing calls wins and the other bails.
set -uo pipefail

EVENT="${1:-done}"
FLAG="${CLAUDE_SOUND_FLAG:-$HOME/.claude/sound.conf}"   # e.g. "sound_enabled: false"

is_off() { [ -f "$FLAG" ] && grep -qiE "^$1:[[:space:]]*(false|0|no|off)\b" "$FLAG"; }

# A missing flag file means "play", so notifications work out of the box.
is_off "sound_enabled" && exit 0
is_off "$EVENT"        && exit 0

LOCK="/tmp/claude-notify-${EVENT}.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  # A fresh lock means this is a duplicate fire; a stale one means we may proceed.
  [ -n "$(find "$LOCK" -newermt '-3 seconds' 2>/dev/null)" ] && exit 0
  touch "$LOCK"
fi

play() {
  if   command -v paplay      >/dev/null 2>&1; then paplay "$1"
  elif command -v afplay      >/dev/null 2>&1; then afplay "$1"
  elif command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "(New-Object Media.SoundPlayer '$2').PlaySync()"
  fi
}

case "$EVENT" in
  input-needed) LINUX_SND=/usr/share/sounds/freedesktop/stereo/dialog-warning.oga
                WIN_SND='C:\Windows\Media\Ring01.wav' ;;
  *)            LINUX_SND=/usr/share/sounds/freedesktop/stereo/complete.oga
                WIN_SND='C:\Windows\Media\Windows Notify.wav' ;;
esac

# Fire and forget so the hook never blocks the turn.
nohup bash -c "$(declare -f play); play '$LINUX_SND' '$WIN_SND'" >/dev/null 2>&1 &
exit 0
