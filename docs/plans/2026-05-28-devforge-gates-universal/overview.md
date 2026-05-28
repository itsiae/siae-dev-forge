# DevForge Gates Universal — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development`
> per implementare questo piano task per task.
>
> **REQUIRED SUB-SKILL per ogni task implementativo:** `siae-tdd` (Red-Green-Refactor)

**Goal:** I 5 gate workflow DevForge (brainstorming, plan-gate-write, tdd, pr-blind-review, pr-premortem) attivano l'enforcement su qualsiasi repository git per default, con env opt-in `DEVFORGE_GATE_SCOPE=itsiae` per ripristinare il comportamento legacy itsiae-only.

**Architettura:** Nuova lib bash condivisa `lib/scope-check.sh` espone `devforge_gate_scope_active()` che legge env var (con fallback a state file `~/.claude/.devforge-gate-scope`). I 5 hook gate source-ano la lib e sostituiscono il blocco inline `grep -qE "[/:]itsiae/"` con la chiamata alla funzione. Default `universal`, opt-in `itsiae`, fail-safe verso universal su valori non riconosciuti.

**Stack:** Bash 4+, shell test framework custom (pattern `tests/*.test.sh`), Claude Code hooks PreToolUse.

**SP:** 3 Umano / 1.5 Augmented

**Design doc:** [`../2026-05-28-devforge-gates-universal-design.md`](../2026-05-28-devforge-gates-universal-design.md)

**Branch:** `feat/skill-premortem` (estende v1.68.0 in v1.69.0)

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 0 | **Pre-task:** rebase su main + version recompute + line number re-verify | `task-00-rebase-and-version-recompute.md` | [PENDING] |
| 1 | Crea `lib/scope-check.sh` + 18 unit test | `task-01-scope-check-lib.md` | [PENDING] |
| 2 | Refactor `pr-premortem-gate` + 7 integration test | `task-02-refactor-pr-premortem-gate.md` | [PENDING] |
| 3 | Refactor `tdd-gate` + 7 integration test | `task-03-refactor-tdd-gate.md` | [PENDING] |
| 4 | Refactor `pr-blind-review-gate` + 7 integration test | `task-04-refactor-pr-blind-review-gate.md` | [PENDING] |
| 5 | Refactor `plan-gate-write` + 7 integration test | `task-05-refactor-plan-gate-write.md` | [PENDING] |
| 6 | Refactor `brainstorming-gate` (riordino + commento) + 7 integration test | `task-06-refactor-brainstorming-gate.md` | [PENDING] |
| 7 | Generalizza `skills/siae-premortem/SKILL.md` | `task-07-generalize-premortem-skill.md` | [PENDING] |
| 8 | Aggiorna `hooks/ENV_VARS.md` + `CHANGELOG.md` + bump v1.69.0 | `task-08-docs-and-version-bump.md` | [PENDING] |
| 9 | E2E smoke test su repo non-itsiae locale | `task-09-e2e-smoke-test.md` | [PENDING] |

---

## Dipendenze

- **Task 1** è prerequisito di tutti i task 2-6 (la lib deve esistere prima del refactor dei gate)
- **Task 2-5** sono indipendenti tra loro (4 hook diversi, no shared state nel branch)
- **Task 6** è indipendente da 2-5 ma richiede attenzione extra (riordino blocchi + commento cleanup)
- **Task 7** è indipendente (SKILL.md), può girare in parallelo a 2-6
- **Task 8** dipende da 1-7 (CHANGELOG riferisce a lib + 5 gate + skill)
- **Task 9** dipende da 1-8 (smoke test sull'intero refactor)

Ordine raccomandato per esecuzione seriale: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9.

---

## Criteri di completamento globale

- Tutti e 9 i task `[DONE]`
- Test totale: 18 unit (task 1) + 5×7=35 integration (task 2-6) + 6 skill (task 7) + 9 docs/version (task 8) + 10 E2E smoke + 8 global grep (task 9) = **86 test PASS** sotto `bash -euo pipefail`
- `grep -rn "grep -qE \"\\[/:\\]itsiae/\"" hooks/` → 0 match (verificato globalmente)
- `bash hooks/<gate> < fixture-acme.json` su tutti e 5 → output `block` (gate attivo fuori itsiae)
- `DEVFORGE_GATE_SCOPE=itsiae bash hooks/<gate> < fixture-acme.json` → output `{}` (rollback verificato)
- `plugin.json` e `marketplace.json` versione `1.69.0` allineata
- `CHANGELOG.md` contiene entry v1.69.0 con BREAKING-NOTE in caps

---

## Memory rilevanti applicate

- `feedback_no_regression_skill_optimization`: ogni refactor preserva comportamento esistente (test "scope=itsiae + repo itsiae → block" deve continuare a passare)
- `project_plugin_version_dual_source`: task 8 bumpa entrambi `plugin.json` (source-of-truth hook) e `marketplace.json` (visibilità marketplace)
- `feedback_plan_review_global_grep`: task 9 verifica `grep -rn "hooks/lib/scope" .` = 0 e `grep -rn "grep -qE.*itsiae" hooks/` = 0
- `feedback_test_verify_via_exit_code`: ogni test usa `assert_exit_code` o pipefail, mai `grep PASS | && commit`
- `feedback_session_start_hook_invariants`: la nuova lib non emette stdout (solo return code), no leak su pipeline JSON dei gate
