#!/usr/bin/env python3
"""Verify every relative Markdown link in the repository resolves to a real file.

The documentation is heavily cross-linked, and a rename silently breaks links without any
test noticing. Run it from the repository root:

    python3 .github/scripts/check-links.py

Only relative links are checked. External URLs are left alone on purpose: a network-dependent
check turns unrelated pull requests red when somebody else's site is down.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")
# Wikilinks in the vault template are checked by the `vault` job instead; relative Markdown
# links there are checked here like everywhere else, because a template that is copied out of
# the repository takes its broken links with it.
SKIP_DIRS = {".git"}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    broken: list[str] = []
    checked = 0

    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root)
        if set(rel.parts) & SKIP_DIRS:
            continue
        for text, target in LINK.findall(md.read_text(encoding="utf-8")):
            if target.startswith(SKIP_PREFIXES):
                continue
            checked += 1
            path_part = target.split("#")[0]
            if not path_part:
                continue
            if not (md.parent / path_part).resolve().exists():
                broken.append(f"{rel}: [{text}]({target})")

    print(f"checked {checked} relative links")
    if broken:
        print(f"BROKEN ({len(broken)}):")
        for b in broken:
            print(f"  {b}")
        return 1
    print("all resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
