#!/usr/bin/env python3
"""Assert the vault template passes the rules it teaches.

Used by BOTH `make vault` and CI, deliberately. An earlier version duplicated the assertions in
the Makefile and the workflow; the Makefile checked three things and the workflow four, so a
change passed locally and failed in CI — breaking exactly the promise CONTRIBUTING.md makes, that
a green `make check` predicts a green pipeline. One script, one set of rules.

    python3 .github/scripts/check-vault.py [vault-dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mcp" / "vault-mcp" / "src"))

from vault_mcp.vault import Vault  # noqa: E402

# MAP.md links two contracts that intentionally do not exist yet. A dangling wikilink is a to-do
# marker, which the page itself documents. Every other dangling link is a defect.
EXPECTED_DANGLING = {
    "GLOBAL/architecture/api-auth-contract",
    "GLOBAL/architecture/shared-database",
}


def main() -> int:
    vault_dir = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "vault-template")
    vault = Vault(vault_dir)
    count = vault.reindex()
    health = vault.health()

    problems: list[str] = []
    if health["gotchas_without_callout"]:
        problems.append(
            "gotchas without a severity callout — invisible to retrieval: "
            f"{health['gotchas_without_callout']}"
        )
    if health["orphans"]:
        problems.append(f"orphan notes, not linked from any index: {health['orphans']}")
    if health["folders_without_index"]:
        problems.append(f"folders without an _INDEX.md: {health['folders_without_index']}")

    unexpected = [b for b in health["broken_links"] if b["to"] not in EXPECTED_DANGLING]
    if unexpected:
        problems.append(f"unexpected broken links: {unexpected}")

    print(f"vault-template: {count} notes")
    if problems:
        print("FAIL")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("OK: the template passes the rules it teaches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
