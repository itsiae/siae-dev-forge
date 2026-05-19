"""Cross-layer finding dedup per design §3.3.0 (AC19).

Quando community Semgrep + SIAE custom matchano stessa riga (file+line range),
applichiamo dedup con severity max wins + tracciabilità secondary rule-ids.
"""
from __future__ import annotations

from typing import Sequence


_SEVERITY_ORDER = {"ERROR": 3, "WARNING": 2, "INFO": 1}


def dedup_findings(findings: Sequence[dict]) -> list[dict]:
    """Merge findings su stesso (path, line) con severity max wins.

    Community rule + SIAE rule su stessa riga → primary = quello con severity max;
    rule_ids dropped diventano `dedup_secondary` per traceability.
    """
    groups: dict[tuple, list[dict]] = {}
    for f in findings:
        path = f.get("path", "")
        line = (f.get("start") or {}).get("line", 0)
        key = (path, line)
        groups.setdefault(key, []).append(f)

    result: list[dict] = []
    for group in groups.values():
        if len(group) == 1:
            result.append(group[0])
            continue
        # Severity max wins (ADR §3.3.0)
        primary = max(
            group,
            key=lambda f: _SEVERITY_ORDER.get(
                (f.get("extra") or {}).get("severity", "INFO"), 0
            ),
        )
        secondary = [f["check_id"] for f in group if f is not primary]
        primary["dedup_secondary"] = secondary
        result.append(primary)
    return result
