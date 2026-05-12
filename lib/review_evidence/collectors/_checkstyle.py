"""Minimal checkstyle XML parser."""
from __future__ import annotations

import xml.etree.ElementTree as ET


def parse_checkstyle_xml(content: str) -> dict:
    root = ET.fromstring(content)
    errors = 0
    warnings = 0
    findings = []
    for f in root.findall("file"):
        for e in f.findall("error"):
            sev = e.get("severity", "error")
            if sev == "error":
                errors += 1
            else:
                warnings += 1
            findings.append({
                "file": f.get("name"),
                "line": int(e.get("line", 0)),
                "rule": e.get("source", "?"),
                "severity": sev,
                "msg": e.get("message", ""),
            })
    return {"errors": errors, "warnings": warnings, "findings": findings}
