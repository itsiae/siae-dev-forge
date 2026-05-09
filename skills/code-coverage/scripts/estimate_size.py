#!/usr/bin/env python3
"""
estimate_size.py — Counts source files and LOC; classifies repo as SMALL/MEDIUM/LARGE/VERY_LARGE.
Usage: python estimate_size.py <repo_path>
Output: JSON to stdout.
Requires: Python 3.8+, stdlib only.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SOURCE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs",
    ".py", ".java", ".kt", ".dart", ".go",
    ".rs", ".cs", ".rb", ".php", ".scala",
}

TEST_PATTERNS = {
    ".spec.", ".test.", "Test.", "IT.", "test_", "_test.",
}

SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "out", "target",
    ".terraform", "vendor", "coverage", "__pycache__", ".venv", "venv",
    ".next", ".nuxt", ".svelte-kit",
}

THRESHOLDS = [
    ("SMALL",      50,   5_000),
    ("MEDIUM",    200,  20_000),
    ("LARGE",     500,  50_000),
    ("VERY_LARGE", 10**9, 10**9),
]


def _is_test_file(name: str) -> bool:
    lower = name.lower()
    return any(p.lower() in lower for p in TEST_PATTERNS)


def _classify(file_count: int, loc: int) -> str:
    for label, max_files, max_loc in THRESHOLDS:
        if file_count <= max_files and loc <= max_loc:
            return label
    return "VERY_LARGE"


def count_lines(path: Path) -> int:
    try:
        return len(path.read_bytes().splitlines())
    except OSError:
        return 0


def main() -> None:
    if sys.version_info < (3, 8):
        print(json.dumps({"error": f"Python 3.8+ required. Found: {sys.version}"}), file=sys.stderr)
        sys.exit(1)
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: estimate_size.py <repo_path>"}), file=sys.stderr)
        sys.exit(1)

    root = Path(sys.argv[1]).resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"Not a directory: {root}"}), file=sys.stderr)
        sys.exit(1)

    want_file_list = "--file-list" in sys.argv

    breakdown: dict[str, dict] = {}
    file_entries: list[dict] = []
    total_files = 0
    total_loc = 0

    lang_map = {
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
        ".py": "python", ".java": "java",
        ".kt": "kotlin", ".kts": "kotlin",
        ".dart": "dart", ".go": "go", ".rs": "rust",
        ".cs": "csharp", ".rb": "ruby", ".php": "php", ".scala": "scala",
    }

    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        if depth > 10:
            dirnames.clear()
            continue
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in SOURCE_EXTENSIONS:
                continue
            if _is_test_file(fname):
                continue

            fpath = Path(dirpath) / fname
            loc = count_lines(fpath)

            # Map extension to language label
            lang = lang_map.get(ext, ext.lstrip("."))

            if lang not in breakdown:
                breakdown[lang] = {"files": 0, "loc": 0}
            breakdown[lang]["files"] += 1
            breakdown[lang]["loc"] += loc
            total_files += 1
            total_loc += loc

            if want_file_list:
                file_entries.append({
                    "path": str(fpath.relative_to(root)),
                    "loc": loc,
                    "lang": lang,
                })

    module_count = max(1, round(total_files * 0.85))
    size_class = _classify(total_files, total_loc)

    output: dict = {
        "repo_path": str(root),
        "file_count": total_files,
        "loc": total_loc,
        "module_count": module_count,
        "class": size_class,
        "breakdown": breakdown,
    }
    if want_file_list:
        output["file_list"] = sorted(file_entries, key=lambda e: e["loc"], reverse=True)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
