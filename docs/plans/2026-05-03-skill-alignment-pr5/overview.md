# PR-5 Discovery & Advisory — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per implementare questo piano task per task.

**Goal:** Audit completo description 39 skill in pattern "Use when X" + hook PostToolUse advisory (non-blocking) + suite test attivazione Bedrock per misurare baseline e regressione.

NB: design doc cita "39 skill" come stima preliminare; conta reale `ls skills/` = 39. Aggiornato.

**Architettura:**
- Edit frontmatter 39 skill
- Bash hook `skill-advisory` (advisory only, exit 0 sempre)
- State file `.claude/projects/<project>/.skill-state` JSON
- Test runner Bedrock Sonnet 4.6 + Python evaluator

**Stack:** Markdown frontmatter, bash hooks, Python 3, AWS Bedrock SDK (boto3).

**SP:** 3 SP-Augmented.

**Design doc:** `../2026-05-03-skill-alignment-design.md` (sezioni 4.1-4.5).

**Vincolo critico:** NO-REGRESSION. Baseline activation accuracy misurata Task 06 PRIMA di description rewrite (Task 07-09). Diff per-skill controllato Task 14.

**Cost cap test Bedrock:** $5 hard-stop CloudWatch alarm. Stima ~$2/ciclo Sonnet, ~$0.70 Haiku.

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | Setup `tests/skill-activation/` directory + README + cost-cap doc | `task-01-test-scaffold.md` | [DONE] |
| 2 | Scrivi `cases.yml` (30 prompt rappresentativi) | `task-02-cases-yml.md` | [DONE] |
| 3 | Scrivi `run.sh` (Bedrock runner Sonnet 4.6 / Haiku fallback) | `task-03-run-sh.md` | [DONE] |
| 4 | Scrivi `evaluator.py` (output parser + match logic + report markdown) | `task-04-evaluator-py.md` | [DONE] |
| 5 | Smoke test runner end-to-end con 3 prompt (validazione setup) | `task-05-smoke-test.md` | [PENDING] |
| 6 | Run baseline completa 30 prompt + commit `baseline-2026-05-03.md` | `task-06-baseline-run.md` | [PENDING] |
| 7 | Description audit batch 1 (skill 1-13: backbone già fatte PR-4 verifica + early non-backbone) | `task-07-description-audit-batch1.md` | [DONE] |
| 8 | Description audit batch 2 (skill 14-26: domain skills) | `task-08-description-audit-batch2.md` | [DONE] |
| 9 | Description audit batch 3 (skill 27-37: tooling + meta) | `task-09-description-audit-batch3.md` | [DONE] |
| 10 | Hook `skill-advisory` implementation (PostToolUse advisory) | `task-10-hook-skill-advisory.md` | [PENDING] |
| 11 | State file `.skill-state` schema + writer hooks (brainstorm/debug/tdd PostToolUse) | `task-11-state-file-writers.md` | [PENDING] |
| 12 | Registra hook in `hooks/hooks.json` + plugin manifest | `task-12-register-hook.md` | [PENDING] |
| 13 | Verification tone-down (rimuovi 4+ "ALWAYS/NEVER", aggiungi "Eccezioni" sezione) | `task-13-verification-tone-down.md` | [PENDING] |
| 14 | Run post-PR + diff vs baseline + regression check no-regression | `task-14-post-pr-run-diff.md` | [PENDING] |
| 15 | Final validation (39/39 description "Use when X", hook attivo, KPI report) | `task-15-validation.md` | [PENDING] |

## Dipendenze

- Task 01-04 indipendenti tra loro (file diversi)
- Task 05 dipende da 01-04
- Task 06 dipende da 05 (smoke OK)
- Task 07-09 indipendenti tra loro (batch separati di skill diverse)
- Task 10-12 sequenziali (hook → state → register)
- Task 13 indipendente
- Task 14 dipende da 06 (baseline) + 07-09 (description rewrite) + 10-12 (hook attivo)
- Task 15 dipende da 14

## Criteri accettazione PR

- 39/39 skill description in pattern "Use when X"
- Hook `skill-advisory` registrato in `hooks/hooks.json` PostToolUse
- State file `.skill-state` scritto correttamente da brainstorm/debug/tdd hook
- Report `baseline-2026-05-03.md` + `report-post-pr5-YYYY-MM-DD.md` pubblicati
- `activation_accuracy` post ≥ baseline +0pp (no regression) e ideal target +15pp
- `chain_completeness` post ≥ baseline
- Cost test Bedrock totale <$5 (sommando smoke + baseline + post)
