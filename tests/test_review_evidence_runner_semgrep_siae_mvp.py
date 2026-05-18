"""MVP test for Semgrep runner SIAE registry inclusion (Wave 1 task-09 minimal).

Verifica che il runner Semgrep di default includa SIA il community ruleset (`auto`)
SIA la SIAE custom rules registry, in modo che le regole SIAE Wave 1 siano
attive immediatamente senza override env var.

Wave 1 design ref: docs/plans/2026-05-18-security-hook-vulnerability-prevention-design.md
"""
from __future__ import annotations

from pathlib import Path

from lib.review_evidence.runners.semgrep import _DEFAULT_CONFIG


REPO_ROOT = Path(__file__).parents[1]


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
