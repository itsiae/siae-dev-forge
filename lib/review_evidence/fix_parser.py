"""Parser block_reasons -> list[FixAction] (auto-fix loop dispatcher).

Reads ``RegressionVerdict.reason`` emitted by ``regression.py`` and
``Verdict.block_reasons`` emitted by ``thresholds.py``. Maps atomic block
reasons to DevForge sub-skill invocations via ``FixAction`` dataclass.

MVP scope (PR fix-evidence-auto-loop, design 2026-05-13):
    - ``coverage_below_threshold:X<Y`` -> ``siae-tdd``
    - ``lint_errors:N>M``              -> ``siae-code-standards``

Follow-up PR-D (this commit) — all 5 atomic patterns now covered:
    - ``ci_critical:X>Y``              -> ``siae-debugging`` SARIF fix (priority 0)
    - ``complexity_max:X>Y``           -> ``siae-tdd`` refactor (priority 3)
    - ``drift_severity_high``          -> ``siae-brainstorming`` design update (priority 4)

Format canonico ``block_reasons`` confirmed at:
    lib/review_evidence/thresholds.py:41,47 (PR #243 c3b6e74).

Forward-compat: any non-matching reason emits ``FixAction(kind="unknown",
sub_skill=None)`` so the orchestrator can escalate to human instead of
crashing on a new reason format introduced upstream.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .schema import Evidence

# Priority semantic (lower = applied first):
#   0 = ci_critical  (security CI findings — highest precedence)
#   1 = lint         (small surface, low blast radius)
#   2 = coverage     (often requires touching more files)
#   3 = complexity   (refactor — larger blast radius)
#   4 = drift        (design doc update — lowest, requires human design loop)
#   99 = unknown     (skipped by loop, escalate)
_PRIORITY_CI_CRITICAL = 0
_PRIORITY_LINT = 1
_PRIORITY_COVERAGE = 2
_PRIORITY_COMPLEXITY = 3
_PRIORITY_DRIFT = 4
_PRIORITY_UNKNOWN = 99


@dataclass
class FixAction:
    """Single auto-fix step the loop dispatches via Skill tool.

    Attributes:
        kind: short tag for telemetry (``coverage`` | ``lint`` | ``complexity``
            | ``drift`` | ``ci_critical`` | ``unknown``).
        priority: lower = higher precedence (applied first in the loop).
        sub_skill: DevForge skill name passed to Skill tool, or ``None`` for
            ``unknown`` reasons that the loop must escalate.
        prompt: dynamic ``args`` payload passed to Skill tool (ADR-7 pattern).
    """
    kind: str
    priority: int
    sub_skill: Optional[str]
    prompt: str


# Compiled patterns + factory. Tuple form keeps registration order stable
# and makes follow-up additions a single-line append.
_COVERAGE_RE = re.compile(r"coverage_below_threshold:(\d+(?:\.\d+)?)<(\d+(?:\.\d+)?)")
_LINT_RE = re.compile(r"lint_errors:(\d+)>(\d+)")
_COMPLEXITY_RE = re.compile(r"complexity_max:(\d+(?:\.\d+)?)>(\d+(?:\.\d+)?)")
_DRIFT_RE = re.compile(r"drift_severity_high")
_CI_CRITICAL_RE = re.compile(r"ci_critical:(\d+)>(\d+)")


def _make_coverage_action(actual: str, target: str) -> FixAction:
    return FixAction(
        kind="coverage",
        priority=_PRIORITY_COVERAGE,
        sub_skill="siae-tdd",
        prompt=(
            f"Aggiungi test per portare coverage da {actual}% a {target}%+. "
            f"Usa file uncovered da `.claude/review-evidence/<sha>.json` "
            f"sezione `metrics.coverage.per_file`. Valida path via "
            f"`jq -e .metrics.coverage.per_file evidence.json` PRIMA del fix. "
            f"Red-Green-Refactor per ogni file aggiunto. Un solo commit."
        ),
    )


def _make_lint_action(actual: str, target: str) -> FixAction:
    return FixAction(
        kind="lint",
        priority=_PRIORITY_LINT,
        sub_skill="siae-code-standards",
        prompt=(
            f"Fixa {actual} lint errors (target <= {target}). Elenco findings: "
            f"`.claude/review-evidence/<sha>.json` sezione "
            f"`metrics.lint.findings`. Valida path via "
            f"`jq -e .metrics.lint.findings evidence.json` PRIMA del fix. "
            f"Applica solo formatting/naming, NON refactoring strutturale. "
            f"Un solo commit."
        ),
    )


def _make_complexity_action(actual: str, target: str) -> FixAction:
    return FixAction(
        kind="complexity",
        priority=_PRIORITY_COMPLEXITY,
        sub_skill="siae-tdd",
        prompt=(
            f"Refactor funzione con cyclomatic complexity {actual} sotto soglia "
            f"{target}. Lista in `.claude/review-evidence/<sha>.json::"
            f"metrics.complexity.files_over_threshold` (campo `function` + "
            f"`path`). Usa pattern Extract Method o Replace Conditional with "
            f"Polymorphism. Validate path via `jq -e "
            f".metrics.complexity.files_over_threshold evidence.json` prima."
        ),
    )


def _make_drift_action() -> FixAction:
    return FixAction(
        kind="drift",
        priority=_PRIORITY_DRIFT,
        sub_skill="siae-brainstorming",
        prompt=(
            "Aggiorna design doc per coprire unplanned_files. Lista in "
            "`.claude/review-evidence/<sha>.json::spec_drift.unplanned_files`. "
            "Aggiungi sezione 'Files coinvolti' al design doc con i path "
            "mancanti. Path design doc in `.claude/review-evidence/<sha>.json::"
            "spec_drift.design_doc_path`. Validate via jq prima."
        ),
    )


def _make_ci_critical_action(actual: str, target: str) -> FixAction:
    return FixAction(
        kind="ci_critical",
        priority=_PRIORITY_CI_CRITICAL,
        sub_skill="siae-debugging",
        prompt=(
            f"Fixa {actual} CI critical security findings (SARIF). Lista in "
            f"`.claude/review-evidence/<sha>.json::metrics.ci_quality.findings` "
            f"(filter level=='error'). Per ogni finding leggere "
            f"physical_location + ruleId, applica root-cause analysis, fix "
            f"mirato. Validate via jq prima."
        ),
    )


def _make_unknown_action(reason: str) -> FixAction:
    return FixAction(
        kind="unknown",
        priority=_PRIORITY_UNKNOWN,
        sub_skill=None,
        prompt=f"unmatched block_reason: {reason!r}",
    )


def parse_block_reasons(evidence: Evidence) -> list[FixAction]:
    """Map ``Verdict.block_reasons`` atomic strings to ``FixAction`` list.

    Returns actions sorted by ``priority`` ASC so the orchestrator can simply
    pop ``actions[0]`` for the highest-priority fix. Order:
    ci_critical (0) -> lint (1) -> coverage (2) -> complexity (3) -> drift (4).
    Empty list = nothing to fix (caller should treat as AUTO_APPROVE).

    Unknown reasons are returned as ``kind="unknown"`` so the orchestrator
    can decide whether to escalate or skip — we never silently drop them.
    """
    reasons = list(getattr(evidence.verdict, "block_reasons", []) or [])
    actions: list[FixAction] = []
    for reason in reasons:
        m = _CI_CRITICAL_RE.search(reason)
        if m:
            actions.append(_make_ci_critical_action(m.group(1), m.group(2)))
            continue
        m = _COVERAGE_RE.search(reason)
        if m:
            actions.append(_make_coverage_action(m.group(1), m.group(2)))
            continue
        m = _LINT_RE.search(reason)
        if m:
            actions.append(_make_lint_action(m.group(1), m.group(2)))
            continue
        m = _COMPLEXITY_RE.search(reason)
        if m:
            actions.append(_make_complexity_action(m.group(1), m.group(2)))
            continue
        if _DRIFT_RE.search(reason):
            actions.append(_make_drift_action())
            continue
        actions.append(_make_unknown_action(reason))
    actions.sort(key=lambda a: a.priority)
    return actions
