#!/usr/bin/env python3
"""surefire_parser.py — Task 09: parsa TEST-*.xml di Surefire per fail/error.

Phase 7 repair single-shot mvn: dopo `mvn test`, parsa
``target/surefire-reports/TEST-*.xml`` per identificare class#method falliti
e ri-eseguire solo quelli (mvn -Dtest=Class#method), evitando full mvn rebuild.

Usage:
    python3 surefire_parser.py <surefire-reports-dir>
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def parse_surefire_failures(reports_dir) -> list:
    """Scansiona TEST-*.xml per testcase con <failure> o <error>.

    Args:
        reports_dir: path a ``target/surefire-reports/`` directory.

    Returns:
        Lista ``["class#method", ...]`` ordinata, deduplicata.
    """
    reports = Path(reports_dir)
    if not reports.is_dir():
        return []
    failures: set[str] = set()
    for xml_file in reports.glob("TEST-*.xml"):
        try:
            tree = ET.parse(str(xml_file))
        except (ET.ParseError, OSError):
            continue
        root = tree.getroot()
        for tc in root.iter("testcase"):
            classname = tc.get("classname") or ""
            method = tc.get("name") or ""
            if not classname or not method:
                continue
            # Failure (assertion) o error (exception) = entrambi da rifare
            has_failure = tc.find("failure") is not None or tc.find("error") is not None
            if has_failure:
                failures.add(f"{classname}#{method}")
    return sorted(failures)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: surefire_parser.py <reports-dir>", file=sys.stderr)
        sys.exit(1)
    failures = parse_surefire_failures(sys.argv[1])
    for f in failures:
        print(f)


if __name__ == "__main__":
    main()
