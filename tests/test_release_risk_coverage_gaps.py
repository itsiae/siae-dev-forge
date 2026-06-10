"""Coverage-gap tests for lib/release_risk — in-process (no subprocess) so
pytest --cov can trace them. Complements the e2e subprocess tests in
test_release_risk_cli.py, which exercise the same paths but are coverage-blind.
"""
from __future__ import annotations

import argparse
import json
import runpy
import subprocess
import sys
import types
from pathlib import Path

import pytest

import lib.release_risk.cache as cache_mod
from lib.release_risk.cache import put as cache_put
from lib.release_risk.cli import (
    assess, main as cli_main,
    _get_main_sha, _get_head_sha, _extract_jira_tickets,
    _ci_config_check, _coverage_pct, _baseline_fetcher_factory,
    _emit_activity_event,
)
from lib.release_risk.coverage_src import (
    _from_evidence_file, _from_jacoco_xml, _from_lcov_info,
)
from lib.release_risk.genesis import build_genesis_info, extract_merge_commits
from lib.release_risk.regression_delta import (
    resolve_prev_release_main_sha, count_test_disabled_deleted,
)
from lib.release_risk.renderer import render_scorecard, write_scorecard
from lib.release_risk.schema import (
    ReleaseRiskReport, ScoreCard, GenesisInfo, CriterionResult,
)
from lib.release_risk.security_state import _load_runners


REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = REPO_ROOT / "lib" / "release_risk" / "cli.py"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True,
                   capture_output=True, text=True)


