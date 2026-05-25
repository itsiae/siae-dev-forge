"""Tests for collector orchestrator."""
import json
import subprocess
from pathlib import Path

from lib.review_evidence.collector import orchestrate
from lib.review_evidence.registry import register, registry


def _init_git_repo(path: Path) -> None:
    """Init a fake git repo with macOS-safe gpgsign disabled."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "x@x"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=path, check=True)
    subprocess.run(["git", "config", "tag.gpgsign", "false"], cwd=path, check=True)
    (path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


class _FakeCollector:
    name = "fake"

    def is_applicable(self, repo_root):
        return True

    def collect(self, repo_root, base_ref, head_ref):
        return {
            "stack": "fake",
            "coverage": {"overall_pct": 90.0, "delta_vs_base": 0.0, "per_file": [], "source": "local:fake"},
            "lint": {"errors": 0, "warnings": 0, "findings": [], "source": "local:fake"},
            "complexity": {"max_cyclomatic": 3, "files_over_threshold": [], "source": "local:fake"},
        }


def test_orchestrate_writes_valid_evidence(tmp_path, monkeypatch):
    # Set _AUTOLOADED so autoload does not re-import real collectors and wipe our fake
    import lib.review_evidence.collector as _coll_mod
    _coll_mod._AUTOLOADED = True
    registry.clear()
    register(_FakeCollector())
    out = tmp_path / "ev.json"
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)

    code = orchestrate(sha="abc", base="main", dirty=False, out_path=out, repo_root=tmp_path)
    assert code == 0
    data = json.loads(out.read_text())
    # v2 bump: writer now emits "2.0" (scoring extension).
    assert data["schema_version"] == "2.0"
    assert data["sha"] == "abc"
    assert "fake" in data["stack_detected"]
    assert data["metrics"]["coverage"]["overall_pct"] == 90.0
    assert data["verdict"]["block"] is False


def test_orchestrate_aggregates_block_verdict(tmp_path, monkeypatch):
    class _BadCollector(_FakeCollector):
        def collect(self, *a, **kw):
            d = super().collect(*a, **kw)
            d["lint"] = {"errors": 5, "warnings": 0, "findings": [], "source": "local:fake"}
            return d

    import lib.review_evidence.collector as _coll_mod
    _coll_mod._AUTOLOADED = True
    registry.clear()
    register(_BadCollector())
    out = tmp_path / "ev.json"
    monkeypatch.chdir(tmp_path)
    _init_git_repo(tmp_path)

    code = orchestrate(sha="def", base="main", dirty=False, out_path=out, repo_root=tmp_path)
    assert code == 0
    data = json.loads(out.read_text())
    assert data["verdict"]["block"] is True
    assert any("lint_errors" in r for r in data["verdict"]["block_reasons"])
