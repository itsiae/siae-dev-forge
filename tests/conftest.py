"""Root-level pytest conftest for siae-devforge.

Mutuated from `tests/zero-loss/conftest.py` pattern (sys.path injection)
but scoped to the entire `tests/` tree so any test_*.py can do:

    from lib.review_evidence.schema import Evidence

without per-suite conftest.

Co-exists with `tests/zero-loss/conftest.py` which has its own fixtures.
This file MUST stay minimal — suite-specific helpers belong to suite-local
conftest.

Naming convention:
- `lib/review_evidence/` (underscore) is a Python module
- `.claude/review-evidence/` (dash) is a filesystem dir (not Python)
- Both are intentional; this conftest only handles the Python path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def repo_root() -> Path:
    """Path to repository root (where lib/ and hooks/ live)."""
    return REPO_ROOT


@pytest.fixture
def review_evidence_fixtures_dir() -> Path:
    """Path to tests/fixtures/review-evidence/."""
    return REPO_ROOT / "tests" / "fixtures" / "review-evidence"
