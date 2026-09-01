"""Tests for the session collector.

The weight is on `parse_line` and `cut_index`. `parse_line` is the only function that knows
Claude Code's transcript format — an internal detail that can change without notice. These
fixtures are what turn such a change into a loud failure instead of silently empty digests.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from collect_sessions import (  # noqa: E402
    collect,
    cut_index,
    parse_line,
    read_transcript,
    render,
)

FIXTURES = Path(__file__).parent / "fixtures"
EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)


@pytest.fixture()
def sample():
    return read_transcript(FIXTURES / "session-sample.jsonl")


# --------------------------------------------------------------- the fragile part

def test_user_prompt_is_extracted_from_a_plain_string(sample):
    events = parse_line(sample[0])
    assert [e.kind for e in events] == ["prompt"]
    assert "Deploy is failing" in events[0].text


def test_thinking_blocks_never_reach_the_digest(sample):
    # Internal reasoning is not knowledge and must not be filed as if it were.
    assert all("internal reasoning" not in e.text for e in parse_line(sample[1]))


def test_failed_tool_calls_are_captured(sample):
    events = parse_line(sample[2])
    assert [e.kind for e in events] == ["tool_error"]
    assert "Unauthorized" in events[0].text


def test_successful_tool_calls_are_not_captured():
    line = {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}
    assert parse_line(line) == []


def test_subagent_replies_are_marked_as_such(sample):
    events = parse_line(sample[4])
    assert [e.kind for e in events] == ["subagent"]
    assert "deploy/overlays/prod" in events[0].text


def test_non_message_lines_are_ignored():
    assert parse_line({"type": "ai-title", "aiTitle": "x"}) == []
    assert parse_line({"type": "system", "message": {"content": "boot"}}) == []


def test_malformed_content_does_not_raise():
    assert parse_line({"type": "assistant", "message": {"content": 42}}) == []
    assert parse_line({"type": "assistant", "message": {}}) == []
    assert parse_line({"type": "assistant"}) == []


# --------------------------------------------------------------- the cut marker

def test_cut_marker_skips_the_already_harvested_part():
    lines = read_transcript(FIXTURES / "session-cut.jsonl")
    index, reason = cut_index(lines)
    assert reason == "KNOWLEDGE_CAPTURED"
    assert index == 2

    session = collect(FIXTURES / "session-cut.jsonl", EPOCH)
    text = "\n".join(e.text for e in session.events)
    assert "new work after the cut" in text
    assert "old work" not in text        # re-harvesting is how duplicates get created


def test_latest_marker_wins():
    lines = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "KNOWLEDGE_CAPTURED"}]}},
        {"type": "user", "message": {"content": "middle"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "MINING_STOP"}]}},
        {"type": "user", "message": {"content": "tail"}},
    ]
    index, reason = cut_index(lines)
    assert reason == "MINING_STOP"
    assert index == 3


def test_session_without_marker_is_collected_whole():
    lines = [{"type": "user", "message": {"content": "hello"}}]
    assert cut_index(lines) == (0, "")


# --------------------------------------------------------------- collection and output

def test_collect_reports_context(sample_path=FIXTURES / "session-sample.jsonl"):
    session = collect(sample_path, EPOCH)
    assert session.cwd == "/work/app"
    assert session.branch == "main"
    assert {e.kind for e in session.events} == {"prompt", "tool_error", "reply", "subagent"}


def test_tool_name_is_attached_to_the_error(sample_path=FIXTURES / "session-sample.jsonl"):
    session = collect(sample_path, EPOCH)
    error = next(e for e in session.events if e.kind == "tool_error")
    assert error.tool == "Bash"


def test_since_filter_excludes_older_events(sample_path=FIXTURES / "session-sample.jsonl"):
    later = datetime(2026, 9, 1, 8, 0, 30, tzinfo=timezone.utc)
    assert collect(sample_path, later) is None


def test_render_puts_tool_errors_first(sample_path=FIXTURES / "session-sample.jsonl"):
    text = render(collect(sample_path, EPOCH))
    assert text.index("Failed tool calls") < text.index("What the user asked")
    assert "**Bash**" in text


def test_a_truncated_final_line_is_survivable(tmp_path):
    path = tmp_path / "partial.jsonl"
    path.write_text(
        json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n{\"type\": \"assi",
        encoding="utf-8",
    )
    assert len(read_transcript(path)) == 1
