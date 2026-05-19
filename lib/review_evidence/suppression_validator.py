"""Suppression schema validator — ADR-009 hard rules.

PR-gate hook invoca questo validator su `rules/semgrep/siae/suppressions.yaml`.
Violazione schema → BLOCK_REGRESSION (exit code 2 nel hook).
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import yaml


class ValidationError(Exception):
    """Raised when suppressions.yaml violates ADR-009 schema rules."""


JIRA_RE = re.compile(r"\b[A-Z]+-[0-9]+\b")
SIAE_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@siae\.it$")
MIN_REASON_LEN = 30
MAX_EXPIRES_DAYS = 90
# Glob shapes considered "catch-all" — reject
CATCH_ALL_GLOBS = {"**", "*", "**/*", "*/**", "**/**", "*.*"}


def validate_suppressions_yaml(path: Path) -> None:
    """Raise ValidationError se qualsiasi entry viola ADR-009 schema.

    Regole hard:
    1. path_glob NON catch-all (`**`, `*`, `**/*`, ...)
    2. reason >=30 char
    3. reason contiene Jira/ticket ref `[A-Z]+-[0-9]+`
    4. expires_at: today < expires_at <= today + 90gg
    5. owner matcha `@siae.it`
    """
    if not path.exists():
        # Empty/missing → no violation (just no suppressions)
        return

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValidationError(f"YAML parse error in {path}: {e}")

    suppressions = data.get("suppressions") or []
    today = date.today()
    errors: list[str] = []

    for i, entry in enumerate(suppressions):
        prefix = f"entry #{i} (rule_id={entry.get('rule_id', '?')})"

        # 1. path_glob NO catch-all (EC-35)
        pg = (entry.get("path_glob") or "").strip()
        if not pg:
            errors.append(f"{prefix}: path_glob missing")
        elif pg in CATCH_ALL_GLOBS:
            errors.append(
                f"{prefix}: path_glob is catch-all ({pg!r}); refuse per EC-35 anti-abuse"
            )

        # 2. reason length
        reason = entry.get("reason") or ""
        if len(reason) < MIN_REASON_LEN:
            errors.append(
                f"{prefix}: reason length {len(reason)} < {MIN_REASON_LEN} (ADR-009)"
            )

        # 3. reason Jira/ticket ref
        if not JIRA_RE.search(reason):
            errors.append(
                f"{prefix}: reason missing Jira/ticket reference [A-Z]+-[0-9]+ "
                f"(ADR-009)"
            )

        # 4. expires_at
        exp_str = entry.get("expires_at")
        if not exp_str:
            errors.append(f"{prefix}: expires_at missing")
        else:
            try:
                exp = date.fromisoformat(str(exp_str))
            except (ValueError, TypeError):
                errors.append(f"{prefix}: expires_at invalid ISO date: {exp_str!r}")
                continue
            days = (exp - today).days
            if days < 0:
                errors.append(
                    f"{prefix}: expires_at {exp} is in the past (expired)"
                )
            elif days > MAX_EXPIRES_DAYS:
                errors.append(
                    f"{prefix}: expires_at {exp} > today+{MAX_EXPIRES_DAYS}d "
                    f"(actual: {days}d, ADR-009 max=90)"
                )

        # 5. owner @siae.it
        owner = entry.get("owner") or ""
        if not SIAE_EMAIL_RE.match(owner):
            errors.append(
                f"{prefix}: owner {owner!r} must match @siae.it regex (ADR-009)"
            )

    if errors:
        raise ValidationError(
            f"Suppression schema validation FAILED ({len(errors)} errors):\n  - "
            + "\n  - ".join(errors)
        )
