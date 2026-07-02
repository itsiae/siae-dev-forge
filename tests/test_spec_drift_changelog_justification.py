"""Guard: spec_drift NON deve hard-bloccare (drift_severity=high) una PR che
documenta esplicitamente i cambiamenti nella CHANGELOG per la versione corrente
(plugin.json) — BUG B documentato in hooks/review-evidence:84-87 ma non implementato.

False-positive tipico: spec_drift seleziona per mtime un design doc non correlato
(iCloud rimaterializza mtime), tutti i file risultano "unplanned" → high → hard-floor.
Se la PR bumpa la versione E la CHANGELOG ha una entry per quella versione, il drift
è giustificato → declassato ad advisory (medium), non blocca. Fix REQ-DF (over-blocking).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib.review_evidence import spec_drift


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _mk_plugin(tmp: Path, version: str) -> None:
    (tmp / ".claude-plugin").mkdir(exist_ok=True)
    (tmp / ".claude-plugin" / "plugin.json").write_text(
        '{"name":"x","version":"%s"}\n' % version, encoding="utf-8"
    )


def test_changelog_justifies_current_version_true(tmp_path: Path) -> None:
    _mk_plugin(tmp_path, "1.100.0")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added / Fixed — cose (1.100.0)\n- x\n",
        encoding="utf-8",
    )
    assert spec_drift._changelog_justifies_current_version(tmp_path) is True


def test_changelog_no_entry_for_current_version_false(tmp_path: Path) -> None:
    _mk_plugin(tmp_path, "1.100.0")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added (1.99.0)\n- vecchio\n",
        encoding="utf-8",
    )
    assert spec_drift._changelog_justifies_current_version(tmp_path) is False


def test_missing_files_not_justified(tmp_path: Path) -> None:
    # Nessun plugin.json / CHANGELOG → non giustificato (fail-safe: resta enforced).
    assert spec_drift._changelog_justifies_current_version(tmp_path) is False


def test_high_drift_downgraded_when_changelog_justifies(tmp_path: Path, monkeypatch) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()

    # Design doc SENZA sezione ## File → nessun file "in plan" → tutti unplanned.
    dd = tmp_path / "docs" / "plans"
    dd.mkdir(parents=True)
    (dd / "x-design.md").write_text("# Design\n\nsolo prosa, nessuna sezione file.\n", encoding="utf-8")
    # >5 file impl → severity high.
    (tmp_path / "lib").mkdir()
    for i in range(6):
        (tmp_path / "lib" / f"mod{i}.py").write_text("x = 1\n", encoding="utf-8")
    _mk_plugin(tmp_path, "2.0.0")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n### Added (2.0.0)\n- documenta i cambiamenti\n", encoding="utf-8"
    )
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "head")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()

    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(dd / "x-design.md"))
    res = spec_drift.detect_drift(tmp_path, base, head)
    assert res is not None
    # >5 unplanned → sarebbe "high", ma la CHANGELOG giustifica la versione corrente.
    assert res["drift_severity"] != "high", res
    assert res.get("drift_justified_by_changelog") is True, res


def test_high_drift_stays_high_without_changelog_justification(tmp_path: Path, monkeypatch) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "base")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()

    dd = tmp_path / "docs" / "plans"
    dd.mkdir(parents=True)
    (dd / "x-design.md").write_text("# Design\n\nsolo prosa.\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    for i in range(6):
        (tmp_path / "lib" / f"mod{i}.py").write_text("x = 1\n", encoding="utf-8")
    _mk_plugin(tmp_path, "2.0.0")
    # CHANGELOG NON documenta 2.0.0 → drift resta high (nessun downgrade).
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n### Added (1.0.0)\n- vecchio\n", encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-m", "head")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True
    ).stdout.strip()

    monkeypatch.setenv("DEVFORGE_EVIDENCE_DESIGN_DOC", str(dd / "x-design.md"))
    res = spec_drift.detect_drift(tmp_path, base, head)
    assert res is not None
    assert res["drift_severity"] == "high", res
    assert not res.get("drift_justified_by_changelog"), res
