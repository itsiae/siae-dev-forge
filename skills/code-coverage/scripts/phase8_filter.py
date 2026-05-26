#!/usr/bin/env python3
"""phase8_filter.py — Phase 8 reporting filter per moduli `jacoco.skip`.

Dopo ``mvn jacoco:report`` JaCoCo produce:
- single-module:  ``target/site/jacoco/jacoco.xml``
- multi-module:   ``target/site/jacoco-aggregate/jacoco.xml`` (con <group> per modulo)

I moduli che dichiarano ``<jacoco.skip>true</jacoco.skip>`` (rilevati in Task 06 e
serializzati in ``.code-coverage/env.json`` come ``skipped_modules``) NON producono
counter coverage validi → se inclusi nel bundle contano come 0% LINE → falsi FAIL.

Questo script esclude i ``skipped_modules`` dal calcolo bundle aggregando solo i
``<group>`` con name NON nella skip-list. Su XML single-module (no <group>) il
filter e' no-op (il file rappresenta gia' un solo modulo).

Usage:
    python3 phase8_filter.py <repo_path>

Output (stdout, sempre):
    {
        "bundle_line_pct": float,
        "bundle_branch_pct": float,
        "skipped_modules_excluded": [str, ...],
        "modules_included": [str, ...],
        "error": str | null
    }

Exit code: 0 sempre (errori veicolati via field ``error``).

Compat: Python 3.8+ (stdlib-only: xml.etree.ElementTree, json, pathlib, sys).
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


def _aggregate_counters(
    element: ET.Element,
) -> Tuple[int, int, int, int]:
    """Aggrega counter LINE e BRANCH ricorsivamente da tutti i <package> sotto element.

    Ritorna (line_missed, line_covered, branch_missed, branch_covered).

    Implementazione: somma i counter package-level (figli diretti di <package>) per
    evitare double-counting con i counter group/report-level. Su single-module XML
    senza <group> si invoca con element=root e raccoglie i package direttamente.
    """
    line_missed = 0
    line_covered = 0
    branch_missed = 0
    branch_covered = 0
    for pkg in element.iter("package"):
        # Solo counter figli diretti del package (non class/sourcefile counters).
        for child in pkg:
            if child.tag != "counter":
                continue
            ctype = child.get("type", "")
            try:
                m = int(child.get("missed", "0"))
                c = int(child.get("covered", "0"))
            except ValueError:
                continue
            if ctype == "LINE":
                line_missed += m
                line_covered += c
            elif ctype == "BRANCH":
                branch_missed += m
                branch_covered += c
    return line_missed, line_covered, branch_missed, branch_covered


def filter_coverage(
    jacoco_xml_path: Path,
    skipped_modules: List[str],
) -> Dict[str, Union[float, List[str], Optional[str]]]:
    """Filtra il bundle coverage escludendo i ``skipped_modules``.

    Args:
        jacoco_xml_path: path al file ``jacoco.xml`` (single-module o aggregate).
        skipped_modules: lista nomi gruppi da escludere (match esatto su
            ``<group name="...">``).

    Returns:
        dict con bundle_line_pct, bundle_branch_pct, skipped_modules_excluded,
        modules_included, error.
    """
    result: Dict[str, Union[float, List[str], Optional[str]]] = {
        "bundle_line_pct": 0.0,
        "bundle_branch_pct": 0.0,
        "skipped_modules_excluded": [],
        "modules_included": [],
        "error": None,
    }

    path = Path(jacoco_xml_path)
    if not path.is_file():
        result["error"] = "jacoco.xml not found: {0}".format(str(path))
        return result

    try:
        tree = ET.parse(str(path))
    except ET.ParseError as exc:
        result["error"] = "XML parse error: {0}".format(str(exc))
        return result
    except OSError as exc:
        result["error"] = "I/O error reading XML: {0}".format(str(exc))
        return result

    root = tree.getroot()
    groups = list(root.findall("group"))

    line_missed = 0
    line_covered = 0
    branch_missed = 0
    branch_covered = 0
    included: List[str] = []
    excluded: List[str] = []

    skip_set = set(skipped_modules or [])

    if groups:
        # Multi-module aggregate: itera sui <group>, applica filter
        for grp in groups:
            name = grp.get("name", "")
            if not name:
                continue
            if name in skip_set:
                excluded.append(name)
                continue
            lm, lc, bm, bc = _aggregate_counters(grp)
            line_missed += lm
            line_covered += lc
            branch_missed += bm
            branch_covered += bc
            included.append(name)
    else:
        # Single-module XML: no <group>, no filter applicabile.
        # Aggrega tutti i package direttamente sotto root.
        lm, lc, bm, bc = _aggregate_counters(root)
        line_missed += lm
        line_covered += lc
        branch_missed += bm
        branch_covered += bc
        # included/excluded restano vuoti (single-module non ha "nomi modulo")

    line_total = line_missed + line_covered
    branch_total = branch_missed + branch_covered
    result["bundle_line_pct"] = (
        (line_covered / line_total * 100) if line_total else 0.0
    )
    result["bundle_branch_pct"] = (
        (branch_covered / branch_total * 100) if branch_total else 0.0
    )
    result["skipped_modules_excluded"] = excluded
    result["modules_included"] = included
    return result


def _load_skipped_from_env(repo: Path) -> List[str]:
    """Legge ``skipped_modules`` da ``<repo>/.code-coverage/env.json``.

    Ritorna lista vuota se file/key mancante o malformato.
    """
    env_path = repo / ".code-coverage" / "env.json"
    if not env_path.is_file():
        return []
    try:
        data = json.loads(env_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    skipped = data.get("skipped_modules", [])
    if not isinstance(skipped, list):
        return []
    return [str(x) for x in skipped]


def _locate_jacoco_xml(repo: Path) -> Optional[Path]:
    """Trova il file ``jacoco.xml`` da usare per il bundle.

    Priorita': ``target/site/jacoco-aggregate/jacoco.xml`` (multi-module)
    fallback: ``target/site/jacoco/jacoco.xml`` (single-module).
    """
    aggregate = repo / "target" / "site" / "jacoco-aggregate" / "jacoco.xml"
    if aggregate.is_file():
        return aggregate
    single = repo / "target" / "site" / "jacoco" / "jacoco.xml"
    if single.is_file():
        return single
    return None


def main() -> None:
    if len(sys.argv) < 2:
        out = {
            "bundle_line_pct": 0.0,
            "bundle_branch_pct": 0.0,
            "skipped_modules_excluded": [],
            "modules_included": [],
            "error": "Usage: phase8_filter.py <repo_path>",
        }
        print(json.dumps(out))
        sys.exit(0)

    repo = Path(sys.argv[1]).resolve()
    skipped = _load_skipped_from_env(repo)
    xml_path = _locate_jacoco_xml(repo)

    if xml_path is None:
        out = {
            "bundle_line_pct": 0.0,
            "bundle_branch_pct": 0.0,
            "skipped_modules_excluded": [],
            "modules_included": [],
            "error": (
                "jacoco.xml not found in {0}/target/site/jacoco-aggregate/ "
                "or {0}/target/site/jacoco/".format(str(repo))
            ),
        }
        print(json.dumps(out))
        sys.exit(0)

    result = filter_coverage(xml_path, skipped)
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
