"""Pytest fixtures condivisi per siae-dev-analytics."""
import json
import sys
import pytest
from pathlib import Path

# Aggiungi scripts/ al sys.path per permettere import diretti (es. import compute_kpis)
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory fixtures con dati mock deterministici."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pr_data(fixtures_dir: Path) -> dict:
    """Sample GitHub PR data (5 PR, 3 dev)."""
    fixture = fixtures_dir / "github_api_response.json"
    if not fixture.exists():
        pytest.skip("fixture missing, run task-03 first")
    return json.loads(fixture.read_text())


@pytest.fixture
def sample_commit_data(fixtures_dir: Path) -> dict:
    """Sample commit data (50 commit cross-dev)."""
    fixture = fixtures_dir / "commits_sample.json"
    if not fixture.exists():
        pytest.skip("fixture missing, run task-03 first")
    return json.loads(fixture.read_text())
