"""Minimal Jacoco XML parser.

E22 mitigation — disable external entity resolution. Jacoco XML carries a
DOCTYPE pointing at ``http://www.jacoco.org/jacoco/report/report.dtd``;
a default ``xml.etree`` parser silently resolves DTDs on some platforms,
which means parsing a report on an air-gapped CI runner can raise opaque
network errors. We use ``xml.etree.ElementTree.XMLParser`` with
``resolve_entities=False`` semantics where supported, and otherwise rely
on the fact that ET ignores DTD references for entity expansion on the
stdlib default. As a defence in depth, ``_strip_doctype`` removes any
``<!DOCTYPE ...>`` declaration before parsing.

E23 mitigation — Maven multi-module reports nest ``<group>`` elements
inside the root ``<report>``. The previous parser only walked direct
``<package>`` children, so multi-module coverage was reported as 0%.
We recursively descend into nested ``<group>`` containers and aggregate.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable

_DOCTYPE_RE = re.compile(rb"<!DOCTYPE[^>]*>", re.DOTALL)
_DOCTYPE_RE_TEXT = re.compile(r"<!DOCTYPE[^>]*>", re.DOTALL)


def _strip_doctype(content: str) -> str:
    """Strip ``<!DOCTYPE ...>`` declarations before parsing (E22).

    Even with non-resolving parsers, the DOCTYPE can carry external
    entity references that an over-eager parser may fetch. Stripping it
    is the simplest portable defence.
    """
    return _DOCTYPE_RE_TEXT.sub("", content)


def _safe_parser() -> ET.XMLParser:
    """Return an XMLParser that does not resolve external entities.

    The expat backend underlying stdlib ET exposes
    ``DefaultHandler`` only — we cannot bind entity resolvers
    directly. Combined with ``_strip_doctype`` above this is sufficient
    for E22 (no network fetch, no billion-laughs).
    """
    return ET.XMLParser()


def _iter_line_counters(elem: ET.Element) -> Iterable[ET.Element]:
    """Yield ``<counter type="LINE">`` from direct children of ``elem``."""
    for c in elem.findall("counter"):
        if c.get("type") == "LINE":
            yield c


def _aggregate_sourcefiles(container: ET.Element, package_name: str = "") -> tuple[list[dict], int, int]:
    """Walk ``<sourcefile>`` under ``container`` and aggregate per-file pct.

    ``container`` is either a ``<package>`` or a ``<group>``. We do not
    recurse from here; recursion happens at the ``<group>``/``<package>``
    level in ``_walk_groups``.
    """
    per_file: list[dict] = []
    container_missed = 0
    container_covered = 0
    for sf in container.findall("sourcefile"):
        f_missed = 0
        f_covered = 0
        for c in _iter_line_counters(sf):
            f_missed = int(c.get("missed", 0))
            f_covered = int(c.get("covered", 0))
        f_total = f_missed + f_covered
        f_pct = (f_covered / f_total * 100) if f_total else 0.0
        per_file.append({
            "path": f"{package_name}/{sf.get('name','')}",
            "pct": round(f_pct, 2),
            "uncovered_lines": [],
        })
        container_missed += f_missed
        container_covered += f_covered
    return per_file, container_missed, container_covered


def _walk_groups(elem: ET.Element) -> tuple[list[dict], int, int]:
    """Recursive walk into ``<group>`` and ``<package>`` children.

    E23 mitigation — Maven multi-module Jacoco reports nest like:
        <report>
          <group name="root-aggregator">
            <group name="module-a">
              <package>...
            <group name="module-b">
              <package>...
    The old parser stopped at the top-level ``<package>`` and reported
    0% for multi-module repos. We descend through every ``<group>``,
    accumulating per_file + missed + covered from each ``<package>``
    encountered at any depth.
    """
    per_file: list[dict] = []
    missed_total = 0
    covered_total = 0
    # Direct <package> children
    for pkg in elem.findall("package"):
        pf, m, c = _aggregate_sourcefiles(pkg, package_name=pkg.get("name", ""))
        per_file.extend(pf)
        missed_total += m
        covered_total += c
    # Nested <group> children — recurse
    for grp in elem.findall("group"):
        pf, m, c = _walk_groups(grp)
        per_file.extend(pf)
        missed_total += m
        covered_total += c
    return per_file, missed_total, covered_total


def parse_jacoco_xml(content: str) -> dict[str, Any]:
    # E22: strip DOCTYPE before handing to ET to keep parsing offline-safe.
    safe_content = _strip_doctype(content)
    root = ET.fromstring(safe_content, parser=_safe_parser())

    # Top-level <counter type="LINE"> if present (Jacoco emits this
    # aggregate at the root). When absent (some Gradle plugins emit only
    # per-package), we fall back to the recursive sum below.
    overall_missed_root = 0
    overall_covered_root = 0
    for c in _iter_line_counters(root):
        overall_missed_root = int(c.get("missed", 0))
        overall_covered_root = int(c.get("covered", 0))

    per_file, walked_missed, walked_covered = _walk_groups(root)

    # Prefer the root counter when it exists and is non-zero — Jacoco's
    # own aggregator is authoritative. Fall back to the walk when the
    # root counter is missing (multi-module Gradle, custom merges).
    if (overall_missed_root + overall_covered_root) > 0:
        overall_missed = overall_missed_root
        overall_covered = overall_covered_root
    else:
        overall_missed = walked_missed
        overall_covered = walked_covered

    total = overall_missed + overall_covered
    pct = (overall_covered / total * 100) if total else 0.0
    return {"overall_pct": round(pct, 2), "per_file": per_file}
