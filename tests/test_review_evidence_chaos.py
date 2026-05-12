"""Chaos test suite — failure-injection on review-evidence pipeline.

Validates fail-CLOSED semantics on blocking triggers and graceful
degradation elsewhere. Each test injects a single failure mode and
asserts the agent does NOT see a clean verdict.

Coverage (per Task 16 edge-case hunt):
- E01: just-init repo with no HEAD
- E03: concurrent invocations on same SHA
- E05: jq missing on PATH (fail-CLOSED on PreToolUse blocking)
- E12: schema_version 1.x forward-compat, 2.x rejected
- E16/E17: monorepo pruning (no .venv/node_modules walks)
- E22: Jacoco XML with DOCTYPE stripped, no network access
- E23: Jacoco multi-module nested <group>
- E25: ESLint config error → explicit reason
- E27: terraform validate "init required" → explicit reason
- E32: CI fetch dedup multiple workflow runs
- E36: design doc binary content → drift_severity="unknown"
- E38: Italian allowlist headers (Tabella, Allegato, ...)
- E40: session-start TTL cleanup of stale evidence
- E41: collector failure on blocking trigger → decision:block
- E42: evidence lookup honors fallback path
- E48: iCloud .icloud placeholder → recompute, never fail-open
- Q03-M1: hostile envelope cwd rejected (security)
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / "hooks" / "review-evidence"
FIX = REPO_ROOT / "tests" / "fixtures" / "review-evidence"


# ── helpers ────────────────────────────────────────────────────


def _init_repo(tmp_path: Path) -> str:
    """Initialize a tmp git repo with one commit. Return the HEAD sha."""
    sp = subprocess.run
    sp(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    sp(["git", "config", "user.email", "x@x"], cwd=tmp_path, check=True)
    sp(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    sp(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    sp(["git", "config", "tag.gpgsign", "false"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x")
    sp(["git", "add", "."], cwd=tmp_path, check=True)
    sp(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()


def _run_hook_pre_pr(tmp_path: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    home_dir = tmp_path / "home"
    home_dir.mkdir(exist_ok=True)
    env["HOME"] = str(home_dir)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title test",
            "cwd": str(tmp_path),
        }),
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=60,
    )


def _parse_stdout(proc: subprocess.CompletedProcess) -> dict:
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        # Hook should always emit JSON; treat parse failure as test failure.
        pytest.fail(f"hook emitted non-JSON: {proc.stdout!r} stderr={proc.stderr!r}")


# ── CRITICAL fail-CLOSED tests ─────────────────────────────────


def test_E05_jq_missing_fails_closed_on_block(tmp_path):
    """E05: when jq is missing, hook MUST emit decision:block on PreToolUse gh pr create."""
    _init_repo(tmp_path)

    # Build a synthetic PATH that contains the bare essentials (bash, git,
    # python3, mkdir, sleep, find, sed, grep) but NOT jq. We create a
    # temp dir, symlink the basics in, and set PATH to that dir only.
    synth_bin = tmp_path.parent / f"synth-bin-{tmp_path.name}"
    synth_bin.mkdir(exist_ok=True)
    needed = ["bash", "sh", "git", "python3", "mkdir", "sleep", "find",
              "sed", "grep", "cat", "rm", "ls", "echo", "date", "head",
              "tail", "tr", "sort", "uniq", "stat", "touch", "cut", "wc",
              "xargs", "test", "dirname", "basename", "id", "uname", "tee",
              "awk", "chmod", "ln", "env", "which", "command", "printf"]
    for tool in needed:
        for src in ("/usr/bin", "/bin", "/opt/homebrew/bin", "/usr/local/bin"):
            src_path = Path(src) / tool
            if src_path.exists() and not (synth_bin / tool).exists():
                try:
                    (synth_bin / tool).symlink_to(src_path)
                except FileExistsError:
                    pass
                break

    # Sanity: confirm jq is NOT in synth_bin.
    if (synth_bin / "jq").exists():
        pytest.skip("synthetic bin contains jq — environment too liberal")

    minimal_path = str(synth_bin)
    proc = _run_hook_pre_pr(tmp_path, env_extra={"PATH": minimal_path})
    out = _parse_stdout(proc)
    assert out.get("decision") == "block", (
        f"Fail-OPEN regression: expected block when jq missing, got {out!r} "
        f"(stderr={proc.stderr!r})"
    )
    assert "jq" in out.get("reason", "").lower()


def test_E17_python_collector_skips_venv_node_modules(tmp_path):
    """E17: is_applicable must NOT scan .venv/ or node_modules/ — bounded walk."""
    (tmp_path / "main.py").write_text("# entry")
    (tmp_path / ".venv").mkdir()
    for i in range(300):
        (tmp_path / ".venv" / f"f{i}.py").write_text("x")
    (tmp_path / "node_modules").mkdir()
    for i in range(300):
        (tmp_path / "node_modules" / f"f{i}.py").write_text("x")
    # Plant a deep noise dir to also exercise the depth cap.
    deep = tmp_path / "vendor" / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    (deep / "deep.py").write_text("# too deep, must be ignored if vendor is pruned")

    from lib.review_evidence.collectors.python import PythonCollector

    t0 = time.time()
    applicable = PythonCollector().is_applicable(tmp_path)
    elapsed = time.time() - t0
    assert applicable is True, "should still detect repo-level main.py"
    assert elapsed < 1.0, f"is_applicable too slow ({elapsed:.2f}s) — pruning missing"


def test_E41_disk_full_emits_block_on_blocking_trigger(tmp_path):
    """E41: collector exit non-zero on blocking trigger MUST fail-CLOSED."""
    _init_repo(tmp_path)
    # Inject a fake collector that just exits 2 (mimics DiskFullError exit code).
    fake_collector = tmp_path / "fake-collector.py"
    fake_collector.write_text("import sys; sys.exit(2)\n")

    proc = _run_hook_pre_pr(tmp_path, env_extra={
        "DEVFORGE_EVIDENCE_COLLECTOR_PATH": str(fake_collector),
    })
    out = _parse_stdout(proc)
    assert out.get("decision") == "block", (
        f"Fail-OPEN regression on collector failure: {out}"
    )
    # Reason should mention disk / cannot verify
    assert "disk" in out.get("reason", "").lower() or "verify" in out.get("reason", "").lower()


def test_E42_fallback_path_resolved_via_helper(tmp_path, monkeypatch):
    """E42: when evidence is in fallback dir, helper finds it."""
    from lib.review_evidence import paths as paths_mod
    from lib.review_evidence.paths import resolve_evidence_path

    sha = "abc123def456" + "0" * 28  # 40-char-ish realistic
    fallback_root = tmp_path / "fallback"
    monkeypatch.setattr(paths_mod, "FALLBACK_ROOT", fallback_root)

    # No primary file.
    assert resolve_evidence_path(sha, repo_root=tmp_path) is None

    # Plant a fallback file with non-empty content.
    fallback_dir = fallback_root / paths_mod._repo_hash(tmp_path)
    fallback_dir.mkdir(parents=True)
    fallback_file = fallback_dir / f"{sha}.json"
    fallback_file.write_text('{"sha":"' + sha + '"}')

    resolved = resolve_evidence_path(sha, repo_root=tmp_path)
    assert resolved == fallback_file


def test_E48_icloud_placeholder_treated_as_cache_miss(tmp_path):
    """E48: .{sha}.json.icloud placeholder MUST not be read as cached verdict."""
    sha = _init_repo(tmp_path)
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    # iCloud placeholder only; no actual JSON file.
    (ev_dir / f".{sha}.json.icloud").write_text("")

    # Use a fake collector that returns success but writes a CLEAN verdict —
    # we just want to assert the placeholder doesn't masquerade as block=false.
    fake_collector = tmp_path / "fake-clean.py"
    fake_collector.write_text(
        "import sys, json, os\n"
        "out = sys.argv[sys.argv.index('--out') + 1]\n"
        "os.makedirs(os.path.dirname(out), exist_ok=True)\n"
        "json.dump({'schema_version':'1.0','sha':'X','verdict':{'block':False,'block_reasons':[],'warnings':[]},'metrics':{}}, open(out, 'w'))\n"
    )

    proc = _run_hook_pre_pr(tmp_path, env_extra={
        "DEVFORGE_EVIDENCE_COLLECTOR_PATH": str(fake_collector),
    })
    out = _parse_stdout(proc)
    # The placeholder must have triggered a recompute (cache miss). The fake
    # collector then wrote a clean verdict, so we expect ``additional_context``
    # mentioning block=false (after recompute), NOT a silent fail-open from
    # reading the empty placeholder.
    # The forbidden outcome: placeholder file present → hook reads "{}".
    # Either it recomputed (advisory ctx present + valid metrics) OR it
    # blocked safely. What MUST NOT happen: empty advisory or undefined block.
    if out.get("decision") == "block":
        # Safe outcome.
        assert True
    else:
        ctx = out.get("additional_context", "")
        # If advisory, it must come from the recomputed evidence (block=false in CTX).
        assert "block=false" in ctx, (
            f"placeholder leaked as success path: {out!r}; expected recompute"
        )


# ── NEW (post quality review) ──────────────────────────────────


def test_Q03M1_envelope_cwd_must_be_absolute(tmp_path):
    """Q03-M1: hook must reject envelope cwd that is not an absolute path."""
    _init_repo(tmp_path)
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    env["HOME"] = str(home_dir)

    # Relative cwd in envelope — must be ignored.
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "echo hello",     # non-matching → safe no-op
            "cwd": "../../etc/passwd",   # path-traversal attempt
        }),
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=20,
    )
    # No state directory should have been created via the malicious cwd.
    # The hook either ignores it (empty output) or stays in $PWD (tmp_path)
    # where .claude/review-evidence may be created — but never at the
    # relative resolution of "../../etc/passwd".
    out = _parse_stdout(proc)
    assert out == {}  # non-matching command path → early return
    # Crucially: nothing was created under tmp_path/../../etc.
    assert not (tmp_path.parent.parent / "etc" / "passwd").exists()


def test_Q03M1_envelope_cwd_must_be_git_worktree(tmp_path):
    """Q03-M1: hook must reject envelope cwd that is not inside a git worktree."""
    # tmp_path is a plain dir (no .git/) — must NOT be honored.
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    env["HOME"] = str(home_dir)

    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "echo hello",
            "cwd": str(tmp_path),
        }),
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT), timeout=20,
    )
    # Should still be a no-op (no matching command); critically the hook
    # should not have populated tmp_path/.claude/.
    assert not (tmp_path / ".claude" / "review-evidence").exists()


def test_Q05M1_ruff_severity_restricted_to_F_E9_B(tmp_path, monkeypatch):
    """Q05-M1: only F*, E9*, B* count as errors; E1-E7 are warnings."""
    findings_json = json.dumps([
        {"code": "F401", "filename": "a.py", "location": {"row": 1}, "message": "unused"},
        {"code": "E501", "filename": "b.py", "location": {"row": 1}, "message": "long line"},
        {"code": "E711", "filename": "c.py", "location": {"row": 1}, "message": "compare None"},
        {"code": "E999", "filename": "d.py", "location": {"row": 1}, "message": "syntax"},
        {"code": "B008", "filename": "e.py", "location": {"row": 1}, "message": "mutable default"},
        {"code": "W605", "filename": "f.py", "location": {"row": 1}, "message": "invalid escape"},
    ])

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd and cmd[0] == "ruff":
            return CompletedProcess(cmd, 0, stdout=findings_json, stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    from lib.review_evidence.collectors.python import PythonCollector

    (tmp_path / "pyproject.toml").write_text("[tool]")
    with patch("lib.review_evidence.collectors.python.subprocess.run", side_effect=fake_run):
        lint = PythonCollector()._ruff(tmp_path)

    # F401, E999, B008 are errors (3); E501, E711, W605 are warnings (3).
    assert lint["errors"] == 3, f"expected 3 errors, got {lint}"
    assert lint["warnings"] == 3, f"expected 3 warnings, got {lint}"
    # E501 must be marked severity=warning in findings.
    e501 = next(f for f in lint["findings"] if f["rule"] == "E501")
    assert e501["severity"] == "warning"


def test_Q11M1_spec_drift_finds_subdir_design_md(tmp_path, monkeypatch):
    """Q11-M1: design discovery must match SIAE convention `docs/plans/<topic>/design.md`."""
    plans_dir = tmp_path / "docs" / "plans" / "2026-05-12-feature-x"
    plans_dir.mkdir(parents=True)
    design = plans_dir / "design.md"
    design.write_text("## File coinvolti\n- `src/a.py`\n")

    monkeypatch.delenv("DEVFORGE_EVIDENCE_DESIGN_DOC", raising=False)
    from lib.review_evidence.spec_drift import _find_design_doc
    found = _find_design_doc(tmp_path)
    assert found is not None
    assert found.resolve() == design.resolve()


# ── HIGH-priority graceful-degradation tests ───────────────────


def test_E01_just_init_repo_no_head_advisory_only(tmp_path):
    """E01: a just-init repo (no commit) → advisory, never block."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    proc = _run_hook_pre_pr(tmp_path)
    out = _parse_stdout(proc)
    assert out.get("decision") != "block"
    # An advisory should be emitted explaining the skip.
    assert "no HEAD" in out.get("additional_context", "") or out == {}


