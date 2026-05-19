"""Tests for skills/siae-codebase-map-tiered/scripts/anti-bloat-lint.py.

Validates the 5 anti-bloat lint rules and CLI behaviour described in
docs/plans/2026-05-19-tiered-claude-md/task-03-anti-bloat-lint-tdd.md.

Lint rules (advisory, never blocking — exit 0 always):
- line_count: file > 200 lines → WARN
- parent_overlap: > 70% textual match with parent CLAUDE.md → WARN
- placeholder: TBD/TODO/<...> in body → WARN
- missing_import: L2/L3 without `@<parent>/CLAUDE.md` import line → WARN
- empty_sections: `##` header with no content underneath → WARN

CLI:
    python3 anti-bloat-lint.py <file_or_dir> [--parent-context <parent_md>]

stdout: JSON (single object if file, JSON array if dir).
exit code: 0 always (advisory).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    REPO_ROOT
    / "skills"
    / "siae-codebase-map-tiered"
    / "scripts"
    / "anti-bloat-lint.py"
)
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "claude-md-samples"


def _import_module():
    """Import the lint script as a module so coverage tracks it in-process.

    The file uses a dash in its name, so a regular `import` won't work — we
    load it via importlib spec and cache the resulting module object.
    """
    spec = importlib.util.spec_from_file_location("anti_bloat_lint", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LINT = _import_module()


def _run_lint(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the lint script via the same Python interpreter."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _rules(payload: dict) -> set[str]:
    return {w["rule"] for w in payload.get("warnings", [])}


def test_lint_warns_on_bloated_file() -> None:
    """File > 200 lines → warnings contains rule 'line_count'."""
    result = _run_lint(str(FIXTURES / "bloated-l1.md"))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["lines"] > 200
    assert "line_count" in _rules(payload)


def test_lint_warns_on_parent_overlap() -> None:
    """L2 duplicate of parent → warning rule 'parent_overlap'."""
    result = _run_lint(
        str(FIXTURES / "duplicated-l2.md"),
        "--parent-context",
        str(FIXTURES / "lean-l1.md"),
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "parent_overlap" in _rules(payload), payload


def test_lint_clean_file_no_warnings() -> None:
    """Lean file <200 lines, no placeholder, no empty section → no warnings."""
    result = _run_lint(str(FIXTURES / "lean-l1.md"))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["warnings"] == [], payload
    assert payload["errors"] == []


def test_lint_dir_recursive(tmp_path: Path) -> None:
    """Lint on directory walks recursively and returns JSON array."""
    # Compose a small directory with 3 CLAUDE.md files
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "CLAUDE.md").write_text(
        (FIXTURES / "lean-l1.md").read_text(), encoding="utf-8"
    )
    (tmp_path / "a" / "CLAUDE.md").write_text(
        (FIXTURES / "bloated-l1.md").read_text(), encoding="utf-8"
    )
    (tmp_path / "b" / "CLAUDE.md").write_text(
        (FIXTURES / "duplicated-l2.md").read_text(), encoding="utf-8"
    )

    result = _run_lint(str(tmp_path))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert isinstance(payload, list), payload
    assert len(payload) == 3, payload
    files = {Path(entry["file"]).name for entry in payload}
    assert files == {"CLAUDE.md"}  # all 3 named CLAUDE.md, different dirs
    # bloated entry should have line_count warning
    bloated_entry = next(
        e for e in payload if "a/CLAUDE.md" in e["file"] or e["lines"] > 200
    )
    assert "line_count" in {w["rule"] for w in bloated_entry["warnings"]}


def test_lint_always_exit_zero(tmp_path: Path) -> None:
    """Advisory lint: exit code MUST be 0 even with multiple warnings."""
    # Synthetic file that triggers many rules at once
    polluted = tmp_path / "CLAUDE.md"
    body_lines = ["# Polluted\n"]
    body_lines.append("\n")
    body_lines.append("## Empty section\n")  # empty_sections trigger
    body_lines.append("\n")
    body_lines.append("## Placeholders\n")
    body_lines.append("TODO write me\n")  # placeholder TODO
    body_lines.append("TBD here\n")  # placeholder TBD
    body_lines.append("see <...> for details\n")  # placeholder <...>
    body_lines.append("\n")
    body_lines.append("## Filler\n")
    # Push line_count over 200
    body_lines.extend([f"line {i}\n" for i in range(220)])
    polluted.write_text("".join(body_lines), encoding="utf-8")

    result = _run_lint(str(polluted))
    assert result.returncode == 0, (
        f"lint must be advisory, exit=0 always. got {result.returncode}\n"
        f"stderr={result.stderr}"
    )
    payload = json.loads(result.stdout)
    rules = _rules(payload)
    # Sanity: at least 2 of the rules should have fired
    assert "line_count" in rules
    assert "placeholder" in rules


def test_lint_missing_file_does_not_crash(tmp_path: Path) -> None:
    """Defensive: missing target prints empty list and exits 0."""
    missing = tmp_path / "does-not-exist"
    result = _run_lint(str(missing))
    # Advisory: never crash the caller.
    assert result.returncode == 0
    # stdout should be valid JSON (null/[] or object with errors)
    payload = json.loads(result.stdout)
    assert isinstance(payload, (list, dict))


@pytest.mark.parametrize(
    "text,expected_rule",
    [
        ("## Header\n\n## Other\n", "empty_sections"),
        ("# title\n\nsee TODO\n", "placeholder"),
    ],
)
def test_lint_unit_rules_trigger(tmp_path: Path, text: str, expected_rule: str) -> None:
    """Parametric sanity check on individual rules."""
    f = tmp_path / "CLAUDE.md"
    f.write_text(text, encoding="utf-8")
    result = _run_lint(str(f))
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert expected_rule in _rules(payload), payload


# -- In-process unit tests (importlib) so coverage instrumentation tracks
# -- the lint script. Subprocess invocations above are end-to-end contract
# -- tests; these mirror them at the function-call level. See memory
# -- `feedback_pytest_cov_subprocess_blind`.


def test_unit_lint_file_clean(tmp_path: Path) -> None:
    payload = LINT.lint_file(FIXTURES / "lean-l1.md")
    assert payload["warnings"] == []
    assert payload["errors"] == []
    assert payload["lines"] > 0


def test_unit_lint_file_bloated() -> None:
    payload = LINT.lint_file(FIXTURES / "bloated-l1.md")
    assert payload["lines"] > LINT.LINE_COUNT_THRESHOLD
    rules = {w["rule"] for w in payload["warnings"]}
    assert "line_count" in rules


def test_unit_lint_file_parent_overlap() -> None:
    parent_text = (FIXTURES / "lean-l1.md").read_text(encoding="utf-8")
    payload = LINT.lint_file(FIXTURES / "duplicated-l2.md", parent_text=parent_text)
    rules = {w["rule"] for w in payload["warnings"]}
    assert "parent_overlap" in rules


def test_unit_lint_file_missing_import_when_parent_given(tmp_path: Path) -> None:
    """L2 file without `@parent/CLAUDE.md` import → missing_import warning."""
    child = tmp_path / "CLAUDE.md"
    child.write_text("# child\n\nsome content here\n", encoding="utf-8")
    payload = LINT.lint_file(child, parent_text="# parent\n\nshared content\n")
    rules = {w["rule"] for w in payload["warnings"]}
    assert "missing_import" in rules


def test_unit_lint_file_read_error(tmp_path: Path) -> None:
    """Unreadable file populates errors but does not raise."""
    payload = LINT.lint_file(tmp_path / "missing.md")
    assert payload["errors"], payload
    assert payload["errors"][0]["rule"] == "read_error"


def test_unit_lint_path_dir(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# root\n\ncontent\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "CLAUDE.md").write_text(
        "# sub\n\nmore content\n", encoding="utf-8"
    )
    result = LINT.lint_path(tmp_path)
    assert isinstance(result, list)
    assert len(result) == 2


def test_unit_lint_path_missing() -> None:
    """Non-existent target returns empty list, no exception."""
    assert LINT.lint_path(Path("/nonexistent/path/xyz")) == []


def test_unit_main_invokes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main() prints JSON and returns 0 regardless of warnings."""
    f = tmp_path / "CLAUDE.md"
    f.write_text("# t\n\nTODO fix later\n", encoding="utf-8")
    rc = LINT.main([str(f)])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "placeholder" in {w["rule"] for w in parsed["warnings"]}


def test_unit_main_with_parent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """main() honours --parent-context flag."""
    parent = tmp_path / "parent.md"
    parent.write_text(
        (FIXTURES / "lean-l1.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    child = tmp_path / "CLAUDE.md"
    child.write_text(
        (FIXTURES / "duplicated-l2.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    rc = LINT.main([str(child), "--parent-context", str(parent)])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "parent_overlap" in {w["rule"] for w in parsed["warnings"]}


def test_unit_main_parent_context_missing_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """--parent-context pointing at a non-existent file does not crash."""
    child = tmp_path / "CLAUDE.md"
    child.write_text("# child\n\ncontent\n", encoding="utf-8")
    rc = LINT.main([str(child), "--parent-context", str(tmp_path / "nope.md")])
    assert rc == 0
    # Should still print JSON.
    json.loads(capsys.readouterr().out)
