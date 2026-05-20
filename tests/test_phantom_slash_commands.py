"""Determinismo catalog onesto: ogni /forge-X menzionato in skills/*/SKILL.md
DEVE esistere come file in commands/. Eccezione: anti-esempi documentati
(whitelist).

Anti-allucinazione: la PR #263 aveva dovuto rimuovere 14 /forge-X fantasma
dalle SKILL.md description. Questo test impedisce regressioni future.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Whitelist intenzionale: slash command NON esistenti citati come anti-esempi
# educativi (es. "NON inventare slash command"). Ogni entry deve avere riga
# di motivazione.
PHANTOM_WHITELIST = {
    "/forge-spec-review": (
        "skills/siae-subagent-development/SKILL.md Permission Denied: anti-esempio "
        "documentato (NON inventare slash command). Tracked in v1.62.3 CHANGELOG."
    ),
}


def _all_mentioned_slash_commands():
    """Ritorna dict {slash_cmd: [(skill_file, line_no), ...]}."""
    mentions = {}
    for skill_md in (REPO_ROOT / "skills").glob("*/SKILL.md"):
        text = skill_md.read_text()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in re.finditer(r"/forge-[a-z][a-z0-9-]*", line):
                cmd = match.group(0)
                mentions.setdefault(cmd, []).append((str(skill_md.relative_to(REPO_ROOT)), line_no))
    return mentions


def _existing_commands():
    return {f"/{p.stem}" for p in (REPO_ROOT / "commands").glob("forge-*.md")}


def test_no_phantom_slash_commands_in_skills():
    """Ogni /forge-X menzionato in SKILL.md deve esistere come command file,
    a meno di whitelist documentata."""
    mentioned = _all_mentioned_slash_commands()
    existing = _existing_commands()
    phantoms = []
    for cmd, locations in mentioned.items():
        if cmd in existing:
            continue
        if cmd in PHANTOM_WHITELIST:
            continue
        phantoms.append((cmd, locations))
    assert not phantoms, (
        "Slash command fantasma trovati in SKILL.md (commands/ non li implementa):\n"
        + "\n".join(
            f"  {cmd} citato in: {locs}" for cmd, locs in phantoms
        )
        + "\n\nO crea il command file, o rimuovi la menzione dalla SKILL.md, "
        "o aggiungi a PHANTOM_WHITELIST con motivazione."
    )


def test_whitelist_entries_actually_referenced():
    """Le entry della whitelist devono essere effettivamente citate in qualche
    SKILL.md (whitelist non-vuota = ground truth). Evita whitelist stale."""
    mentioned = _all_mentioned_slash_commands()
    stale = [c for c in PHANTOM_WHITELIST if c not in mentioned]
    assert not stale, (
        f"Whitelist entries stale (non piu' citate in nessuna SKILL.md): {stale}. "
        "Rimuoverle dalla PHANTOM_WHITELIST."
    )


def test_no_orphan_commands():
    """Ogni command file in commands/ deve essere associato a una skill
    (citato in almeno una SKILL.md description o body, oppure ha logica propria
    documentata in commands/<X>.md stesso)."""
    existing = _existing_commands()
    skills_text = "\n".join(
        p.read_text() for p in (REPO_ROOT / "skills").glob("*/SKILL.md")
    )
    orphans = []
    # commands logic-heavy ammessi anche se non citati nelle skill (hanno logica propria)
    LOGIC_HEAVY_OK = {"/forge-evidence", "/forge-score", "/forge-fix-evidence",
                      "/forge-release-risk", "/forge-mcp-preflight",
                      "/forge-adoption", "/forge-analytics", "/code-coverage"}
    for cmd in existing:
        if cmd in LOGIC_HEAVY_OK:
            continue
        if cmd not in skills_text:
            orphans.append(cmd)
    assert not orphans, (
        f"Command file orfani (nessuna skill li menziona, no logica propria documentata): {orphans}"
    )
