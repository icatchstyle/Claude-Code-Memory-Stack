"""Tests for the harvest runner.

The weight is on the four decisions that separate a run which did the work from one that only
looks like it did: is this reply a completed harvest, is this output an authentication failure,
what does the window cover, and what does the state say happened. Each of them has produced a
silent multi-day outage somewhere, which is why they are pure functions with tests rather than
inline conditions in a shell script.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from run import (  # noqa: E402
    catch_up_note,
    find_result_marker,
    is_auth_failure,
    parse_counts,
    print_status,
    read_cursor,
    take_lock,
    window_args,
    write_state,
)


# ------------------------------------------------------- the marker must be anchored

def test_marker_is_recognised_at_the_start_of_a_line():
    reply = "Filed three gotchas.\nMINER_RESULT new=3 updated=1 skipped=0"
    assert find_result_marker(reply) == "MINER_RESULT new=3 updated=1 skipped=0"


def test_quoted_instructions_do_not_count_as_a_result():
    # An agent that dies early often echoes its brief first. Unanchored matching reads that
    # back as a finished run, which is how a fortnight of failed runs passed for successful.
    reply = "You asked me to end with MINER_RESULT new=<n> updated=<n>, but I cannot reach the vault."
    assert find_result_marker(reply) == ""


def test_the_last_marker_wins():
    reply = "MINER_RESULT new=1 updated=0 skipped=0\nretrying\nMINER_RESULT new=4 updated=2 skipped=1"
    assert parse_counts(find_result_marker(reply)) == (4, 2)


def test_counts_default_to_zero_when_the_marker_is_malformed():
    assert parse_counts("MINER_RESULT done") == (0, 0)


# ------------------------------------------------------- authentication failures

@pytest.mark.parametrize("output", [
    "Failed to authenticate: OAuth session expired and could not be refreshed",
    "Invalid bearer token",
    "401 Unauthorized",
    "You are not logged in",
])
def test_authentication_failures_are_recognised(output):
    assert is_auth_failure(output)


@pytest.mark.parametrize("output", [
    "READY",
    "MINER_RESULT new=2 updated=0 skipped=3",
    "The vault note mentions the mandatory callout. OK",
    "",
])
def test_ordinary_output_is_not_mistaken_for_an_auth_failure(output):
    assert not is_auth_failure(output)


# ------------------------------------------------------- the window

def test_an_explicit_window_overrides_the_cursor(tmp_path):
    (tmp_path / "last-run").write_text("2024-01-01T00:00:00Z", encoding="utf-8")
    args, described = window_args(tmp_path, 7)
    assert args == ["--since-days", "7"]
    assert "explicitly requested" in described


def test_the_cursor_is_used_when_there_is_one(tmp_path):
    (tmp_path / "last-run").write_text("2024-05-06T07:08:09Z", encoding="utf-8")
    args, _ = window_args(tmp_path, None)
    assert args == ["--since-iso", "2024-05-06T07:08:09Z"]


def test_a_first_run_falls_back_to_24h(tmp_path):
    args, described = window_args(tmp_path, None)
    assert args == ["--since-days", "1"]
    assert "no previous run" in described


def test_a_wide_window_announces_itself_as_a_catch_up():
    assert "catch-up" in catch_up_note("2024-01-01T00:00:00Z")


def test_a_normal_window_says_nothing():
    # Every run would otherwise claim to be a catch-up, and the note would stop meaning anything.
    from datetime import datetime, timezone
    assert catch_up_note(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")) == ""


def test_an_unparseable_cursor_does_not_crash_the_run():
    assert catch_up_note("last tuesday") == ""


# ------------------------------------------------------- state

def test_the_cursor_advances_only_when_asked(tmp_path):
    write_state(tmp_path, "failed", detail="collector")
    assert read_cursor(tmp_path) == ""
    write_state(tmp_path, "ok", advance_to="2024-07-07T07:07:07Z")
    assert read_cursor(tmp_path) == "2024-07-07T07:07:07Z"


def test_consecutive_failures_are_counted(tmp_path):
    for _ in range(3):
        write_state(tmp_path, "auth_failed", detail="login expired")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["consecutive_failures"] == 3
    assert state["failing_since"]


def test_a_success_clears_the_failure_streak(tmp_path):
    write_state(tmp_path, "auth_failed")
    write_state(tmp_path, "ok", advance_to="2024-07-07T07:07:07Z")
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["consecutive_failures"] == 0
    assert "failing_since" not in state
    assert state["last_success"]


def test_status_exits_non_zero_while_runs_are_failing(tmp_path, capsys):
    write_state(tmp_path, "auth_failed", detail="login expired")
    assert print_status(tmp_path) == 1
    assert "consecutive failures" in capsys.readouterr().out


def test_status_exits_zero_after_a_success(tmp_path, capsys):
    write_state(tmp_path, "ok", advance_to="2024-07-07T07:07:07Z")
    assert print_status(tmp_path) == 0
    capsys.readouterr()


def test_a_truncated_state_file_is_survivable(tmp_path):
    (tmp_path / "state.json").write_text("{not json", encoding="utf-8")
    write_state(tmp_path, "ok", advance_to="2024-07-07T07:07:07Z")
    assert json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))["status"] == "ok"


# ------------------------------------------------------- the lock

def test_the_second_run_does_not_get_the_lock(tmp_path):
    lock = tmp_path / "lock"
    assert take_lock(lock) is True
    assert take_lock(lock) is False


def test_a_stale_lock_is_taken_over(tmp_path):
    import os
    import time
    lock = tmp_path / "lock"
    lock.mkdir()
    old = time.time() - (3 * 60 * 60)
    os.utime(lock, (old, old))
    # A crashed run must not block every following day forever.
    assert take_lock(lock) is True
