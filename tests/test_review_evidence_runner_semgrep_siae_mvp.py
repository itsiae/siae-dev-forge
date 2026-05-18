"""MVP test for Semgrep runner SIAE registry inclusion (Wave 1 task-09 minimal).

Verifica che il runner Semgrep di default includa SIA il community ruleset (`auto`)
SIA la SIAE custom rules registry, in modo che le regole SIAE Wave 1 siano
attive immediatamente senza override env var.

Wave 1 design ref: docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.review_evidence.runners.semgrep import _DEFAULT_CONFIG


REPO_ROOT = Path(__file__).parents[1]
RULE_F1 = REPO_ROOT / "rules" / "semgrep" / "siae" / "formula-injection" / "ts-csv-concat.yaml"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "semgrep_siae" / "synthetic"


def test_default_config_includes_siae_registry():
    """AC6 MVP: default config Semgrep include il path SIAE registry.yaml."""
    assert "siae/registry.yaml" in _DEFAULT_CONFIG, (
        f"_DEFAULT_CONFIG must include SIAE registry path, got: {_DEFAULT_CONFIG!r}"
    )


def test_default_config_preserves_community_auto():
    """AC6 MVP: backward-compat — community 'auto' ruleset resta nel default."""
    assert "auto" in _DEFAULT_CONFIG, (
        f"_DEFAULT_CONFIG must preserve community 'auto', got: {_DEFAULT_CONFIG!r}"
    )


def test_siae_registry_path_exists_on_disk():
    """Sanity check: il path che _DEFAULT_CONFIG referenzia esiste sul filesystem."""
    registry = REPO_ROOT / "rules" / "semgrep" / "siae" / "registry.yaml"
    assert registry.is_file(), f"SIAE registry must exist at: {registry}"


# ---------------------------------------------------------------------------
# AC1 Wave 1 — Semgrep --test integration for rule F1 Formula Injection.
# Skipped if `semgrep` binary not on PATH (CI runner setup).
# ---------------------------------------------------------------------------

def _run_semgrep_on(target: Path, tmp_path: Path) -> list[dict]:
    """Copy target outside the repo (paths.exclude bypass) and run Semgrep rule F1."""
    dest = tmp_path / target.name
    dest.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run(
        ["semgrep", "--config", str(RULE_F1), "--json", "--quiet", str(dest)],
        capture_output=True, text=True, timeout=60, check=False,
    )
    if not p.stdout.strip():
        return []
    return json.loads(p.stdout).get("results", [])


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_matches_vulnerable_csv_concat(tmp_path):
    """AC1 must-catch: vulnerable fixture must produce >=2 findings."""
    findings = _run_semgrep_on(FIXTURES / "vulnerable" / "f1-csv-concat.ts", tmp_path)
    assert len(findings) >= 2, (
        f"Rule F1 must catch vulnerable CSV concat; got {len(findings)} findings"
    )
    rule_ids = {f["check_id"].split(".")[-1] for f in findings}
    assert "csv-row-join-naive" in rule_ids, (
        f"Expected csv-row-join-naive in findings; got {rule_ids}"
    )


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_matches_hyperlink_poc(tmp_path):
    """AC1 PoC: =HYPERLINK pentest payload must be caught."""
    findings = _run_semgrep_on(FIXTURES / "vulnerable" / "f1-csv-poc-hyperlink.ts", tmp_path)
    assert len(findings) >= 2, (
        f"Rule F1 must catch HYPERLINK PoC; got {len(findings)} findings"
    )


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_does_not_match_safe_stringify(tmp_path):
    """AC1 must-skip: safe csv-stringify fixture must produce 0 findings."""
    findings = _run_semgrep_on(FIXTURES / "safe" / "f1-csv-stringify.ts", tmp_path)
    assert findings == [], (
        f"Rule F1 must NOT match safe csv-stringify; got {len(findings)} findings"
    )


@pytest.mark.skipif(not shutil.which("semgrep"), reason="semgrep not installed")
def test_rule_f1_does_not_match_numeric_pre_filter(tmp_path):
    """EC-03: numeric values mapped via String(i) must NOT trigger rule F1."""
    findings = _run_semgrep_on(FIXTURES / "safe" / "f1-csv-concat-numeric.ts", tmp_path)
    assert findings == [], (
        f"Rule F1 must NOT match numeric-mapped CSV (EC-03 pre-filter); "
        f"got {len(findings)} findings"
    )
