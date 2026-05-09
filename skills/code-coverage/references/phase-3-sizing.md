# Phase 3 — Repository Sizing

## Purpose
Classify the repository as SMALL / MEDIUM / LARGE / VERY_LARGE to determine
the execution strategy (single-session vs. phased enterprise mode).
**Run `scripts/estimate_size.py <repo_path> --file-list` to classify the repo and obtain a per-file LOC ranking. The `--file-list` flag is required — it produces the `file_list` array consumed by Phase 5 for intra-priority ordering (highest LOC processed first).**

---

## Classification Thresholds

Thresholds are defined in `assets/priority-rules.json` → `module_classification`. `estimate_size.py` reads that file directly and applies the rules. The resulting class is one of: **SMALL / MEDIUM / LARGE / VERY_LARGE**.

**Rule:** If file count and LOC fall in different classes, `estimate_size.py` uses the higher class.

Key behavioral implications:
- **SMALL / MEDIUM** → single-session processing (no batch plan required)
- **LARGE / VERY_LARGE** → phased enterprise mode (batch plan saved to `.code-coverage/batch-plan.json`)

Additionally: if `pre_existing_coverage_pct` from Phase 1 is ≥ 70%, declare the global target already met and skip Phases 5–7. Report existing coverage in Block 8 and suggest specific uncovered modules in Block 9.

---

## File Counting Rules

`estimate_size.py` counts **source files only** — not test files, not config, not assets.

**Include:**
- `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.mjs`
- `*.py`
- `*.java`, `*.kt`
- `*.go`
- `*.rs`
- `*.cs`
- `*.dart`
- `*.rb`, `*.php`, `*.scala`

**Exclude (same as Phase 1 walk exclusions):**
```
node_modules/  dist/  build/  out/  target/  .git/  vendor/
coverage/  __pycache__/  .venv/  .next/  .nuxt/  .svelte-kit/
```

**Also exclude test files:**
```
*.spec.ts  *.spec.js  *.test.ts  *.test.js
*.spec.py  *_test.py  test_*.py
*Test.java  *Spec.kt  *_test.go
```

---

## Module Count

A "module" for sizing purposes is:
- One `.ts`/`.js` file that exports at least one function/class
- One `.py` file with at least one function or class definition
- One `.java`/`.kt` file with at least one class
- One `.go` file with at least one exported function

`estimate_size.py` estimates module count as `source_file_count × 0.85`
(accounting for re-export files, barrel files, and config-only files).

---

## Phased Enterprise Mode

When class = LARGE or VERY_LARGE, **emit this exact string**:

```
Repository exceeds safe single-session capacity. Switching to phased enterprise mode.
```

Then present the batch plan:

```
PHASED EXECUTION PLAN
Total source files: <N>
Total estimated LOC: <N>
Batch size: <max_files_per_batch>
Estimated batches: <N>

Batch 1: P1 modules (critical business logic) — <N> files
Batch 2: P1 modules continued — <N> files
Batch 3: P2 modules (utilities) — <N> files
...

Batch plan will be saved to: <repo_root>/.code-coverage/batch-plan.json
Do you approve saving the batch plan? (Required to continue phased mode)
```

**Do not proceed without user approval on the batch plan save location.**

---

## Batch Plan File Format

`.code-coverage/batch-plan.json` (written to target repo with approval):

```json
{
  "created_at": "2026-05-07T12:00:00Z",
  "repo_path": "<path>",
  "size_class": "LARGE",
  "total_source_files": 312,
  "total_loc": 38500,
  "completed_batches": [],
  "pending_batches": [
    {
      "id": 1,
      "priority": "P1",
      "files": ["src/services/auth.ts", "src/services/payment.ts"],
      "status": "pending"
    }
  ],
  "coverage_summary": {}
}
```

---

## Output Contract

`estimate_size.py` must produce:

```json
{
  "repo_path": "<path>",
  "file_count": 142,
  "loc": 18420,
  "module_count": 120,
  "class": "MEDIUM",
  "breakdown": {
    "typescript": {"files": 98, "loc": 12300},
    "python": {"files": 44, "loc": 6120}
  },
  "file_list": [
    {"path": "src/services/payment.ts", "loc": 412, "lang": "typescript"},
    {"path": "src/utils/formatter.ts", "loc": 87, "lang": "typescript"}
  ]
}
```

`file_list` is sorted by `loc` descending. It is produced only when `--file-list` flag is passed (omit for quick size-only checks). Phase 5 uses this array to order files within each priority level: highest LOC processed first maximizes coverage gain per token spent.
