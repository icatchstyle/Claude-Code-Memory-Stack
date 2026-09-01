"""Tests for the vault layer.

Deliberately no MCP dependency: the logic worth testing is parsing, ranking and health, which
is exactly the part you will change when adapting this to your own conventions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402

from vault_mcp.vault import Vault, parse_frontmatter  # noqa: E402


@pytest.fixture()
def vault(tmp_path):
    (tmp_path / "GLOBAL" / "gotchas" / "docker").mkdir(parents=True)
    (tmp_path / "GLOBAL" / "gotchas" / "docker" / "mount-stale.md").write_text(
        "---\n"
        "title: A bind mount can go stale\n"
        "type: gotcha\n"
        "tags: [docker, wsl2]\n"
        "severity: danger\n"
        "---\n\n"
        "# A bind mount can go stale\n\n"
        "> [!danger] The server reports healthy and finds nothing\n"
        "> After a re-sync the mount points at nothing.\n\n"
        "## Fix\n\nRestart the container.\n",
        encoding="utf-8",
    )
    (tmp_path / "GLOBAL" / "gotchas" / "_INDEX.md").write_text(
        "---\ntitle: Gotchas\ntype: index\n---\n\n"
        "# Gotchas\n\n- [[GLOBAL/gotchas/docker/mount-stale|Stale mount]]\n",
        encoding="utf-8",
    )
    (tmp_path / "HOME.md").write_text(
        "---\ntitle: Home\ntype: index\n---\n\n# Home\n\n"
        "- [[GLOBAL/gotchas/_INDEX|Gotchas]]\n- [[NOWHERE/missing|Broken]]\n",
        encoding="utf-8",
    )
    return Vault(tmp_path)


def test_frontmatter_scalars_and_lists():
    meta, body = parse_frontmatter(
        "---\ntitle: Hello\ntags: [a, b]\nseverity: warning\n---\n\nBody text\n"
    )
    assert meta["title"] == "Hello"
    assert meta["tags"] == ["a", "b"]
    assert meta["severity"] == "warning"
    assert body.strip() == "Body text"


def test_frontmatter_absent_is_not_an_error():
    meta, body = parse_frontmatter("# Just a heading\n")
    assert meta == {}
    assert body.startswith("# Just")


def test_reindex_finds_notes(vault):
    assert vault.reindex() == 3


def test_search_ranks_title_matches_first(vault):
    hits = vault.search("stale mount")
    assert hits
    assert hits[0]["path"].endswith("mount-stale.md")


def test_search_ignores_noise_terms(vault):
    assert vault.search("a") == []


def test_callout_is_parsed_with_its_detail(vault):
    note = vault.notes["GLOBAL/gotchas/docker/mount-stale.md"]
    callouts = note.callouts
    assert len(callouts) == 1
    assert callouts[0]["severity"] == "danger"
    assert "points at nothing" in callouts[0]["detail"]


def test_gotcha_check_matches_context(vault):
    hits = vault.gotcha_check("docker container mount")
    assert hits
    assert hits[0]["severity"] == "danger"
    assert hits[0]["source"].endswith("mount-stale.md")


def test_gotcha_check_ignores_notes_without_a_callout(vault, tmp_path):
    # A note that CLAIMS to be a gotcha but carries no callout must stay invisible —
    # this is the convention the whole retrieval story rests on.
    (tmp_path / "GLOBAL" / "gotchas" / "docker" / "no-callout.md").write_text(
        "---\ntitle: Docker container trap\ntype: gotcha\n---\n\nNo callout here.\n",
        encoding="utf-8",
    )
    vault.reindex()
    sources = [h["source"] for h in vault.gotcha_check("docker container")]
    assert not any(s.endswith("no-callout.md") for s in sources)


def test_health_flags_gotcha_without_callout(vault, tmp_path):
    (tmp_path / "GLOBAL" / "gotchas" / "docker" / "no-callout.md").write_text(
        "---\ntitle: Trap\ntype: gotcha\n---\n\nNothing.\n", encoding="utf-8"
    )
    report = vault.health()
    assert "GLOBAL/gotchas/docker/no-callout.md" in report["gotchas_without_callout"]


def test_health_finds_broken_links(vault):
    report = vault.health()
    assert any(b["to"] == "NOWHERE/missing" for b in report["broken_links"])


def test_resolve_refuses_traversal(vault):
    with pytest.raises(ValueError):
        vault.resolve("../../etc/passwd")


def test_skill_payload_is_exempt_from_index_and_orphan_rules(vault, tmp_path):
    # A multi-file skill: SKILL.md is a browsable note, references/ is payload the skill reads.
    skill = tmp_path / "SKILLS" / "ops" / "ship"
    (skill / "references").mkdir(parents=True)
    (tmp_path / "SKILLS" / "ops" / "_INDEX.md").write_text(
        "---\ntitle: Ops\ntype: index\n---\n\n# Ops\n\n- [[SKILLS/ops/ship/SKILL|ship]]\n",
        encoding="utf-8",
    )
    (skill / "SKILL.md").write_text(
        "---\nname: ship\ntype: skill\n---\n\n# Ship\n", encoding="utf-8"
    )
    (skill / "references" / "checklist.md").write_text(
        "---\ntitle: Checklist\n---\n\n# Checklist\n", encoding="utf-8"
    )
    vault.reindex()
    report = vault.health()

    # The payload note is neither an orphan nor does its folder need an _INDEX.md.
    assert "SKILLS/ops/ship/references/checklist.md" not in report["orphans"]
    assert "SKILLS/ops/ship/references" not in report["folders_without_index"]
    # The skill itself is still subject to the normal rules.
    assert "SKILLS/ops/ship" not in report["folders_without_index"]


def test_gotcha_check_ignores_templates(vault, tmp_path):
    # A template's callout is placeholder text; surfacing it as a warning is noise on every query.
    (tmp_path / "TEMPLATES").mkdir()
    (tmp_path / "TEMPLATES" / "gotcha.md").write_text(
        "---\ntitle: <Gotcha title>\ntype: gotcha\n---\n\n"
        "# <Gotcha title>\n\n> [!warning] <Short title>\n> <One sentence about docker.>\n",
        encoding="utf-8",
    )
    vault.reindex()
    sources = [h["source"] for h in vault.gotcha_check("docker")]
    assert not any(s.startswith("TEMPLATES/") for s in sources)