@pytest.fixture
def git_repo_with_origin(tmp_path):
    """Repo git con refs origin/main + origin/release/* simulate via update-ref."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README.md").write_text("# t")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init SPORT-123")
    r = subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path,
                       capture_output=True, text=True)
    if r.returncode != 0:
        _git(tmp_path, "checkout", "-q", "main")
    (tmp_path / "feature.txt").write_text("x")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "feat: x DIRITTI-9")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                   cwd=tmp_path, text=True).strip()
    first = subprocess.check_output(["git", "rev-list", "--max-parents=0", "HEAD"],
                                    cwd=tmp_path, text=True).strip()
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", first)
    _git(tmp_path, "update-ref", "refs/remotes/origin/release/1.0.0", head)
    return tmp_path


def _make_report(**overrides):
    kwargs = dict(
        service="sport-test-service", release_branch="release/1.0.0",
        target_branch="main", diff_hash="abc123def456",
        baseline_main_sha="1a2b3c4d", diff_summary={"files_changed": 1},
        identification={"version": "1.0.0"},
        genesis=GenesisInfo(merge_commits=[]),
        criteria=[], scorecard=ScoreCard(
            total_score=2, level="LOW", decision="GO", decision_rationale="r"),
        generated_at="2026-06-10T10:00:00Z", output_path="docs/releases/x.md",
    )
    kwargs.update(overrides)
    return ReleaseRiskReport(**kwargs)


def _assess_args(repo, diff_files_path=None, diff_content_path=None, **overrides):
    ns = argparse.Namespace(
        repo_root=str(repo), branch="release/1.0.0", service="sport-test-service",
        diff_files=diff_files_path, diff_content=diff_content_path,
        version="1.0.0", owner="team-x", release_date="2026-06-10",
        user_impact_ge_50=True, genesis_confirmed=None, genesis_declined=False,
        trigger="manual", no_cache=True, kg_data_file=None,
    )
    for k, v in overrides.items():
        setattr(ns, k, v)
    return ns


# --- cli.assess in-process ---------------------------------------------------

def test_assess_in_process_full_run(git_repo_with_origin, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    df = tmp_path / "df.txt"
    df.write_text("pom.xml\nsrc/App.java\n")
    dc = tmp_path / "dc.txt"
    dc.write_text("+ <dependency>x</dependency>\n")
    rc = assess(_assess_args(git_repo_with_origin, str(df), str(dc)))
    assert rc == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["cached"] is False
    assert out["level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert list((git_repo_with_origin / "docs" / "releases").glob("*.md"))


def test_assess_cache_hit_second_run(git_repo_with_origin, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    args = _assess_args(git_repo_with_origin, no_cache=False,
                        genesis_confirmed="feat/a", genesis_declined=True)
    assert assess(args) == 0
    assert assess(args) == 0
    last = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert last["cached"] is True


def test_cli_main_in_process(git_repo_with_origin, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(sys, "argv", [
        "lib.release_risk", "assess",
        "--repo-root", str(git_repo_with_origin),
        "--branch", "release/1.0.0", "--service", "test-service",
        "--user-impact-ge-50", "true", "--trigger", "manual", "--no-cache",
    ])
    assert cli_main() == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "score" in out


def test_cli_main_unknown_cmd_returns_1(monkeypatch):
    """Guard difensivo: cmd diverso da assess → return 1 (irraggiungibile da CLI
    reale perché il subparser è required con un solo comando)."""
    monkeypatch.setattr(argparse.ArgumentParser, "parse_args",
                        lambda self: argparse.Namespace(cmd="unknown"))
    assert cli_main() == 1


def test_cli_dunder_main_guard(monkeypatch):
    """Esegue cli.py come __main__ via runpy (copre il blocco if __name__)."""
    monkeypatch.setattr(sys, "argv", ["cli.py", "assess", "--help"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(CLI_PATH), run_name="__main__")
    assert exc.value.code == 0


def test_package_dunder_main(monkeypatch):
    """Esegue python -m lib.release_risk in-process (copre __main__.py)."""
    monkeypatch.setattr(sys, "argv", ["lib.release_risk", "assess", "--help"])
    monkeypatch.delitem(sys.modules, "lib.release_risk.__main__", raising=False)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib.release_risk", run_name="__main__")
    assert exc.value.code == 0


# --- cli helpers --------------------------------------------------------------

def test_get_main_sha_success_and_failure(git_repo_with_origin, tmp_path):
    assert _get_main_sha(git_repo_with_origin)
    assert _get_main_sha(tmp_path / "not-a-repo") is None


def test_get_head_sha_success_and_failure(git_repo_with_origin, tmp_path):
    assert len(_get_head_sha(git_repo_with_origin)) == 40
    assert _get_head_sha(tmp_path / "not-a-repo") == "unknown"


def test_extract_jira_tickets(git_repo_with_origin, tmp_path):
    tickets = _extract_jira_tickets(git_repo_with_origin, "release/1.0.0")
    assert "DIRITTI-9" in tickets
    assert _extract_jira_tickets(tmp_path / "not-a-repo", "release/1.0.0") == []


def test_ci_config_check_variants(tmp_path):
    assert _ci_config_check(tmp_path) == (False, False)
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "build.yml").write_text("jobs:\n  build:\n    steps: []\n")
    assert _ci_config_check(tmp_path) == (True, False)
    (wf / "e2e.yml").write_text("jobs:\n  e2e-tests:\n    steps: []\n")
    assert _ci_config_check(tmp_path) == (True, True)


def test_coverage_pct_parsing():
    ok = CriterionResult(id=11, name="c", status="NO", weight=2,
                         evidence=["overall_pct=85.5", "threshold=70.0"])
    assert _coverage_pct(ok) == 85.5
    bad = CriterionResult(id=11, name="c", status="NO", weight=2,
                          evidence=["overall_pct=not-a-number"])
    assert _coverage_pct(bad) is None
    empty = CriterionResult(id=11, name="c", status="REQUIRES_INPUT", weight=2)
    assert _coverage_pct(empty) is None


def test_baseline_fetcher_factory(monkeypatch):
    fake = types.ModuleType("lib.review_evidence.baseline_cache")
    fake.fetch_baseline = lambda service, sha: {"service": service, "sha": sha}
    monkeypatch.setitem(sys.modules, "lib.review_evidence.baseline_cache", fake)
    fetcher = _baseline_fetcher_factory("svc")
    assert fetcher("abc") == {"service": "svc", "sha": "abc"}

    def boom(service, sha):
        raise RuntimeError("s3 down")
    fake.fetch_baseline = boom
    assert fetcher("abc") is None


def test_emit_activity_event_paths(monkeypatch, tmp_path):
    report = _make_report()
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    _emit_activity_event(report)  # early return, no plugin root

    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "nonexistent"))
    _emit_activity_event(report)  # bash fails, check=False → no raise

    def boom(*a, **k):
        raise OSError("no bash")
    monkeypatch.setattr("lib.release_risk.cli.subprocess.run", boom)
    _emit_activity_event(report)  # except path → swallowed


# --- regression_delta success paths -------------------------------------------

@pytest.fixture
def repo_with_prev_release(tmp_path):
    """main contiene merge commit della release precedente release/0.9.0."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "AppTest.java").write_text("class AppTest {}")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    r = subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path,
                       capture_output=True, text=True)
    if r.returncode != 0:
        _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "checkout", "-q", "-b", "release/0.9.0")
    (tmp_path / "f1.txt").write_text("v0.9")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "release 0.9 content")
    _git(tmp_path, "checkout", "-q", "main")
    _git(tmp_path, "merge", "--no-ff", "-q", "-m",
         "Merge branch 'release/0.9.0'", "release/0.9.0")
    prev_merge_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True).strip()
    # post-merge: disabilita un test + cancella un test file
    (tmp_path / "src" / "OtherTest.java").write_text("@Disabled\nclass OtherTest {}")
    _git(tmp_path, "rm", "-q", "src/AppTest.java")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "regress tests")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                   cwd=tmp_path, text=True).strip()
    rel_sha = subprocess.check_output(["git", "rev-parse", "release/0.9.0"],
                                      cwd=tmp_path, text=True).strip()
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", head)
    _git(tmp_path, "update-ref", "refs/remotes/origin/release/0.9.0", rel_sha)
    _git(tmp_path, "update-ref", "refs/remotes/origin/release/1.0.0", head)
    return tmp_path, prev_merge_sha


