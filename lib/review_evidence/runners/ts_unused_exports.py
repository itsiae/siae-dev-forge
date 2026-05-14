"""ts-unused-exports TypeScript dead exports runner.

Invokes ``npx --no-install ts-unused-exports tsconfig.json`` and parses
stdout. The tool exits 1 when findings exist; stdout lines look like::

    /abs/path/to/file.ts: exportA, exportB
    /abs/path/to/other.ts: default

The first line of output is a summary (``N modules with unused exports``)
and is ignored. Each comma-separated export name on a remaining line
counts as one dead export.

All findings map to QualityFindings.dead_code_blocks (each dead export
is one block).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from lib.review_evidence.runners._registry import register
from lib.review_evidence.scoring import QualityFindings

_TS_GLOBS = ("*.ts", "*.tsx")


def _has_typescript_dep(package_json: Path) -> bool:
    try:
        import json as _json

        data = _json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps = data.get(key) or {}
        if "typescript" in deps:
            return True
    return False


class TsUnusedExportsRunner:
    name = "ts-unused-exports"
    category = "quality"

    def is_applicable(self, repo_root: Path) -> bool:
        package_json = repo_root / "package.json"
        if not package_json.exists():
            return False
        if not _has_typescript_dep(package_json):
            return False
        for pattern in _TS_GLOBS:
            for _ in repo_root.rglob(pattern):
                return True
        return False

    def run(self, repo_root: Path) -> Optional[QualityFindings]:
        try:
            p = subprocess.run(
                ["npx", "--no-install", "ts-unused-exports", "tsconfig.json"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            # exit 0 = no findings; exit 1 = findings present
            if p.returncode not in (0, 1):
                return None
            dead = 0
            for line in p.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Skip the summary line, e.g. "3 modules with unused exports"
                if "modules with unused exports" in line or "module with unused exports" in line:
                    continue
                # Finding lines have format: "<filepath>: name1, name2, ..."
                if ":" not in line:
                    continue
                _, rhs = line.split(":", 1)
                names = [n.strip() for n in rhs.split(",") if n.strip()]
                dead += len(names)
            return QualityFindings(dead_code_blocks=dead)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None


register(TsUnusedExportsRunner())