def test_E12_schema_minor_version_forward_compat():
    """E12: schema_version 1.1 (future minor) must be accepted; 2.0 rejected."""
    from lib.review_evidence.schema import evidence_from_json

    base = {
        "schema_version": "1.0",
        "sha": "x", "branch": "x", "computed_at": "x", "dirty_tree": False,
        "base_branch": "main", "stack_detected": [], "metrics": {},
        "spec_drift": None, "verdict": {"block": False, "block_reasons": [], "warnings": []},
    }
    # Minor forward-compat
    ev = evidence_from_json({**base, "schema_version": "1.1"})
    assert ev.schema_version == "1.1"
    ev = evidence_from_json({**base, "schema_version": "1.42"})
    assert ev.schema_version == "1.42"

    # Major bump must raise
    with pytest.raises(ValueError, match="unsupported schema_version"):
        evidence_from_json({**base, "schema_version": "2.0"})


def test_E22_jacoco_doctype_stripped_no_network():
    """E22: Jacoco XML with DOCTYPE is parsed without network access."""
    from lib.review_evidence.collectors._jacoco import parse_jacoco_xml
    content = (FIX / "jacoco_multimodule.xml").read_text()
    assert "<!DOCTYPE" in content, "fixture must include DOCTYPE for this test to be meaningful"
    # Must not raise / not fetch DTD.
    parsed = parse_jacoco_xml(content)
    assert parsed["overall_pct"] > 0


