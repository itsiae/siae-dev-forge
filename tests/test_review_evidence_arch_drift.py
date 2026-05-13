"""Tests for arch_drift check (W3 spec, Task 06)."""
from __future__ import annotations

from pathlib import Path

from lib.review_evidence.checks.arch_drift import ArchDrift, detect_arch_drift

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_no_arch_yml_no_violations(tmp_path: Path) -> None:
    result = detect_arch_drift(tmp_path, changed_files=["src/api/handler.py"])
    assert isinstance(result, ArchDrift)
    assert result.violations == []
    assert result.rules_file_present is False


def test_forbidden_path_violation_detected(tmp_path: Path) -> None:
    (tmp_path / ".devforge-arch.yml").write_text(
        (FIX / "devforge_arch.yml").read_text()
    )
    api_dir = tmp_path / "src" / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "handler.py").write_text("from src.db.connection import db\n")

    result = detect_arch_drift(tmp_path, changed_files=["src/api/handler.py"])
    assert result.rules_file_present is True
    assert len(result.violations) == 1
    v = result.violations[0]
    assert v.file == "src/api/handler.py"
    assert v.rule_from == "src/api/"
    assert v.rule_to == "src/db/"


def test_allowed_path_no_violation(tmp_path: Path) -> None:
    (tmp_path / ".devforge-arch.yml").write_text(
        (FIX / "devforge_arch.yml").read_text()
    )
    api_dir = tmp_path / "src" / "api"
    api_dir.mkdir(parents=True)
    # `src/database/x` shares prefix with rule `to: src/db/` — must NOT
    # produce a false positive (ITER1 BLOCK fix).
    (api_dir / "handler.py").write_text(
        "from src.service.user import service\n"
        "from src.database.helpers import helper\n"
    )

    result = detect_arch_drift(tmp_path, changed_files=["src/api/handler.py"])
    assert result.violations == []
