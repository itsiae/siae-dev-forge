"""Drools `.drl` PR-gate review check (ADR-007 + EC-29).

Semgrep CE non parsa Drools DSL. Mitigation: review esplicita su PR che
modificano `*.drl` via UNA delle 2 forme di "segnalazione esplicita":

Form A (PR-level): label `drools-security-reviewed` (security team adds it)
Form B (file-level): file header `// drools-security-reviewed: <Jira> by:<email@siae.it> on:<YYYY-MM-DD>`

Goal #2 "no bloccare tutto": missing form → WARNING (NON BLOCK).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DROOLS_REVIEW_LABEL = "drools-security-reviewed"

DROOLS_HEADER_RE = re.compile(
    r"^//\s*drools-security-reviewed:\s+"
    r"([A-Z]+-\d+)\s+"
    r"by:([a-zA-Z0-9._%+-]+@siae\.it)\s+"
    r"on:(\d{4}-\d{2}-\d{2})\s*$",
    re.MULTILINE,
)


@dataclass
class DroolsReviewResult:
    ok: bool
    method: str  # "form-a-label" | "form-b-header" | "no-drools-files" | "missing"
    message: str = ""


def check_drools_review(
    modified_files: Iterable[Path],
    pr_labels: Iterable[str],
) -> DroolsReviewResult:
    """Verifica che ogni `.drl` modificato abbia Form A OR Form B."""
    drl_files = [Path(p) for p in modified_files if str(p).endswith(".drl")]

    if not drl_files:
        return DroolsReviewResult(ok=True, method="no-drools-files")

    # Form A: PR-level label
    if DROOLS_REVIEW_LABEL in pr_labels:
        return DroolsReviewResult(ok=True, method="form-a-label")

    # Form B: tutti i .drl devono avere header valido
    missing: list[Path] = []
    for f in drl_files:
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            missing.append(f)
            continue
        if not DROOLS_HEADER_RE.search(content):
            missing.append(f)

    if missing:
        files_str = "\n  - ".join(str(f) for f in missing)
        return DroolsReviewResult(
            ok=False,
            method="missing",
            message=(
                f"WARNING: {len(missing)} .drl file(s) modificati senza Drools "
                f"security review (ADR-007).\n"
                f"Add PR label '{DROOLS_REVIEW_LABEL}' (Form A) OR header comment "
                f"`// drools-security-reviewed: <JIRA> by:<email@siae.it> on:<YYYY-MM-DD>` "
                f"in each .drl file (Form B).\n"
                f"Missing in:\n  - {files_str}"
            ),
        )

    return DroolsReviewResult(ok=True, method="form-b-header")
