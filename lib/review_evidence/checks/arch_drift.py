"""Arch drift detection — forbidden_paths cross-check (W3 spec).

Reads `.devforge-arch.yml` from the repo root. For each changed file in a
`from:` zone, parses the imports and raises a violation when any import
target sits under the matching `to:` zone.

ITER1 BLOCK fix: anchored startswith. Without it, a rule `to: "src/db/"`
would falsely match `src/database/x` (shared prefix). We compare against
`to_clean + "/"` (or full equality to `to_clean`) so siblings are safe.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


ARCH_FILENAME = ".devforge-arch.yml"


@dataclass
class ArchViolation:
    file: str
    import_: str
    rule_from: str
    rule_to: str
    reason: str


@dataclass
class ArchDrift:
    violations: list[ArchViolation] = field(default_factory=list)
    rules_file_present: bool = False


_PYTHON_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+([a-zA-Z0-9_.]+)",
    re.MULTILINE,
)
_TS_IMPORT_RE = re.compile(
    r"""(?:from|require)\s*\(?\s*['"]([^'"]+)['"]"""
)


def _extract_imports(file_path: Path) -> list[str]:
    """Return module-style paths (slash-separated) imported by file_path."""
    if not file_path.exists() or not file_path.is_file():
        return []
    try:
        content = file_path.read_text()
    except (UnicodeDecodeError, OSError):
        return []

    suffix = file_path.suffix.lower()
    if suffix == ".py":
        return [
            m.group(1).replace(".", "/")
            for m in _PYTHON_IMPORT_RE.finditer(content)
        ]
    if suffix in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        return list(_TS_IMPORT_RE.findall(content))
    return []


def _matches_to_zone(import_path: str, to_zone: str) -> bool:
    """Anchored prefix match: avoid false positives on sibling directories.

    Rule `to: "src/db/"` must match `src/db/x` but NOT `src/database/x`.
    """
    to_clean = to_zone.rstrip("/")
    if not to_clean:
        return False
    return import_path == to_clean or import_path.startswith(to_clean + "/")


def detect_arch_drift(repo_root: Path, changed_files: list[str]) -> ArchDrift:
    """Detect forbidden-path import violations in changed files.

    Returns an empty `ArchDrift(rules_file_present=False)` when
    `.devforge-arch.yml` is missing — that is *not* a violation, it just
    means the repo opted out of arch policing.
    """
    repo_root = Path(repo_root)
    rules_path = repo_root / ARCH_FILENAME
    if not rules_path.exists():
        return ArchDrift(violations=[], rules_file_present=False)

    try:
        rules: Any = yaml.safe_load(rules_path.read_text()) or {}
    except yaml.YAMLError:
        return ArchDrift(violations=[], rules_file_present=False)

    if not isinstance(rules, dict):
        return ArchDrift(violations=[], rules_file_present=True)

    forbidden = rules.get("forbidden_paths", []) or []
    if not isinstance(forbidden, list):
        return ArchDrift(violations=[], rules_file_present=True)

    violations: list[ArchViolation] = []
    for changed in changed_files:
        from_rules = [
            r for r in forbidden
            if isinstance(r, dict)
            and isinstance(r.get("from"), str)
            and changed.startswith(r["from"])
        ]
        if not from_rules:
            continue

        imports = _extract_imports(repo_root / changed)
        if not imports:
            continue

        for rule in from_rules:
            to_zone = rule.get("to")
            if not isinstance(to_zone, str):
                continue
            for imp in imports:
                if _matches_to_zone(imp, to_zone):
                    violations.append(
                        ArchViolation(
                            file=changed,
                            import_=imp,
                            rule_from=rule["from"],
                            rule_to=to_zone,
                            reason=str(rule.get("reason", "forbidden path")),
                        )
                    )
    return ArchDrift(violations=violations, rules_file_present=True)
