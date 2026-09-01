#!/usr/bin/env python3
"""Turn past Claude Code sessions into compact digests for an unattended harvest run.

WHY THIS EXISTS
    The write-back loop is the part of the stack that fails quietly. Everything else is
    structural — a hook fires or it does not — but "write down what you learned" depends on a
    human remembering, at the end of a long day, to do one more thing. It is the only line in
    the adoption table that decays without a symptom.

    This closes that gap: a scheduled run reads yesterday's sessions, extracts what a person
    would have written down, and hands it to an agent that files it.

WHAT IT DELIBERATELY EXTRACTS
    Three sources a human never reports, because they happen in passing:

      1. Failed tool calls — wrong parameter name, missing permission, timeout, "not found".
         Worked around in the moment and never discussed. The richest source of gotchas there
         is, and mechanically collectable, which is exactly why a machine should do it.
      2. Subagent output — the main transcript keeps only the conclusion; the route to it
         (where things live, which query answered what) is in the agent's reply.
      3. Prompts and reports — the narrative that gives the other two their context.
    Tooling friction — where a tool was missing or awkward — is deliberately NOT extracted
    here: recognising it needs judgement, not pattern matching. The harvesting skill looks for
    it in the digest instead.

THE FRAGILE PART
    `parse_line` below reads Claude Code's transcript format, which is an internal detail and
    can change without notice. It is deliberately the ONLY place that knows the format, and it
    is covered by fixture tests. If the format changes, that test fails loudly instead of the
    collector quietly producing empty digests — and this one function is what you adapt.

USAGE
    collect_sessions.py --out ./staging --since-days 1
    collect_sessions.py --out ./staging --since-iso 2026-09-01T07:00:00 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Budget per session, so one enormous session cannot crowd out the rest.
MAX_ASSISTANT_CHARS = 1_200
MAX_USER_CHARS = 800
MAX_TOOL_ERROR_CHARS = 400
MAX_SIDECHAIN_CHARS = 1_500
MAX_EVENTS_PER_SESSION = 120

# Markers a session can carry to say "everything before this point is already handled".
# The later of the two wins; see `cut_index`.
CUT_MARKERS = (
    "KNOWLEDGE_CAPTURED",   # a harvest skill ran and wrote the earlier part to the vault
    "MINING_STOP",          # the user declared the earlier part not worth harvesting
)


@dataclass
class Event:
    kind: str          # prompt | reply | tool_error | subagent
    text: str
    timestamp: str = ""
    tool: str = ""


@dataclass
class Session:
    session_id: str
    path: Path
    cwd: str = ""
    branch: str = ""
    title: str = ""
    events: list[Event] = field(default_factory=list)
    cut_reason: str = ""

    @property
    def has_content(self) -> bool:
        return any(e.kind in ("prompt", "reply") for e in self.events)


# --------------------------------------------------------------------------- the fragile part

def parse_line(obj: dict) -> list[Event]:
    """Extract the interesting events from ONE transcript line.

    This is the only function that knows Claude Code's transcript format:

        {"type": "user"|"assistant"|..., "timestamp": ..., "isSidechain": bool,
         "message": {"content": str | [ {"type": "text"|"thinking"|"tool_use"|"tool_result",
                                          ...} ]}}

    Everything else in this file works on `Event` objects and is unaffected by format changes.
    Covered by tests/fixtures/session-sample.jsonl — if that test fails, the format moved.
    """
    kind = obj.get("type")
    if kind not in ("user", "assistant"):
        return []

    ts = obj.get("timestamp", "")
    sidechain = bool(obj.get("isSidechain"))
    message = obj.get("message") or {}
    content = message.get("content")

    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return []

    events: list[Event] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")

        if btype == "text":
            text = (block.get("text") or "").strip()
            if not text:
                continue
            if sidechain:
                events.append(Event("subagent", text[:MAX_SIDECHAIN_CHARS], ts))
            elif kind == "user":
                events.append(Event("prompt", text[:MAX_USER_CHARS], ts))
            else:
                events.append(Event("reply", text[:MAX_ASSISTANT_CHARS], ts))

        elif btype == "tool_result" and block.get("is_error"):
            # The single most valuable signal here: it is never discussed and never remembered.
            raw = block.get("content")
            if isinstance(raw, list):
                raw = " ".join(
                    b.get("text", "") for b in raw if isinstance(b, dict)
                )
            text = str(raw or "").strip()
            if text:
                events.append(Event("tool_error", text[:MAX_TOOL_ERROR_CHARS], ts))

    return events


def tool_name_for_errors(lines: list[dict]) -> dict[str, str]:
    """Map tool_use ids to tool names, so an error can say which tool failed."""
    names: dict[str, str] = {}
    for obj in lines:
        for block in ((obj.get("message") or {}).get("content") or []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                names[block.get("id", "")] = block.get("name", "")
    return names


# --------------------------------------------------------------------------- collection

def cut_index(lines: list[dict]) -> tuple[int, str]:
    """Where does the harvestable part of this session start?

    A session may already have been harvested (a skill wrote its earlier part to the vault) or
    explicitly declared not worth harvesting. Both leave a marker in an assistant message. The
    LATEST marker wins — re-harvesting what is already filed produces duplicates, which is the
    one failure mode a knowledge base does not recover from on its own.
    """
    index, reason = 0, ""
    for i, obj in enumerate(lines):
        if obj.get("type") != "assistant":
            continue
        content = (obj.get("message") or {}).get("content")
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
        for block in blocks:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            text = block.get("text") or ""
            for marker in CUT_MARKERS:
                if marker in text:
                    index, reason = i + 1, marker
    return index, reason


def read_transcript(path: Path) -> list[dict]:
    lines: list[dict] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    lines.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue        # a partially written line at the tail is normal
    except OSError:
        return []
    return lines


def collect(path: Path, since: datetime) -> Session | None:
    lines = read_transcript(path)
    if not lines:
        return None

    start, reason = cut_index(lines)
    tail = lines[start:]
    names = tool_name_for_errors(tail)

    session = Session(session_id=path.stem, path=path, cut_reason=reason)
    for obj in tail:
        session.cwd = session.cwd or obj.get("cwd", "")
        session.branch = session.branch or obj.get("gitBranch", "")
        if obj.get("type") == "ai-title":
            session.title = obj.get("aiTitle", "") or session.title

        ts = obj.get("timestamp", "")
        if ts and not _after(ts, since):
            continue

        for event in parse_line(obj):
            if event.kind == "tool_error":
                for block in ((obj.get("message") or {}).get("content") or []):
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        event.tool = names.get(block.get("tool_use_id", ""), "")
            session.events.append(event)
            if len(session.events) >= MAX_EVENTS_PER_SESSION:
                return session if session.has_content else None

    return session if session.has_content else None


def _after(timestamp: str, since: datetime) -> bool:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return True                 # unparseable: keep it rather than lose it
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed >= since


# --------------------------------------------------------------------------- output

def render(session: Session) -> str:
    """Render one session as Markdown for the harvesting agent to read."""
    out = [f"# Session {session.session_id}"]
    if session.title:
        out.append(f"**Title:** {session.title}")
    if session.cwd:
        out.append(f"**Directory:** {session.cwd}")
    if session.branch:
        out.append(f"**Branch:** {session.branch}")
    if session.cut_reason:
        out.append(f"**Note:** everything before `{session.cut_reason}` was already handled.")

    groups = {
        "tool_error": "## Failed tool calls — check these first",
        "subagent": "## Subagent findings",
        "prompt": "## What the user asked",
        "reply": "## What the assistant reported",
    }
    for kind, heading in groups.items():
        items = [e for e in session.events if e.kind == kind]
        if not items:
            continue
        out.append("")
        out.append(heading)
        if kind == "tool_error":
            out.append("")
            out.append(
                "_Worked around in the moment and never discussed. The richest source of "
                "gotchas in the whole digest._"
            )
        for event in items:
            label = f"**{event.tool}** — " if event.tool else ""
            out.append("")
            out.append(f"- {label}{event.text}")

    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True, help="directory to write digests into")
    ap.add_argument("--since-days", type=float, help="only events newer than N days")
    ap.add_argument("--since-iso", help="only events at or after this ISO timestamp")
    ap.add_argument("--projects-dir", default=str(Path.home() / ".claude" / "projects"))
    ap.add_argument("--self-session", default=os.environ.get("CLAUDE_SESSION_ID", ""),
                    help="session id to skip — never harvest the run doing the harvesting")
    ap.add_argument("--dry-run", action="store_true", help="report what would be written")
    args = ap.parse_args()

    if args.since_iso:
        since = datetime.fromisoformat(args.since_iso.replace("Z", "+00:00"))
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
    elif args.since_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=args.since_days)
    else:
        since = datetime.now(timezone.utc) - timedelta(days=1)

    projects = Path(args.projects_dir).expanduser()
    if not projects.is_dir():
        print(f"No transcripts at {projects}", file=sys.stderr)
        return 1

    out_dir = Path(args.out).expanduser()
    written, skipped = 0, 0

    for transcript in sorted(projects.glob("*/*.jsonl")):
        if args.self_session and transcript.stem == args.self_session:
            continue
        session = collect(transcript, since)
        if session is None:
            skipped += 1
            continue
        text = render(session)
        if args.dry_run:
            print(f"[dry-run] would write {session.session_id}.md "
                  f"({len(session.events)} events, {len(text)} chars)")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{session.session_id}.md").write_text(text, encoding="utf-8")
        written += 1

    verb = "would write" if args.dry_run else "wrote"
    print(f"{verb} {written} digest(s), skipped {skipped} session(s) with nothing to harvest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
