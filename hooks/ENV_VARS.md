# DevForge Hooks — Environment Variables

Reference for all environment variables that control hook behaviour.
Bypass vars are tracked and log `*_abuse_suspected` when used >= 5 times
in a single UTC day (3× for `DEVFORGE_FORCE_STOP`).

## Global

| Env var | Default | Introduced | Description |
|---|---|---|---|
| `DEVFORGE_ENFORCEMENT_OFF` | `0` | v1.45 | Disable **all** gates. Exit `{}` on every invocation. |
| `DEVFORGE_USE_SESSION_SCOPE` | `0` | **v1.47 (PR #2)** | Rollback switch. Restores session-scoped enforcement for every task-scoped gate (tdd, brainstorming, stop, pre-commit, pr-blind-review, plan-gate-write). Set for an entire shell if task-scope enforcement misbehaves. |

## Per-gate bypass (tracked)

| Env var | Default | Gate | Abuse threshold | Notes |
|---|---|---|---|---|
| `DEVFORGE_SKIP_BRAINSTORMING` | `0` | brainstorming-gate | 5 / day | Emits `brainstorming_bypass_abuse_suspected` on threshold. |
| `DEVFORGE_SKIP_GIT_GATE` | `0` | pre-commit (git-workflow check) | 5 / day | Emergency bypass introduced to unblock users affected by the session-skills reset bug. |
| `DEVFORGE_SKIP_RETRO_GATE` | `0` | stop-gate (retrospective) | — | For non-interactive CI/agent sessions. |
| `DEVFORGE_SKIP_BLIND_REVIEW` | `0` | pr-blind-review-gate | 5 / day | **v1.47 NEW.** Allows `gh pr create` / `gh pr edit` without siae-blind-review validation. |
| `DEVFORGE_FORCE_STOP` | `0` | stop-gate (verification) | **3 / day** | **v1.47 NEW.** Explicit replacement for the old 2-block auto-escape (ADR-006). Lower threshold because Stop is high-impact. |

## Review Evidence (v1.54+)

| Env var | Default | Significato |
|---|---|---|
| `DEVFORGE_EVIDENCE_MIN_COVERAGE` | `60` | Coverage % sotto cui block |
| `DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA` | `-5` | Delta vs base sotto cui block (pp) |
| `DEVFORGE_EVIDENCE_MAX_LINT_ERRORS` | `0` | Lint errors sopra cui block |
| `DEVFORGE_EVIDENCE_MAX_COMPLEXITY` | `15` | Max cyclomatic per funzione |
| `DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL` | `critical` | `critical` / `high` / `off` per findings SARIF CI |
| `DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK` | `1` | Block se `drift_severity == high` |
| `DEVFORGE_EVIDENCE_DESIGN_DOC` | (auto) | Override path design doc (default: file piu' recente in `docs/plans/`) |
| `DEVFORGE_SKIP_EVIDENCE` | `0` | Bypass fallback. Preferito: `export DEVFORGE_SKIP_EVIDENCE=1 (breakglass session-scoped)` (state file piu' affidabile in subprocess hook). Tracked, abuse log a 5/day. |
| `DEVFORGE_EVIDENCE_ICLOUD_WARN` | `1` | Emit warning se repo in iCloudDocs (atomic rename fragile) |
| `DEVFORGE_EVIDENCE_COLLECTOR_PATH` | (auto) | Override path al collector.py (default: `lib/review_evidence/collector.py`). Usato in chaos test E41 per inject fake collector + power-user override. |
| `DEVFORGE_EVIDENCE_ICLOUD_WARNING` | (auto) | Internal env exported dal hook bash quando cwd matcha pattern iCloudDocs; collector legge questa per emit warning in `verdict.warnings`. Non settare manualmente. |

**State file bypass primario:** `~/.claude/.devforge-skip-evidence` — l'hook
controlla l'esistenza del file PRIMA di compute. Il file puo' contenere
`N=<count>` per auto-decremento. Pattern raccomandato vs env var perche' le
env var possono non propagare a subprocess hook Claude Code (vedi memory
`feedback_env_var_not_propagated_to_hooks`).

**Pattern operativo CI:** vedi `commands/forge-evidence.md` per il flow
`gh pr create` -> CI completes -> `gh pr edit` per pickup SARIF.

## Review Evidence v2 — Scoring (v1.55+)

Estensione di Review Evidence v1 con scoring deterministico regression-based.
Tutte le env var v1 (`DEVFORGE_EVIDENCE_*`) restano valide.

### Config file paths

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_SCORES_CONFIG_PATH` | `.devforge-scores.yml` | Override path config (testing) |
| `DEVFORGE_ARCH_CONFIG_PATH` | `.devforge-arch.yml` | Override path arch rules |

### Behavior toggles (PR-A foundation)

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_SCORING_V2_ENABLED` | `0` (PR-A rollout phase) -> `1` (PR-B GA) | Master kill-switch v2 scoring (fallback v1) |

### PR-B vars (Baseline cache + Break-glass + Activity)

Introdotte in PR-B (Task 09-15). Tutte hanno default operativi: override solo
per test/staging o ambienti dev offline.

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_BASELINE_S3_BUCKET` | `itsiae-review-evidence-baseline-prod` | S3 bucket cache baseline (provisioned via Terraform `infra/terraform/review-evidence-baseline/`). Cache key = main HEAD SHA, NO TTL (A1 CRITICAL fix). Force-push invalidation via `git cat-file -e` (A2 fix). |
| `DEVFORGE_BASELINE_S3_REGION` | `eu-west-1` | AWS region per S3 + OIDC IAM trust |
| `DEVFORGE_BASELINE_LOCAL_DIR` | `~/.claude/review-evidence-baseline-local` | Local fallback path quando S3 unreachable (dev offline, network drop). Cache hit locale preferito S3 quando entrambi presenti per latency. |
| `DEVFORGE_BREAK_GLASS_REGEX` | `BREAK-GLASS:\s+\w+-\d+` | Pattern commit msg per override `BLOCK_HARD_FLOOR` (admin only). Match = log `break_glass_invoked` in activity.jsonl + bypass gate. |
| `DEVFORGE_ACTIVITY_PROJECT` | (auto, derivato da repo root) | Project name per lookup `~/.claude/projects/<X>/devforge-state/activity.jsonl` nel check `skill_adoption` (4-tier fallback signal). Override per test multi-project. |

**Bypass behaviour:**
- `BLOCK_REGRESSION` (delta sotto hard_block budget) -> overridable via `export DEVFORGE_SKIP_EVIDENCE=1 (breakglass session-scoped)` (tracked, abuse 5/day).
- `BLOCK_HARD_FLOOR` (score sotto hard_floors) -> **NON** overridable da reviewer agent. Solo admin BREAK-GLASS via commit message regex.
- `SEVERELY_DEGRADED` (< 2 dim disponibili) -> fail-closed, no bypass. Fix tooling prima di re-run.

### Mutation Testing (v1.58+)

Advisory test-quality metric via mutation runner (PIT/mutmut/Stryker).
**Opt-in** — runner ritorna `None` quando disabled, zero overhead.
Reviewer agent advisory: `mutation_score < threshold` -> `REVIEWER_HANDOFF`,
**mai BLOCK** (ThoughtWorks pattern "shift focus from execution to verification").

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_MUTATION_ENABLED` | `0` | Master switch. `1` abilita PIT/mutmut/Stryker runner. Default OFF perche' mutation testing e' slow per definizione (M x test_runtime). |
| `DEVFORGE_MUTATION_THRESHOLD` | `60` | `mutation_score < threshold` -> reviewer advisory `REVIEWER_HANDOFF`. Mai BLOCK su mutation alone. |
| `DEVFORGE_PIT_REPORT_PATH` | `target/pit-reports/mutations.xml` | Override Java PIT XML report path. |
| `DEVFORGE_MUTMUT_CACHE_PATH` | `.mutmut-cache` | Override Python mutmut SQLite cache directory. |
| `DEVFORGE_STRYKER_REPORT_PATH` | `reports/mutation/mutation.json` | Override JS/TS Stryker JSON report path. |

**Operational note:** mutation runner NON eseguono i tool live (M x test_runtime troppo
slow). Parse SOLO pre-existing report file. Dev runna `mvn org.pitest:pitest-maven:mutationCoverage` / `mutmut run` / `npx stryker run` separatamente (CI o local) e DevForge
collector legge il report quando presente.

### Fix Evidence Auto-Loop (skill `siae-fix-evidence`, v1.55+)

Auto-remediation loop hook-driven invocato da `/forge-fix-evidence` su
`BLOCK_REGRESSION`. Override solo per test/staging.

| Env var                              | Default  | Note |
|--------------------------------------|----------|------|
| `DEVFORGE_FIX_EVIDENCE_TOKEN_BUDGET` | `200000` | Token budget totale loop (rough est. via Claude API usage). Loop exit con `TOKEN_BUDGET_EXCEEDED` quando consumed > budget. Misurabile vs cap $5 originale che era non verificabile in-process. |
| `DEVFORGE_FIX_EVIDENCE_MAX_ITER`     | `5`      | Hard cap iter del loop. Override richiede design review (pattern memory `feedback_spec_reviewer_iter2_roi`). |
| `DEVFORGE_FIX_EVIDENCE_AUTO`         | `1`      | **v1.55+ NEW.** **Default ON dal follow-up `feat/fix-evidence-auto-trigger` (BREAKING vs v1.55 PR #244).** Hook `review-evidence` v2 emette signal canonico `AUTO_FIX_TRIGGER:/forge-fix-evidence:sha=<SHA>` in `additional_context` su `BLOCK_REGRESSION` (no hard floor, no bot, not degraded). Agent (Claude Code) intercept signal e auto-invoca `siae-fix-evidence`. Set `0` per disabilitare globalmente (opt-out kill-switch). |

**Escalation conditions (no env override):** `hard_floor_breaches` non vuoto,
`is_bot_pr=True`, `decision == SEVERELY_DEGRADED`, action `kind == "unknown"`,
oscillation guard (stesso `frozenset(block_reasons)` per 2 iter consecutivi).

**Auto-trigger skip conditions hook-level** (signal NON emesso, block resta):
identiche alle skill skip conditions sopra (`hard_floor_breaches` non vuoto,
`GITHUB_ACTOR` matches bot pattern). Vedi
`skills/siae-fix-evidence/SKILL.md` sezione "Auto-trigger pattern".

#### Opt-out kill-switch

A partire dal follow-up `feat/fix-evidence-auto-trigger` il default di
`DEVFORGE_FIX_EVIDENCE_AUTO` e' flippato da `0` a `1`: l'auto-trigger e' ora
il comportamento **default** (DevForge opinionato verso "zero bug usando
DevForge"). Le skip conditions semantic (hard floor / bot PR /
SEVERELY_DEGRADED) restano invariate come safety net.

Per disabilitare globalmente l'auto-trigger (kill-switch):

```bash
# Shell corrente (opt-out per la sessione)
export DEVFORGE_FIX_EVIDENCE_AUTO=0

# Persistente in shell rc (~/.zshrc, ~/.bashrc)
echo 'export DEVFORGE_FIX_EVIDENCE_AUTO=0' >> ~/.zshrc

# One-shot per singolo comando
DEVFORGE_FIX_EVIDENCE_AUTO=0 gh pr create --title "..."
```

Quando `DEVFORGE_FIX_EVIDENCE_AUTO=0`:

- Hook **non** emette il marker `AUTO_FIX_TRIGGER` in `additional_context`.
- `decision:block` resta normalmente per safety (BLOCK_REGRESSION va risolto
  manualmente via `/forge-fix-evidence` o human review).
- Telemetry log resta `evidence_auto_fix_trigger_skipped` (motivazione skip
  tracciata in `is_bot=0,hard_floor_count=0` -> implicito env opt-out).

## Scope / feature flags

| Env var | Default | Gate | Description |
|---|---|---|---|
| `DEVFORGE_BASH_TDD` | `0` | tdd-gate (via file-taxonomy) | **v1.47 NEW.** Opt-in TDD gating for `.sh` / `.bash` files. Deny-by-default keeps DevForge's own hooks from locking themselves. |

## Removed in v1.47 (PR #2)

| Env var | Why removed |
|---|---|
| `DEVFORGE_W2_DEFAULT` | Replaced by always-on enforcement (ADR-006). Old `W2_DEFAULT=0` was a no-op that diluted the gate to zero effect. |
| `DEVFORGE_ENFORCEMENT_STRICT` | Superseded by always-on enforcement. Reading it is now ignored. |

## Rollout and rollback

Task-scoped enforcement (ADR-001) runs in dual-write mode: every hook still
reads the legacy `~/.claude/.devforge-session-skills` in addition to the
task-keyed ledger at `~/.claude/.devforge-task-skills/<task_id>/`.

- Per-gate rollback: set `DEVFORGE_USE_SESSION_SCOPE=1` in the shell that
  exhibits the problem. The gate will skip the task-id layer entirely and
  behave identically to v1.46.
- Global rollback: `DEVFORGE_ENFORCEMENT_OFF=1` (pre-existing).
- Hard revert: `git revert <PR #2 merge commit>`.

## Abuse-tracking data files

These files are rewritten atomically by the hooks; they are safe to delete
to reset counters.

| File | Written by | Purpose |
|---|---|---|
| `~/.claude/.devforge-bypass-count` | brainstorming-gate | Daily bypass counter |
| `~/.claude/.devforge-git-gate-bypass-count` | pre-commit | Daily bypass counter |
| `~/.claude/.devforge-blind-review-bypass-count` | pr-blind-review-gate | Daily bypass counter |
| `~/.claude/.devforge-force-stop-count` | stop-gate | Daily force-stop counter |

## Plugin root resolution

| Env var | Source | Description |
|---|---|---|
| `CLAUDE_PLUGIN_ROOT` | Iniettata da Claude Code nell'env del processo hook | Path assoluto della directory installata del plugin (es. `~/.claude/plugins/cache/siae-devforge/siae-devforge/<version>`). Da NON valorizzare nel plugin: e' responsabilita' dell'harness. |

### Convenzione quoting in `hooks.json`

Il pattern canonico per riferire `${CLAUDE_PLUGIN_ROOT}` in `hooks.json` usa double-quotes JSON-escaped:

**JSON source** (sorgente con escape):

```json
"command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd\" session-start"
```

**Stringa ricevuta da bash dopo parse JSON dall'harness**:

```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start
```

Le double-quote (escaped come `\"` nel JSON source) sono **necessarie** per consentire a bash di espandere `${CLAUDE_PLUGIN_ROOT}` iniettata dall'harness. Single quotes bloccherebbero l'espansione e l'hook fallisce con `bash: ${CLAUDE_PLUGIN_ROOT}/hooks/run-hook.cmd: No such file or directory`.

Regola enforced da `tests/hooks/hooks-json-var-expansion.test.sh`.

## Release Risk Assessment

| Env var | Default | Effect |
|---|---|---|
| `DEVFORGE_RELEASE_RISK_DISABLED` | `0` | `1` → skip hook pr-release-gate + slash skill (kill switch) |
| `DEVFORGE_RELEASE_RISK_KG_TIMEOUT_SEC` | `5` | Timeout MCP sport-kg lookup (Criterion 5 critical service detection) |
| `DEVFORGE_RELEASE_RISK_SECURITY_CRITICAL_THRESHOLD` | `0` | Soglia Criterion 17 critical CVE count per trigger YES (>) |
| `DEVFORGE_RELEASE_RISK_SECURITY_HIGH_THRESHOLD` | `5` | Soglia Criterion 17 high CVE count per trigger YES (>) |

### Skip override file-based

```bash
# Disabilita hook pr-release-gate
touch ~/.claude/.devforge-skip-release-risk

# Riabilita
rm ~/.claude/.devforge-skip-release-risk
```

### Trigger automatico

Hook `pr-release-gate` (PostToolUse Bash, 30s timeout) si attiva su:
- `gh pr create --base main` AND
- branch corrente `release/**`

Posta scorecard come PR comment con idempotency marker `<!-- release-risk:<diff-hash> -->`.
