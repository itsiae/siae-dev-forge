"""Determinismo evidence contract: ogni backbone skill DEVE dichiarare
validates_via well-formed nel frontmatter. Senza, il gate hook non puo'
verificare il completamento e l'utente puo' claimare 'fatto' senza evidence.

Coverage target: 9/9 backbone skill = 100%.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Lista backbone explicit — modifiche a questa lista vanno discusse via brainstorming
BACKBONE_SKILLS = [
    "siae-brainstorming",
    "siae-writing-plans",
    "siae-tdd",
    "siae-verification",
    "siae-blind-review",
    "siae-debugging",
    "siae-security",
    "siae-finishing-branch",
    "siae-git-workflow",
]

VALID_EVIDENCE_TYPES = {"log_event", "file_exists", "exit_code", "state_file", "file_pattern", "git_state"}


def _read_frontmatter(skill_name: str) -> str:
    p = REPO_ROOT / "skills" / skill_name / "SKILL.md"
    text = p.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, f"{skill_name}: SKILL.md non ha frontmatter YAML valido"
    return m.group(1)


def test_backbone_skills_all_have_validates_via():
    """9/9 backbone skill devono avere validates_via nel frontmatter."""
    missing = []
    for skill in BACKBONE_SKILLS:
        fm = _read_frontmatter(skill)
        if "validates_via:" not in fm:
            missing.append(skill)
    assert not missing, (
        f"Backbone skill senza validates_via: {missing}. "
        "Ogni promessa del backbone deve essere verificabile (memoria anti-dilution)."
    )


def test_validates_via_has_predicate():
    """Ogni validates_via deve dichiarare un 'predicate' non-vuoto."""
    for skill in BACKBONE_SKILLS:
        fm = _read_frontmatter(skill)
        m = re.search(r"validates_via:.*?predicate:\s*(\S+)", fm, re.DOTALL)
        assert m, f"{skill}: validates_via senza 'predicate'"
        assert m.group(1) not in ("", "null", "TBD"), (
            f"{skill}: predicate placeholder/vuoto = {m.group(1)!r}"
        )


def test_validates_via_has_evidence_type():
    """Ogni validates_via deve dichiarare 'evidence_type' nella allowlist."""
    for skill in BACKBONE_SKILLS:
        fm = _read_frontmatter(skill)
        m = re.search(r"validates_via:.*?evidence_type:\s*(\S+)", fm, re.DOTALL)
        assert m, f"{skill}: validates_via senza 'evidence_type'"
        et = m.group(1)
        assert et in VALID_EVIDENCE_TYPES, (
            f"{skill}: evidence_type={et!r} non in allowlist {VALID_EVIDENCE_TYPES}"
        )


def test_validates_via_has_evidence_check():
    """Ogni validates_via deve dichiarare 'evidence_check' non-vuoto, non-TBD."""
    for skill in BACKBONE_SKILLS:
        fm = _read_frontmatter(skill)
        m = re.search(r"validates_via:.*?evidence_check:\s*\"?([^\n\"]+)", fm, re.DOTALL)
        assert m, f"{skill}: validates_via senza 'evidence_check'"
        check = m.group(1).strip()
        assert "TBD" not in check.upper(), f"{skill}: evidence_check contiene TBD"
        assert len(check) > 10, f"{skill}: evidence_check troppo corto = {check!r}"


def test_predicate_names_unique_across_backbone():
    """Ogni predicate deve essere unico fra i backbone (evita ambiguita' del gate)."""
    seen = {}
    for skill in BACKBONE_SKILLS:
        fm = _read_frontmatter(skill)
        m = re.search(r"validates_via:.*?predicate:\s*(\S+)", fm, re.DOTALL)
        if m:
            pred = m.group(1)
            assert pred not in seen, (
                f"Predicate duplicato '{pred}' in {skill} e {seen[pred]}"
            )
            seen[pred] = skill
