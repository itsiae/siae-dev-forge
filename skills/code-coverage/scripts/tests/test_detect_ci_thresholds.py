import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "detect_ci_thresholds.py"


def _run(repo: Path) -> dict:
    out = subprocess.run([sys.executable, str(SCRIPT), str(repo)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _wf(repo: Path, name: str, content: str):
    d = repo / ".github" / "workflows"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(content, encoding="utf-8")


def test_literal_thresholds(tmp_path):
    _wf(tmp_path, "CI.yaml", """
jobs:
  test:
    uses: itsiae/siae-gh-actions/.github/workflows/JS_CI.yaml@v3.0.0
    with:
      working-directory: modules/service/lambda-handler
      COVERAGE_BRANCHES: 70
      COVERAGE_LINES: 80
""")
    out = _run(tmp_path)
    assert out["COVERAGE_BRANCHES"] == 70
    assert out["COVERAGE_LINES"] == 80
    assert out["working_directory_issues"] == []


def test_working_directory_issue_detected(tmp_path):
    # stack.json con manifest_root sub-workspace
    cc = tmp_path / ".code-coverage"
    cc.mkdir()
    (cc / "stack.json").write_text(json.dumps({"manifest_root": "modules/service/lambda-handler"}))
    _wf(tmp_path, "CI.yaml", """
jobs:
  test:
    uses: itsiae/siae-gh-actions/.github/workflows/JS_CI.yaml@v3.0.0
    with:
      node-version: 20
""")
    out = _run(tmp_path)
    assert any("CI.yaml" in iss for iss in out["working_directory_issues"])


def test_no_workflows_dir(tmp_path):
    out = _run(tmp_path)
    assert out == {"working_directory_issues": []} or out.get("working_directory_issues") == []


# ── M-1: argv guard ──────────────────────────────────────────────────────────

def test_no_args_exits_zero_with_valid_json():
    """M-1: invocazione senza argomenti → exit 0 + JSON valido con working_directory_issues."""
    out = subprocess.run([sys.executable, str(SCRIPT)],
                         capture_output=True, text=True)
    assert out.returncode == 0, f"Expected exit 0, got {out.returncode}. stderr={out.stderr}"
    data = json.loads(out.stdout)
    assert "working_directory_issues" in data
    assert isinstance(data["working_directory_issues"], list)


# ── M-2: cross-file max ───────────────────────────────────────────────────────

def test_multifile_keeps_max_threshold(tmp_path):
    """M-2: quando più file CI hanno COVERAGE_LINES diversi, vince il massimo."""
    _wf(tmp_path, "CI.yaml", """
jobs:
  test:
    env:
      COVERAGE_LINES: 80
""")
    _wf(tmp_path, "test.yml", """
jobs:
  test:
    env:
      COVERAGE_LINES: 60
""")
    out = _run(tmp_path)
    # Deve riportare 80 (max), non 60 (sovrascrittura last-wins)
    assert out["COVERAGE_LINES"] == 80, (
        f"Expected COVERAGE_LINES=80 (max across files), got {out.get('COVERAGE_LINES')}"
    )