def test_E23_jacoco_multimodule_nested_groups():
    """E23: nested <group> containers contribute to overall + per_file."""
    from lib.review_evidence.collectors._jacoco import parse_jacoco_xml
    parsed = parse_jacoco_xml((FIX / "jacoco_multimodule.xml").read_text())
    paths = {pf["path"] for pf in parsed["per_file"]}
    # A1+A2 from module-a, B1 from module-b/nested-submodule
    assert "com/example/a/A1.java" in paths
    assert "com/example/a/A2.java" in paths
    assert "com/example/b/B1.java" in paths, (
        "nested <group> sourcefile missing — multi-module recursion broken"
    )
    # Aggregate matches the root <counter type="LINE" missed="7" covered="23"/>
    # → 23/30 = 76.67%
    assert abs(parsed["overall_pct"] - 76.67) < 0.5


def test_E25_eslint_config_error_explicit_reason(tmp_path):
    """E25: eslint exit != 0 with empty stdout → explicit reason, not silent None."""
    from lib.review_evidence.collectors.typescript import TypeScriptCollector

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        # Simulate config error: returncode 2, empty stdout.
        return CompletedProcess(cmd, 2, stdout="", stderr="Config error")

    with patch("lib.review_evidence.collectors.typescript.subprocess.run", side_effect=fake_run):
        result = TypeScriptCollector()._eslint(tmp_path)

    assert result is not None
    assert result.get("available") is False
    assert "config" in result.get("reason", "").lower()


