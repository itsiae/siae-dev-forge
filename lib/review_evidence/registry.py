"""Plug-in registry for per-stack collectors."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Collector(Protocol):
    name: str

    def is_applicable(self, repo_root: Path) -> bool: ...
    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> dict[str, Any]: ...


registry: list[Collector] = []


def register(collector: Collector) -> None:
    registry.append(collector)


def applicable(repo_root: Path) -> list[Collector]:
    return [c for c in registry if c.is_applicable(repo_root)]
