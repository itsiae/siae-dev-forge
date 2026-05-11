# siae-qa v2.1.0 Residual Fixes — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: usa `siae-executing-plans` per eseguire questo piano in sessione separata, oppure `siae-subagent-development` per dispatch parallelo in-session.

**Goal:** Chiudere 5 gap residui MEDIUM trovati dalla simulazione end-to-end di siae-qa v2.0.0 sulle 3 golden fixture, portando la skill a Gold tier consolidato (43→48/50 scorecard).

**Architettura:** 7 ADR (001-007) implementati come clarification patch non-breaking su SKILL.md + XRAY-TEMPLATES.md + validator Python + golden fixture. Bump version 2.0.0 → 2.1.0.

**Stack:** Markdown skill spec + JSON Schema + Python 3.10+ validator + golden fixture JSON.

**SP:** 11 Umano / 4.5 Augmented (rivisto post 5-case simulation: aggiunto Task 11 bug fix G-DB-5 schema regex 1-line, +0.5 SP)

**Design doc:** `docs/plans/2026-05-11-siae-qa-v21-residual-design.md` (iter 4, PASS spec-review)

**Branch target:** `feat/siae-qa-v21-residual`

---

## Indice Task

| # | Task | File | SP | Stato |
|---|------|------|---:|-------|
| 1 | Estendere tabella regole di esplosione con strict/non-strict numerico + string length opt-in (ADR-001/002/003) | `task-01-skill-explosion-table.md` | 2 | [DONE] |
| 2 | Aggiornare prompt Matrix A/B con POS unification + NEG collapse + B-rows conditional (ADR-007) | `task-02-skill-adr007-matrix-prompts.md` | 2 | [DONE] |
| 3 | Prescrivere multi-step per azioni mutating in Phase 4b (ADR-005) | `task-03-skill-adr005-phase4b-multistep.md` | 1 | [DONE] |
| 4 | Aggiornare Anti-Razionalizzazione + Vincoli Non Negoziabili + version 2.1.0 + changelog | `task-04-skill-vincoli-version.md` | 1 | [DONE] |
| 5 | Aggiungere gerarchia entity naming a XRAY-TEMPLATES.md (ADR-004) | `task-05-xray-entity-naming.md` | 0.5 | [DONE] |
| 6 | Aggiungere domanda strict vs non-strict al question-tree Backend | `task-06-question-trees-update.md` | 0.5 | [DONE] |
| 7 | Estendere validator con WARN channel + check_neg_numeric_has_edge_low (ADR-006) | `task-07-validator-warn-channel.md` | 1.5 | [DONE] |
| 8 | Verifica entity `Opera` su 3 file golden role_based (ADR-004 compliance gate) | `task-08-golden-role-entity.md` | 0.5 | [DONE] |
| 9 | Aggiungere step "side-effect not occurred" ai 4 TC error mutating | `task-09-golden-mutating-step.md` | 0.5 | [DONE] |
| 10 | Re-run simulazione 3 fixture + verifica Criterio #7 (diff strutturale) | `task-10-rerun-sim-verify.md` | 1 | [DONE] |
| 11 | **BUG FIX G-DB-5** — regex `matrix_row_id` schema accetta solo `[ABC]-\d{3}` → estendi a `[A-Z]-\d{3}` per spec con 4+ entità | `task-11-schema-regex-bugfix.md` | 0.5 | [DONE] |

## Dipendenze

- **Task 1-4** modificano `skills/siae-qa/SKILL.md` → vanno eseguiti in **sequenza** per evitare merge conflict (1 → 2 → 3 → 4).
- **Task 5** (XRAY-TEMPLATES.md), **Task 6** (question-trees.md), **Task 7** (validator.py), **Task 8** (role_based golden), **Task 9** (mutating golden) sono **indipendenti tra loro** e dai Task 1-4: dispatch parallelo possibile.
- **Task 10** (re-run sim + verifica) **dipende da TUTTI** i task precedenti completati.
- Ordine ottimale: `[1→2→3→4]` sequenziale + `[5,6,7,8,9]` parallelo → `10` finale.

## Criteri di Acceptance Globali

Il piano è completo (= tutti task `[DONE]`) se e solo se:
1. `git diff main..feat/siae-qa-v21-residual --stat` mostra modifiche a tutti i file listati nella tabella "Componenti Toccati" del design.
2. `python3 skills/siae-qa/reference/scripts/validate_outputs.py --m-final ... --tc-draft ... --certificate ...` esce con `exit 0` su tutte e 3 le golden fixture (PASS o WARN, no FAIL).
3. Re-run simulazione produce delta strutturale rientrante nel Criterio #7 rivisto (vedi Task 10 per i bound).
4. `grep "^version:" skills/siae-qa/SKILL.md` restituisce `version: 2.1.0`.
5. Changelog inline nel frontmatter cita tutti gli ADR-001..007.

## Risk Register

| Risk | Mitigation |
|------|------------|
| Modifiche a SKILL.md rompono il flusso di parsing automatico DevForge | Verifica con `siae-verification` post-Task 4 |
| Validator extension introduce false-positive WARN | Task 7 include unit test su synthetic input |
| Cascading entity rename in golden role_based incompleto | Task 8 include grep `"opere"` post-edit per verifica 0 occorrenze residue |
| Re-run simulazione diverge oltre Criterio #7 | Task 10 documenta delta per fixture; se fail, blocca PR e itera |
