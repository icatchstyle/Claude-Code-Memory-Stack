#!/usr/bin/env python3
"""Unattended harvest run: collect past sessions, hand them to an agent, file the result.

    python3 run.py                    # DRY RUN - collects and reports, writes nothing
    python3 run.py --write            # actually let the agent write to the knowledge base
    python3 run.py --write --since-days 7
    python3 run.py --status           # what the last runs did, without running anything

Runs on Linux, macOS and Windows with nothing but the standard library. That portability is
the point: the harvest is the one part of this stack that runs while nobody is watching, so it
must not depend on a shell that happens to be installed. `run.sh` remains as a thin wrapper.

DRY RUN IS THE DEFAULT ON PURPOSE. This script points an unsupervised agent at your notes with
write access. Nobody should get that by forgetting a flag.

THE SAFETY RAILS, in order of importance:

  1. State advances only on success. If the run fails, the next one covers the same window
     again. Advancing a cursor past work that was never done loses it permanently, silently.
  2. The write procedure must load before anything is written. An agent that cannot read the
     conventions writes notes that violate them - at scale, unattended, and you find out at
     the next lint, after dozens of them exist.
  3. The run must be able to authenticate. A scheduled job whose login has expired starts on
     time, dies in seconds and leaves a log that looks almost normal. Checked up front, and
     never retried, because a second attempt fails the same way and buries the cause.
  4. One run at a time. A second run harvesting the same window creates duplicates.
  5. Version-control your vault. Not as a backup: so you can read the diff of what an agent
     wrote while you slept. This script cannot enforce it; do it anyway.

Environment:
  MINER_VAULT_DIR        path to the vault; if it is a git repository, the run verifies that
                         reported writes actually landed instead of trusting the report
  MINER_PERMISSION_MODE  permission mode for the headless agent (default: acceptEdits)
  MINER_PROJECTS_DIR     where transcripts live (default: ~/.claude/projects)
  MINER_STATE_DIR        where state, staging and logs live (default: ~/.claude/knowledge-miner)
  MINER_CONFIG_DIR       a separate CLAUDE_CONFIG_DIR for the run, if you keep one for jobs
  MINER_SKILL            the skill to invoke (default: capture-knowledge)
  MINER_CLI              full path to the agent CLI, if it is not on PATH
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The cursor file predates state.json and stays the cursor: one ISO timestamp, nothing else.
# state.json is added beside it for what the cursor cannot express - why a run ended and how
# many failed before this one.
CURSOR_NAME = "last-run"
STATE_NAME = "state.json"
LOCK_NAME = "lock"
STALE_LOCK_SECONDS = 2 * 60 * 60

# Anchored at the start of a line. The unanchored form matches the agent quoting its own
# instructions back ("you asked me to end with MINER_RESULT ..."), which reads as a completed
# run in a log full of failures.
RESULT_RE = re.compile(r"^MINER_RESULT\b.*", re.MULTILINE)

# What an expired or missing login looks like in the CLI's output. Retrying any of these is
# waste: it fails within seconds, identically, and pushes the real cause out of view.
AUTH_FAILURE_RE = re.compile(
    r"Failed to authenticate|OAuth session expired|Invalid (?:bearer )?token"
    r"|401 Unauthorized|Please run .?/login|not logged in",
    re.IGNORECASE,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------- state

def read_cursor(state_dir: Path) -> str:
    try:
        return (state_dir / CURSOR_NAME).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def read_state(state_dir: Path) -> dict:
    try:
        data = json.loads((state_dir / STATE_NAME).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(state_dir: Path, status: str, *, advance_to: str = "", detail: str = "") -> None:
    """Record every attempt; move the cursor only when the run actually succeeded.

    The consecutive-failure count is the number that matters: a job that starts on time and
    fails every time is invisible in a scheduler, and a single failure looks like bad luck.
    """
    state = read_state(state_dir)
    previous = state.get("status")
    failures = int(state.get("consecutive_failures") or 0)
    ok = status.startswith("ok")

    state["status"] = status
    state["last_attempt"] = utc_now_iso()
    if detail:
        state["detail"] = detail
    elif "detail" in state:
        del state["detail"]

    if ok:
        state["consecutive_failures"] = 0
        state["last_success"] = state["last_attempt"]
    else:
        state["consecutive_failures"] = failures + 1 if previous and not previous.startswith("ok") else 1
        state.setdefault("failing_since", state["last_attempt"])
    if ok and "failing_since" in state:
        del state["failing_since"]

    _atomic_write(state_dir / STATE_NAME, json.dumps(state, indent=2) + "\n")
    if advance_to:
        _atomic_write(state_dir / CURSOR_NAME, advance_to)


def _atomic_write(path: Path, text: str) -> None:
    # A crash mid-write must not leave a truncated cursor: the next run would then harvest
    # from the beginning of time, or from nothing at all.
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def print_status(state_dir: Path) -> int:
    cursor = read_cursor(state_dir) or "never"
    state = read_state(state_dir)
    print(f"cursor (window starts here) : {cursor}")
    print(f"last attempt                : {state.get('last_attempt', 'never')}")
    print(f"last successful harvest     : {state.get('last_success', 'never')}")
    print(f"status                      : {state.get('status', 'unknown')}")
    if detail := state.get("detail"):
        print(f"detail                      : {detail}")
    failures = int(state.get("consecutive_failures") or 0)
    if failures:
        print(f"consecutive failures        : {failures} (since {state.get('failing_since', '?')})")
        print("\nA scheduler shows this job as healthy while this counter climbs. Read the newest")
        print(f"log in {state_dir / 'logs'} before the next scheduled run.")
    return 1 if failures else 0


# --------------------------------------------------------------------- lock

def take_lock(lock: Path) -> bool:
    """Atomic across platforms: mkdir either creates the directory or fails."""
    try:
        lock.mkdir()
        return True
    except FileExistsError:
        pass
    try:
        age = time.time() - lock.stat().st_mtime
    except OSError:
        return False
    if age < STALE_LOCK_SECONDS:
        return False
    os.utime(lock, None)  # refresh, or a run starting moments later takes over as well
    return True


# --------------------------------------------------------------------- the agent CLI

def find_cli() -> str | None:
    """Locate the agent CLI. On Windows the executable is a .cmd shim, which needs the
    PATHEXT lookup that shutil.which does and a bare name in subprocess does not.

    MINER_CLI overrides the lookup, for an install outside PATH and for tests that need the
    "no CLI" path deterministically — forcing that through PATH would find the real CLI on a
    developer machine and start an actual unattended run.
    """
    if override := os.environ.get("MINER_CLI"):
        return override if Path(override).exists() else None
    for name in ("claude", "claude.cmd", "claude.exe"):
        if found := shutil.which(name):
            return found
    return None


def run_cli(cli: str, prompt: str, *, extra: list[str] | None = None,
            env: dict | None = None, timeout: int = 3600) -> tuple[int, str]:
    cmd = [cli, "-p", prompt]
    if extra:
        cmd[1:1] = extra
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, env=env, check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def is_auth_failure(text: str) -> bool:
    return bool(AUTH_FAILURE_RE.search(text or ""))


def find_result_marker(text: str) -> str:
    matches = RESULT_RE.findall(text or "")
    return matches[-1].strip() if matches else ""


def parse_counts(marker: str) -> tuple[int, int]:
    def num(field: str) -> int:
        m = re.search(rf"{field}=(\d+)", marker)
        return int(m.group(1)) if m else 0
    return num("new"), num("updated")


# --------------------------------------------------------------------- vault verification

def vault_state(vault_dir: str) -> int:
    """0 = dirty, 1 = clean, 2 = not a git repository (so nothing can be verified)."""
    if not vault_dir:
        return 2
    try:
        probe = subprocess.run(["git", "-C", vault_dir, "rev-parse", "--git-dir"],
                               capture_output=True, text=True, check=False)
    except OSError:
        return 2
    if probe.returncode != 0:
        return 2
    status = subprocess.run(["git", "-C", vault_dir, "status", "--porcelain"],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", check=False)
    return 0 if (status.stdout or "").strip() else 1


# --------------------------------------------------------------------- window

def window_args(state_dir: Path, since_days: float | None) -> tuple[list[str], str]:
    if since_days is not None:
        return ["--since-days", str(since_days)], f"last {since_days} day(s), explicitly requested"
    if cursor := read_cursor(state_dir):
        return ["--since-iso", cursor], f"since {cursor} (last successful run)"
    return ["--since-days", "1"], "last 24h (no previous run recorded)"


def catch_up_note(cursor: str) -> str:
    """Say so when the window is much wider than a day. A silent multi-week window is how a
    long outage gets harvested as if it were routine."""
    if not cursor:
        return ""
    try:
        then = datetime.strptime(cursor, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    days = (datetime.now(timezone.utc) - then) / timedelta(days=1)
    if days < 2:
        return ""
    return (f"This is a catch-up run covering {days:.0f} days - earlier runs failed or were "
            f"skipped. Say so in what you file.")


# --------------------------------------------------------------------- prompts

PROBE_PROMPT = (
    "Read the knowledge base note describing the write procedure for knowledge-writing "
    "skills. Reply with exactly OK if it loaded and mentions the mandatory severity callout "
    "for gotchas, otherwise reply MISSING."
)


def harvest_prompt(skill: str, staging: Path, note: str) -> str:
    return f"""Run /{skill} over the session digests in {staging}.