def test_resolve_prev_release_finds_merge_commit(repo_with_prev_release):
    repo, prev_merge_sha = repo_with_prev_release
    sha = resolve_prev_release_main_sha("release/1.0.0", repo)
    assert sha == prev_merge_sha


def test_resolve_prev_release_no_merge_in_main(tmp_path):
    """Ref release precedente esiste ma nessun merge commit in main → None."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "f").write_text("x")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                   cwd=tmp_path, text=True).strip()
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", head)
    _git(tmp_path, "update-ref", "refs/remotes/origin/release/0.9.0", head)
    assert resolve_prev_release_main_sha("release/1.0.0", tmp_path) is None


def test_count_test_disabled_deleted(repo_with_prev_release):
    repo, prev_merge_sha = repo_with_prev_release
    disabled, deleted = count_test_disabled_deleted(repo, prev_merge_sha)
    assert disabled == 1   # "@Disabled" aggiunto in OtherTest.java
    assert deleted == 1    # src/AppTest.java cancellato


def test_count_test_disabled_deleted_error_path(tmp_path):
    # directory esistente ma non-git → CalledProcessError → (0, 0)
    assert count_test_disabled_deleted(tmp_path, "deadbeef") == (0, 0)


# --- security_state._load_runners ----------------------------------------------

def test_load_runners_imports_available():
    runners = _load_runners()
    names = {type(r).__name__ for r in runners}
    assert {"PipAuditRunner", "NpmAuditRunner"} <= names


def test_load_runners_import_error_fallback(monkeypatch):
    monkeypatch.setitem(sys.modules, "lib.review_evidence.runners.pip_audit", None)
    monkeypatch.setitem(sys.modules, "lib.review_evidence.runners.npm_audit", None)
    assert _load_runners() == []


# --- renderer gaps --------------------------------------------------------------

def test_render_genesis_unexpected_features():
    genesis = GenesisInfo(
        merge_commits=[{"sha": "a", "subject": "s", "feature_branch": "feat/x"}],
        user_confirmed=["feat/y"], unexpected=["feat/x"], anomaly=True,
    )
    md = render_scorecard(_make_report(genesis=genesis))
    assert "Feature non attese (anomaly)" in md
    assert "feat/x" in md


def test_render_criteria_table_with_truncation_and_empty_evidence():
    criteria = [
        CriterionResult(id=1, name="DB change", status="YES", weight=3,
                        evidence=["x" * 100]),
        CriterionResult(id=10, name="Feature flag", status="YES", weight=-1),
    ]
    md = render_scorecard(_make_report(criteria=criteria))
    assert "..." in md          # evidence > 80 char troncata
    assert "| — |" in md        # evidence vuota → em dash
    assert "✅ YES" in md       # peso negativo: YES = mitigation
    assert "❌ YES" in md       # peso positivo: YES = risk


def test_write_scorecard_success(tmp_path):
    out = tmp_path / "docs" / "releases" / "scorecard.md"
    assert write_scorecard(_make_report(), out, "<!-- release-risk:abc -->") is True
    content = out.read_text()
    assert content.startswith("<!-- release-risk:abc -->")
    assert "Release Risk Scorecard" in content


def test_write_scorecard_failure_returns_false(tmp_path):
    target = tmp_path / "scorecard.md"
    target.mkdir()  # write su directory → exception → False
    assert write_scorecard(_make_report(), target) is False


# --- genesis gaps -----------------------------------------------------------------

def test_build_genesis_info_branches():
    assert build_genesis_info([]).no_merges_found is True
    commits = [{"sha": "a", "subject": "s", "feature_branch": "feat/x"}]
    assert build_genesis_info(commits, declined=True).declined is True
    # nessuna conferma esplicita → fallback declined
    assert build_genesis_info(commits, user_confirmed=None).declined is True


def test_extract_merge_commits_skips_malformed_lines(tmp_path, monkeypatch):
    fake = subprocess.CompletedProcess(
        args=[], returncode=0,
        stdout="malformed-line-no-pipe\nabc123|Merge branch 'feat/x'\n", stderr="")
    monkeypatch.setattr("lib.release_risk.genesis.subprocess.run",
                        lambda *a, **k: fake)
    commits = extract_merge_commits(tmp_path, "release/1.0.0")
    assert len(commits) == 1
    assert commits[0]["feature_branch"] == "feat/x"


# --- coverage_src error paths --------------------------------------------------------

def test_evidence_file_malformed_json(tmp_path):
    p = tmp_path / ".claude" / "review-evidence"
    p.mkdir(parents=True)
    (p / "abc.json").write_text("{not-json")
    assert _from_evidence_file(tmp_path, "abc") is None


def test_jacoco_xml_no_counter_match(tmp_path):
    cov = tmp_path / "coverage"
    cov.mkdir()
    (cov / "jacoco.xml").write_text("<report></report>")
    assert _from_jacoco_xml(tmp_path) is None


def test_jacoco_xml_read_error(tmp_path):
    cov = tmp_path / "coverage"
    cov.mkdir()
    (cov / "jacoco.xml").mkdir()  # directory → read_text raises → None
    assert _from_jacoco_xml(tmp_path) is None


def test_lcov_info_malformed(tmp_path):
    cov = tmp_path / "coverage"
    cov.mkdir()
    (cov / "lcov.info").write_text("LH:abc\nLF:def\n")
    assert _from_lcov_info(tmp_path) is None


# --- cache.put failure ------------------------------------------------------------------

def test_cache_put_failure_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(cache_mod, "CACHE_DIR", tmp_path / "cache")

    def boom(src, dst):
        raise OSError("disk full")
    monkeypatch.setattr(cache_mod.os, "replace", boom)
    assert cache_put("release/1.0.0", "abc123", "1a2b3c4d", _make_report()) is False
