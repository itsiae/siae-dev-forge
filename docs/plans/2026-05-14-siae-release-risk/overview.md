# siae-release-risk — Piano Implementativo

> **Per Claude:** REQUIRED SUB-SKILL: Usa `siae-subagent-development` (in-session) o `siae-executing-plans` (sessione separata) per implementare questo piano task per task.

**Goal:** Implementare skill DevForge `siae-release-risk` per pre-deploy risk assessment release branch vs main (18 criteri, score 0-36, decision GO/POSTPONE/NO_GO), con hook automatico `pr-release-gate` su PR-open release/**→main, integrazione MCP sport-kg + baseline_cache + runners + activity ledger.

**Architettura:** SKILL.md orchestratore markdown sottile + 12 moduli Python in `lib/release_risk/` (mirror pattern `lib/review_evidence/`). Hook PostToolUse Bash advisory-only. Output versionato in `docs/releases/<date>-<service>-<branch>.md` + PR comment auto. Cache by `(branch, diff-hash, baseline-main-sha)`.

**Stack:** Python 3.11+, bash, markdown. Reuse `lib/review_evidence/baseline_cache.py` (Criterion 16) + `lib/review_evidence/runners/pip_audit.py`+`npm_audit.py` (Criterion 17). MCP sport-kg (Criterion 5).

**SP totale:** 47 Human / 21.5 Augmented (~3 settimane augmented).

**Design doc:** `docs/plans/2026-05-14-siae-release-risk-design.md` (13 ADR, Status: Ready for User Gate, approvato 2026-05-14).

**Plugin manifest target:** bump 1.56.0 → 1.57.0. Count post-merge: 42 skill / 17 cmd / 5 agent / 24 hook.

---

## Indice Task

| # | Task | File | SP (H/A) | Stato |
|---|------|------|---|-------|
| 01 | Pre-flight infra check (baseline_cache schema, runners, MCP) | `task-01-preflight-infra-check.md` | 1.5/0.5 | [DONE] |
| 02 | Plugin manifest count audit (pre-bump) | `task-02-plugin-manifest-audit.md` | 1/0.5 | [DONE] |
| 03 | Scaffold directory structure (skills/, lib/, tests/, evals/) | `task-03-scaffold-structure.md` | 0.5/0.25 | [DONE] |
| 04 | lib/release_risk/schema.py — dataclass CriterionResult, ScoreCard, GenesisInfo, ReleaseRiskReport | `task-04-schema-dataclass.md` | 1.5/0.5 | [DONE] |
| 05 | [TDD] tests/test_release_risk_schema.py — roundtrip serialization | `task-05-test-schema.md` | 1/0.5 | [DONE] |
| 06 | detector.py criteri 1-5 (DB, OCP, API, deps, critical-stub) | `task-06-detector-criteri-1-5.md` | 1.5/0.5 | [DONE] |
| 07 | [TDD] tests detector.py criteri 1-5 con fixture diff | `task-07-test-detector-1-5.md` | 1/0.5 | [DONE] |
| 08 | detector.py criteri 6-10 (first release, rollback, downtime, migration, feature flag) | `task-08-detector-criteri-6-10.md` | 1.5/0.5 | [PENDING] |
| 09 | [TDD] tests detector.py criteri 6-10 | `task-09-test-detector-6-10.md` | 1/0.5 | [PENDING] |
| 10 | detector.py criteri 11-15 (coverage-stub, E2E, perf, user impact, files count) | `task-10-detector-criteri-11-15.md` | 1.5/0.5 | [PENDING] |
| 11 | [TDD] tests detector.py criteri 11-15 + integration end-to-end | `task-11-test-detector-11-15.md` | 1/0.5 | [PENDING] |
| 12 | kg_lookup.py (MCP sport-kg + heuristic 6 condizioni) — Criterion 5 | `task-12-kg-lookup.md` | 2/1 | [PENDING] |
| 12b | Bridge MCP sport-kg → CLI via JSON prefetch (resolve ADR-2 inesigibilità) | `task-12b-kg-bridge-skill-to-cli.md` | 1.5/0.75 | [PENDING] |
| 13 | [TDD] tests kg_lookup.py (mock MCP, timeout, criticality matrix) | `task-13-test-kg-lookup.md` | 1.5/0.5 | [PENDING] |
| 14 | coverage_src.py chain fallback (evidence → CI artifact → ask) — Criterion 11 | `task-14-coverage-src.md` | 1.5/0.5 | [PENDING] |
| 15 | [TDD] tests coverage_src.py | `task-15-test-coverage-src.md` | 1/0.5 | [PENDING] |
| 16 | regression_delta.py + prev_release_main_sha resolution — Criterion 16 | `task-16-regression-delta.md` | 2/1 | [PENDING] |
| 17 | [TDD] tests regression_delta.py (mock baseline_cache) | `task-17-test-regression-delta.md` | 1.5/0.5 | [PENDING] |
| 18 | security_state.py HEAD-only MVP (runners pip_audit/npm_audit) — Criterion 17 | `task-18-security-state.md` | 2/1 | [PENDING] |
| 19 | [TDD] tests security_state.py | `task-19-test-security-state.md` | 1.5/0.5 | [PENDING] |
| 20 | genesis.py Step 4b workflow + 3-outcome — Criterion 18 | `task-20-genesis.md` | 2/1 | [PENDING] |
| 21 | [TDD] tests genesis.py | `task-21-test-genesis.md` | 1/0.5 | [PENDING] |
| 22 | scoring.py compute_score + level assignment max 36 | `task-22-scoring.md` | 1/0.5 | [PENDING] |
| 23 | [TDD] tests scoring.py boundaries 0-4/5-9/10-14/15+ | `task-23-test-scoring.md` | 1/0.5 | [PENDING] |
| 24 | cache.py 3-key (branch, diff-hash, baseline-main-sha) + idempotency marker | `task-24-cache.md` | 2/1 | [PENDING] |
| 25 | [TDD] tests cache.py (hit/miss/baseline drift) | `task-25-test-cache.md` | 1/0.5 | [PENDING] |
| 26 | renderer.py template fill + 4 livelli + SUGGESTED FOLLOW-UP block | `task-26-renderer.md` | 2/1 | [PENDING] |
| 27 | [TDD] tests renderer.py snapshot 4 livelli | `task-27-test-renderer.md` | 1.5/0.5 | [PENDING] |
| 28 | cli.py argparse + entry point `python -m lib.release_risk assess` | `task-28-cli.md` | 1.5/0.5 | [PENDING] |
| 29 | [TDD] tests cli.py e2e con fixture repo | `task-29-test-cli.md` | 1.5/0.5 | [PENDING] |
| 30 | skills/siae-release-risk/reference/release-criticality-checklist.md (template) | `task-30-reference-checklist.md` | 1/0.5 | [PENDING] |
| 31 | skills/siae-release-risk/reference/release-risk-criteria.md (18 criteri detail) | `task-31-reference-criteri.md` | 1/0.5 | [PENDING] |
| 32 | skills/siae-release-risk/SKILL.md (10-step orchestrator) | `task-32-skill-md.md` | 2/1 | [PENDING] |
| 33 | commands/forge-release-risk.md (slash command) | `task-33-slash-command.md` | 1/0.5 | [PENDING] |
| 34 | hooks/pr-release-gate (PostToolUse Bash + cache + gh api comments idempotency) | `task-34-hook-pr-release-gate.md` | 2.5/1 | [PENDING] |
| 35 | hooks/hooks.json register pr-release-gate | `task-35-hooks-json-register.md` | 0.5/0.25 | [PENDING] |
| 36 | [TDD] tests/test_release_risk_hook.py integration | `task-36-test-hook.md` | 2/1 | [PENDING] |
| 37 | evals/release-risk/disambiguation.yaml (10 prompt) | `task-37-eval-set.md` | 1/0.5 | [PENDING] |
| 38 | .claude-plugin/plugin.json bump 1.56→1.57 + count | `task-38-plugin-manifest-bump.md` | 0.5/0.25 | [PENDING] |
| 39 | README.md skill count update + CHANGELOG.md 1.57.0 + hooks/ENV_VARS.md | `task-39-docs-update.md` | 1.5/0.5 | [PENDING] |
| 40 | Full test suite + mutation testing target ≥60% + coverage ≥85% verification | `task-40-test-suite-verification.md` | 1/0.5 | [PENDING] |
| 41 | siae-finishing-branch pre-flight + open PR | `task-41-finishing-branch-pr.md` | 1/0.5 | [PENDING] |

**Totale:** 42 task (41 + task-12b bridge MCP) — somma effettiva tabella: **51 Human SP / 22.25 Augmented SP**.

**Drift vs design (47/21.5):** Human +8.5%, Augmented +3.5%. Drift accettato per:
- task-12b bridge MCP sport-kg→CLI (BLOCK-1 plan-review chiuso): +1.5 H / +0.75 A
- Test detailed coverage (task-13/17/21 inflation 1→1.5 H per casi edge KG/regression/genesis): +2 H totale
- Hook portabilità + idempotency complexity (task-34 inflation 2→2.5 H per timeout fallback): +0.5 H

**Plan-review status:**
- Iter 1: WARN (1 BLOCK + 6 WARN)
- Iter 2: WARN (1 BLOCK regression import + propagation incomplete)
- Iter 3: fix applicati — `import os` aggiunto, `--kg-data-file` propagato a CLI + SKILL.md Step 6, accounting overview corretto

---

## Dipendenze

```
task-01 (preflight) ── task-02 (manifest audit) ── task-03 (scaffold)
                                                        │
                                                        ▼
                                              task-04 (schema) ── task-05 (TDD)
                                                        │
                              ┌───────────────────────┬─┴────────────────────────┐
                              ▼                       ▼                          ▼
                  task-06/07/08/09/10/11 (detector)  task-22/23 (scoring)  task-30/31 (reference)
                              │                       │                          │
                              ▼                       │                          │
                  task-12-21 (adattatori SIAE)        │                          │
                              │                       │                          │
                              └───────────┬───────────┴────────────┬─────────────┘
                                          ▼                        ▼
                              task-24/25 (cache)          task-26/27 (renderer)
                                          │                        │
                                          └────────────┬───────────┘
                                                       ▼
                                              task-28/29 (cli)
                                                       │
                                                       ▼
                                          task-32 (SKILL.md) ── task-33 (slash)
                                                       │
                                                       ▼
                                          task-34/35/36 (hook)
                                                       │
                                                       ▼
                                          task-37 (eval) ── task-38 (manifest bump)
                                                       │
                                                       ▼
                                          task-39 (docs) ── task-40 (full test)
                                                       │
                                                       ▼
                                          task-41 (finishing-branch + PR)
```

**Critical path:** task-01 → 03 → 04 → 28 → 32 → 34 → 41 (lineare per integration).

**Parallelizzabile:** task-06/08/10 (detector chunk), task-12/14/16/18/20 (adattatori SIAE indipendenti), task-22/26/30 (scoring/renderer/reference indipendenti dopo schema).

---

## Vincoli & Out of Scope

**In scope (questa PR):**
- 18 criteri scoring + workflow 10-step
- Hook automation pr-release-gate advisory-only
- Cache by (branch, diff-hash, baseline-main-sha) + idempotency
- Integrazione MCP sport-kg (Criterion 5) + baseline_cache (Criterion 16) + runners (Criterion 17 HEAD-only MVP)
- Activity ledger emit via `devforge_log`
- Output versionato `docs/releases/<date>-<service>-<branch>.md`
- Plugin manifest bump 1.56→1.57 con count audit

**Out of scope (backlog design sez. 12):**
- CVE per-ID identification (v3.x)
- Criterion 17 delta vs baseline (v2.x — richiede estensione schema EvidenceV2 con `security_findings_raw`)
- Maven security runner (estensione runners/)
- 4 controlli aggiuntivi: data migration delta, perf regression, contract breaking, OCP drift
- Auto-calibrazione weight via incident correlation
- CAB ticket auto-creation
- Dashboard release-risk in siae-dev-analytics
- Tag-creation hook + auto-block evolution

---

## Acceptance Criteria globali (design sez. 10)

- ✅ Test coverage ≥85% su `lib/release_risk/`
- ✅ Mutation score ≥60% su `lib/release_risk/`
- ✅ Eval disambiguation 10/10 PASS
- ✅ Lint 0 errors (ruff + shellcheck)
- ✅ review-evidence v2 PASS (non BLOCK) per commit merge
- ✅ No regressioni su `siae-finishing-branch`, `siae-branching-strategy-check`, `forge-evidence`
- ✅ Plugin manifest count audit completato pre-bump (42/17/5/24)

---

## Stato Piano

- **Created:** 2026-05-14
- **Author:** Lorenzo De Tomasi
- **Design approval:** 2026-05-14 (user gate PASS)
- **Spec-review:** iter 3 PASS, iter 4 fix locali applicati
- **Plan review:** iter 3 fix completati (BLOCK-1 + 6 WARN chiusi)