Each file is one past session. Work through them and file what is durable and generalisable.
Pay particular attention to the 'Failed tool calls' sections: they are the richest source of
gotchas and nobody reports them, which is why they are collected mechanically.

Discard case detail. Save the transferable core, never the incident. Deduplicate against what
already exists before writing anything new. If a session yielded nothing durable, say so and
write nothing - that is a valid outcome, not a failure.
{note}
End your reply with a line that starts at the beginning of the line:
MINER_RESULT new=<n> updated=<n> skipped=<n>"""


# --------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Unattended harvest run (dry run unless --write is given).")
    ap.add_argument("--write", action="store_true",
                    help="let the agent write to the knowledge base")
    ap.add_argument("--since-days", type=float,
                    help="override the window instead of continuing from the cursor")
    ap.add_argument("--skill", default=os.environ.get("MINER_SKILL", "capture-knowledge"))
    ap.add_argument("--status", action="store_true",
                    help="report what the last runs did and exit")
    ap.add_argument("--timeout", type=int, default=3600,
                    help="seconds allowed for the harvest call (default: 3600)")
    args = ap.parse_args(argv)

    state_dir = Path(os.environ.get("MINER_STATE_DIR") or
                     Path.home() / ".claude" / "knowledge-miner")
    if args.status:
        return print_status(state_dir)

    staging = state_dir / "staging"
    log_dir = state_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    log_file = log_path.open("a", encoding="utf-8")

    def log(message: str) -> None:
        line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}"
        print(line, flush=True)
        log_file.write(line + "\n")
        log_file.flush()

    def fail(reason: str, status: str = "failed") -> int:
        log(f"FAILED: {reason}")
        log("State not advanced - the next run covers this window again.")
        write_state(state_dir, status, detail=reason)
        return 1

    lock = state_dir / LOCK_NAME
    if not take_lock(lock):
        log("Another run is in progress (lock younger than 2h). Exiting.")
        return 0

    try:
        cursor = read_cursor(state_dir)
        collector_args, described = window_args(state_dir, args.since_days)
        log(f"Window: {described}")

        # Captured BEFORE the work, so sessions written during the run are picked up next
        # time rather than skipped.
        new_cursor = utc_now_iso()

        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)

        collect_cmd = [sys.executable, str(HERE / "collect_sessions.py"),
                       "--out", str(staging), *collector_args]
        if session_id := os.environ.get("CLAUDE_SESSION_ID"):
            collect_cmd += ["--self-session", session_id]
        if projects := os.environ.get("MINER_PROJECTS_DIR"):
            collect_cmd += ["--projects-dir", projects]

        log("Collecting...")
        collected = subprocess.run(collect_cmd, capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", check=False)
        for line in (collected.stdout or "").splitlines():
            log(f"  {line}")
        if collected.returncode != 0:
            return fail(f"collector exited {collected.returncode}: "
                        f"{(collected.stderr or '').strip()[:300]}", "collector_failed")

        digests = sorted(staging.glob("*.md")) if staging.exists() else []
        if not digests:
            log("Nothing to harvest. Advancing state.")
            write_state(state_dir, "ok_empty", advance_to=new_cursor)
            return 0
        log(f"{len(digests)} digest(s) in {staging}")

        if not args.write:
            log("DRY RUN - no agent invoked, nothing written, state not advanced.")
            log(f"Inspect the digests in {staging}, then re-run with --write.")
            return 0

        cli = find_cli()
        if not cli:
            return fail("the 'claude' CLI is not on PATH")

        env = os.environ.copy()
        if config_dir := os.environ.get("MINER_CONFIG_DIR"):
            env["CLAUDE_CONFIG_DIR"] = config_dir

        # --- 3. the run must be able to authenticate ---------------------------------
        # The probe below would also surface this, but not legibly: an auth failure and a
        # missing write procedure both come back as "not OK", and the run would be reported
        # as a convention problem for as long as nobody reads the raw output.
        log("Checking the login...")
        code, output = run_cli(cli, "Reply with exactly READY.", env=env, timeout=120)
        if is_auth_failure(output):
            return fail("the CLI cannot authenticate - log in once interactively, then "
                        "re-run. Not retried: it fails the same way in seconds.", "auth_failed")
        if code != 0 or "READY" not in output:
            return fail(f"the CLI did not answer a trivial prompt (exit {code}): "
                        f"{output.strip()[:200]}")
        log("Login accepted.")

        # --- 2. the conventions must load --------------------------------------------
        log("Verifying the write procedure is reachable...")
        code, probe = run_cli(cli, PROBE_PROMPT, env=env, timeout=300)
        if is_auth_failure(probe):
            return fail("login expired between the check and the probe", "auth_failed")
        if "OK" not in probe:
            return fail(f"write procedure did not load (got: {probe.strip()[:200]}). "
                        "Refusing to write.")
        log("Write procedure loaded.")

        permission_mode = os.environ.get("MINER_PERMISSION_MODE", "acceptEdits")
        vault_dir = os.environ.get("MINER_VAULT_DIR", "")
        before = vault_state(vault_dir)

        log(f"Harvesting with /{args.skill} (permission mode: {permission_mode})...")
        code, reply = run_cli(
            cli, harvest_prompt(args.skill, staging, catch_up_note(cursor)),
            extra=["--permission-mode", permission_mode], env=env, timeout=args.timeout,
        )
        log_file.write(reply + "\n")
        log_file.flush()

        if is_auth_failure(reply):
            return fail("login expired during the harvest", "auth_failed")
        if code == 124:
            return fail(f"the harvest call timed out after {args.timeout}s")

        marker = find_result_marker(reply)
        if not marker:
            return fail("no MINER_RESULT marker at the start of a line - treating the run "
                        "as incomplete")
        log(f"Reported: {marker}")

        # The marker alone is not proof. An agent whose writes were refused still reports a
        # result - with zeroes, or worse, with counts for writes that never landed.
        new_count, updated_count = parse_counts(marker)
        if new_count + updated_count > 0:
            after = vault_state(vault_dir)
            if before == 2 or after == 2:
                log("NOTE: the vault is not a git repository, so the report could not be verified.")
            elif after == 0:
                log("Verified: the vault changed on disk.")
            else:
                return fail(f"reported {new_count + updated_count} write(s) but the vault is "
                            "unchanged - writes were refused")

        write_state(state_dir, "ok", advance_to=new_cursor, detail=marker)
        log(f"Done. State advanced to {new_cursor}.")
        return 0
    finally:
        log_file.close()
        try:
            lock.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
