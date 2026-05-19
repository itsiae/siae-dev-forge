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
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PRIORITY_RULES_PATH = SKILL_ROOT / "assets" / "priority-rules.json"


def _glob_to_regex(pattern: str) -> str:
    """Converte glob in regex senza cascade re-replace.

    Strategia sentinel-based: rimpiazza `**/` e `**` con sentinel uniche prima
    di sostituire `*` singolo, poi ripristina le sentinel a `.*/` / `.*`.
    Evita il bug del triple-cascade replace che trasforma `.*` in `.[^/]*`.
    """
    SENT_DSTAR_SLASH = "\x00DSTARSLASH\x00"
    SENT_DSTAR = "\x00DSTAR\x00"
    s = pattern.replace("**/", SENT_DSTAR_SLASH).replace("**", SENT_DSTAR)
    s = s.replace("*", "[^/]*")
    return s.replace(SENT_DSTAR, ".*").replace(SENT_DSTAR_SLASH, ".*/")


def _load_priority_rules() -> dict:
    try:
        with open(PRIORITY_RULES_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _classify_priority(rel_path: str, priority_rules: dict) -> str | None:
    """P1/P2/P3: prima match diretto su ``parent_dirs`` (basename del dir
    contenitore), poi fallback ANCORATO su ``path_patterns`` glob ristretto
    agli ultimi 2 segment di directory.

    ADR-3: Pass 2 anchored a ``last_2_segments`` previene il bug per cui
    namespace progetto contenente ``services`` (Java SIAE
    ``it/siae/pae/services/``) o ``modules/service/lambda/**`` (SIAE Lambda
    layout) classifica TUTTI i file come P1 esplodendo il floor enforcement
    loop. Empirical baseline Agent-A: 90% file → P1 false-positive.
    """
    # parent dir basename (immediato sopra il file)
    dirname = rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""
    parent = dirname.rsplit("/", 1)[-1] if dirname else ""

    levels = priority_rules.get("priority_levels", {})
    # Pass 1: parent_dirs (preferito, niente glob)
    if parent:
        for level_name in ("P1", "P2", "P3"):
            dir_names = levels.get(level_name, {}).get("parent_dirs", [])
            if parent in dir_names:
                return level_name
    # Pass 2: path_patterns fallback ANCORATO agli ultimi 2 segment.
    # "modules/service/lambda/src/api/uptime/uptime.get.ts" -> window = "uptime/uptime.get.ts"
    # cosi' "**/service/**" NON triggera P1 su file con penultimate ancestor != "service".
    segments = rel_path.split("/")
    anchor_window = "/".join(segments[-2:]) if len(segments) >= 2 else rel_path
    for level_name in ("P1", "P2", "P3"):
        patterns = levels.get(level_name, {}).get("path_patterns", [])
        for pattern in patterns:
            regex = _glob_to_regex(pattern)
            if re.search(regex, anchor_window):
                return level_name
    return None


_HEADER_SNIFF_BYTES = 1024


def _is_generated_file(abs_path: Path, generated_markers: list) -> bool:
    """True se prime ~1KB del file contengono un marker di generazione automatica.

    ADR-4: skip auto-generated files (OpenAPI codegen, drizzle-kit, prisma,
    protoc, gRPC, jOOQ, ts-proto). Marker list in
    ``priority-rules.json.generated_file_markers``.
    """
    if not generated_markers:
        return False
    try:
        head = abs_path.read_bytes()[:_HEADER_SNIFF_BYTES].decode("utf-8", errors="ignore")
    except OSError:
        return False
    return any(marker in head for marker in generated_markers)


_T4_PATH_RE = re.compile(r"(?:^|/)(handlers?|controllers?|repositor(?:y|ies)|gateways?|adapters?)/")
_T3_PATH_RE = re.compile(r"(?:^|/)(components?|hooks?|stores?|reducers?|pages?|views?)/")
_T1_PATH_RE = re.compile(r"(?:^|/)(utils?|helpers?|lib|formatters?|validators?)/")
_IO_IMPORT_RE = re.compile(
    r"(?:from\s+|import\s+)(['\"]?)("
    r"@aws-sdk|aws-sdk|aws-lambda|axios|node-fetch|got|undici|"
    r"boto3|botocore|requests|httpx|aiohttp|urllib|"
    r"java\.io|java\.net|jakarta\.servlet|"
    r"reqwest|hyper|tokio::net"
    r")",
    re.IGNORECASE,
)


def _classify_tier(rel_path: str, abs_path: Path) -> str:
    """T1-T4 testability classifier:
      - T4 I/O: path match handlers/repos/gateways OR import AWS SDK / HTTP client
      - T3 Components: path match components/hooks/stores/views (frontend) OR services
      - T1 Pure: path match utils/helpers/lib AND nessun import esterno significativo
      - T2 Injectable: default
    """
    if _T4_PATH_RE.search(rel_path):
        return "T4"
    try:
        head = abs_path.read_text(encoding="utf-8", errors="ignore")[:4096]
        if _IO_IMPORT_RE.search(head):
            return "T4"
        import_count = len(re.findall(r"^\s*(?:import|from)\s+\S", head, re.MULTILINE))
    except OSError:
        head = ""
        import_count = 0
    if _T3_PATH_RE.search(rel_path):
        return "T3"
    if _T1_PATH_RE.search(rel_path) and import_count <= 1:
        return "T1"
    return "T2"

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

    coverage_path: Path | None = None
    if "--with-coverage" in sys.argv:
        idx = sys.argv.index("--with-coverage")
        if idx + 1 < len(sys.argv):
            coverage_path = Path(sys.argv[idx + 1])

    priority_rules = _load_priority_rules() if want_file_list else {}
    generated_markers = priority_rules.get("generated_file_markers", []) if want_file_list else []

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
            # ADR-4: skip auto-generated files (sniff header)
            if generated_markers and _is_generated_file(fpath, generated_markers):
                continue
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
                rel_path = str(fpath.relative_to(root))
                file_entries.append({
                    "path": rel_path,
                    "loc": loc,
                    "lang": lang,
                    "tier": _classify_tier(rel_path, fpath),
                    "priority": _classify_priority(rel_path, priority_rules) or "P2",
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
        if coverage_path and coverage_path.exists():
            try:
                cov_data = json.loads(coverage_path.read_text(encoding="utf-8", errors="ignore"))
                cov_map = {m["path"]: m.get("lines_pct", 0) / 100.0 for m in cov_data.get("modules", [])}
                for f in file_entries:
                    current = cov_map.get(f["path"], 0.0)
                    f["current_coverage"] = current
                    f["priority_score"] = round((1 - current) * f["loc"], 2)
                output["file_list"] = sorted(file_entries, key=lambda e: e.get("priority_score", e["loc"]), reverse=True)
            except (json.JSONDecodeError, OSError):
                output["file_list"] = sorted(file_entries, key=lambda e: e["loc"], reverse=True)
        else:
            output["file_list"] = sorted(file_entries, key=lambda e: e["loc"], reverse=True)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
