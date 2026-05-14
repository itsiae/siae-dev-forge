"""Tests for ts-unused-exports runner (TS dead exports)."""
from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from lib.review_evidence.runners.ts_unused_exports import TsUnusedExportsRunner

FIX = Path(__file__).parent / "fixtures" / "review-evidence"


def _write_pkg_json(tmp_path: Path, with_ts: bool = True) -> None:
    payload = {"name": "demo"}
    if with_ts:
        payload["devDependencies"] = {"typescript": "^5.0.0"}
    (tmp_path / "package.json").write_text(json.dumps(payload))


def test_is_applicable_ts_repo(tmp_path):
    _write_pkg_json(tmp_path, with_ts=True)
    (tmp_path / "main.ts").write_text("export const x = 1;\n")
    assert TsUnusedExportsRunner().is_applicable(tmp_path) is True


def test_not_applicable_no_typescript_dep(tmp_path):
    _write_pkg_json(tmp_path, with_ts=False)
    (tmp_path / "main.ts").write_text("export const x = 1;\n")
    assert TsUnusedExportsRunner().is_applicable(tmp_path) is False


def test_not_applicable_no_ts_files(tmp_path):
    _write_pkg_json(tmp_path, with_ts=True)
    assert TsUnusedExportsRunner().is_applicable(tmp_path) is False


def test_run_counts_each_export_as_dead_code_block(tmp_path):
    _write_pkg_json(tmp_path, with_ts=True)
    (tmp_path / "main.ts").write_text("export const x = 1;\n")
    out = (FIX / "ts_unused_exports_output.txt").read_text()

    def fake_run(cmd, **kw):
        # ts-unused-exports exits 1 when findings present
        return CompletedProcess(cmd, 1, stdout=out, stderr="")

    with patch(
        "lib.review_evidence.runners.ts_unused_exports.subprocess.run",
        side_effect=fake_run,
    ):
        result = TsUnusedExportsRunner().run(tmp_path)
    assert result is not None
    # fixture: 2 + 1 + 3 = 6 exports across 3 files
    assert result.dead_code_blocks == 6


def test_run_missing_tool_returns_none(tmp_path):
    _write_pkg_json(tmp_path, with_ts=True)
    (tmp_path / "main.ts").write_text("export const x = 1;\n")

    def fake_run(cmd, **kw):
        raise FileNotFoundError("npx")

    with patch(
        "lib.review_evidence.runners.ts_unused_exports.subprocess.run",
        side_effect=fake_run,
    ):
        assert TsUnusedExportsRunner().run(tmp_path) is None