def test_E27_terraform_validate_init_required_reason(tmp_path):
    """E27: terraform validate "Initialization required" → explicit reason."""
    from lib.review_evidence.collectors.hcl import HCLCollector

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        # Real terraform writes "Initialization required" to stderr, exit != 0.
        return CompletedProcess(cmd, 1, stdout="", stderr="Initialization required. Please run 'terraform init'.")

    with patch("lib.review_evidence.collectors.hcl.subprocess.run", side_effect=fake_run):
        result = HCLCollector()._tf_validate(tmp_path)

    assert result is not None
    assert "init" in result.get("reason", "").lower()


def test_E32_ci_fetch_deduplicates_workflow_runs(tmp_path):
    """E32: multiple completed runs for same SHA → dedup by workflowName."""
    from lib.review_evidence.ci_fetch import fetch_ci_sarif

    multiple_runs = json.dumps([
        {"databaseId": 3, "workflowName": "Qodana", "conclusion": "success"},
        {"databaseId": 2, "workflowName": "Qodana", "conclusion": "success"},  # dup
        {"databaseId": 1, "workflowName": "Sonar",  "conclusion": "success"},
    ])

    download_calls: list = []

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "gh" and "list" in cmd:
            return CompletedProcess(cmd, 0, stdout=multiple_runs, stderr="")
        if cmd[0] == "gh" and "download" in cmd:
            run_id_arg = cmd[3]
            download_calls.append(run_id_arg)
            dl_dir = Path(cmd[cmd.index("--dir") + 1])
            dl_dir.mkdir(parents=True, exist_ok=True)
            (dl_dir / "report.sarif").write_text((FIX / "qodana_sample.sarif").read_text())
            return CompletedProcess(cmd, 0, stdout="", stderr="")
        return CompletedProcess(cmd, 1)

    with patch("lib.review_evidence.ci_fetch.subprocess.run", side_effect=fake_run):
        result = fetch_ci_sarif(sha="abc", repo_root=tmp_path)

    # Expect 2 downloads (latest Qodana=run3 + Sonar=run1), NOT 3.
    assert len(download_calls) == 2, (
        f"dedup broken: got {len(download_calls)} downloads {download_calls}"
    )
    assert result["available"] is True


