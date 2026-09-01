"""Vault access layer: parsing, indexing, search.

Deliberately dependency-free (stdlib only) and re-indexed in memory on demand. A vault of a few
thousand notes indexes in well under a second, which is cheaper than the operational cost of
maintaining a persistent index — and, notably, immune to the stale-index failure that a
persistent one brings with it.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

NOTE_SUFFIXES = {".md", ".mmd"}

# Obsidian-style callout: "> [!warning] Title"
CALLOUT_RE = re.compile(r"^>\s*\[!(?P<severity>\w+)\]\s*(?P<title>.*)$", re.MULTILINE)
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")

# A vault documents its own conventions, so `[[path|alias]]` appears as an EXAMPLE in prose far
# more often than one expects. Counting those as real links produces phantom broken links that
# no amount of staring at the note explains.
FENCED_CODE = re.compile(r"^([ \t]*)(```|~~~).*?^\1\2[^\n]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)

SEVERITY_ORDER = {"danger": 0, "warning": 1, "tip": 2, "info": 3}

# A multi-file skill carries payload beside its SKILL.md. Those files are read by the skill when
# it runs, not browsed as vault notes, so they are exempt from the index and orphan rules — a
# reference sheet nobody links to is correct, not a defect.
PAYLOAD_DIRS = {"references", "scripts", "assets"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split YAML-ish frontmatter from the body.

    A minimal parser on purpose: it handles the scalar/list shapes this vault convention uses and
    does not pull in a YAML dependency. Unknown shapes are kept as raw strings rather than
    guessed at, so nothing is silently mangled.
    """
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text

    meta: dict = {}
    key = None
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(("  - ", "- ")) and key:            # list continuation
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line.split("- ", 1)[1].strip().strip("\"'"))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if value.startswith("[") and value.endswith("]"):
            meta[key] = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
        elif value == "":
            meta[key] = []                                      # a block list may follow
        else:
            meta[key] = value.strip("\"'")
    return meta, text[m.end():]


@dataclass
class Note:
    path: str                       # vault-relative, POSIX separators
    title: str
    body: str
    meta: dict = field(default_factory=dict)
    mtime: float = 0.0

    @property
    def type(self) -> str:
        return str(self.meta.get("type", ""))

    @property
    def tags(self) -> list[str]:
        t = self.meta.get("tags", [])
        return t if isinstance(t, list) else [str(t)]

    @property
    def callouts(self) -> list[dict]:
        """Every severity callout in the note, with the sentence that follows it.

        This is what turns "notes about problems" into a queryable warning system.
        """
        out = []
        prose = INLINE_CODE.sub("", FENCED_CODE.sub("", self.body))
        lines = prose.splitlines()
        for i, line in enumerate(lines):
            m = CALLOUT_RE.match(line)
            if not m:
                continue
            detail = []
            for follow in lines[i + 1:]:
                if not follow.startswith(">"):
                    break
                detail.append(follow.lstrip("> ").rstrip())
            out.append({
                "severity": m.group("severity").lower(),
                "title": m.group("title").strip(),
                "detail": " ".join(detail).strip(),
            })
        return out

    @property
    def links(self) -> list[str]:
        """Outgoing wikilinks, ignoring anything inside code.

        Known limitation: four-space-indented code blocks are not recognised, because they are
        indistinguishable from list continuation without a full Markdown parse. Put examples in a
        fenced block or in backticks.
        """
        prose = FENCED_CODE.sub("", self.body)
        prose = INLINE_CODE.sub("", prose)
        return [m.group(1).strip() for m in WIKILINK_RE.finditer(prose)]


