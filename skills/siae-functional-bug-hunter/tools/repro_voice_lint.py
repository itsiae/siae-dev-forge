#!/usr/bin/env python3
"""repro_voice_lint.py — validates qa_report.md against repro_voice_guide.md.

Every QA test case must obey the 10 rules V-001 through V-010 declared
in references/repro_voice_guide.md. This linter walks a Markdown file,
extracts step lines, and reports violations.

Quality Bar #5 — examples in assets/examples/*/qa_report.md must lint
PASS against this tool.

Usage:
    python3 tools/repro_voice_lint.py <qa_report.md> [<another.md> ...]

Exit code: 0 if all files pass, 1 otherwise. One violation per line on
stdout, prefixed with rule id.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_TAGS = {
    "ui-user", "api-caller", "event-publisher", "scheduler",
    "iac-operator", "batch-runner", "db-operator", "observer",
}

# Numbered step line, with optional (tag) prefix:
# "1. (ui-user) Click the button labeled \"Submit\""
STEP_RE = re.compile(r"^\s*\d+\.\s+(?:\(([a-z-]+)\)\s+)?(.+)$")

# V-001 — passive voice (English and Italian heuristics)
PASSIVE_PATTERNS = [
    re.compile(r"\b(is|are|was|were|been|being)\s+\w+ed\b", re.IGNORECASE),
    re.compile(r"\b(viene|vengono|è stato|sono stati|sono stata|sono state)\s+\w+", re.IGNORECASE),
]

# V-002 — modal verbs without instruction
MODAL_PATTERNS = [
    re.compile(r"\b(should|would|might|could|may)\b", re.IGNORECASE),
    re.compile(r"\b(dovrebbe|dovrebbero|potrebbe|potrebbero)\b", re.IGNORECASE),
]

# V-004 — multiple verbs / actions per step (heuristic: " and ", " e " between two verbs)
MULTI_VERB = re.compile(
    r"\b(?:click|tap|type|press|open|send|invoke|trigger|publish|run|execute|swipe)\b.*\b(?:and|e)\b.*\b(?:click|tap|type|press|open|send|invoke|trigger|publish|run|execute|swipe|wait|verify|inspect)\b",
    re.IGNORECASE,
)

# V-006 — "verify internally"
INTERNAL_VERIFY = re.compile(
    r"verify\s+internally|verifica\s+internamente|controlla\s+internamente",
    re.IGNORECASE,
)

# V-008 — tool-specific phrasings
TOOL_SPECIFIC = re.compile(
    r"open\s+(?:postman|insomnia|curl)|apri\s+(?:postman|insomnia|curl)",
    re.IGNORECASE,
)

# V-010 — time-without-units in race steps
RACE_KEYWORDS = re.compile(r"\b(?:concurrently|race|simultaneous|in parallel|contempor)", re.IGNORECASE)
TIME_UNIT_OK = re.compile(r"\b\d+\s*(?:ms|millisecond|s|seconds?|sec|secondi?|minuti?)\b", re.IGNORECASE)

# V-005 — vague target heuristic (button/field without label)
VAGUE_TARGET = re.compile(
    r"\b(click|tap|press|premi|premere|clicca|cliccare)\s+(?:the\s+|il\s+|la\s+)?(button|field|link|bottone|campo|link)\b(?!.*[\"'<])",
    re.IGNORECASE,
)


def lint_step(step_no: int, tag: str | None, body: str, file_lang_hint: str | None) -> list[str]:
    violations: list[str] = []

    # V-003 — missing tag
    if tag is None:
        violations.append(f"V-003 step {step_no}: missing actor tag")
    elif tag not in ALLOWED_TAGS:
        violations.append(f"V-003 step {step_no}: unknown actor tag '({tag})'")

    # V-001 — passive
    for pat in PASSIVE_PATTERNS:
        if pat.search(body):
            violations.append(f"V-001 step {step_no}: passive voice detected")
            break

    # V-002 — modal verb
    for pat in MODAL_PATTERNS:
        if pat.search(body):
            violations.append(f"V-002 step {step_no}: modal verb suggests expectation, not action")
            break

    # V-004 — multiple verbs
    if MULTI_VERB.search(body):
        violations.append(f"V-004 step {step_no}: multiple verbs/actions in one step")

    # V-005 — vague target
    if VAGUE_TARGET.search(body):
        violations.append(f"V-005 step {step_no}: vague target (no label / id)")

    # V-006 — verify internally
    if INTERNAL_VERIFY.search(body):
        violations.append(f"V-006 step {step_no}: 'verify internally' is unobservable")

    # V-008 — tool-specific
    if TOOL_SPECIFIC.search(body):
        violations.append(f"V-008 step {step_no}: tool-specific phrasing; describe the action, not the tool")

    # V-009 — language mix when lang hint set
    if file_lang_hint in ("en", "it"):
        # Simple heuristic: detect tokens unambiguously from the other language.
        en_only = re.compile(r"\b(click|tap|button|field|send|publish)\b", re.IGNORECASE)
        it_only = re.compile(r"\b(cliccare|toccare|bottone|campo|inviare|pubblicare|premere|digitare)\b", re.IGNORECASE)
        if file_lang_hint == "en" and it_only.search(body):
            violations.append(f"V-009 step {step_no}: Italian phrasing in lang=en file")
        if file_lang_hint == "it" and en_only.search(body):
            violations.append(f"V-009 step {step_no}: English phrasing in lang=it file")

    return violations


def detect_lang(text: str) -> str | None:
    # Look for a "Lang: en" or "Lang: it" line in the header.
    m = re.search(r"^\s*-\s*\*\*Lang\*\*:\s*([a-z]{2})", text, re.MULTILINE)
    if m:
        return m.group(1)
    return None


def lint_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lang_hint = detect_lang(text)
    violations: list[str] = []
    in_steps = False
    for raw in text.splitlines():
        if raw.strip().lower().startswith("**steps**"):
            in_steps = True
            step_no = 0
            continue
        if in_steps:
            # End of steps block: a blank line followed by a bold header
            if raw.strip().startswith("**Expected"):
                in_steps = False
                continue
            m = STEP_RE.match(raw)
            if not m:
                continue
            step_no += 1
            tag, body = m.group(1), m.group(2).strip()
            file_label = f"{path}:"
            for v in lint_step(step_no, tag, body, lang_hint):
                violations.append(file_label + " " + v)

            # V-010 — race step without time unit
            if RACE_KEYWORDS.search(body) and not TIME_UNIT_OK.search(body):
                violations.append(
                    f"{file_label} V-010 step {step_no}: race/concurrency step missing time unit"
                )
    return violations


def main(argv: list[str]) -> int:
    if not argv:
        sys.stderr.write("usage: repro_voice_lint.py <qa_report.md> [...]\n")
        return 2
    overall_failures = 0
    for arg in argv:
        p = Path(arg)
        if not p.is_file():
            print(f"FAIL: file not found: {arg}")
            overall_failures += 1
            continue
        violations = lint_file(p)
        if violations:
            for v in violations:
                print(v)
            overall_failures += 1
        else:
            print(f"PASS: {arg}")
    return 0 if overall_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
