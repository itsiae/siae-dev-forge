"""Minimal Jacoco XML parser (no external deps -- xml.etree)."""
from __future__ import annotations

import xml.etree.ElementTree as ET


def parse_jacoco_xml(content: str) -> dict:
    root = ET.fromstring(content)
    # Top-level <counter type="LINE" missed=".." covered=".."/>
    overall_missed = 0
    overall_covered = 0
    for c in root.findall("counter"):
        if c.get("type") == "LINE":
            overall_missed = int(c.get("missed", 0))
            overall_covered = int(c.get("covered", 0))
    total = overall_missed + overall_covered
    pct = (overall_covered / total * 100) if total else 0.0

    per_file = []
    for pkg in root.findall("package"):
        for sf in pkg.findall("sourcefile"):
            f_missed = 0
            f_covered = 0
            for c in sf.findall("counter"):
                if c.get("type") == "LINE":
                    f_missed = int(c.get("missed", 0))
                    f_covered = int(c.get("covered", 0))
            f_total = f_missed + f_covered
            f_pct = (f_covered / f_total * 100) if f_total else 0.0
            per_file.append({
                "path": f"{pkg.get('name','')}/{sf.get('name','')}",
                "pct": round(f_pct, 2),
                "uncovered_lines": [],
            })
    return {"overall_pct": round(pct, 2), "per_file": per_file}
