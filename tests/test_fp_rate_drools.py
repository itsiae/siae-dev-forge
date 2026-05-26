"""Wave 1 follow-up task-14+15:
- FP rate measurement tool (ADR-005a)
- Drools .drl PR-gate review check (ADR-007)
"""
from __future__ import annotations



from lib.review_evidence.tools.fp_rate import (
    is_false_positive_marker,
    measure_fp_rate,
    threshold_decision,
)
from lib.review_evidence.drools_check import (
    DROOLS_REVIEW_LABEL,
    check_drools_review,
)


# ---------------------------------------------------------------------------
# FP measurement tool
# ---------------------------------------------------------------------------

def test_threshold_decisions():
    """ADR-005a thresholds: <5% PROMOTE, 5-10% RETRY, >=10% REWORK."""
    assert threshold_decision(0.03) == "PROMOTE"
    assert threshold_decision(0.07) == "RETRY"
    assert threshold_decision(0.15) == "REWORK"
    assert threshold_decision(0.0) == "PROMOTE"
    assert threshold_decision(0.099) == "RETRY"


def test_is_false_positive_marker():
    """Marker FP = nosemgrep con reason=false-positive*."""
    assert is_false_positive_marker(
        "// nosemgrep: siae.x reason=false-positive expires=2026-09-01"
    )
    assert is_false_positive_marker(
        "// nosemgrep: siae.x reason=false-positive-confirmed expires=2026-09-01"
    )
    assert not is_false_positive_marker(
        "// nosemgrep: siae.x reason=fix-pending SDLC-1234 expires=2026-09-01"
    )
    assert not is_false_positive_marker("// some other comment")
    assert not is_false_positive_marker("")


def test_measure_fp_rate_with_findings(tmp_path):
    """FP rate = (suppressed + nosemgrep_fp) / total."""
    findings = [
        {"check_id": "siae.x", "path": "src/a.ts", "extra": {"severity": "WARNING"}}
    ] * 10

    suppressions_file = tmp_path / "supp.yaml"
    suppressions_file.write_text("suppressions: []")

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "fp1.ts").write_text(
        "// nosemgrep: siae.x reason=false-positive expires=2026-09-01\nfoo();\n"
    )

    report = measure_fp_rate(
        rule_id="siae.x",
        findings=findings,
        suppressions_file=suppressions_file,
        scan_root=tmp_path,
    )
    assert report.rule_id == "siae.x"
    assert report.n_findings == 10
    assert report.n_nosemgrep_fp == 1
    assert 0.0 <= report.fp_rate <= 1.0
    j = report.to_dict()
    assert "fp_rate" in j and isinstance(j["fp_rate"], float)


def test_measure_fp_rate_zero_findings(tmp_path):
    """No findings → fp_rate=0.0 (no divisione per zero)."""
    suppressions_file = tmp_path / "supp.yaml"
    suppressions_file.write_text("suppressions: []")
    report = measure_fp_rate(
        rule_id="siae.x",
        findings=[],
        suppressions_file=suppressions_file,
        scan_root=tmp_path,
    )
    assert report.n_findings == 0
    assert report.fp_rate == 0.0


# ---------------------------------------------------------------------------
# Drools PR-gate review check
# ---------------------------------------------------------------------------

def test_no_drl_files_check_ok(tmp_path):
    """Nessun .drl modificato → ok, no warning."""
    py_file = tmp_path / "x.py"
    py_file.write_text("print(1)")
    r = check_drools_review(modified_files=[py_file], pr_labels=[])
    assert r.ok and r.method == "no-drools-files"


def test_form_a_label_accepted(tmp_path):
    """Form A: PR label drools-security-reviewed valida."""
    drl = tmp_path / "rule.drl"
    drl.write_text("rule \"x\" when then end")
    r = check_drools_review(
        modified_files=[drl], pr_labels=[DROOLS_REVIEW_LABEL]
    )
    assert r.ok and r.method == "form-a-label"


def test_form_b_header_accepted(tmp_path):
    """Form B: file header drools-security-reviewed con Jira + email + date."""
    drl = tmp_path / "rule.drl"
    drl.write_text(
        "// drools-security-reviewed: SDLC-1234 by:lorenzo.detomasi@siae.it on:2026-05-19\n"
        "rule \"x\" when then end\n"
    )
    r = check_drools_review(modified_files=[drl], pr_labels=[])
    assert r.ok and r.method == "form-b-header"


def test_missing_form_emits_warning_not_block(tmp_path):
    """ADR-007 + goal 'no block': missing form → WARNING NON BLOCK."""
    drl = tmp_path / "rule.drl"
    drl.write_text("rule \"x\" when then end")
    r = check_drools_review(modified_files=[drl], pr_labels=[])
    assert not r.ok
    assert "WARNING" in r.message
    assert DROOLS_REVIEW_LABEL in r.message


def test_form_b_malformed_header_rejected(tmp_path):
    """Form B header senza Jira ref / email valido → rifiutato."""
    drl = tmp_path / "rule.drl"
    drl.write_text(
        "// drools-security-reviewed: not-jira\nrule \"x\" end\n"
    )
    r = check_drools_review(modified_files=[drl], pr_labels=[])
    assert not r.ok


def test_form_b_non_siae_email_rejected(tmp_path):
    """Form B header con email non @siae.it → rifiutato."""
    drl = tmp_path / "rule.drl"
    drl.write_text(
        "// drools-security-reviewed: SDLC-1234 by:external@gmail.com on:2026-05-19\n"
        "rule \"x\" end\n"
    )
    r = check_drools_review(modified_files=[drl], pr_labels=[])
    assert not r.ok
