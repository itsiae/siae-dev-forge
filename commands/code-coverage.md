---
name: code-coverage
description: "Enterprise test generation agent invoked via /code-coverage. Analyzes a repository, infers tech stack, and generates deterministic unit tests targeting >=70% coverage. Zero user runtime interactions."
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - WebFetch
---

# Enterprise Test Generation Agent — Command Mode

**This file is the command-mode entry point. Load `skills/code-coverage/SKILL.md` immediately after loading this file — all execution logic, INPUT MODE policy, phase descriptions, global principles, output schema, and supporting files are defined there.**

**This skill activates ONLY when the user explicitly types `/code-coverage`. Do not self-activate on any semantic trigger.**

---

## Quick reference

- **INPUT MODE**: deterministic, autonomous (see `SKILL.md` — `INPUT MODE`).
  - No args → use `$(pwd)`.
  - Local absolute path → use it.
  - GitHub URL → auto-clone in `mktemp -d` (default branch=`main`).
  - Malformed URL OR missing path → emit single error message and STOP.
  - NEVER ask user — fully autonomous.

- **GLOBAL EXECUTION PRINCIPLES (7)**: see `SKILL.md` — Autonomous Execution Policy, Context-safety, Determinism, Vitest-first, Per-priority coverage thresholds, Progressive disclosure, State persistence + cache.

- **WORKFLOW**: Phase 0 (init) → Phase 1 (Discovery) → Phase 2 (Strategy) → Phase 3 (Sizing) → Phase 4 (Environment) → Phase 5 (Generation, conditional ordering D1) → Phase 6 (Coverage) → Phase 7 (Repair, max 3 iter). See `SKILL.md` — `WORKFLOW`.

- **OUTPUT**: Block 1, 5, 8 sempre presenti; Block 4, 6, 9 conditional. See `SKILL.md` — `OUTPUT — Conditional Blocks`.

### Invocation examples

```
/code-coverage /path/to/repo                 — local absolute path
/code-coverage https://github.com/owner/repo — GitHub URL, branch = main
/code-coverage                               — no args, uses $(pwd)
```

---

## Supporting files

See `SKILL.md` — `SUPPORTING FILES` for the full asset/script/lib/template inventory.
