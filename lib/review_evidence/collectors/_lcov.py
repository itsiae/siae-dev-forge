"""Minimal LCOV parser — extracts file-level + total line coverage."""
from __future__ import annotations


def parse_lcov(content: str) -> dict:
    per_file = []
    total_lines = 0
    hit_lines = 0
    current: dict = {}
    for line in content.splitlines():
        if line.startswith("SF:"):
            current = {"path": line[3:]}
        elif line.startswith("LF:"):
            current["lf"] = int(line[3:])
        elif line.startswith("LH:"):
            current["lh"] = int(line[3:])
        elif line == "end_of_record":
            lf = current.get("lf", 0)
            lh = current.get("lh", 0)
            total_lines += lf
            hit_lines += lh
            pct = (lh / lf * 100) if lf else 0.0
            per_file.append({"path": current.get("path", ""), "pct": round(pct, 2), "uncovered_lines": []})
            current = {}
    pct = (hit_lines / total_lines * 100) if total_lines else 0.0
    return {"total_lines": total_lines, "hit_lines": hit_lines, "pct": pct, "per_file": per_file}
