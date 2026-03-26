"""Tests for check-branching.py — Branching Strategy Compliance Check."""

import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest


# --- Test helpers ---

def make_gh_response(data):
    """Create a mock subprocess.CompletedProcess with JSON stdout."""
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 0
    result.stdout = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
    result.stderr = ""
    return result


def make_gh_failure(stderr="error"):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = 1
    result.stdout = ""
    result.stderr = stderr
    return result


# --- Phase 1: current repo checks ---

class TestCheckDefaultBranch:
    """Control A: default branch must be main."""

    def test_violation_when_default_branch_is_not_main(self):
        from check_branching import check_default_branch
        with patch("check_branching.run_gh", return_value="develop"):
            result = check_default_branch("itsiae/my-repo")
        assert result == "develop"

    def test_compliant_when_default_branch_is_main(self):
        from check_branching import check_default_branch
        with patch("check_branching.run_gh", return_value="main"):
            result = check_default_branch("itsiae/my-repo")
        assert result == "main"

    def test_returns_none_on_gh_failure(self):
        from check_branching import check_default_branch
        with patch("check_branching.run_gh", return_value=None):
            result = check_default_branch("itsiae/my-repo")
        assert result is None


class TestCheckPRsTargetingMain:
    """Control B: only release/** can target main."""

    def test_returns_prs_list(self):
        from check_branching import check_prs_targeting_main
        prs = [
            {"number": 1, "title": "feat", "headRefName": "feature/foo"},
            {"number": 2, "title": "release", "headRefName": "release/1.0"},
        ]
        with patch("check_branching.run_gh", return_value=json.dumps(prs)):
            result = check_prs_targeting_main("itsiae/my-repo")
        assert len(result) == 2
        assert result[0]["headRefName"] == "feature/foo"

    def test_returns_empty_on_no_prs(self):
        from check_branching import check_prs_targeting_main
        with patch("check_branching.run_gh", return_value="[]"):
            result = check_prs_targeting_main("itsiae/my-repo")
        assert result == []

    def test_returns_empty_on_gh_failure(self):
        from check_branching import check_prs_targeting_main
        with patch("check_branching.run_gh", return_value=None):
            result = check_prs_targeting_main("itsiae/my-repo")
        assert result == []


class TestCheckRepo:
    """check_repo runs both controls independently and populates report."""

    def test_both_violations_detected_independently(self):
        from check_branching import check_repo, Report
        report = Report()
        prs = [{"number": 42, "title": "feat", "headRefName": "feature/bar"}]

        with patch("check_branching.check_default_branch", return_value="develop"), \
             patch("check_branching.check_prs_targeting_main", return_value=prs):
            check_repo("itsiae/test", "corrente", report)

        default_viols = [v for v in report.violations if v.kind == "default_branch"]
        pr_viols = [v for v in report.violations if v.kind == "pr_targets_main"]
        assert len(default_viols) == 1
        assert len(pr_viols) == 1

    def test_skips_already_checked_repo(self):
        from check_branching import check_repo, Report
        report = Report()
        report.repos_checked.add("itsiae/test")

        with patch("check_branching.check_default_branch") as mock_db:
            check_repo("itsiae/test", "corrente", report)
        mock_db.assert_not_called()

    def test_release_branch_is_compliant(self):
        from check_branching import check_repo, Report
        report = Report()
        prs = [{"number": 10, "title": "rel", "headRefName": "release/2.0"}]

        with patch("check_branching.check_default_branch", return_value="main"), \
             patch("check_branching.check_prs_targeting_main", return_value=prs):
            check_repo("itsiae/test", "corrente", report)

        assert len(report.violations) == 0
        assert len(report.compliant) == 1


# --- Report rendering ---

class TestRenderReport:
    """Report generation produces valid markdown."""

    def test_no_violations_shows_compliant_message(self):
        from check_branching import render_report, Report
        report = Report()
        report.current_repo = "itsiae/ok-repo"
        report.repos_checked.add("itsiae/ok-repo")
        md = render_report(report)
        assert "✅" in md
        assert "compliant" in md.lower()
        assert "VIOLAZIONI" not in md.split("### Sommario")[1].split("---")[0] or "**0 VIOLAZIONI**" in md

    def test_violations_appear_before_compliant(self):
        from check_branching import render_report, Report, Violation, CompliantPR
        report = Report()
        report.current_repo = "itsiae/bad"
        report.repos_checked.add("itsiae/bad")
        report.violations.append(Violation(
            repo="itsiae/bad", kind="pr_targets_main",
            detail="PR #1 from feature/x targets main",
            source="corrente", pr_number=1, branch="feature/x"
        ))
        report.compliant.append(CompliantPR(
            repo="itsiae/bad", pr_number=2, branch="release/1.0", target="main"
        ))
        md = render_report(report)
        viol_pos = md.index("VIOLAZIONI")
        compl_pos = md.index("PR compliant")
        assert viol_pos < compl_pos


# --- Review PRs classification ---

class TestCheckReviewPRs:
    """Phase 2: PR classification from review search."""

    def test_pr_targeting_main_from_feature_is_violation(self):
        from check_branching import check_review_prs, Report
        report = Report()
        check_review_prs("itsiae/svc", 5, "feature/x", "main", "review", report)
        assert len(report.violations) == 1
        assert report.violations[0].source == "review"

    def test_pr_targeting_main_from_release_is_compliant(self):
        from check_branching import check_review_prs, Report
        report = Report()
        check_review_prs("itsiae/svc", 5, "release/1.0", "main", "review", report)
        assert len(report.compliant) == 1

    def test_pr_not_targeting_main_is_exempt(self):
        from check_branching import check_review_prs, Report
        report = Report()
        check_review_prs("itsiae/svc", 5, "feature/x", "release/1.0", "review", report)
        assert len(report.exempt) == 1
