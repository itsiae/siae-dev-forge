# Review Evidence Hook — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per
> implementare questo piano task per task (stessa sessione, parallel-safe).
> In alternativa `siae-executing-plans` per sessione separata.

**Goal:** Aggiungere un hook deterministico `review-evidence` che pre-calcola
coverage, lint, complessità ciclomatica, spec-drift e fetcha artefatti SARIF
dalla CI, scrivendo un JSON cacheable per SHA che gli agent review consumano
come renderer (zero ricalcolo soggettivo).

**Architettura:** Hook bash thin wrapper `hooks/review-evidence` →
orchestrator Python `lib/review-evidence/collector.py` → per-stack collectors
(Java/TS/Python/HCL) + CI-fetch SARIF + spec-drift detector → atomic write
in `.claude/review-evidence/<sha>.json` → renderer in `code-reviewer.md` /
`spec-reviewer.md` (Step 0.5 evidence-loading).

**Stack:** Bash (hook), Python 3 (lib + collectors + tests), Markdown (agent
docs + skill command), JSON Schema v1.

**SP totale:** 22.0 umano / 8.7 augmented (16 task, post plan-review iter 2)

**Design doc:** `docs/plans/2026-05-12-review-evidence-hook-design.md`

---

## Indice Task

| # | Task | File | SP | Stato |
|---|------|------|----|-------|
| 0 | Test infrastructure bootstrap (root conftest + sys.path) | `task-00-test-infra.md` | 0.5 | [PENDING] |
| 1 | Schema JSON v1 + dataclass + serialization | `task-01-schema.md` | 1.5 | [PENDING] |
| 2 | Atomic write con iCloud retry + fallback | `task-02-atomic-write-icloud.md` | 1.0 | [PENDING] |
| 3 | Hook bash entry point + hooks.json + bypass state file | `task-03-hook-bash-entry.md` | 1.5 | [PENDING] |
| 4 | Collector framework orchestrator (collector.py) | `task-04-orchestrator.md` | 2.0 | [PENDING] |
| 5 | Python collector (coverage.py + ruff + radon) | `task-05-python-collector.md` | 1.0 | [PENDING] |
| 6 | TypeScript collector (vitest + eslint + complexity) | `task-06-typescript-collector.md` | 2.0 | [PENDING] |
| 7 | Java collector — coverage (jacoco Maven+Gradle) | `task-07-java-coverage.md` | 1.5 | [PENDING] |
| 8 | Java collector — static analysis (checkstyle+pmd) | `task-08-java-static.md` | 2.0 | [PENDING] |
| 9 | HCL collector (tflint + terraform validate) | `task-09-hcl-collector.md` | 1.0 | [PENDING] |
| 10 | CI-fetch SARIF parser multi-tool (Qodana/Sonar/CodeQL) | `task-10-ci-fetch-sarif.md` | 3.5 | [PENDING] |
| 11 | Spec-drift detector + code-fence robustness | `task-11-spec-drift.md` | 1.5 | [PENDING] |
| 12 | Renderer integration (code-reviewer + spec-reviewer) | `task-12-renderer-agents.md` | 1.0 | [PENDING] |
| 13 | Skill `/forge-evidence` + command | `task-13-skill-command.md` | 0.5 | [PENDING] |
| 14 | E2E renderer contract test + hook integration | `task-14-e2e-test.md` | 1.5 | [PENDING] |
| 15 | Docs: ENV_VARS + CHANGELOG + .gitignore + README | `task-15-docs.md` | 1.0 | [PENDING] |
| 16 | Edge case hardening + chaos tests (5 CRITICAL + 14 HIGH) | `task-16-edge-case-hardening.md` | 3.0 | [PENDING] |

**Totale:** 25.0 SP (umano) / ~10 SP (augmented)

**Edge case coverage:** un edge-case hunt sistematico ha identificato 50 edge case (5 CRITICAL, 14 HIGH, 31 LOW). Task 16 mitiga i 19 più critici con chaos test suite (failure injection). I 31 LOW restano nel backlog follow-up (vedi Task 16 sezione finale).

**Convenzione path test (semplificata post plan-review iter 2):**

- File test: `tests/test_review_evidence_<scope>.py` (root `tests/`, pattern flat — coerente con `tests/lib/test_adoption_analyzer.py`)
- Fixture: `tests/fixtures/review-evidence/<file>.{json,xml,md}`
- **Root conftest.py** in `tests/conftest.py` (creato da Task 00) inietta `REPO_ROOT` in `sys.path` repo-wide. Pattern mutuato da `tests/zero-loss/conftest.py` ma esposto a tutta la suite. Tutti i task 01-15 funzionano come scritti (no path correction massiva richiesta).

