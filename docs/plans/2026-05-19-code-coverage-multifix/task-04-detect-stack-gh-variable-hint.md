# Task 04 — detect_stack.py: gh variable demote-to-hint

**Fix-group:** G8
**ADR riferito:** ADR-8 (local report priorita', gh variable hint)
**Stato:** [PENDING]
**Dipendenze:** —

## File modificati

- `skills/code-coverage/scripts/detect_stack.py`
- `skills/code-coverage/scripts/tests/test_detect_stack_ext.py` (extend)

## Test (TDD-first)

1. `test_pre_existing_coverage_from_local_lcov_wins`:
   - Setup: `coverage/lcov.info` valido (global=82%) + gh var che ritorna 0
   - Atteso: `pre_existing_coverage_pct=82.0`, `pre_existing_coverage_source="local_report"`

2. `test_pre_existing_coverage_from_local_jacoco_wins`:
   - Setup: `target/site/jacoco/jacoco.xml` con missed=20/covered=80 (80%)
   - Atteso: `pre_existing_coverage_pct=80.0`, `pre_existing_coverage_source="local_report"`

3. `test_pre_existing_coverage_hint_from_gh_when_no_local`:
   - Setup: no local report, gh var ritorna 65
   - Atteso: `pre_existing_coverage_pct=0.0` (nessun local), `pre_existing_coverage_hint=65.0`, `pre_existing_coverage_source="missing"` (no local)

4. `test_pre_existing_coverage_missing_both`:
   - Setup: nessun local, nessun gh var
   - Atteso: pct=0.0, hint=0.0, source="missing"

## Implementazione

In `detect_stack.py`:

1. Refactor `main()` ordering coverage:
   ```python
   # Priorita' 1: local report
   pre_existing_pct = 0.0
   pre_existing_source = "missing"
   module_cov = []
   lcov_pct, lcov_modules = parse_lcov_info(root / "coverage" / "lcov.info")
   if lcov_modules:
       pre_existing_pct = lcov_pct
       pre_existing_source = "local_report"
       module_cov = lcov_modules
   else:
       jacoco_pct, jacoco_modules = parse_jacoco_for_existing(root / "target" / "site" / "jacoco" / "jacoco.xml")
       if jacoco_modules:
           pre_existing_pct = jacoco_pct
           pre_existing_source = "local_report"
           module_cov = jacoco_modules

   # Priorita' 2: gh variable come HINT (non source of truth)
   gh_hint, _ = read_github_coverage_variable(root)
   ```

2. Estendi output JSON:
   ```python
   "pre_existing_coverage_pct": pre_existing_pct,
   "pre_existing_coverage_source": pre_existing_source,
   "pre_existing_coverage_hint": gh_hint,
   ```

3. Estendi `_OUTPUT_SCHEMA_DEFAULTS`: `"pre_existing_coverage_hint": 0.0`.

## Criterio di accettazione

- 4/4 test PASS
- Test esistenti che dipendevano da `gh variable` come truth continuano a passare (compatibilita': il campo `pre_existing_coverage_pct` resta presente)
