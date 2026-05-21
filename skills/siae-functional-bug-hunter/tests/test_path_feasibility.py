"""test_path_feasibility.py — Phase 6 feasibility filter verdicts.

Tests the four verdict branches the script must emit, plus the
no-predicates-declared default-to-feasible branch.

Run: pytest tests/test_path_feasibility.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = THIS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest  # noqa: E402

from path_feasibility import verdict_for  # noqa: E402


@pytest.fixture
def repo_with_login(tmp_path: Path) -> Path:
    src = tmp_path / "src" / "auth"
    src.mkdir(parents=True)
    login_file = src / "login.py"
    login_file.write_text(
        "def login(user, pwd):\n"
        "    if not validate(pwd):\n"
        "        raise ValueError\n"
        "    session.create(user)\n",
        encoding="utf-8",
    )
    return tmp_path


def _enumerate(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file()]


def test_feasible_with_predicate_match(repo_with_login: Path) -> None:
    files = _enumerate(repo_with_login)
    hypothesis = {
        "actor_primitives": ["end_user"],
        "evidence_path": "src/auth/login.py",
        "path_predicates": ["validate", "session"],
    }
    result = verdict_for(hypothesis, files, [repo_with_login])
    assert result["verdict"] == "feasible"
    assert result["verdict_reason"] == "at_least_one_predicate_matched"
    assert any("login.py" in f for f in result["matched_files"])


def test_infeasible_no_actor(repo_with_login: Path) -> None:
    files = _enumerate(repo_with_login)
    hypothesis = {
        "actor_primitives": [],
        "evidence_path": "src/auth/login.py",
        "path_predicates": ["validate"],
    }
    result = verdict_for(hypothesis, files, [repo_with_login])
    assert result["verdict"] == "infeasible"
    assert result["verdict_reason"] == "no_actor_primitive"
    assert result["matched_files"] == []


def test_infeasible_evidence_path_not_in_scope(repo_with_login: Path) -> None:
    files = _enumerate(repo_with_login)
    hypothesis = {
        "actor_primitives": ["end_user"],
        "evidence_path": "src/payments/charge.py",
        "path_predicates": ["validate"],
    }
    result = verdict_for(hypothesis, files, [repo_with_login])
    assert result["verdict"] == "infeasible"
    assert result["verdict_reason"] == "evidence_path_not_in_scope"


def test_infeasible_no_predicate_matched(repo_with_login: Path) -> None:
    files = _enumerate(repo_with_login)
    hypothesis = {
        "actor_primitives": ["end_user"],
        "evidence_path": "src/auth/login.py",
        "path_predicates": ["nonexistent_token_xyz123"],
    }
    result = verdict_for(hypothesis, files, [repo_with_login])
    assert result["verdict"] == "infeasible"
    assert result["verdict_reason"] == "no_predicate_matched"


def test_feasible_no_predicates_declared(repo_with_login: Path) -> None:
    files = _enumerate(repo_with_login)
    hypothesis = {
        "actor_primitives": ["end_user"],
        "evidence_path": "src/auth/login.py",
        "path_predicates": [],
    }
    result = verdict_for(hypothesis, files, [repo_with_login])
    assert result["verdict"] == "feasible"
    assert result["verdict_reason"] == "no_predicates_declared"
