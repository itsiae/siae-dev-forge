# Telemetria adoption DevForge — Layer 1 (producer raw) — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: usa `siae-subagent-development` (stessa sessione) o
> `siae-executing-plans` (sessione separata) per implementare task per task.

**Goal:** emettere su S3 i segnali raw che rendono misurabile l'aderenza al workflow DevForge
per-developer (`task_adoption`), i bypass dei gate (`gate_bypassed`) e la join-key
`task_id` sugli outcome — fondazione del Layer 2 (insight infra + read API).
**Architettura:** solo producer (hook + lib bash + 1 modalità Python). Eventi raw additivi
schema v2; il Lambda ingest li passa trasparenti (nessuna modifica infra). No score nel producer.
**Stack:** Bash (hooks `stop-gate`/`session-start`/`post-commit-review`, lib `adoption-emit.sh`),
Python (`lib/adoption-analyzer.py`), test bash `tests/hooks/*.test.sh` + pytest.
**SP:** Umano ~5 / Augmented ~2
**Design doc:** `docs/plans/2026-06-14-devforge-adoption-telemetry-design.md`
**API contract (Layer 2):** `docs/plans/2026-06-14-devforge-telemetry-insights-api.openapi.yaml`

---

## Nota di refinement implementativo (vs design §5.4)

Il design §5.4 elencava `devforge_read_task_ledger` (bash) + `devforge_emit_task_adoption`.
Per **evitare bug di escaping JSON in bash** e **riusare la single-source dei 5 core skill** già
presente in `lib/adoption-analyzer.py` (`CORE_SKILLS`, righe 25-31), la **lettura del ledger e
la costruzione del meta JSON sono centralizzate in Python** (nuova modalità
`adoption-analyzer.py --task-adoption-meta <task_id>`, Task 01). `lib/adoption-emit.sh` (Task 02)
è un thin wrapper bash che calcola il `task_id` e invoca la modalità Python. Questo soddisfa gli
stessi AC (1-3, 8) con meno superficie di rischio. Nessun `devforge_read_task_ledger` bash
separato.

---

## Indice Task

| # | Task | File | Stato |
|---|------|------|-------|
| 1 | `adoption-analyzer.py --task-adoption-meta` (read ledger + meta JSON, riuso CORE_SKILLS) | `task-01-task-adoption-meta-python.md` | [DONE] |
| 2 | `lib/adoption-emit.sh` — `devforge_emit_task_adoption` (wrapper best-effort) | `task-02-adoption-emit-lib.md` | [DONE] |
| 3 | Wiring in `hooks/stop-gate` `_devforge_emit_session_end` | `task-03-stop-gate-wiring.md` | [DONE] |
| 4 | `hooks/session-start` — `gate_bypassed` enforcement_off (pipefail-safe) | `task-04-session-start-enforcement-off.md` | [DONE] |
| 5 | `hooks/post-commit-review` — detection `--no-verify`/`-n` → `gate_bypassed` | `task-05-post-commit-no-verify.md` | [DONE] |
| 6 | `hooks/post-commit-review` — `task_id` su commit_created/pr_* | `task-06-post-commit-task-id-joinkey.md` | [DONE] |
| 7 | No-regression + registrazione test + version bump | `task-07-no-regression-and-release.md` | [DONE] |

## Dipendenze

- **Precondizione globale:** feature branch da `main` (via `siae-git-workflow`). Branch corrente
  `fix/installer-network-resilience` NON è la base. Per i Task 5-6 (`post-commit-review`):
  rebase da `main` dopo eventuale merge di `feat/telemetry-kpi-enrichment` (overlap su quel file,
  design §9) — verificare conflitti prima di iniziare.
- Task 2 dipende da Task 1 (usa `--task-adoption-meta`).
- Task 3 dipende da Task 2 (source di `adoption-emit.sh`).
- Task 4 indipendente (file diverso: `session-start`).
- Task 5 e Task 6 toccano lo **stesso file** `hooks/post-commit-review` → eseguire **5 poi 6**
  in serie (evita conflitti); Task 6 calcola `TASK_ID` una volta, riusato anche dal blocco Task 5.
- Task 7 dipende da TUTTI (finale: suite completa + count consistency + bump versione).

## Mappa AC → Task

| AC (design §10) | Task |
|---|---|
| AC1 task_adoption emesso | 1, 2, 3 |
| AC2 fuori scope → niente | 1 |
| AC3 ledger vuoto → niente | 1 |
| AC4 enforcement_off | 4 |
| AC5 git_no_verify (3 casi) | 5 |
| AC6 task_id su outcome | 6 |
| AC7 best-effort non-bloccante | 2, 3, 4, 5 |
| AC8 no duplicazione lista core | 1 |
| AC9 no modifica Lambda/Terraform | 7 (verifica) |
| AC10 no-regression test count | 7 |
