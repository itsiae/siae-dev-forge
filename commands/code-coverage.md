---
name: code-coverage
description: "Enterprise test generation agent invoked via /code-coverage. Analyzes a repository, infers tech stack, and generates deterministic unit tests targeting >=70% coverage."
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebFetch
---

# Enterprise Test Generation Agent — Command Mode

**This file is the command-mode entry point. Load `skills/code-coverage/SKILL.md` immediately after loading this file — all execution logic, phase descriptions, global principles, output schema, and supporting files are defined there.**

**This skill activates ONLY when the user explicitly types `/code-coverage`.
Do not self-activate on any semantic trigger.**

---

## INPUT MODE — Identify Target Repository

Before executing any phase, check the invocation arguments:

- If a path or URL is present in the arguments, use it directly and **skip the question below**.
- Otherwise, ask the user exactly:

```
Choose input mode:
  1) GitHub  — provide URL; branch defaults to `main` if omitted (no confirmation needed); subdirectory is optional
  2) Local   — provide absolute path on disk

Which mode? (1 or 2)
```

Block the workflow until the target is unambiguously identified. Do not proceed to Phase 1 with an empty or ambiguous target.
If the user provides a GitHub URL without branch or subdirectory, use `main` as branch and proceed without asking.

### Invocation Examples

```
/code-coverage /path/to/repo                 — local path, skips question
/code-coverage https://github.com/owner/repo — GitHub URL, skips question, branch = main
/code-coverage                               — no args, asks the question above
```

---

## Global Execution Principles

See **SKILL.md — GLOBAL EXECUTION PRINCIPLES** for all six principles, including:
- Principle 4 (Vitest-first rule with all 4 conditions evaluated in order)
- Principle 5 (per-priority coverage thresholds: P1 ≥ 80%, P2 ≥ 70%, P3 ≥ 60%, global ≥ 70%)

---

## Workflow — 7 Phases

See **SKILL.md — WORKFLOW — 7 Phases** for the complete phase descriptions, including:
- Phase 5 Processing order (ALL P1 before P2; ALL P2 before P3; sorted by LOC descending within tier)
- Phase 5 Coverage Gate (context-safe redirect + Early Stop condition)
- Phase 6 → Phase 7 Gate

---

## Output — 9 Required Blocks

See **SKILL.md — OUTPUT — 9 Required Blocks** for the complete schema, including Block 8 column definitions (`Module | Lines% | Branch% | Threshold | Status`).

---

## Supporting Files

See **SKILL.md — SUPPORTING FILES** for the full asset and script inventory.
