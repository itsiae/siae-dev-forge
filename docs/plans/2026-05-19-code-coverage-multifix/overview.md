# Code-Coverage Skill — Multi-Fix Plan

**Design doc:** `../2026-05-19-code-coverage-multifix-design.md`
**Topic:** code-coverage multi-fix da multi-blind review 2026-05-19
**REQUIRED SUB-SKILL:** siae-tdd
**Execution mode:** Parallel-batched (NO sub-agent worktree — preserva 1549 righe unstaged)
**Target compliance:** 67% → ~95%

## Indice task

| ID | Task | Stato | Fix-group |
|----|------|-------|-----------|
| 01 | estimate_size.py: anti-greedy P1 + generated-file skip | [PENDING] | G3, G4 |
| 02 | detect_stack.py: orchestration-only gate (IaC/Terragrunt) | [PENDING] | G1 |
| 03 | detect_stack.py: manifest_root surfacing + monorepo extend | [PENDING] | G2 |
| 04 | detect_stack.py: gh variable demote-to-hint | [PENDING] | G8 |
| 05 | detect_stack.py: test_infrastructure co-presence fix | [PENDING] | G12 |
| 06 | select_command.py: manifest_root + JaCoCo plugin pre-check | [PENDING] | G2, G10 |
| 07 | validate_env.py: manifest_root path resolution | [PENDING] | G2 |
| 08 | priority-rules.json: skip_patterns + generated_file_markers | [PENDING] | G4 |
| 09 | SKILL.md compaction + new lib/phase{1,6}-*.sh + references | [PENDING] | G5 |
| 10 | references/phase-5-generation.md: preserve-existing gate | [PENDING] | G6 |
| 11 | SKILL.md wiring: probe-first + drop jq + eval hardening | [PENDING] | G7, G9, G11 |
| 12 | Verification: smoke E2E sui 4 archetipi + pytest + LOC check | [PENDING] | — |

## Dipendenze

- Task 01-08 (script + data): indipendenti, parallel-eseguibili
- Task 09 (SKILL.md compaction): dipende da 01-08 (schema fields nuovi devono esistere)
- Task 10 (refs phase-5): indipendente da 09
- Task 11 (SKILL.md wiring): dipende da 09
- Task 12 (verification): dipende da TUTTI

## Constraint critico (applica a TUTTI i task)

**Preservare 1549 righe unstaged** in `skills/code-coverage/`. NO sub-agent worktree.
NO overwrite massivo. **Ogni task usa Edit (non Write) per file esistenti**.

**Procedura obbligatoria per ogni task:**
1. `git status --porcelain` prima di iniziare → annota file modificati
2. Read del file target prima di Edit (verifica stato unstaged corrente)
3. Edit puntuale con `old_string` che riflette lo stato attuale (non HEAD)
4. `git status --porcelain` dopo → diff atteso = quello del task, no overwrite altrui

## Criteri di accettazione globali

1. Tutti i test esistenti in `scripts/tests/` continuano a passare
2. `SKILL.md` ≤ 100 LOC
3. Zero `jq` references in `SKILL.md`
4. `detect_stack.py` su `itsiae/dataplatform-dwh-etl` → `orchestration_only=true`
5. `detect_stack.py` su `itsiae/uptime-console-backend` → `manifest_root="modules/service/lambda"`
6. `estimate_size.py` su `itsiae/pae-pae-services-be` → riduzione P1 ≥50% vs baseline 90%

## SP residui

- Human: 5-7 (~60% lavoro gia' assorbito in unstaged)
- Augmented: ~3
