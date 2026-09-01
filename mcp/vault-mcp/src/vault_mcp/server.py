"""MCP server exposing the vault.

Design notes worth carrying into your own servers:

  * ONE JOB PER TOOL, enforced at the boundary. `read_note` refuses a non-note file. Two tools
    that both "read something" invite the agent to reach for whichever one skips the validation.
  * GUARDRAILS IN CODE, not in prose. Path traversal is refused here, where the model cannot
    argue with it.
  * BOUNDED OUTPUT. Every list tool caps its result. One unbounded response fills the context
    and every turn after it is worse.
  * ERRORS THAT SAY WHAT TO DO NEXT. "Note not found: X. Did you mean Y?" beats a stack trace.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from .vault import Vault, NOTE_SUFFIXES

VAULT_PATH = os.environ.get("VAULT_PATH", "")
if not VAULT_PATH:
    raise SystemExit("VAULT_PATH is not set — point it at your vault directory.")

vault = Vault(VAULT_PATH)
mcp = MCPServer("vault")

MAX_NOTE_CHARS = 40_000


@mcp.tool()
def status() -> dict:
    """Server and vault status. Call this first when anything looks wrong.

    A note count of 0 with a non-empty vault directory is the classic stale-mount symptom —
    the container's bind mount points at nothing while the host path is full.
    """
    count = vault.reindex()
    return {
        "vault_path": str(vault.root),
        "notes": count,
        "healthy": count > 0,
        "hint": None if count else (
            "0 notes. If the vault directory is not actually empty, the mount is stale — "
            "restart the container (an idempotent ensure-up script will not do it)."
        ),
    }


@mcp.tool()
def search(query: str, limit: int = 10, folder: str = "") -> dict:
    """Full-text search across the vault, ranked, capped.

    Args:
        query: one or two precise terms — not a sentence.
        limit: maximum hits (capped at 25).
        folder: restrict to a subtree, e.g. "PROJECTS/acme".
    """
    hits = vault.search(query, limit=min(limit, 25), folder=folder or None)
    return {"query": query, "count": len(hits), "results": hits}


@mcp.tool()
def gotcha_check(context: str, limit: int = 8) -> dict:
    """Return known traps relevant to a context, before you make the mistake.

    Pass what you are about to work on: project, technologies, paths. Only notes carrying a
    severity callout are returned — that marker is what makes them retrievable.

    Args:
        context: e.g. "acme-portal, docker, terraform, deploy to QA".
        limit: maximum warnings (capped at 20).
    """
    hits = vault.gotcha_check(context, limit=min(limit, 20))
    return {"context": context, "count": len(hits), "gotchas": hits}


@mcp.tool()
def read_note(path: str) -> dict:
    """Read one note: frontmatter, body, outgoing links, and its callouts.

    Args:
        path: vault-relative, e.g. "GLOBAL/gotchas/docker/mount-stale.md".
    """
    p = vault.resolve(path)
    if p.suffix.lower() not in NOTE_SUFFIXES:
        raise ValueError(
            f"{path} is not a note. read_note handles {sorted(NOTE_SUFFIXES)} only; "
            "use read_file for assets."
        )
    if not p.is_file():
        near = vault.search(Path(path).stem.replace("-", " "), limit=3)
        hint = f" Closest matches: {[n['path'] for n in near]}" if near else ""
        raise FileNotFoundError(f"Note not found: {path}.{hint}")

    note = vault.notes.get(p.relative_to(vault.root).as_posix())
    if note is None:
        vault.reindex()
        note = vault.notes[p.relative_to(vault.root).as_posix()]

    body = note.body
    truncated = len(body) > MAX_NOTE_CHARS
    return {
        "path": note.path,
        "title": note.title,
        "frontmatter": note.meta,
        "content": body[:MAX_NOTE_CHARS],
        "truncated": truncated,
        "links": note.links,
        "callouts": note.callouts,
    }


@mcp.tool()
def create_note(path: str, title: str, content: str, note_type: str = "",
                tags: list[str] | None = None, severity: str = "",
                auto_index: bool = True) -> dict:
    """Create a note with consistent frontmatter, optionally linking it into the folder index.

    Refuses to overwrite. A gotcha without a severity callout in its content is rejected —
    the marker is not decoration, it is what makes the note retrievable.

    Args:
        path: vault-relative target, e.g. "GLOBAL/gotchas/docker/mount-stale.md".
        title: state the CONCLUSION, not the topic.
        content: the body, without frontmatter.
        note_type: gotcha | insight | adr | snippet | analysis | project-index | index
        tags: list of tags.
        severity: for gotchas — danger | warning | tip | info
        auto_index: append a line to the folder's _INDEX.md.
    """
    p = vault.resolve(path)
    if p.exists():
        raise FileExistsError(f"{path} already exists. Use update_note to change it.")
    if p.suffix.lower() not in NOTE_SUFFIXES:
        raise ValueError(f"{path} is not a note path (expected one of {sorted(NOTE_SUFFIXES)}).")
    if note_type == "gotcha" and "> [!" not in content:
        raise ValueError(
            "A gotcha must open with a severity callout, e.g.\n"
            "> [!warning] Short title\n> One sentence: problem and consequence.\n"
            "Without it the note is invisible to gotcha_check."
        )

    fm = [f'title: "{title}"']
    if note_type:
        fm.append(f"type: {note_type}")
    fm.append(f"tags: [{', '.join(tags or [])}]")
    if severity:
        fm.append(f"severity: {severity}")
    fm.append(f"date: {date.today().isoformat()}")

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\n" + "\n".join(fm) + "\n---\n\n" + content.lstrip("\n"), encoding="utf-8")

    indexed = False
    if auto_index:
        idx = p.parent / "_INDEX.md"
        if idx.is_file():
            stem = p.relative_to(vault.root).as_posix().rsplit(".", 1)[0]
            with idx.open("a", encoding="utf-8") as fh:
                fh.write(f"\n- [[{stem}|{title}]]\n")
            indexed = True

    vault.reindex()
    return {"path": p.relative_to(vault.root).as_posix(), "indexed": indexed, "created": True}


@mcp.tool()
def update_note(path: str, content: str, mode: str = "append") -> dict:
    """Update a note, preserving its frontmatter.

    Args:
        path: vault-relative note path.
        content: the text to write.
        mode: "append" (default) or "replace_body".
    """
    p = vault.resolve(path)
    if not p.is_file():
        raise FileNotFoundError(f"Note not found: {path}")
    if mode not in ("append", "replace_body"):
        raise ValueError('mode must be "append" or "replace_body"')

    from .vault import parse_frontmatter
    raw = p.read_text(encoding="utf-8")
    meta_block = raw[:len(raw) - len(parse_frontmatter(raw)[1])]
    body = parse_frontmatter(raw)[1]

    new_body = (body.rstrip() + "\n\n" + content.lstrip("\n") + "\n") if mode == "append" \
        else (content.lstrip("\n") + "\n")
    p.write_text(meta_block + new_body, encoding="utf-8")
    vault.reindex()
    return {"path": path, "mode": mode, "bytes": len(new_body)}


@mcp.tool()
def list_directory(path: str = "", depth: int = 1) -> dict:
    """Structural overview of a folder without reading any content.

    Use this to orient before reading. Reading a folder's `_INDEX.md` is usually cheaper still.

    Args:
        path: vault-relative folder, "" for the root.
        depth: how many levels to descend (capped at 3).
    """
    base = vault.resolve(path) if path else vault.root
    if not base.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    depth = max(1, min(depth, 3))
    entries = []
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if len(rel.parts) > depth or any(part.startswith(".") for part in rel.parts):
            continue
        if p.is_dir():
            n = sum(1 for f in p.rglob("*") if f.suffix.lower() in NOTE_SUFFIXES)
            entries.append({"path": rel.as_posix() + "/", "kind": "dir", "notes": n})
        elif p.suffix.lower() in NOTE_SUFFIXES:
            entries.append({"path": rel.as_posix(), "kind": "note", "bytes": p.stat().st_size})
    return {"path": path or "/", "count": len(entries), "entries": entries[:300]}


@mcp.tool()
def vault_health() -> dict:
    """Hygiene report: gotchas without a callout, broken links, orphans, missing indexes.

    `gotchas_without_callout` is the one to act on first — every entry is a note that exists and
    will never surface when it is needed.
    """
    vault.reindex()
    return vault.health()


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "http":
        # Since SDK 2.x transport parameters go to run(); mcp.settings.host/port are gone.
        mcp.run(
            transport="streamable-http",
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "8765")),
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
