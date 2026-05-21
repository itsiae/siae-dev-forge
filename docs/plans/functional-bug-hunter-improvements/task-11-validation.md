# Task 11 — Validation + CHANGELOG + version bump

**Stato**: [PENDING] · **Effort**: 30min · **File toccati**: 3 (SKILL.md frontmatter + CHANGELOG.md + plugin.json)

## Goal

Validazione finale + bump versione skill da 1.1.0 → 1.2.0 + CHANGELOG
entry che riferisce a audit-report e design doc.

## Acceptance

1. SKILL.md frontmatter: `skill_semver: 1.2.0`.
2. CHANGELOG.md ha entry `## [1.2.0] - 2026-05-21` con:
   - Sezione `### Added`: path_feasibility script, modes dispatcher,
     command file, BP-024..027, references/README, pipeline_internals,
     hallucination_guard.
   - Sezione `### Changed`: SKILL.md compress, dedup hallucination guard.
   - Reference a `audit-reports/functional-bug-hunter-audit-2026-05-21.md`.
3. Smoke test eseguito:
   - `python3 scripts/path_feasibility.py --help` exit 0.
   - `python3 scripts/run_lock.py dispatch strict STOP_AMBIGUOUS_SCOPE`
     stampa `CONTINUE`, exit 0.
   - `python3 scripts/run_lock.py dispatch interactive STOP_AMBIGUOUS_SCOPE`
     stampa `PAUSE`, exit 0.
   - `python3 scripts/run_lock.py dispatch report-only STOP_AMBIGUOUS_SCOPE`
     stampa `DEGRADE`, exit 0.
   - `wc -l skills/siae-functional-bug-hunter/SKILL.md` ≤220 LOC.
   - Description char count ≤1024.
4. Plugin marketplace `.claude-plugin/marketplace.json` aggiornato se
   contiene version pinned (verificare).

## Implementation

1. Edit `SKILL.md` frontmatter: `skill_semver: 1.1.0` → `1.2.0`.
2. Edit `CHANGELOG.md` aggiungendo entry in cima.
3. Read `.claude-plugin/marketplace.json` e `plugin.json`: se hanno
   `version` pinned per la skill, allineare.
4. Run smoke test bash.
5. Report risultato finale.