class Vault:
    """An in-memory view of the vault, rebuilt when files change."""

    def __init__(self, root: str | os.PathLike):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError(f"vault path is not a directory: {self.root}")
        self._notes: dict[str, Note] = {}
        self._indexed_at = 0.0

    # ---------------------------------------------------------------- indexing

    def reindex(self) -> int:
        notes: dict[str, Note] = {}
        for p in self.root.rglob("*"):
            if p.suffix.lower() not in NOTE_SUFFIXES or not p.is_file():
                continue
            if any(part.startswith(".") for part in p.relative_to(self.root).parts):
                continue                                        # .obsidian, .git, …
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            meta, body = parse_frontmatter(text)
            rel = p.relative_to(self.root).as_posix()
            title = str(meta.get("title") or self._first_heading(body) or p.stem)
            notes[rel] = Note(path=rel, title=title, body=body, meta=meta,
                              mtime=p.stat().st_mtime)
        self._notes = notes
        self._indexed_at = time.time()
        return len(notes)

    @staticmethod
    def _first_heading(body: str) -> str | None:
        for line in body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def ensure_index(self, max_age: float = 30.0) -> None:
        """Re-index if the cache is older than max_age seconds.

        A time-based refresh keeps writes made outside this process visible without the
        bookkeeping of a file watcher.
        """
        if time.time() - self._indexed_at > max_age:
            self.reindex()

    @property
    def notes(self) -> dict[str, Note]:
        self.ensure_index()
        return self._notes

    # ---------------------------------------------------------------- paths

    def resolve(self, path: str) -> Path:
        """Resolve a vault-relative path, refusing anything that escapes the vault.

        Compares paths, not strings. A prefix test on the string form lets a SIBLING directory
        through — for a vault at `/data/vault`, the path `../vault-secrets/x.md` resolves to
        `/data/vault-secrets/x.md`, which starts with `/data/vault` and would be accepted.
        """
        candidate = (self.root / path.lstrip("/")).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"path escapes the vault: {path}")
        return candidate

    # ---------------------------------------------------------------- search

    def search(self, query: str, limit: int = 10, folder: str | None = None) -> list[dict]:
        """Keyword search, ranked. Title matches dominate on purpose.

        This is why the naming convention matters: a title that states the conclusion is what
        makes a note findable at all.
        """
        terms = [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]
        if not terms:
            return []

        results = []
        for note in self.notes.values():
            if folder and not note.path.startswith(folder.strip("/")):
                continue
            haystack_title = note.title.lower()
            haystack_body = note.body.lower()
            haystack_tags = " ".join(note.tags).lower()

            score = 0.0
            for term in terms:
                score += haystack_title.count(term) * 10.0
                score += haystack_tags.count(term) * 4.0
                score += min(haystack_body.count(term), 8) * 1.0
                if term in note.path.lower():
                    score += 3.0
            if score <= 0:
                continue
            results.append({
                "path": note.path,
                "title": note.title,
                "type": note.type,
                "score": round(score, 2),
                "snippet": self._snippet(note.body, terms),
            })

        results.sort(key=lambda r: -r["score"])
        return results[:limit]

    @staticmethod
    def _snippet(body: str, terms: list[str], width: int = 160) -> str:
        low = body.lower()
        pos = min((low.find(t) for t in terms if low.find(t) >= 0), default=-1)
        if pos < 0:
            return body[:width].replace("\n", " ").strip()
        start = max(0, pos - width // 3)
        return ("…" if start else "") + body[start:start + width].replace("\n", " ").strip() + "…"

    # ---------------------------------------------------------------- gotchas

    def gotcha_check(self, context: str, limit: int = 8) -> list[dict]:
        """Return callout-marked warnings relevant to a context.

        The payoff tool: it surfaces traps BEFORE the mistake instead of documenting them after.
        Ranking is severity first, then term overlap — a `danger` you half-match beats an `info`
        you fully match.
        """
        terms = {t for t in re.split(r"\W+", context.lower()) if len(t) > 2}
        hits = []
        for note in self.notes.values():
            # Templates carry placeholder callouts ("<One sentence: the problem>"), and indexes
            # and entry points carry navigational ones ("How to use this"). Both are guidance,
            # not traps — returning them as warnings puts noise on every single query, which is
            # exactly how a warning system gets ignored.
            stem = note.path.rsplit(".", 1)[0]
            if note.path.startswith("TEMPLATES/") or stem.endswith("_INDEX") \
                    or stem in ("HOME", "MAP"):
                continue
            callouts = note.callouts
            if not callouts:
                continue                                        # no marker → not a gotcha
            surface = f"{note.title} {note.path} {' '.join(note.tags)}".lower()
            overlap = sum(1 for t in terms if t in surface)
            body_overlap = sum(1 for t in terms if t in note.body.lower())
            if overlap == 0 and body_overlap == 0:
                continue
            for c in callouts:
                hits.append({
                    "severity": c["severity"],
                    "title": c["title"] or note.title,
                    "detail": c["detail"][:400],
                    "source": note.path,
                    "_rank": (SEVERITY_ORDER.get(c["severity"], 9),
                              -(overlap * 3 + body_overlap)),
                })
        hits.sort(key=lambda h: h["_rank"])
        for h in hits:
            h.pop("_rank")
        return hits[:limit]

    # ---------------------------------------------------------------- health

    @staticmethod
    def _is_payload(path: str) -> bool:
        """True for a skill's support files (references/, scripts/, assets/)."""
        return any(part in PAYLOAD_DIRS for part in path.split("/")[:-1])

    def health(self) -> dict:
        notes = self.notes
        known = set(notes)
        stems = {p.rsplit(".", 1)[0] for p in known}

        broken, orphan_candidates, no_callout, index_missing = [], [], [], []
        linked_to: set[str] = set()

        for note in notes.values():
            for link in note.links:
                target = link.split("#")[0].strip()
                linked_to.add(target)
                if target not in stems and f"{target}.md" not in known:
                    broken.append({"from": note.path, "to": target})
            if note.type == "gotcha" and not note.callouts:
                no_callout.append(note.path)

        for note in notes.values():
            stem = note.path.rsplit(".", 1)[0]
            if stem.endswith("_INDEX") or stem in ("HOME", "MAP"):
                continue
            if self._is_payload(note.path):
                continue
            if stem not in linked_to:
                orphan_candidates.append(note.path)

        folders = {os.path.dirname(p) for p in known if os.path.dirname(p)}
        for folder in sorted(folders):
            if self._is_payload(folder + "/"):
                continue
            # A folder holding a SKILL.md is a skill root, not a section of the vault:
            # its category index links to it, so it needs no index of its own.
            if f"{folder}/SKILL.md" in known:
                continue
            if f"{folder}/_INDEX.md" not in known:
                index_missing.append(folder)

        return {
            "notes": len(notes),
            "gotchas_without_callout": no_callout,      # the highest-value check
            "broken_links": broken[:50],
            "broken_link_count": len(broken),
            "orphans": orphan_candidates[:50],
            "orphan_count": len(orphan_candidates),
            "folders_without_index": index_missing,
        }
