#!/usr/bin/env python3
"""setter_scanner.py — Task 08: classifica setter Java come trivial/non_trivial.

Scopo: Phase 5 generation evita di emettere round-trip assertion naive
(``entity.setX("Foo"); assertEquals("Foo", entity.getX())``) per setter con
normalizer / escape / conditional che trasformano l'input. Quei test
fallirebbero al primo run (es. ``Foo.toLowerCase()`` → ``foo``).

Output:
  - stdout: JSON ``{ClassName: {setterName: {kind, transforms, has_conditional}}}``
  - opzionale: scrive ``<repo>/.code-coverage/setter-scan.json`` se ``--write`` passato

Limiti M2 (Task 08):
  - Regex multilinea su body Java (no AST). Setter su una sola riga supportati.
  - Body con ``{}`` annidati profondi può confondere il regex — accettabile per
    pattern SIAE entity comuni.
  - ``apply_transforms`` implementa trim/lowercase/uppercase native; replace e
    escape sono pass-through (genera WARN ma no crash).

Usage:
    python3 setter_scanner.py <repo_path>            # stdout
    python3 setter_scanner.py <repo_path> --write    # scrive setter-scan.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


# Pattern transforms riconosciuti (regex per match nel body + nome canonico).
NORMALIZER_PATTERNS = [
    (re.compile(r"\.toLowerCase\s*\("), "lowercase"),
    (re.compile(r"\.toUpperCase\s*\("), "uppercase"),
    (re.compile(r"\.trim\s*\("), "trim"),
    (re.compile(r"StringEscapeUtils\.escapeHtml"), "escape_html"),
    (re.compile(r"StringEscapeUtils\.unescapeHtml"), "unescape_html"),
    (re.compile(r"\.replace\s*\("), "replace"),
    (re.compile(r"\.replaceAll\s*\("), "replace_all"),
]
CONDITIONAL_PATTERNS = [
    re.compile(r"\bif\s*\("),
    re.compile(r"\bswitch\s*\("),
    re.compile(r"\?\s*[^:]+:"),  # ternary
]

# Setter signature + body. Body è non-greedy fino a } bilanciato approssimato.
SETTER_REGEX = re.compile(
    r"public\s+(?:final\s+)?void\s+set([A-Z][\w]*)\s*\([^)]+\)\s*\{([^}]*)\}",
    re.DOTALL,
)

# Trivial: body è esattamente `this.<field> = <param>;` (eventualmente con whitespace)
_TRIVIAL_BODY_RE = re.compile(r"^\s*this\.\w+\s*=\s*\w+\s*;\s*$", re.DOTALL)


def scan_setters(java_file: Path) -> dict:
    """Scansiona un file .java, classifica ogni setter.

    Args:
        java_file: Path al file Java.

    Returns:
        dict {setter_name: {kind: 'trivial'|'non_trivial', transforms: [str],
                            has_conditional: bool}}
    """
    try:
        content = Path(java_file).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}

    result: dict[str, dict] = {}
    for match in SETTER_REGEX.finditer(content):
        suffix, body = match.group(1), match.group(2)
        setter_name = f"set{suffix}"
        transforms = [name for pat, name in NORMALIZER_PATTERNS if pat.search(body)]
        has_cond = any(pat.search(body) for pat in CONDITIONAL_PATTERNS)
        is_trivial = bool(_TRIVIAL_BODY_RE.match(body)) and not transforms and not has_cond
        result[setter_name] = {
            "kind": "trivial" if is_trivial else "non_trivial",
            "transforms": transforms,
            "has_conditional": has_cond,
        }
    return result


def apply_transforms(value: str, transforms: list) -> str:
    """Applica le transforms native in ordine. Transforms sconosciute = pass-through.

    Implementato: trim, lowercase, uppercase. Altre (replace, escape_html, ...)
    sono pass-through (WARN dovrebbe essere loggato dal consumer Phase 5).
    """
    out = value
    for t in transforms:
        if t == "trim":
            out = out.strip()
        elif t == "lowercase":
            out = out.lower()
        elif t == "uppercase":
            out = out.upper()
        # else: pass-through (unknown / non-native)
    return out


_SKIP_DIRS = {"target", "build", ".git", "node_modules", ".code-coverage", ".idea"}


def _find_java_files(repo_root: Path, max_files: int = 5000):
    """Yield .java files sotto repo_root (skip build dirs)."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for f in filenames:
            if f.endswith(".java"):
                yield Path(dirpath) / f
                count += 1
                if count >= max_files:
                    return


def scan_repo(repo_root: Path) -> dict:
    """Scansiona tutti i .java sotto repo_root, raccoglie setters per ClassName.

    Returns:
        {ClassName: {setterName: {kind, transforms, has_conditional}}}
    """
    out: dict[str, dict] = {}
    for jf in _find_java_files(repo_root):
        # Nome classe ≈ stem del file (limite: 1 classe pubblica per file = convenzione Java)
        cls_name = jf.stem
        setters = scan_setters(jf)
        if setters:
            # Se più file hanno stessa stem (raro, ma possibile in test) → merge
            if cls_name in out:
                out[cls_name].update(setters)
            else:
                out[cls_name] = setters
    return out


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: setter_scanner.py <repo_path> [--write]"}),
              file=sys.stderr)
        sys.exit(1)
    repo = Path(sys.argv[1]).resolve()
    if not repo.is_dir():
        print(json.dumps({"error": f"Not a directory: {repo}"}), file=sys.stderr)
        sys.exit(1)
    data = scan_repo(repo)
    output = json.dumps(data, indent=2, sort_keys=True)
    print(output)
    if "--write" in sys.argv:
        cov = repo / ".code-coverage"
        cov.mkdir(exist_ok=True)
        (cov / "setter-scan.json").write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
