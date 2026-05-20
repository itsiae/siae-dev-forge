"""Determinismo anti-allucinazione: count empirici nel filesystem devono
matchare le description in plugin.json/marketplace.json. Fail = drift dichiarato.

Follow-up code-reviewer PR #263: "Senza un test deterministico, il drift si
ripresenterà alla prossima release."
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _empirical_counts():
    skills = list((REPO_ROOT / "skills").glob("*/"))
    commands = list((REPO_ROOT / "commands").glob("*.md"))
    agents = list((REPO_ROOT / "agents").glob("*.md"))
    hook_excludes = {"hooks.json", "run-hook.cmd", "skill-advisory-helpers.sh", "lib"}
    hooks_dir = REPO_ROOT / "hooks"
    hooks = [
        h for h in hooks_dir.iterdir()
        if h.name not in hook_excludes
        and not h.name.endswith(".md")
        and not h.name.endswith(".json")
        and not h.is_dir()
    ]
    return {
        "skill": len(skills),
        "comandi": len(commands),
        "agent": len(agents),
        "hook": len(hooks),
    }


def _parse_counts_from_description(desc: str):
    pattern = r"(\d+)\s+(skill|comandi|agent|hook)"
    return {kind: int(n) for n, kind in re.findall(pattern, desc)}


def test_plugin_json_exists_and_valid():
    data = json.loads(PLUGIN_JSON.read_text())
    assert "version" in data
    assert "description" in data


def test_marketplace_json_exists_and_valid():
    data = json.loads(MARKETPLACE_JSON.read_text())
    assert data["plugins"]
    assert "version" in data["plugins"][0]
    assert "description" in data["plugins"][0]


def test_dual_source_version_sync():
    """Memoria project_plugin_version_dual_source: plugin.json E marketplace.json
    devono avere la stessa version. PR Gate hook usa plugin.json come source-of-truth."""
    plugin_v = json.loads(PLUGIN_JSON.read_text())["version"]
    marketplace_v = json.loads(MARKETPLACE_JSON.read_text())["plugins"][0]["version"]
    assert plugin_v == marketplace_v, (
        f"Version drift: plugin.json={plugin_v} vs marketplace.json={marketplace_v}. "
        "Memoria project_plugin_version_dual_source: ogni bump aggiorna ENTRAMBI."
    )


def test_dual_source_description_sync():
    """plugin.json E marketplace.json description identiche carattere-per-carattere."""
    plugin_d = json.loads(PLUGIN_JSON.read_text())["description"]
    marketplace_d = json.loads(MARKETPLACE_JSON.read_text())["plugins"][0]["description"]
    assert plugin_d == marketplace_d, (
        "Description drift fra plugin.json e marketplace.json.\n"
        f"  plugin.json:      {plugin_d}\n"
        f"  marketplace.json: {marketplace_d}"
    )


def test_description_counts_match_empirical():
    """Count nella description plugin.json deve matchare empiria filesystem.
    Anti-allucinazione: la PR #263 aveva dichiarato '30 hook' (count inventato);
    questo test l'avrebbe bloccata."""
    desc = json.loads(PLUGIN_JSON.read_text())["description"]
    declared = _parse_counts_from_description(desc)
    empirical = _empirical_counts()
    for kind, n_emp in empirical.items():
        n_dec = declared.get(kind)
        assert n_dec is not None, f"Description plugin.json non dichiara count per '{kind}'"
        assert n_dec == n_emp, (
            f"Count drift '{kind}': description dichiara {n_dec}, filesystem ha {n_emp}. "
            f"Aggiornare description in plugin.json/marketplace.json."
        )


def test_readme_version_matches_plugin():
    """README.md metadata tabella deve dichiarare la stessa version di plugin.json.
    Anti-allucinazione: la PR #263 aveva README su 1.62.3 mentre plugin.json era 1.62.4."""
    readme = (REPO_ROOT / "README.md").read_text()
    plugin_v = json.loads(PLUGIN_JSON.read_text())["version"]
    m = re.search(r"\|\s*Versione\s*\|\s*`([^`]+)`\s*\|", readme)
    assert m is not None, "README.md tabella metadata non ha riga 'Versione'"
    assert m.group(1) == plugin_v, (
        f"README version drift: README dichiara {m.group(1)}, plugin.json ha {plugin_v}"
    )
