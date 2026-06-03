"""Tests for SIAE Semgrep suppression engine (Layer 3 — Wave 1 follow-up task-11+12+13)."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from lib.review_evidence.suppression import (
    Suppression,
    SuppressionEngine,
    SuppressionStatus,
    apply_suppressions,
    load_suppressions,
)
from lib.review_evidence.suppression_validator import (
    ValidationError,
    validate_suppressions_yaml,
)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _supp_yaml(tmp_path, future_days=30, past_days=1, soon_days=10):
    f = tmp_path / "supp.yaml"
    future = (date.today() + timedelta(days=future_days)).isoformat()
    past = (date.today() - timedelta(days=past_days)).isoformat()
    soon = (date.today() + timedelta(days=soon_days)).isoformat()
    f.write_text(f"""
suppressions:
  - rule_id: siae.authz-tenant.ts.dao-missing-tenant-filter
    path_glob: "**/dao/audit_log*.ts"
    reason: "Globale by-design ARCH-2026-05-12 confermato review-arch"
    owner: lorenzo.detomasi@siae.it
    expires_at: "{future}"
  - rule_id: siae.formula-injection.ts.csv-row-join-naive
    path_glob: "**/legacy/*.ts"
    reason: "Legacy refactor in SDLC-9999 entro Q3"
    owner: lorenzo.detomasi@siae.it
    expires_at: "{past}"
  - rule_id: siae.jwt.ts.jwt-in-localstorage
    path_glob: "**/preview/*.ts"
    reason: "Preview environment SDLC-8888 fix entro release Q4"
    owner: lorenzo.detomasi@siae.it
    expires_at: "{soon}"
""")
    return f


def test_load_suppressions(tmp_path):
    f = _supp_yaml(tmp_path)
    suppressions = load_suppressions(f)
    assert len(suppressions) == 3
    assert all(isinstance(s, Suppression) for s in suppressions)
    assert suppressions[0].rule_id == "siae.authz-tenant.ts.dao-missing-tenant-filter"


def test_load_suppressions_empty_or_missing(tmp_path):
    empty = tmp_path / "empty.yaml"
    empty.write_text("suppressions: []")
    assert load_suppressions(empty) == []
    nonexist = tmp_path / "nonexist.yaml"
    assert load_suppressions(nonexist) == []


def test_drop_finding_when_valid_suppression(tmp_path):
    findings = [
        {"check_id": "siae.authz-tenant.ts.dao-missing-tenant-filter",
         "path": "src/dao/audit_log_dao.ts", "extra": {"severity": "WARNING"}},
    ]
    engine = SuppressionEngine.from_file(_supp_yaml(tmp_path))
    result = apply_suppressions(findings, engine)
    assert len(result.kept) == 0
    assert len(result.dropped) == 1
    assert result.dropped[0].status == SuppressionStatus.APPLIED


def test_expired_suppression_keeps_finding_and_warns(tmp_path):
    findings = [
        {"check_id": "siae.formula-injection.ts.csv-row-join-naive",
         "path": "src/legacy/old_export.ts", "extra": {"severity": "WARNING"}},
    ]
    engine = SuppressionEngine.from_file(_supp_yaml(tmp_path))
    result = apply_suppressions(findings, engine)
    assert len(result.kept) == 1
    assert any("expired" in w.lower() for w in result.warnings)


def test_expiring_soon_drops_but_warns(tmp_path):
    findings = [
        {"check_id": "siae.jwt.ts.jwt-in-localstorage",
         "path": "src/preview/login.ts", "extra": {"severity": "WARNING"}},
    ]
    engine = SuppressionEngine.from_file(_supp_yaml(tmp_path))
    result = apply_suppressions(findings, engine)
    assert len(result.dropped) == 1
    assert result.dropped[0].status == SuppressionStatus.EXPIRING_SOON
    assert any("expir" in w.lower() for w in result.warnings)


def test_finding_no_path_match_kept(tmp_path):
    findings = [
        {"check_id": "siae.authz-tenant.ts.dao-missing-tenant-filter",
         "path": "src/dao/report_dao.ts",  # NOT audit_log path
         "extra": {"severity": "WARNING"}},
    ]
    engine = SuppressionEngine.from_file(_supp_yaml(tmp_path))
    result = apply_suppressions(findings, engine)
    assert len(result.kept) == 1
    assert len(result.dropped) == 0


# ---------------------------------------------------------------------------
# Schema validator (ADR-009)
# ---------------------------------------------------------------------------

def _valid_entry_yaml(tmp_path, **overrides):
    """Build a valid suppressions.yaml + apply overrides."""
    defaults = dict(
        rule_id="siae.authz-tenant.ts.dao-missing-tenant-filter",
        path_glob="**/dao/audit_log*.ts",
        reason="Tabella audit globale by-design ARCH-2026-05-12 confermato",
        owner="lorenzo.detomasi@siae.it",
        expires_at=(date.today() + timedelta(days=30)).isoformat(),
    )
    defaults.update(overrides)
    f = tmp_path / "supp.yaml"
    f.write_text(
        f"""suppressions:
  - rule_id: {defaults["rule_id"]}
    path_glob: "{defaults["path_glob"]}"
    reason: "{defaults["reason"]}"
    owner: {defaults["owner"]}
    expires_at: "{defaults["expires_at"]}"
"""
    )
    return f


def test_validator_accepts_well_formed(tmp_path):
    f = _valid_entry_yaml(tmp_path)
    validate_suppressions_yaml(f)  # no raise


def test_validator_rejects_catch_all_path_glob(tmp_path):
    """ADR-009 EC-35: path_glob solo ** rifiutato."""
    f = _valid_entry_yaml(tmp_path, path_glob="**")
    with pytest.raises(ValidationError, match=r"(?i)catch-all"):
        validate_suppressions_yaml(f)


def test_validator_rejects_short_reason(tmp_path):
    """ADR-009: reason >=30 char."""
    f = _valid_entry_yaml(tmp_path, reason="TODO fix later")
    with pytest.raises(ValidationError, match=r"(?i)reason"):
        validate_suppressions_yaml(f)


def test_validator_rejects_no_jira_ref(tmp_path):
    """ADR-009: reason deve contenere ref Jira [A-Z]+-[0-9]+."""
    f = _valid_entry_yaml(tmp_path, reason="Long enough reason but without ticket ref at all whatsoever today")
    with pytest.raises(ValidationError, match=r"(?i)jira|ticket"):
        validate_suppressions_yaml(f)


def test_validator_rejects_expires_too_far(tmp_path):
    """ADR-009: expires_at <=90gg."""
    f = _valid_entry_yaml(tmp_path, expires_at=(date.today() + timedelta(days=200)).isoformat())
    with pytest.raises(ValidationError, match=r"(?i)expires|90"):
        validate_suppressions_yaml(f)


def test_validator_rejects_non_siae_email(tmp_path):
    """ADR-009: owner deve matchare @siae.it."""
    f = _valid_entry_yaml(tmp_path, owner="external@gmail.com")
    with pytest.raises(ValidationError, match=r"(?i)owner|siae\.it"):
        validate_suppressions_yaml(f)


def test_validator_rejects_past_expires_at(tmp_path):
    """expires_at non può essere passato."""
    f = _valid_entry_yaml(tmp_path, expires_at=(date.today() - timedelta(days=5)).isoformat())
    with pytest.raises(ValidationError, match=r"(?i)past|expired"):
        validate_suppressions_yaml(f)


def test_validator_handles_missing_file_gracefully(tmp_path):
    """Empty / missing suppressions file → no error."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("suppressions: []")
    validate_suppressions_yaml(empty)
