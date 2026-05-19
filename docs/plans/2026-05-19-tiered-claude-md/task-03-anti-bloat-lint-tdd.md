---
task: 03
title: TDD anti-bloat-lint.py
status: PENDING
estimate_min: 45
type: TDD
depends_on: [01]
---

# Task 03 — TDD `anti-bloat-lint.py`

## Obiettivo

Implementare via TDD lint script che valida ogni CLAUDE.md generato contro
le best practice anti-bloat Anthropic (post 14 mag 2026).

## File da creare

1. `skills/siae-codebase-map-tiered/scripts/anti-bloat-lint.py` (~80 righe)
2. `tests/test_anti_bloat_lint.py` (~80 righe pytest)
3. `tests/fixtures/claude-md-samples/` con fixture:
   - `bloated-l1.md` (300 righe, mix di codice e descrizioni)
   - `lean-l1.md` (150 righe, focalizzato)
   - `duplicated-l2.md` (L2 che ripete 80% del parent L1)

## CLI signature

```bash
python3 anti-bloat-lint.py <file_or_dir> [--parent-context <parent_claude_md>]
```

Output JSON:
```json
{
  "file": "./api/CLAUDE.md",
  "lines": 187,
  "warnings": [
    {"rule": "line_count", "msg": "...", "severity": "WARN"},
    {"rule": "parent_overlap", "msg": "...", "severity": "WARN"}
  ],
  "errors": []
}
```

Exit code: 0 sempre (lint advisory, non bloccante).

## Regole

| Rule | Soglia | Severity |
|---|---|---|
| `line_count` | file >200 righe | WARN |
| `parent_overlap` | >70% match testuale con parent (se `--parent-context` fornito) | WARN |
| `placeholder` | contiene `TBD`/`TODO`/`<...>` | WARN |
| `missing_import` | L2/L3 senza riga `@<parent>/CLAUDE.md` | WARN |
| `empty_sections` | header `##` senza contenuto sotto | WARN |

## TDD cycle

**RED 1:** `test_lint_warns_on_bloated_file`
- Arrange: fixture `bloated-l1.md` (300 righe)
- Act: lint
- Assert: `warnings` contiene rule `line_count`

**RED 2:** `test_lint_warns_on_parent_overlap`
- Arrange: `duplicated-l2.md` + parent fixture
- Act: lint con `--parent-context`
- Assert: `warnings` contiene rule `parent_overlap`

**RED 3:** `test_lint_clean_file_no_warnings`
- Arrange: `lean-l1.md`
- Act: lint
- Assert: `warnings == []`, exit 0

**RED 4:** `test_lint_dir_recursive`
- Arrange: directory con 3 CLAUDE.md misti
- Act: lint dir
- Assert: output JSON è array, 1 entry per file

**RED 5:** `test_lint_always_exit_zero`
- Act: lint su file con 5 warning
- Assert: exit code 0 (advisory, non bloccante)

## Criteri di accettazione

1. ✅ 5 test pytest PASS
2. ✅ Coverage >=85%
3. ✅ Exit code 0 sempre (anche con warning)
4. ✅ Output JSON parsabile
5. ✅ Nessun import esterno oltre stdlib

## Definition of Done

- Script + test creati
- 5/5 PASS, coverage >=85%
- Commit: `feat(skills): anti-bloat-lint.py per CLAUDE.md best practice`