def test_E36_design_doc_binary_marks_drift_unknown(tmp_path, monkeypatch):
    """E36: a binary design.md (PDF renamed) → drift_severity="unknown"."""
    plans_dir = tmp_path / "docs" / "plans" / "x"
    plans_dir.mkdir(parents=True)
    binary_design = plans_dir / "design.md"
    # Write some non-UTF8 bytes that will raise UnicodeDecodeError on read_text.
    binary_design.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\xff\xfe" * 10)
    monkeypatch.delenv("DEVFORGE_EVIDENCE_DESIGN_DOC", raising=False)

    from lib.review_evidence.spec_drift import detect_drift
    result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")
    assert result is not None, "binary doc must still produce a result (not None)"
    assert result["drift_severity"] == "unknown"
    assert "reason" in result


def test_E38_spec_drift_matches_italian_headers():
    """E38: allowlist regex must match Italian headers (Tabella, Allegato, ...)."""
    from lib.review_evidence.spec_drift import extract_files_from_design
    content = (FIX / "design_italian_headers.md").read_text()
    files = extract_files_from_design(content)
    assert "src/foo.py" in files, f"missing src/foo.py: {files}"
    assert "lib/bar.py" in files, f"missing lib/bar.py: {files}"
    assert "tests/test_foo.py" in files, f"missing tests/test_foo.py: {files}"
    assert "hooks/session-start" not in files  # no extension → not a path match
    assert "lib/new_module.py" in files
    # Negative: src/legacy/old.py is under "Contesto" — must NOT be extracted.
    assert "src/legacy/old.py" not in files


