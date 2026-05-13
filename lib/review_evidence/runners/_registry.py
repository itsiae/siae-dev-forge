"""Plug-in registry for OSS runners (security, quality, deps, etc)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Runner(Protocol):
    name: str
    category: str  # "security" | "quality" | "deps" | "secret"

    def is_applicable(self, repo_root: Path) -> bool: ...
    def run(self, repo_root: Path) -> Any: ...


registry: list[Runner] = []


def register(runner: Runner) -> None:
    registry.append(runner)


def applicable(repo_root: Path) -> list[Runner]:
    return [r for r in registry if r.is_applicable(repo_root)]
