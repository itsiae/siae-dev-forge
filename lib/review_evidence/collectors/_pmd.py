"""Minimal PMD XML parser."""
from __future__ import annotations

import xml.etree.ElementTree as ET


def parse_pmd_xml(content: str) -> dict:
    root = ET.fromstring(content)
    errors = 0
    warnings = 0
    findings = []
    for f in root.findall("file"):
        for v in f.findall("violation"):
            priority = int(v.get("priority", 5))
            sev = "error" if priority <= 2 else "warning"
            if sev == "error":
                errors += 1
            else:
                warnings += 1
            findings.append({
                "file": f.get("name"),
                "line": int(v.get("beginline", 0)),
                "rule": v.get("rule", "?"),
                "severity": sev,
                "msg": (v.text or "").strip(),
            })
    return {"errors": errors, "warnings": warnings, "findings": findings}
