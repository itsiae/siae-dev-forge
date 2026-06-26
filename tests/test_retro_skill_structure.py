from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "forge-retrospect" / "SKILL.md"


def test_skill_exists_and_has_three_modes():
    src = SKILL.read_text(encoding="utf-8")
    for mode in ("MINE", "APPLY", "DISMISS"):
        assert mode in src
    assert "dry-run" in src.lower()


def test_skill_references_real_modules_and_reuses_retrospective():
    src = SKILL.read_text(encoding="utf-8")
    assert "lib/retro/digest.py" in src
    assert "lib/retro/writer.py" in src
    assert "siae-retrospective" in src           # riuso, non duplicazione
    assert "evidence_count" in src               # soglia ≥2 lezioni
    assert "retro-pending" in src
