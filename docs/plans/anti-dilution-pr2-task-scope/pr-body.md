## Summary

PR #2 of 3 dell'initiative **Anti-Dilution Enforcement**
(design: [`docs/plans/2026-04-25-anti-dilution-enforcement-design.md`](docs/plans/2026-04-25-anti-dilution-enforcement-design.md)).
Base: `feat/anti-dilution-pr1-foundation` — stacked su PR [#215](https://github.com/itsiae/siae-dev-forge/pull/215).

**Problema chiuso**: l'enforcement session-scoped di v1.46 lascia adoption
reale a 38% brainstorming, 38% tdd, 3% verification, **0% blind-review**.
Telemetria su 230 sessioni (`docs/measurements/baseline-2026-04-25/`) ha
identificato 9 vie di fuga (7 ADR attivi + 2 rejected nel design doc).

**Questa PR** migra l'enforcement a **task-scoped** (ADR-001), rimuove
3 escape hatches ceremoniali (ADR-006), espande `sub-skill-gate` da 7 a
20 entry autogenerate (ADR-007), introduce 2 nuovi gate che chiudono i
gap `plan-gate bypass via Write` e `blind-review 0%` (ADR-008).

## Changes per ADR

### ADR-001 — Task-scoped enforcement
- **`lib/task-id.sh`** (NEW): `devforge_compute_task_id()` =
  `sha256(branch | latest-design-doc | design-mtime)[:12]`. Empty string
  fuori da repo `itsiae/*`. `devforge_task_id_transition()` copia-avanti
  l'evidenza quando il design doc viene revisionato sullo stesso branch.
  14 test PASS (source-safe, hex format, branch change, design revision,
  concurrent append atomicity).
- **Dual-write in tdd-gate / brainstorming-gate / stop-gate / pre-commit /
  pr-blind-review-gate**: la lettura di session-skills resta per backward
  compat; il gate emette un evento `*_task_divergence` quando i due scope
  disaccordano (shadow-log per misurare prima del cutover completo in PR
  #3).

### ADR-005 — Scope cleanup
- **`lib/file-taxonomy.sh`** (NEW): unica fonte di verità per la
  classificazione. 13 estensioni TDD-required, `.tf`/`.hcl` aggiunti a
  brainstorming-required, `.sh`/`.bash` deny-by-default con opt-in
  `DEVFORGE_BASH_TDD=1`. 46 test PASS.
- `itsiae/*` scope mantenuto hardcoded (decisione utente 2026-04-25).

### ADR-006 — Rimozione escape hatches
- **`stop-gate` 2-block auto-escape** → `DEVFORGE_FORCE_STOP=1` esplicito,
  tracked 3/giorno, emette `force_stop_abuse_suspected` alla soglia.
- **`brainstorming-gate` `W2_DEFAULT=0`** → rimosso. Gate sempre attivo.
  L'unico escape globale resta `DEVFORGE_ENFORCEMENT_OFF=1`.
- **`pre-commit` regex substring** → **`lib/cmd-parser.sh`** (NEW) con
  token-aware matching. Strip di env-var, sudo/env/nice/time/timeout,
  primary-segment su shell operators. Elimina falsi positivi su
  `git log | grep commit`, `echo "git commit"`,
  `python run_git_commit_analyzer.py`. 20 test PASS.

### ADR-007 — Prereq map autogenerata
- **`lib/generate-prereq-map.sh`** (NEW): legge frontmatter
  `prerequisites:` + curated overrides + fallback body `REQUIRED SUB-SKILL:`
  (con strip backtick / blockquote). Filtra cross-cutting
  (siae-verification, siae-retrospective).
- **`lib/prereq-map.generated`**: 20 entry, sorted, committate.
- `sub-skill-gate` legge il file; fallback a hardcoded 7 entry se
  assente. 10 + 8 test PASS.

### ADR-008 — Nuovi gate
- **`hooks/pr-blind-review-gate`** (NEW): matcher Bash, token-gated su
  `gh pr create` / `gh pr edit`. Bypass
  `DEVFORGE_SKIP_BLIND_REVIEW=1`, 5/day. 8 test PASS.
- **`hooks/plan-gate-write`** (NEW): matcher Write,
  `docs/plans/*-design.md`. Invocation-check (non validation —
  chicken-and-egg: il design doc E' l'evidenza). 6 test PASS.
- **`evidence-stop-gate`**: verification via `verification_run event
  exit=0` in task-scope; fallback grep session. 4 test PASS.
- **`coverage-force-run`**: block su commit con file di test staged e
  coverage cache stale (> 30 min). 4 test PASS.

## Extra-scope absorbed: PR #215 auto-review findings

1 CRITICAL + 5 MAJOR documentati nel body di PR #215 sono stati assorbiti
in Task 1 di questa PR per non trascinarli in review:
- `hooks/pre-commit` commento fall-through chiarito.
- `hooks/devforge-context` `compute_state_hash` include `design_doc_mtime`.
- `hooks/devforge-context` emit-then-persist ordering (hash scritto solo
  dopo successo del `cat <<EOF`).
- `tests/.../assert_injection_reduction.sh` usa `env HOME=... bash` invece
  del buggy `HOME=... echo | bash`.
- `lib/logger.sh :: devforge_sanitize_json_str` strippa control chars
  0x00-0x1F; 5 duplicate inline `escape_for_json` rimosse e aliasate
  al centralizzato.

## Bugfix extra-scope: session-start default-preserve

Scoperto durante il commit loop: `hooks/session-start` veniva invocato
ripetutamente mid-sessione con JSON stdin vuoto (no `source` field),
cadendo nel ramo `*)` che **azzerava** `.devforge-session-skills`,
producendo recurring sub-skill-gate false positive. Fix:

- Case `startup)` resetta.
- Case `resume|clear|compact)` preserva (già esistente).
- Case `*)` / empty source ora **preserva** (era: reset). Razionale:
  over-preservation è rumore, under-preservation è hard block.

Test suite aggiornata (`tests/hooks/test_session_start_preserve_skills.sh`,
Case 5 invertito + Case 6 nuovo per empty stdin). 6/6 PASS.

## Env vars introdotte / rimosse

Vedi [`hooks/ENV_VARS.md`](hooks/ENV_VARS.md) per la matrix completa.

**NEW:**
- `DEVFORGE_USE_SESSION_SCOPE` — rollback per-gate
- `DEVFORGE_FORCE_STOP` — escape esplicito stop-gate, 3/day
- `DEVFORGE_BASH_TDD` — opt-in TDD su .sh/.bash
- `DEVFORGE_SKIP_BLIND_REVIEW` — bypass pr-blind-review, 5/day

**REMOVED:**
- `DEVFORGE_W2_DEFAULT` — no-op, rimosso
- `DEVFORGE_ENFORCEMENT_STRICT` — deprecato, ignorato

## Test results

```
tests/pr2-task-scope/run-all.sh — 137/137 PASS
  lib:   task-id (14), file-taxonomy (46), generate-prereq-map (10),
         cmd-parser (20) = 90
  hooks: brainstorming-gate (13), sub-skill-gate-autogen (8),
         evidence-stop-gate (4), coverage-force-run (4),
         pr-blind-review-gate (8), plan-gate-write (6) = 43
  PR#1 regression: compression-regression (52) + baseline 161 (Δ=0)
```

Baseline pre-esistente: 161 PASS / 6 FAIL / 1 SKIP. **Zero nuovi
fallimenti** introdotti da PR #2. La FAIL list del baseline è la stessa
di PR #215.

## Acceptance criteria

- [x] Dual-write phase funzionante (session + task coesistono).
- [x] `gate_divergence` telemetry emesso dai gate task-scoped.
- [x] Rollback `DEVFORGE_USE_SESSION_SCOPE=1` testato via scenari
      dedicati in `brainstorming-gate.test.sh` + `test_pr_blind_review_gate.sh` +
      `test_plan_gate_write.sh` + `test_evidence_stop_gate.sh`.
- [x] Tutti i nuovi gate: positive + negative case.
- [x] Abuse tracking definito per ogni bypass (5/giorno, 3 per FORCE_STOP).
- [x] Zero regression sulla suite PR #1 (52/52 compression, 161 baseline).

## Rollback

Per-gate: `DEVFORGE_USE_SESSION_SCOPE=1` ripristina v1.46.
Globale: `git revert <merge commit>` oppure `DEVFORGE_ENFORCEMENT_OFF=1`.

## Cosa NON è in questa PR

- **ADR-009 Observability loop** (`/forge-adoption` command, stop-gate
  recap, dashboard extension): deferred a PR #3 v1.48.
- **FSM backbone**: documentato in
  `docs/plans/2026-04-25-fsm-backbone-decision.md`, deferred.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