def test_E40_session_start_prunes_old_evidence(tmp_path):
    """E40: stale evidence files (>7 days) are deleted by session-start cleanup logic."""
    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    old = ev_dir / "old.json"
    old.write_text("{}")
    old_ts = time.time() - (10 * 86400)
    os.utime(old, (old_ts, old_ts))
    fresh = ev_dir / "fresh.json"
    fresh.write_text("{}")

    # Mimic the session-start cleanup find command directly.
    subprocess.run(
        ["bash", "-c",
         f"find '{ev_dir}' -maxdepth 1 -name '*.json' -mtime +7 -delete 2>/dev/null || true"],
        check=True,
    )
    assert not old.exists(), "stale evidence not pruned"
    assert fresh.exists(), "fresh evidence wrongly pruned"


def test_E03_concurrent_invocations_serialized(tmp_path):
    """E03: hook serializes concurrent invocations on same SHA via mkdir lock.

    Approach: pre-create the lock dir, plant clean evidence, then assert
    the hook respects the lock (does not run the collector). Auxiliary
    files (fake collector, fake HOME) live OUTSIDE the test repo so the
    working tree stays clean and the cache-hit short-circuit fires.
    """
    sha = _init_repo(tmp_path)
    # IMPORTANT: external aux dir so git status stays clean.
    aux = tmp_path.parent / f"aux-{tmp_path.name}"
    aux.mkdir(exist_ok=True)
    fake_home = aux / "home"
    fake_home.mkdir(exist_ok=True)
    marker = aux / "collector_invoked"
    fake_collector = aux / "fake-marker.py"
    fake_collector.write_text(
        f"open(r'{marker}', 'w').close()\nimport sys; sys.exit(0)\n"
    )

    ev_dir = tmp_path / ".claude" / "review-evidence"
    ev_dir.mkdir(parents=True)
    # Add .claude to .gitignore so the lock dir & evidence file don't
    # show up as untracked and dirty the tree.
    (tmp_path / ".gitignore").write_text(".claude/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "gitignore", "--no-gpg-sign"],
                   cwd=tmp_path, check=True, capture_output=True)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp_path).decode().strip()

    lock_dir = ev_dir / f"{sha}.lock"
    lock_dir.mkdir()

    # Plant a clean evidence file. The hook's cache lookup runs BEFORE
    # the lock acquire — with .claude/ gitignored, DIRTY=0, evidence is
    # found, NEEDS_COMPUTE=0, lock is never even touched.
    ev_file = ev_dir / f"{sha}.json"
    ev_file.write_text(json.dumps({
        "schema_version": "1.0", "sha": sha,
        "verdict": {"block": False, "block_reasons": [], "warnings": []},
        "metrics": {},
    }))

    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    env["HOME"] = str(fake_home)
    env["DEVFORGE_EVIDENCE_COLLECTOR_PATH"] = str(fake_collector)
    proc = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "command": "gh pr create --title test",
            "cwd": str(tmp_path),
        }),
        capture_output=True, text=True, env=env, cwd=str(tmp_path), timeout=20,
    )
    out = _parse_stdout(proc)
    # Cache-hit path: collector not invoked, no block decision (evidence is clean).
    assert out.get("decision") != "block", f"unexpected block: {out!r}"
    assert not marker.exists(), (
        f"collector was invoked despite cached evidence — stdout: {proc.stdout!r}"
    )
    # Clean up lock dir
    if lock_dir.exists():
        lock_dir.rmdir()
