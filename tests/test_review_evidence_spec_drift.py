"""Tests for spec-drift detector."""
from pathlib import Path
from unittest.mock import patch


from lib.review_evidence.spec_drift import (
    extract_files_from_design,
    detect_drift,
    severity,
)

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def test_extract_files_strips_code_fence_and_quote():
    content = (FIX / "design_with_codefences.md").read_text()
    files = extract_files_from_design(content)
    assert "src/feature/new_module.py" in files
    assert "lib/helper.py" in files
    assert "tests/test_new_module.py" in files
    # Negatives
    assert "src/legacy/old_module.py" not in files  # in Contesto (not allowlist)
    assert "src/quote_only.py" not in files  # blockquote stripped
    assert "src/fake_path" not in files  # code-fence stripped
    assert "lib/fake_module" not in files  # code-fence stripped


def test_severity_none():
    assert severity([]) == "none"


def test_severity_low_same_dir():
    in_plan = ["src/feature/a.py"]
    unplanned = ["src/feature/b.py"]
    assert severity(unplanned, in_plan=in_plan) == "low"


def test_severity_medium_different_dir():
    in_plan = ["src/feature/a.py"]
    unplanned = ["src/other/b.py", "src/other/c.py", "src/yet_another/d.py"]
    assert severity(unplanned, in_plan=in_plan) == "medium"


def test_severity_high_many_files():
    in_plan = ["src/feature/a.py"]
    unplanned = [f"src/other/f{i}.py" for i in range(7)]
    assert severity(unplanned, in_plan=in_plan) == "high"


def test_detect_drift_uses_env_override(tmp_path, monkeypatch):
    design = tmp_path / "design.md"
    design.write_text("## File coinvolti\n- `src/a.py`\n")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(design))

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "git" and "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="src/a.py\nsrc/b.py\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    assert result["design_doc_path"] == str(design)
    assert "src/a.py" in result["files_in_plan"]
    assert "src/b.py" in result["unplanned_files"]
    assert result["drift_severity"] in ("low", "medium")


def test_detect_drift_auto_picks_latest_design(tmp_path, monkeypatch):
    plans_dir = tmp_path / "docs" / "plans"
    plans_dir.mkdir(parents=True)
    old_design = plans_dir / "2026-01-01-old-design.md"
    old_design.write_text("## File coinvolti\n- `src/old.py`\n")
    import time
    time.sleep(0.05)
    new_design = plans_dir / "2026-05-12-new-design.md"
    new_design.write_text("## File coinvolti\n- `src/new.py`\n")

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="src/new.py\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    monkeypatch.delenv("DEVFORGE_EVIDENCE_DESIGN_DOC", raising=False)
    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    assert result["design_doc_path"].endswith("2026-05-12-new-design.md")
    assert "src/new.py" in result["files_in_plan"]
    assert result["unplanned_files"] == []
    assert result["drift_severity"] == "none"


def test_detect_drift_returns_none_when_no_design(tmp_path):
    result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")
    assert result is None


def test_detect_drift_treats_docs_plans_changes_as_planning_artifacts(
    tmp_path, monkeypatch
):
    """Regression: commits that only touch ``docs/plans/`` are planning
    artifacts (the plan itself), not implementation drift.

    Before the fix: a docs-only commit with 6+ files under ``docs/plans/``
    flagged ``drift_severity:high`` and blocked the commit (e.g. brainstorming
    + writing-plans output: design.md + overview.md + task-NN.md files).
    """
    design = tmp_path / "design.md"
    design.write_text("## File coinvolti\n- `src/feature/a.py`\n")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(design))

    docs_plans_files = [
        "docs/plans/2026-05-14-new-feature-design.md",
        "docs/plans/2026-05-14-new-feature/overview.md",
        "docs/plans/2026-05-14-new-feature/task-01.md",
        "docs/plans/2026-05-14-new-feature/task-02.md",
        "docs/plans/2026-05-14-new-feature/task-03.md",
        "docs/plans/2026-05-14-new-feature/task-04.md",
        "docs/plans/2026-05-14-new-feature/task-05.md",
        "docs/plans/2026-05-14-new-feature/task-06.md",
    ]

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "git" and "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="\n".join(docs_plans_files) + "\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    # files_changed must remain raw for transparency
    assert result["files_changed"] == docs_plans_files
    # but unplanned excludes planning artifacts (docs/plans/*)
    assert result["unplanned_files"] == []
    assert result["drift_severity"] == "none"


def test_detect_drift_mixed_impl_and_planning_only_counts_impl(
    tmp_path, monkeypatch
):
    """Mixed commit: impl files outside ``docs/plans/`` still count toward
    drift. The planning-artifact filter must NOT mask real implementation
    drift hidden alongside a docs/plans update.
    """
    design = tmp_path / "design.md"
    design.write_text("## File coinvolti\n- `src/feature/a.py`\n")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(design))

    changed = [
        "docs/plans/2026-05-14-feature-design.md",  # planning — excluded
        "docs/plans/2026-05-14-feature/task-01.md",  # planning — excluded
        "src/feature/a.py",  # in plan
        "src/feature/b.py",  # IMPL drift — must be flagged
    ]

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "git" and "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="\n".join(changed) + "\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    assert result["files_changed"] == changed
    assert result["unplanned_files"] == ["src/feature/b.py"]
    # 1 unplanned, same parent dir as in_plan → low (severity helper logic)
    assert result["drift_severity"] == "low"


def test_detect_drift_docs_outside_plans_still_counted(tmp_path, monkeypatch):
    """``docs/hld/``, ``docs/api/`` are implementation artifacts (not plans).
    They must NOT be filtered by the planning-artifact rule.
    """
    design = tmp_path / "design.md"
    design.write_text("## File coinvolti\n- `src/feature/a.py`\n")
    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(design))

    changed = [
        "docs/hld/service-x.md",
        "docs/api/openapi.yaml",
        "docs/runbook.md",
    ]

    def fake_run(cmd, **kwargs):
        from subprocess import CompletedProcess
        if cmd[0] == "git" and "diff" in cmd:
            return CompletedProcess(cmd, 0, stdout="\n".join(changed) + "\n", stderr="")
        return CompletedProcess(cmd, 1, stdout="", stderr="")

    with patch("lib.review_evidence.spec_drift.subprocess.run", side_effect=fake_run):
        result = detect_drift(repo_root=tmp_path, base="main", head="HEAD")

    # All 3 are unplanned (outside docs/plans/ — they ARE impl artifacts).
    assert set(result["unplanned_files"]) == set(changed)
