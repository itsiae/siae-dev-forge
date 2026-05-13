"""Tests for runners registry framework."""
from __future__ import annotations

from pathlib import Path

from lib.review_evidence.runners import _registry as R


def test_register_and_list():
    R.registry.clear()

    class FakeRunner:
        name = "fake"
        category = "security"

        def is_applicable(self, repo_root: Path) -> bool:
            return True

        def run(self, repo_root: Path):
            return {"critical": 0, "high": 0, "medium": 0, "low": 0}

    R.register(FakeRunner())
    assert len(R.registry) == 1
    assert R.registry[0].name == "fake"


def test_applicable_filters_inapplicable():
    R.registry.clear()

    class AlwaysFalse:
        name = "no-op"
        category = "security"

        def is_applicable(self, repo_root):
            return False

        def run(self, repo_root):
            return None

    class AlwaysTrue:
        name = "yes-op"
        category = "security"

        def is_applicable(self, repo_root):
            return True

        def run(self, repo_root):
            return {}

    R.register(AlwaysFalse())
    R.register(AlwaysTrue())
    applicable = R.applicable(Path("/tmp"))
    assert len(applicable) == 1
    assert applicable[0].name == "yes-op"