**git config nei test integration:** ogni test che fa `git init` + `git commit` in `tmp_path` deve disabilitare gpg-signing (macOS dev box con `commit.gpgsign=true` globale fallisce):

```bash
git init && git -C "$tmp" config commit.gpgsign false && git -C "$tmp" config tag.gpgsign false
```

Pattern obbligatorio in `_init_git_repo` di Task 03, Task 04, Task 14.

---

## Dipendenze

```
Task 00 (test infra) ─► Task 01 (schema) ─┬─► Task 04 (orchestrator) ─┬─► Task 05 (python)
                                          │                            ├─► Task 06 (typescript)
                       Task 02 (write) ──┤                            ├─► Task 07 (java cov)
                                          │                            ├─► Task 08 (java static)
                       Task 03 (hook) ───┘                            ├─► Task 09 (hcl)
                                                                       ├─► Task 10 (ci-fetch sarif)
                                                                       └─► Task 11 (spec-drift)

Task 04-11 ──► Task 12 (renderer agents) ──► Task 14 (E2E test)
Task 04-11 ──► Task 13 (skill /forge-evidence)
Task 14 ──► Task 15 (docs)
```

**Parallel-safe groups (per subagent dispatch):**
- **Wave 0 (infra):** Task 00 — prerequisito di tutti
- **Wave 1 (foundation):** Task 01, 02, 03 — indipendenti tra loro, dipendono da 00
- **Wave 2 (orchestrator):** Task 04 — dipende da Wave 1
- **Wave 3 (collectors):** Task 05, 06, 07, 08, 09, 10, 11 — tutti dipendono da 04, tra loro indipendenti
- **Wave 4 (integration):** Task 12, 13 — dipendono da Wave 3
- **Wave 5 (verification):** Task 14 — dipende da Wave 4
- **Wave 6 (docs):** Task 15 — dipende da Wave 5
- **Wave 7 (hardening):** Task 16 — dipende da TUTTI i Wave precedenti (chaos test richiede pipeline completa)

Subagent dispatch consigliato max 3 paralleli per Wave 3 (race git index → cfr.
feedback_parallel_subagent_git_race in memory). Usa worktree per safety.

---

## Acceptance criteria mapping

Ogni AC del design doc è mappato a uno o più task:

| AC | Task | Verifica |
|----|------|----------|
| AC #1 (hook 3 trigger) | Task 03 | `hooks.json` ha review-evidence in 3 punti |
| AC #2 (schema valido versioned) | Task 01 | Test schema validation |
| AC #3 (≥1 collector per stack) | Task 05-09 | Test per-stack collector |
| AC #4 (CI-fetch SARIF multi-tool) | Task 10 | Test fixture Qodana+Sonar+CodeQL |
| AC #5 (spec-drift auto+env+code-fence) | Task 11 | Test fixture code-fence noise |
| AC #6 (hard-block + bypass state file) | Task 03 + Task 04 | Test threshold matrix + bypass |
| AC #7 (renderer Step 0.5) | Task 12 | Diff su agent .md |
| AC #8 (coverage ≥80% lib/review-evidence) | Task 14 | pytest --cov report |
| AC #9 (ENV_VARS updated) | Task 15 | Doc-sync test |
| AC #10 (CHANGELOG entry) | Task 15 | Grep entry |
| AC #11 (commands/forge-evidence.md) | Task 13 | File esiste + skill loadable |
| AC #12 (no regression pr-gate/etc) | Task 14 | Test suite verde |
| AC #13 (.gitignore entry) | Task 15 | Grep `.claude/review-evidence/` |
| AC #14 (E2E renderer contract) | Task 14 | Test asserisce affermazioni atomiche |
| AC #15 (CI lifecycle doc) | Task 13 + Task 15 | commands/forge-evidence.md + README |

---

## Note operative

- **iCloud safety:** repo è in `~/Library/Mobile Documents/com~apple~CloudDocs/`. Atomic write deve retry-are su `EBUSY` (Task 02). Ogni task che tocca filesystem usa `lib/atomic_write.py`.
- **No emoji nel codice/markdown** se non già presenti (regola DevForge globale).
- **Conventional commits:** ogni task chiude con un commit del tipo `feat(review-evidence): <task scope>` o `test(review-evidence): <task scope>`.
- **TDD obbligatorio:** Red prima di Green per ogni task con codice eseguibile. Task solo-doc (Task 15) può saltare TDD ma deve avere doc-sync test (verifica che la doc sia coerente con codice).
- **Branch:** lavorare su `feat/review-evidence-hook` (creare con `siae-git-workflow` prima del Task 01).
