"""SIAE Semgrep suppression engine (Layer 3 — ADR-009).

Parses `rules/semgrep/siae/suppressions.yaml` and applies filters to Semgrep
findings: drop finding if (rule_id, path_glob) matches AND expires_at > today.
Expired suppressions: finding torna a contare + WARNING emitted.
Expiring <14gg: drop ma WARNING re-validate emitted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Sequence

import yaml


_EXPIRING_THRESHOLD_DAYS = 14


class SuppressionStatus(str, Enum):
    APPLIED = "applied"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    NO_MATCH = "no_match"


@dataclass
class Suppression:
    rule_id: str
    path_glob: str
    reason: str
    owner: str
    expires_at: date

    @classmethod
    def from_dict(cls, d: dict) -> "Suppression":
        return cls(
            rule_id=d["rule_id"],
            path_glob=d["path_glob"],
            reason=d["reason"],
            owner=d["owner"],
            expires_at=date.fromisoformat(str(d["expires_at"])),
        )


@dataclass
class DroppedFinding:
    finding: dict
    suppression: Suppression
    status: SuppressionStatus


@dataclass
class SuppressionResult:
    kept: list[dict] = field(default_factory=list)
    dropped: list[DroppedFinding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SuppressionEngine:
    suppressions: list[Suppression]

    @classmethod
    def from_file(cls, path: Path) -> "SuppressionEngine":
        return cls(suppressions=load_suppressions(path))

    def find_matching(self, finding: dict) -> Suppression | None:
        rule_id = finding.get("check_id", "")
        path = finding.get("path", "")
        for s in self.suppressions:
            if s.rule_id == rule_id and fnmatch(path, s.path_glob):
                return s
        return None


def load_suppressions(path: Path) -> list[Suppression]:
    """Carica suppressions da YAML. File mancante/empty → [] (no errore)."""
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return []
    raw = data.get("suppressions") or []
    return [Suppression.from_dict(d) for d in raw]


def apply_suppressions(
    findings: Sequence[dict],
    engine: SuppressionEngine,
    today: date | None = None,
) -> SuppressionResult:
    """Applica suppressions ai finding.

    - rule_id+path_glob match + expires_at > today → drop (APPLIED)
    - rule_id+path_glob match + expires_at in <=14gg → drop + WARNING (EXPIRING_SOON)
    - rule_id+path_glob match + expires_at < today → keep + WARNING (EXPIRED)
    - no match → keep
    """
    today = today or date.today()
    result = SuppressionResult()

    for f in findings:
        match = engine.find_matching(f)
        if match is None:
            result.kept.append(f)
            continue

        days_remaining = (match.expires_at - today).days
        if days_remaining < 0:
            # Expired → finding torna a contare + warning
            result.kept.append(f)
            result.warnings.append(
                f"Suppression EXPIRED for rule={match.rule_id} "
                f"path={f.get('path')} expired_at={match.expires_at} "
                f"owner={match.owner}"
            )
        elif days_remaining <= _EXPIRING_THRESHOLD_DAYS:
            # Expiring soon → drop ma warning re-validate
            result.dropped.append(
                DroppedFinding(f, match, SuppressionStatus.EXPIRING_SOON)
            )
            result.warnings.append(
                f"Suppression EXPIRING in {days_remaining}d for rule={match.rule_id} "
                f"path={f.get('path')} expires={match.expires_at} owner={match.owner}"
            )
        else:
            result.dropped.append(
                DroppedFinding(f, match, SuppressionStatus.APPLIED)
            )

    return result
