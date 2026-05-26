#!/usr/bin/env python3
"""generate_pom_patches.py — emit suggested pom.xml diff for restrictive surefire.

Task 05 follow-up (Opzione B): quando ``env.json.surefire_config.restrictive=true``,
i test generati da Phase 5 sarebbero ignorati silenziosamente da maven-surefire-plugin
(coverage 0%). Questa skill NON modifica il pom autonomamente (Principle 1) — emette
solo un diff suggerito che l'operatore può applicare con ``git apply``.

Usage:
    python3 generate_pom_patches.py <repo_path> [--package <pkg>]

Behaviour:
    - Legge ``<repo>/.code-coverage/env.json`` per ``surefire_config``.
    - Se ``restrictive=false`` o env.json mancante: exit 0, stdout vuoto, no-op.
    - Determina il pom rilevante via ``<repo>/.code-coverage/stack.json``
      (``maven_aggregator.aggregator_pom``), fallback a ``<repo>/pom.xml``.
    - Genera diff unified che aggiunge ``<include>{pattern}</include>``
      come ultima riga prima di ``</includes>``.
    - ``--package model`` => pattern ``**/model/*Test.java``; senza pacchetto
      => ``**/*Test.java``.
    - Cumulative append: scrive in ``<repo>/.code-coverage/proposed-pom-patches.diff``
      (non sovrascrive — più chiamate accumulano diff multipli).
    - Stampa diff su stdout. Exit 0 sempre (idempotente).

Requires: Python 3.8+, stdlib only.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path
from typing import Optional

# Regex per individuare il blocco maven-surefire-plugin (multi-line, DOTALL).
_SUREFIRE_PLUGIN_BLOCK_RE = re.compile(
    r"<plugin>\s*(?:<groupId>[^<]+</groupId>\s*)?"
    r"<artifactId>\s*maven-surefire-plugin\s*</artifactId>(.*?)</plugin>",
    re.DOTALL,
)
# Pattern surefire "standard" considerati NON restrittivi (default behaviour).
_SUREFIRE_DEFAULT_PATTERNS = {
    "**/*Test.java", "**/Test*.java", "**/*Tests.java", "**/*TestCase.java",
}
_SUREFIRE_INCLUDE_LINE_RE = re.compile(r"<include>([^<]+)</include>")
# Match <includes>...</includes> con cattura del contenuto interno.
_INCLUDES_BLOCK_RE = re.compile(r"(<includes>)(.*?)(</includes>)", re.DOTALL)


def _is_restrictive(plugin_block: str) -> bool:
    """True se il blocco surefire ha <includes> non-standard."""
    if "<includes>" not in plugin_block:
        return False
    includes = [m.strip() for m in _SUREFIRE_INCLUDE_LINE_RE.findall(plugin_block) if m.strip()]
    if not includes:
        return False
    return not any(inc in _SUREFIRE_DEFAULT_PATTERNS for inc in includes)


def generate_surefire_patch(
    pom_path,
    additional_include: str,
    pom_relative: Optional[str] = None,
) -> str:
    """Genera diff unified che aggiunge ``additional_include`` agli <includes>.

    Args:
        pom_path: path al pom.xml da analizzare.
        additional_include: pattern da aggiungere (es. ``**/model/*Test.java``).
        pom_relative: path relativo da usare negli header del diff
            (default: nome file). Usato per produrre header tipo ``a/pom.xml``.

    Returns:
        Stringa diff unified (con newline finali). Stringa vuota se:
        - pom non esiste o non leggibile
        - nessun blocco maven-surefire-plugin trovato
        - blocco surefire non è restrittivo (default patterns)
        - additional_include già presente
    """
    pom = Path(pom_path)
    try:
        original_text = pom.read_text(encoding="utf-8", errors="ignore")
    except (OSError, FileNotFoundError):
        return ""

    block_match = _SUREFIRE_PLUGIN_BLOCK_RE.search(original_text)
    if not block_match:
        return ""

    plugin_block = block_match.group(1)
    if not _is_restrictive(plugin_block):
        return ""

    # Verifica che l'include non sia già presente (idempotente).
    existing_includes = [
        m.strip() for m in _SUREFIRE_INCLUDE_LINE_RE.findall(plugin_block) if m.strip()
    ]
    if additional_include in existing_includes:
        return ""

    # Localizza il blocco <includes>...</includes> all'interno del plugin block
    # e ricostruisci il testo aggiungendo una riga <include>.
    includes_match = _INCLUDES_BLOCK_RE.search(plugin_block)
    if not includes_match:
        return ""

    # Posizione assoluta dell'<includes> nel file originale.
    plugin_block_start = block_match.start(1)
    includes_start_abs = plugin_block_start + includes_match.start()
    includes_end_abs = plugin_block_start + includes_match.end()
    includes_segment = original_text[includes_start_abs:includes_end_abs]

    # Determina indent: cerca l'ultima riga <include> esistente per
    # replicare il suo indent. Fallback: 10 spazi (convenzione SIAE).
    inner = includes_match.group(2)
    inner_lines = inner.splitlines()
    include_indent = "          "  # 10 spazi default
    for line in inner_lines:
        if "<include>" in line:
            stripped = line.lstrip(" \t")
            include_indent = line[: len(line) - len(stripped)]
            break

    # Determina indent del </includes>: ultima riga prima del closing tag.
    closing_indent = "        "  # 8 spazi default
    seg_lines = includes_segment.splitlines()
    for line in seg_lines:
        if line.lstrip().startswith("</includes>"):
            stripped = line.lstrip(" \t")
            closing_indent = line[: len(line) - len(stripped)]
            break

    new_include_line = f"{include_indent}<include>{additional_include}</include>"

    # Ricostruisci il segmento <includes>: aggiungi il nuovo <include>
    # come ultima riga prima di </includes>, preservando newline finali.
    new_inner_lines = []
    inserted = False
    for line in seg_lines:
        if not inserted and line.lstrip().startswith("</includes>"):
            new_inner_lines.append(new_include_line)
            new_inner_lines.append(line)
            inserted = True
        else:
            new_inner_lines.append(line)
    new_segment = "\n".join(new_inner_lines)
    # Preserva trailing newline se presente nell'originale
    if includes_segment.endswith("\n") and not new_segment.endswith("\n"):
        new_segment += "\n"

    modified_text = (
        original_text[:includes_start_abs]
        + new_segment
        + original_text[includes_end_abs:]
    )

    rel = pom_relative or pom.name
    original_lines = original_text.splitlines(keepends=True)
    modified_lines = modified_text.splitlines(keepends=True)
    diff_lines = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{rel}",
        tofile=f"b/{rel}",
        n=3,
    )
    return "".join(diff_lines)


def _resolve_pom_path(repo_path: Path) -> Optional[Path]:
    """Determina il pom rilevante via stack.json, fallback a <repo>/pom.xml."""
    stack_file = repo_path / ".code-coverage" / "stack.json"
    if stack_file.is_file():
        try:
            stack = json.loads(stack_file.read_text(encoding="utf-8", errors="ignore"))
            agg = stack.get("maven_aggregator") or {}
            agg_rel = agg.get("aggregator_pom")
            if agg_rel:
                candidate = repo_path / agg_rel
                if candidate.is_file():
                    return candidate
        except (json.JSONDecodeError, OSError):
            pass
    fallback = repo_path / "pom.xml"
    if fallback.is_file():
        return fallback
    return None


def _pattern_for_package(package: Optional[str]) -> str:
    """Costruisce additional_include da arg ``--package``.

    Esempi:
        None        -> ``**/*Test.java``
        ``""``      -> ``**/*Test.java``
        ``model``   -> ``**/model/*Test.java``
        ``a/b``     -> ``**/a/b/*Test.java``
    """
    if not package:
        return "**/*Test.java"
    pkg = package.strip().strip("/")
    if not pkg:
        return "**/*Test.java"
    return f"**/{pkg}/*Test.java"


def _parse_args(argv: list) -> tuple:
    """Parse minimale: posizionale <repo_path> + opzionale --package <pkg>."""
    repo_path: Optional[str] = None
    package: Optional[str] = None
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--package":
            if i + 1 >= len(argv):
                print("Error: --package richiede un valore", file=sys.stderr)
                sys.exit(2)
            package = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--package="):
            package = arg.split("=", 1)[1]
            i += 1
            continue
        if arg.startswith("--"):
            print(f"Error: argomento sconosciuto {arg}", file=sys.stderr)
            sys.exit(2)
        if repo_path is None:
            repo_path = arg
            i += 1
            continue
        print(f"Error: argomento posizionale inatteso {arg}", file=sys.stderr)
        sys.exit(2)
    if repo_path is None:
        print("Usage: generate_pom_patches.py <repo_path> [--package <pkg>]", file=sys.stderr)
        sys.exit(2)
    return repo_path, package


def main(argv: Optional[list] = None) -> int:
    if argv is None:
        argv = sys.argv
    repo_str, package = _parse_args(argv)
    repo_path = Path(repo_str).resolve()

    # Leggi env.json; se assente o non-restrictive => no-op.
    env_file = repo_path / ".code-coverage" / "env.json"
    if not env_file.is_file():
        return 0
    try:
        env = json.loads(env_file.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return 0

    surefire_cfg = env.get("surefire_config") or {}
    if not surefire_cfg.get("restrictive"):
        return 0

    pom_path = _resolve_pom_path(repo_path)
    if pom_path is None:
        return 0

    try:
        pom_relative = str(pom_path.relative_to(repo_path))
    except ValueError:
        pom_relative = pom_path.name

    additional_include = _pattern_for_package(package)
    diff = generate_surefire_patch(pom_path, additional_include, pom_relative=pom_relative)
    if not diff:
        return 0

    # Cumulative append nel file proposed-pom-patches.diff.
    out_dir = repo_path / ".code-coverage"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "proposed-pom-patches.diff"
    with out_file.open("a", encoding="utf-8") as fh:
        fh.write(diff)
        if not diff.endswith("\n"):
            fh.write("\n")

    sys.stdout.write(diff)
    if not diff.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
