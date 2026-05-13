# Review Evidence v2 (Scoring) — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` per
> implementare questo piano task per task (stessa sessione, parallel-safe).
> In alternativa `siae-executing-plans` per sessione separata.

**Goal:** Estendere `review-evidence v1` (PR #241 merged, commit `1a4f11c`) con
**scoring deterministico regression-based** (5 dimensioni, 0-100, weighted overall)
+ reviewer agent gatekeeper finale (5 decision branch) + 5 OSS runner MVP +
2 nuovi check (arch_drift, skill_adoption) + baseline cache S3 + 8 CRITICAL edge
case fix. Sostituisce verdetto binary v1 (block:bool) con scoring numerico
allineato a north star "zero bug shift-left".

**Architettura:** Hook bash thin wrapper `hooks/review-evidence` (esteso v2 con
5 decision branch) → Python orchestrator `lib/review_evidence/collector.py`
(esteso con scoring layer) → runners OSS + 2 check nostri + baseline_cache S3
+ scoring algorithm → evidence v2 JSON → renderer agents/code-reviewer.md Step 0.6.

**Stack:** Bash 5 (hook), Python 3.9.6 (lib + runners + tests), Markdown (agent
docs + skill command), JSON Schema v2, YAML (`.devforge-scores.yml`,
`.devforge-arch.yml`), Terraform HCL (S3 + IAM OIDC).

**SP totale:** 30.0 umano / 12.5 augmented (16 task, split 2 PR + Terraform)

**Design doc:** `docs/plans/2026-05-13-review-evidence-v2-scoring-design.md`

---

## Indice Task

### PR-A foundation (15.5 SP) — schema + scoring + 5 runner MVP + hook v2

| # | Task | File | SP | Stato |
|---|------|------|----|-------|
| 01 | Schema v2 dataclass (ScoreCard, RegressionVerdict, ReviewerVerdict) + forward-compat | `task-01-schema-v2.md` | 1.5 | [PENDING] |
| 02 | Score algorithm 5 formule + compute_overall tuple + coverage anti-gaming | `task-02-scoring-algorithm.md` | 3.0 | [PENDING] |
| 03 | Runner registry framework + bandit + gitleaks (2 MVP reference) | `task-03-runners-registry-bandit-gitleaks.md` | 2.0 | [PENDING] |
| 04 | 3 runner MVP aggiuntivi (pip-audit, npm-audit, eslint-security) | `task-04-runners-deps-eslint.md` | 1.5 | [PENDING] |
| 05 | Hook bash v2 extension (5 decision branch + SEVERELY_DEGRADED) | `task-05-hook-v2.md` | 2.0 | [PENDING] |
| 06 | Config parsers (.devforge-scores.yml + .devforge-arch.yml) + arch_drift check | `task-06-config-parsers-arch-drift.md` | 3.0 | [PENDING] |
| 07 | Test foundation PR-A (schema + scoring + runner mock + arch_drift) | `task-07-test-foundation.md` | 2.0 | [PENDING] |
| 08 | Docs partial PR-A (ENV_VARS draft + CHANGELOG entry v1.55.0 placeholder) | `task-08-docs-partial.md` | 0.5 | [PENDING] |

### PR-B advanced (14 SP) — cache S3 + reviewer agent + E2E + 8 CRITICAL coverage

| # | Task | File | SP | Stato |
|---|------|------|----|-------|
| 09 | baseline_cache.py S3 backend + local fallback + repo hash | `task-09-baseline-cache-s3.md` | 3.0 | [PENDING] |
| 10 | skill_adoption check (4-tier fallback signal) | `task-10-skill-adoption.md` | 1.5 | [PENDING] |
| 11 | Budget snapshot at PR_OPEN_TIME (E1) + hard floor non-overridable (F1+E5) | `task-11-budget-snapshot-hard-floor.md` | 2.5 | [PENDING] |
| 12 | Reviewer agent Step 0.6 (5 decision branch) + agents/code-reviewer.md edit | `task-12-reviewer-step-06.md` | 1.5 | [PENDING] |
| 13 | Edge case chaos suite v2 (40 cases mapped from design) | `task-13-chaos-suite-v2.md` | 3.0 | [PENDING] |
| 14 | E2E test full pipeline (hook → collector → S3 → agent) | `task-14-e2e-full-pipeline.md` | 1.5 | [PENDING] |
| 15 | Docs final PR-B (forge-score skill + README + CHANGELOG v1.55.0) | `task-15-docs-final.md` | 1.0 | [PENDING] |

### Terraform (0.5 SP) — infra-prep pre-PR-B

| # | Task | File | SP | Stato |
|---|------|------|----|-------|
| 16 | S3 bucket itsiae-review-evidence-baseline-prod + IAM OIDC trust itsiae/* | `task-16-terraform-s3-iam.md` | 0.5 | [PENDING] |

**Totale:** 16 task · 30.0 SP umano · 12.5 SP augmented

---

## Dipendenze

```
PR-A foundation (8 task):
  Task 01 (schema v2) ─┬─► Task 02 (scoring algorithm)
                       │       │
                       │       ├─► Task 03 (runners registry + 2)
                       │       │       │
                       │       │       └─► Task 04 (3 runner aggiuntivi)
                       │       │
                       │       └─► Task 06 (config + arch_drift)
                       │
                       └─► Task 05 (hook v2 — usa schema decision enum)

  Task 02-06 ──► Task 07 (test foundation)
  Task 07 ──► Task 08 (docs partial PR-A)

Terraform (parallel a PR-A o pre-PR-B):
  Task 16 (S3 + IAM)

PR-B advanced (7 task) — dipende da PR-A merged + Task 16 done:
  Task 09 (baseline cache S3) ── needs Task 16 done
  Task 10 (skill_adoption) ── needs Task 02 (scoring algorithm)
  Task 11 (budget snapshot + hard floor) ── needs Task 09 + Task 02
  Task 12 (reviewer Step 0.6) ── needs Task 05 (hook decision enum)
  Task 09-12 ──► Task 13 (chaos suite v2)
  Task 13 ──► Task 14 (E2E)
  Task 14 ──► Task 15 (docs final)
```

**Wave dispatch (per subagent execution):**
- **Wave 0 (parallel-safe):** Task 16 (Terraform, indipendente da Python)
- **Wave 1 (PR-A foundation):**
  - Task 01 → Task 02 (seriali, schema base poi algorithm)
  - Wave 1b (parallel-2 worktree): Task 03 + Task 06 — file disgiunti
  - Task 04 (dopo 03, stesso file pattern)
  - Task 05 (dopo 02, usa enum)
- **Wave 2 (test PR-A):** Task 07 → Task 08
- **Wave 3 (PR-B core):** Task 09 (dopo Task 16) → Task 10 → Task 11 → Task 12
- **Wave 4 (test PR-B):** Task 13 → Task 14 → Task 15

---

## Acceptance criteria mapping (19 AC, 8 CRITICAL bloccanti)

| AC | Task | Verifica |
|----|------|----------|
| **CRITICAL — Cache key SHA-based, no TTL** | Task 09 | `baseline_key()` usa main HEAD SHA, NO TTL check |
| **CRITICAL — Coverage anti-gaming lines_covered** | Task 02 | `score_coverage` test su `baseline_lines_covered` drop |
| **CRITICAL — Config file change require override** | Task 06 | Test diff su `.devforge-scores.yml` modificato in PR → marker `config_change_require_override` |
| **CRITICAL — Baseline cache S3 + OIDC IAM** | Task 09 + Task 16 | S3 fetch via boto3 + Terraform OIDC role |
| **CRITICAL — Budget snapshot at PR_OPEN_TIME** | Task 11 | Test admin change budget post-PR → snapshot wins |
| **CRITICAL — min_dim_score hard floor** | Task 11 | Test `min_dim: 40` block separato da overall |
| **CRITICAL — Hard floor non-overridable by reviewer** | Task 12 + Task 11 | Test reviewer APPROVED su hard_floor → still block |
| **CRITICAL — Combined lines_covered + coverage% gate** | Task 02 | Test refactor che riduce LOC: lines_covered drop AND % rise → block |
| AC #9 Schema v2 forward-compat | Task 01 | Test deserialize v1 + v2 + v1.5 (unknown fields ignored) |
| AC #10 5 score formule produce 0-100 | Task 02 | Param test boundary 0/50/100/missing |
| AC #11 5 OSS runner MVP integrate graceful | Task 03+04 | Test mock subprocess missing tool → None metric |
| AC #12 Reviewer agent Step 0.6 5 decision branch | Task 12 | Grep contract test sul markdown agent |
| AC #13 Hook bash chain v1 unchanged (no regression) | Task 05 | `tests/test_review_evidence_e2e.py` v1 still PASS |
| AC #14 Test coverage ≥85% su lib/review_evidence/ | Task 07 + Task 13 + Task 14 | `pytest --cov` report |
| AC #15 ENV_VARS.md updated (10+ new vars) | Task 08 + Task 15 | Doc-sync test estende existing `test_env_vars_doc_sync.py` |
| AC #16 CHANGELOG.md entry v1.55.0 | Task 15 | grep entry |
| AC #17 Terraform module deployed (S3 + IAM OIDC) | Task 16 | `terraform plan` clean, no drift |
| AC #18 .devforge-scores.yml schema + template | Task 06 + Task 15 | Template file + JSON schema validator |
| AC #19 `commands/forge-score.md` skill on-demand | Task 15 | File exists, contract test |

---

## Note operative

- **iCloud safety:** repo è in `~/Library/Mobile Documents/com~apple~CloudDocs/`. Atomic write con retry EBUSY (esistente v1). Cache locale fallback se AWS unreachable.
- **No regression v1:** tutti i 158 test review-evidence v1 devono restare verdi durante l'intero ciclo. Verifica post-task.
- **Conventional commits:** ogni task chiude con commit del tipo `feat(review-evidence-v2): <task scope> (#task-NN)` o `test(...)` o `docs(...)`.
- **TDD obbligatorio:** Red prima di Green per ogni task con codice eseguibile. Task solo-doc (Task 08, 15) può saltare TDD ma deve avere doc-sync test.
- **gpg-sign disable:** ogni test che fa `git init` in tmp_path deve disabilitare gpg-sign (memory `feedback_branch_hop_during_push`).
- **pytest path:** `python3 -m pytest`, non `pytest` diretto (memory v1 PR #241 task-00 discovery).
- **Forward-compat schema:** schema v2 deve essere **additive only** su v1 (Optional fields aggiunti). Test esplicito che v1 fixture continua a deserialize OK.
- **Branch:** `feat/review-evidence-v2-scoring` (già checked out).
- **No push automatico:** push solo quando esplicito (memory iCloud tax).
- **5 decision branch enum:** `RegressionVerdict.decision = AUTO_APPROVE | REVIEWER_HANDOFF | BLOCK_HARD_FLOOR | BLOCK_REGRESSION | SEVERELY_DEGRADED`. Coerente cross-section (schema + hook bash + reviewer + criterio).
- **Runner MVP scope:** 5 (bandit, gitleaks, pip-audit, npm-audit, eslint-security). NO vulture/pyright/spotbugs/mvn-deps/tfsec/checkov/ts-unused (W1 iter1 fix — out-of-scope MVP, follow-up PR).

---

## Edge case coverage (40 mapped from design doc)

| Categoria | Count | Status |
|---|---|---|
| CRITICAL (A1, B1+B7, B3, D3+D5, E1, E5, F1, C5) | 8 | ✅ All mapped → Task 02, 06, 09, 11, 12, 16 |
| HIGH (A2, A3, A5, A6, A8, B2, C1, C2, C3, C4, D2, D6, E2, E4, F3, F4) | 17 | ✅ Mapped → Task 02, 09, 10, 11, 12, 13 |
| LOW (C6, C7, D1, D4, E3, F2) | 9 | ✅ Mapped → Task 13 (chaos suite) |
| DEFERRED (A4, A7, B6, altri 3) | 6 | ❌ Backlog follow-up |

**Coverage MVP:** 34/40 (85%) — vedi design doc sezione "Edge case coverage".
