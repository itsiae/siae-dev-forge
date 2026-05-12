---
status: implemented
created: 2026-05-12
revised: 2026-05-12 (iter 2 — implementation manifest added, post live drift detection)
topic: review-evidence-hook
owner: lodetomasi
priority: high
sp_human: 22.0
sp_augmented: 8.7
---

# Design — Hook deterministico pre-review: `review-evidence`

## Implementation manifest (esaustivo, post-implementation)

Tutti i file prodotti dall'implementazione del piano `docs/plans/2026-05-12-review-evidence-hook/`. Questa sezione è autoritativa per il **spec-drift detector** (cfr. `lib/review_evidence/spec_drift.py`): file in questa lista NON sono unplanned.

### Componenti runtime (hook + lib)

- `hooks/review-evidence`
- `hooks/session-start`
- `lib/review_evidence/__init__.py`
- `lib/review_evidence/_sarif.py`
- `lib/review_evidence/atomic_io.py`
- `lib/review_evidence/ci_fetch.py`
- `lib/review_evidence/collector.py`
- `lib/review_evidence/collectors/__init__.py`
- `lib/review_evidence/collectors/_checkstyle.py`
- `lib/review_evidence/collectors/_jacoco.py`
- `lib/review_evidence/collectors/_lcov.py`
- `lib/review_evidence/collectors/_pmd.py`
- `lib/review_evidence/collectors/hcl.py`
- `lib/review_evidence/collectors/java.py`
- `lib/review_evidence/collectors/python.py`
- `lib/review_evidence/collectors/typescript.py`
- `lib/review_evidence/paths.py`
- `lib/review_evidence/registry.py`
- `lib/review_evidence/schema.py`
- `lib/review_evidence/spec_drift.py`
- `lib/review_evidence/thresholds.py`

### Renderer integration (agents)

- `agents/code-reviewer.md`
- `agents/spec-reviewer.md`

### Skill on-demand

- `commands/forge-evidence.md`

### Test suite

- `tests/conftest.py`
- `tests/review-evidence/__init__.py`
- `tests/review-evidence/test_no_regression.py`
- `tests/test_env_vars_doc_sync.py`
- `tests/test_forge_evidence_command.py`
- `tests/test_review_evidence_atomic_io.py`
- `tests/test_review_evidence_chaos.py`
- `tests/test_review_evidence_ci_fetch.py`
- `tests/test_review_evidence_collector_hcl.py`
- `tests/test_review_evidence_collector_java_coverage.py`
- `tests/test_review_evidence_collector_java_static.py`
- `tests/test_review_evidence_collector_python.py`
- `tests/test_review_evidence_collector_script.py`
- `tests/test_review_evidence_collector_typescript.py`
- `tests/test_review_evidence_e2e.py`
- `tests/test_review_evidence_followup.py`
- `tests/test_review_evidence_hook.py`
- `tests/test_review_evidence_orchestrator.py`
- `tests/test_review_evidence_renderer_contract.py`
- `tests/test_review_evidence_schema.py`
- `tests/test_review_evidence_spec_drift.py`
- `tests/test_review_evidence_thresholds.py`
- `tests/hooks/hooks-json-var-expansion.test.sh`

### Test fixture

- `tests/fixtures/review-evidence/.gitkeep`
- `tests/fixtures/review-evidence/checkstyle_result.xml`
- `tests/fixtures/review-evidence/codeql_sample.sarif`
- `tests/fixtures/review-evidence/coverage_python.json`
- `tests/fixtures/review-evidence/design_italian_headers.md`
- `tests/fixtures/review-evidence/design_with_codefences.md`
- `tests/fixtures/review-evidence/eslint_output.json`
- `tests/fixtures/review-evidence/evidence_clean.json`
- `tests/fixtures/review-evidence/evidence_full_block.json`
- `tests/fixtures/review-evidence/jacoco_gradle.xml`
- `tests/fixtures/review-evidence/jacoco_maven.xml`
- `tests/fixtures/review-evidence/jacoco_multimodule.xml`
- `tests/fixtures/review-evidence/lcov.info`
- `tests/fixtures/review-evidence/pmd_report.xml`
- `tests/fixtures/review-evidence/qodana_sample.sarif`
- `tests/fixtures/review-evidence/radon_cc.json`
- `tests/fixtures/review-evidence/ruff_output.json`
- `tests/fixtures/review-evidence/sonar_sample.sarif`
- `tests/fixtures/review-evidence/terraform_validate.json`
- `tests/fixtures/review-evidence/tflint_output.json`

### Planning artifacts (questo file e sotto-piano)

- `docs/plans/2026-05-12-review-evidence-hook-design.md`
- `docs/plans/2026-05-12-review-evidence-hook/overview.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-00-test-infra.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-01-schema.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-02-atomic-write-icloud.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-03-hook-bash-entry.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-04-orchestrator.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-05-python-collector.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-06-typescript-collector.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-07-java-coverage.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-08-java-static.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-09-hcl-collector.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-10-ci-fetch-sarif.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-11-spec-drift.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-12-renderer-agents.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-13-skill-command.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-14-e2e-test.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-15-docs.md`
- `docs/plans/2026-05-12-review-evidence-hook/task-16-edge-case-hardening.md`

### Root-level (non matchabili da PATH_RE, accettati implicit)

- `.gitignore`, `CHANGELOG.md`, `README.md`, `hooks/ENV_VARS.md`, `hooks/hooks.json` (modifiche additive, già parte del repo)

## Contesto

Gli agent di code review DevForge (`agents/code-reviewer.md`, `agents/spec-reviewer.md`) producono verdetti **non riproducibili**: ogni invocazione ricalcola coverage/lint/complessità soggettivamente, inferendo dai file letti. Conseguenza osservata in sessione: review che dichiarano "OK" passano poi al fail sui CI quality reports della pipeline di integrazione SIAE (qualunque sia lo strumento — Qodana, SonarQube, CodeQL, Semgrep — purché emetta SARIF).

Pain point in una frase: **review agent OK ⇒ CI quality reports rossi**, perché l'agent non ha mai eseguito i tool che gli stessi quality gate di CI eseguiranno.

## Obiettivo

Spostare i segnali oggettivi (coverage, lint, complessità ciclomatica, spec-drift, problemi rilevati dai CI quality reports) in un **hook deterministico** che li pre-calcola, scrive un **JSON cacheable per SHA** in `.claude/review-evidence/<sha>.json`, ed espone l'evidence agli agent review come **renderer** anziché come computer. Verdetto riproducibile, allineato a CI, e blocco hard configurabile su soglie critical.

**Nota su strumenti CI:** il design non assume alcun tool specifico. Il `ci_fetch` parser legge artefatti **SARIF** (formato standard adottato da Qodana, SonarQube, CodeQL, Semgrep e altri). Repo senza alcun CI quality report ricevono evidence basata solo su metriche locali — vedi sezione "CI report availability lifecycle".

## Decisioni chiave (intake utente, gate Step 3-4)

| Decisione | Scelta | Razionale |
|---|---|---|
| MVP scope | Multi-stack day-one (Java, TypeScript, Python, HCL) | Copre il portfolio SIAE — evita seconda PR per stack. W2 spec-review declinato dall'utente (preferenza completezza) |
| CI parity | Dual signal: local + CI-fetch via `gh run download` (SARIF generico) | Local risolve il pre-PR (CI non ha ancora girato); CI-fetch arricchisce su `gh pr edit` successivi con artefatti SARIF di qualsiasi tool |
| Trigger | Triplice: PreToolUse `gh pr create/edit` + PostToolUse Bash (commit) + Skill on-demand | Pre-PR per blocco, post-commit per cache warm, skill per controllo manuale |
| Blocking policy | Hard block su soglie critical, env-overridable, bypass via state file | Forza qualità senza essere irreversibile; bypass tramite state file (env var non sempre propagate, vedi feedback memory) |
| Soglie default | coverage 60%, delta -5pp, lint errors 0, complessità 15, CI SARIF critical block | Compromesso tra repo legacy e ambizione |
| Spec-drift match | File più recente in `docs/plans/`, override via `DEVFORGE_EVIDENCE_DESIGN_DOC` | Copre 80% casi senza overhead disciplina |
| CI report assente | Warning visibile in evidence (`ci_quality.available=false`), non blocca | Repo senza CI quality reports SARIF non vengono esclusi dall'hook |
| Convivenza | Coesiste con `pr-gate` (security) come hook separato | Single responsibility, rollback indipendente |

## Architettura

```
PreToolUse Bash (gh pr create/edit)  ─┐
PostToolUse Bash (commit detected)   ─┼──► hooks/review-evidence (bash, ~120 righe)
Skill /forge-evidence                 ─┘
                                            │
                                            ▼
                                hooks/review-evidence
                                  • detect trigger source
                                  • compute SHA + dirty flag
                                  • cache lookup
                                  • on miss → invoke collector.py
                                  • PreToolUse: enforce hard-block
                                  • emit additional_context
                                            │
                                            ▼ subprocess python3
                                lib/review_evidence/collector.py
                                  (orchestrator: stack detect,
                                   dispatch, merge, atomic_write)
                                            │
              ┌──────────────────┬──────────┴──────────┬──────────────────┐
              ▼                  ▼                     ▼                  ▼
       collectors/java.py  collectors/typescript.py  collectors/python.py  collectors/hcl.py
       (jacoco XML,        (vitest lcov,             (coverage.py JSON,   (tflint stdout,
        checkstyle,         eslint JSON,              ruff JSON, radon)    terraform validate)
        pmd)                complexity-report)
                                            │
                                            ▼
                                lib/review_evidence/ci_fetch.py
                                  • gh run list --commit <sha>
                                  • gh run download → Qodana SARIF
                                  • parse → schema common
                                  • async, timeout 30s
                                            │
                                            ▼
                                lib/review_evidence/spec_drift.py
                                  • cerca design doc
                                  • diff vs files_in_plan
                                  • drift_severity
                                            │
                                            ▼
                            .claude/review-evidence/<sha>.json
                                            │
                                            ▼
                         Renderer (agents/code-reviewer.md Step 0.5,
                                   agents/spec-reviewer.md Step 0.5)
```

## Componenti

### `hooks/review-evidence` (bash)

Entry point. Sceneggiatura:

1. Detect trigger via `DEVFORGE_CURRENT_HOOK` o argomento parser (PreToolUse, PostToolUse, Skill).
2. Compute `SHA=$(git rev-parse HEAD)`, `DIRTY=$(git status --porcelain)`.
3. Cache lookup: se `.claude/review-evidence/<sha>.json` esiste e tree clean → emit cached + exit.
4. Cache miss → `python3 lib/review_evidence/collector.py --sha "$SHA" --base "$BASE"`.
5. Solo su PreToolUse `gh pr create/edit`:
   - Carica `verdict.block` dall'evidence
   - Se `true` e nessun bypass: ritorna JSON con `decision: "block"` e `reason` umano-leggibile
6. Sempre: emit `additional_context` con riepilogo a 5 righe + path evidence.
7. Logging via `lib/logger.sh devforge_log "review_evidence" "success" "{...}"`.

Pattern coerente con `hooks/pr-gate` (riuso `devforge_sanitize_json_str`, `MERGE_BASE`, escape).

### `lib/review_evidence/collector.py` (Python, orchestrator)

- Detect stack via `lib/file-taxonomy.sh` (subprocess) + extension fallback.
- Per ogni stack rilevato, dispatch al collector corrispondente con timeout per-collector (default 10s).
- Merge risultati nello schema v1.
- Invoca `spec_drift.py` se trovato design doc.
- Invoca `ci_fetch.py` async (background thread, join con timeout 30s) — il risultato è additivo, non blocca lo schema.
- Atomic write via `lib/atomic_write.py` (già presente).
- Calcola `verdict` confrontando metriche con soglie env.

### `lib/review_evidence/schema.py` (Python, JSON schema v1)

Definisce dataclass + serializzazione. Versionato (`schema_version: "1.0"`). Validazione opzionale via jsonschema se installato, altrimenti dataclass-only.

Schema completo (cfr. sezione 5.2 del brainstorming, replicato qui):

```json
{
  "schema_version": "1.0",
  "sha": "abc123...",
  "branch": "feature/x",
  "computed_at": "2026-05-12T16:00:00Z",
  "dirty_tree": false,
  "base_branch": "main",
  "stack_detected": ["python", "typescript"],
  "metrics": {
    "coverage": {
      "overall_pct": 78.5,
      "delta_vs_base": -2.1,
      "per_file": [{"path": "src/foo.py", "pct": 65.0, "uncovered_lines": [12, 45, 67]}],
      "source": "local:coverage.py"
    },
    "lint": {
      "errors": 3,
      "warnings": 12,
      "findings": [{"file": "src/foo.py", "line": 23, "rule": "E501", "severity": "error", "msg": "line too long"}],
      "source": "local:ruff"
    },
    "complexity": {
      "max_cyclomatic": 18,
      "files_over_threshold": [{"path": "src/bar.py", "function": "process", "cyclomatic": 22, "threshold": 10}],
      "source": "local:radon"
    },
    "qodana": {
      "available": true,
      "ci_run_id": "9876543",
      "problems_critical": 2,
      "problems_high": 7,
      "findings": [],
      "source": "ci:qodana-sarif"
    }
  },
  "spec_drift": {
    "design_doc_path": "docs/plans/2026-05-12-foo-design.md",
    "files_in_plan": ["src/foo.py", "src/bar.py"],
    "files_changed": ["src/foo.py", "src/bar.py", "src/UNPLANNED.py"],
    "unplanned_files": ["src/UNPLANNED.py"],
    "drift_severity": "medium"
  },
  "verdict": {
    "block": false,
    "block_reasons": [],
    "warnings": ["coverage delta -2.1pp below threshold -2.0pp"]
  }
}
```

### `lib/review_evidence/collectors/`

Un file per stack. Interfaccia minimale:

```python
class Collector:
    name: str
    def is_applicable(self, repo_root: Path) -> bool: ...
    def collect(self, repo_root: Path, base_ref: str, head_ref: str) -> StackMetrics: ...
```

- `java.py`: prova `target/site/jacoco/jacoco.xml` (Maven) o `build/reports/jacoco/test/jacocoTestReport.xml` (Gradle); parsa checkstyle-result.xml, pmd.xml se presenti.
- `typescript.py`: prova `coverage/lcov.info`, esegue `npx eslint --format json` se config presente; complexity via `npx complexity-report` opzionale.
- `python.py`: prova `coverage.json` (`coverage json`), `ruff check --output-format json`, `radon cc -j src/`.
- `hcl.py`: `tflint --format json`, `terraform validate -json`. Coverage non applicabile.

Ogni collector ritorna `{"available": bool, "reason": str?, ...metriche}` — mai eccezione non gestita.

### `lib/review_evidence/ci_fetch.py`

Generico — non assume tool specifico. Pipeline:

1. `gh run list --commit <sha> --json databaseId,workflowName,conclusion --limit 10`
2. Filtra run completati (`conclusion in ["success","failure","neutral"]`).
3. Per ogni run completato: `gh run download <id> --dir <tmp>` (best-effort).
4. Scansiona tmp per file `*.sarif` (formato standard SARIF 2.1.0).
5. Parsa con jsonschema (opzionale) o dict access: estrai `runs[].tool.driver.name` (es. `Qodana`, `Sonar`, `CodeQL`), `runs[].results[].ruleId`, `level` (`error`/`warning`/`note`), `locations[].physicalLocation.artifactLocation.uri`.
6. Aggrega: `problems_critical` (`level==error`), `problems_high` (`level==warning`), per-tool breakdown.
7. Emette blocco `ci_quality` dello schema con `source: "ci:sarif:<tool_name>"`.

Timeout globale 30s. Errori → `{"available": false, "reason": "..."}`, mai abort.

**CI report availability lifecycle (W1 fix):**

Il vincolo realistico è che i CI quality reports girano **dopo** il push. Conseguenza per i 3 trigger:

| Trigger | SHA appena pushato | SHA con CI completato |
|---|---|---|
| `gh pr create` (primo) | `ci_quality.available=false`, reason: "no completed CI runs for this SHA". Block solo su metriche locali. | N/A (primo create per definizione) |
| `gh pr edit` (successivo) | Idem | `ci_quality.available=true`, blocca se findings sopra soglia |
| PostToolUse commit | Esegue sempre, popola cache. Se CI non ancora pronto: cache contiene solo locali. | Next post-commit invocation arricchisce cache con SARIF |
| Skill `/forge-evidence` | On-demand, idempotente | Idem |

**Pattern operativo per l'utente:** primo `gh pr create` apre PR su soli segnali locali; dopo che la CI finisce (~3-10 min), `gh pr edit --add-label ready-for-review` ri-attiva l'hook che fetcha gli artefatti SARIF e aggiorna l'evidence. Documentato in `commands/forge-evidence.md`.

### `lib/review_evidence/spec_drift.py`

1. Risolve design doc:
   - Se `DEVFORGE_EVIDENCE_DESIGN_DOC` env set → usa quello
   - Altrimenti: `ls -t docs/plans/*-design.md | head -1`
2. Parse markdown (W4 fix — robust contro code-fence/quote false positive):
   - **Strip code-fence:** rimuovi blocchi delimitati da ``` o ~~~ prima del path extraction
   - **Strip inline code:** rimuovi `` `...` `` (path in inline code = esempio, non claim)
   - **Strip blockquote:** rimuovi righe che iniziano con `>` 
   - **Section allowlist:** estrai solo da sezioni con header matching `(?i)^#+\s*(file|component|output|acceptance|test|deliverable|piano)` fino al prossimo header
   - **Regex finale:** `\b(src|lib|hooks|agents|commands|tests|skills|docs|scripts|tools)/[A-Za-z0-9_./-]+\.[a-z]+\b` (root dir whitelist, no false-positive su nomi generici)
3. `git diff --name-only --diff-filter=AMR <base>...HEAD -M` (rename-aware).
4. `unplanned_files = changed - in_plan`.
5. Severity:
   - `none`: empty unplanned
   - `low`: 1-2 file, stessa root dir di un file in plan
   - `medium`: 3-5 file OR nuova directory top-level
   - `high`: >5 file OR modulo intero non menzionato

Test fixture obbligatorio (`tests/fixtures/spec_drift/design_with_codefences.md`) che contiene path in code-fence, inline code, blockquote: il parser deve estrarli SOLO dalle sezioni allowlist.

## Hard-block: variabili e default

| Env var | Default | Significato |
|---|---|---|
| `DEVFORGE_EVIDENCE_MIN_COVERAGE` | `60` | Coverage % sotto cui block |
| `DEVFORGE_EVIDENCE_MAX_COVERAGE_DELTA` | `-5` | Delta vs base sotto cui block |
| `DEVFORGE_EVIDENCE_MAX_LINT_ERRORS` | `0` | Lint errors sopra cui block |
| `DEVFORGE_EVIDENCE_MAX_COMPLEXITY` | `15` | Cyclomatic max per funzione |
| `DEVFORGE_EVIDENCE_CI_SARIF_BLOCK_LEVEL` | `critical` | `critical`/`high`/`off` su findings SARIF da CI |
| `DEVFORGE_EVIDENCE_SPEC_DRIFT_BLOCK` | `1` | Block su drift `high` |
| `DEVFORGE_EVIDENCE_DESIGN_DOC` | (auto) | Override path design doc |
| `DEVFORGE_SKIP_EVIDENCE` | `0` | Bypass via env (env potrebbe non propagare a subprocess) |

**Bypass via state file (W8 fix):** il pattern env var solo non è affidabile per i subprocess hook (cfr. feedback_env_var_not_propagated_to_hooks). Il bypass primario usa un state file:

- Touch: `touch ~/.claude/.devforge-skip-evidence` (o `.claude/.devforge-skip-evidence` repo-local)
- L'hook controlla l'esistenza del file PRIMA del compute
- Auto-cleanup dopo N usi (counter nel file: `echo "N=3" > file`, decremento per ogni usage; `0` = remove file)
- Logging `evidence_bypass_used` ogni invocazione bypassata, `evidence_bypass_abuse_suspected` su soglia 5/day
- Env var `DEVFORGE_SKIP_EVIDENCE=1` resta come fallback secondario per CI/test, ma docs raccomandano state file per uso interattivo

Aggiornare `hooks/ENV_VARS.md` con questi.

## Cache strategy

- **Key:** `<sha>` da `git rev-parse HEAD`.
- **Dirty tree:** se `git status --porcelain` non vuoto → genera evidence "live" con `dirty_tree=true`, NON scrive cache. Agent vede flag e cita come limitazione.
- **Invalidazione:** SHA cambia (rebase, amend, new commit) → cache miss automatica.
- **TTL:** soft 7 giorni. Cleanup in `hooks/session-start` (`find .claude/review-evidence -mtime +7 -delete`).
- **Atomicità:** `lib/atomic_write.py`.

**iCloud safety (W7 fix):**

Il repo è in `~/Library/Mobile Documents/com~apple~CloudDocs/` (iCloud Drive). `feedback_icloud_repo_operational_tax` documenta che iCloud può rompere `rename` atomico sotto sync attivo (file `*-icloud` orfani, push HTTPS bloccati 15-25min).

Mitigazioni:
1. Hook detect iCloud cwd via path matching `Mobile Documents/com~apple~CloudDocs`; se rilevato e env `DEVFORGE_EVIDENCE_ICLOUD_WARN!=0`, emette warning visibile nel verdetto.
2. `.claude/review-evidence/` viene aggiunta a `.gitignore` (la directory è transitoria, evidence è derivabile dal SHA).
3. `atomic_write.py` resta primo livello di safety, ma se il rename fallisce per `EBUSY` (iCloud sync), retry 3× con backoff esponenziale; ultimate fallback: scrivi su `~/.claude/review-evidence-fallback/<repo-hash>/<sha>.json` (fuori da iCloud).
4. Quando possibile, considerare di spostare il repo su filesystem locale (raccomandazione operativa, non gate).

## Renderer integration (agent)

### `agents/code-reviewer.md` — nuovo Step 0.5

Inserito tra Step 0 (MCP tool loading) e "PRIMA DELLA REVIEW":

```markdown
## Step 0.5 — Load Pre-Computed Evidence

Prima di iniziare il 6-punti, leggi `.claude/review-evidence/<sha>.json`
se presente (dove `<sha>` è l'output di `git rev-parse HEAD`).

**Se evidence presente:**
- Usa i valori NUMERICI da evidence per coverage/lint/complexity (NON ricalcolare)
- Cita `source` per ogni claim (es. "ruff segnala 3 errors", "Qodana SARIF segnala 2 critical")
- Se `verdict.block=true`, parti dal verdetto: "Block triggered, reasons: ..."
- Se `dirty_tree=true`, annota: "Evidence calcolata su working tree dirty"

**Se evidence assente:**
- Annota nel verdetto: "evidence not pre-computed, falling back to subjective review"
- Procedi con review classica ma marca findings come "NON-DETERMINISTIC"
- Suggerisci all'utente di lanciare `/forge-evidence` prima di re-runnare review
```

### `agents/spec-reviewer.md` — sezione spec-drift pre-loaded

Analoga, focalizzata sulla sezione `spec_drift` dell'evidence.

## Trigger logic dettaglio

| Evento | Matcher | Comportamento |
|---|---|---|
| `PreToolUse` Bash | `gh pr (create\|edit)` | Sync compute se cache miss; **HARD BLOCK** se `verdict.block=true` AND `DEVFORGE_SKIP_EVIDENCE != 1` |
| `PostToolUse` Bash | commit detected (analogia `post-commit-review`) | Async compute (background), non-blocking. Aggiorna cache. |
| `Skill` | `siae-devforge:forge-evidence` | Sync compute on-demand. Stampa JSON human-readable + path file. |

Registrazione in `hooks/hooks.json`:
- PreToolUse Bash: aggiunto **dopo** `pr-gate` (security prima, quality dopo)
- PostToolUse Bash: aggiunto **dopo** `post-commit-review`
- Skill: nuovo command `commands/forge-evidence.md` che lancia bash hook

## Testing

| Test | File | Tipo | Acceptance criterion mappato |
|---|---|---|---|
| Schema v1 validation | `tests/test_review_evidence_schema.py` | Unit | AC #2 |
| Per-stack collector (Java) | `tests/test_review_evidence_collector_java.py` | Unit con fixture XML | AC #3 |
| Per-stack collector (TS) | `tests/test_review_evidence_collector_typescript.py` | Unit | AC #3 |
| Per-stack collector (Python) | `tests/test_review_evidence_collector_python.py` | Unit | AC #3 |
| Per-stack collector (HCL) | `tests/test_review_evidence_collector_hcl.py` | Unit | AC #3 |
| **CI-fetch SARIF parse + multi-tool** | `tests/test_review_evidence_ci_fetch.py` | Unit (mock `gh`, fixture SARIF Qodana+Sonar+CodeQL) | **AC #4** |
| Spec-drift detector (incl. code-fence robustness) | `tests/test_review_evidence_spec_drift.py` | Unit, fixture `design_with_codefences.md` | AC #5 |
| **Hard-block threshold matrix** | `tests/test_review_evidence_thresholds.py` | Unit (param: ogni env var * sopra/sotto soglia) | **AC #6** |
| **Bypass via state file** | `tests/test_review_evidence_bypass.py` | Unit + integration | AC #6 |
| Hook bash integration | `tests/test_review_evidence_hook.py` | Integration (subprocess) | AC #1 |
| **E2E renderer contract** | `tests/test_review_evidence_renderer_e2e.py` | E2E: simulate full pipeline hook→evidence→agent prompt rendering | **gap critico anti-dilution** |
| iCloud retry path | `tests/test_review_evidence_icloud_retry.py` | Unit (mock filesystem EBUSY) | R3 mitigation |
| ENV_VARS doc sync | `tests/test_env_vars_doc_sync.py` | Doc test (verifica che ogni env nuova sia in `hooks/ENV_VARS.md`) | AC #9 |

**E2E renderer test format (W5 fix):** anziché snapshot fragile, test contract-based:
1. Genera evidence sintetica con valori noti (es. coverage 55%, lint errors 5, qodana critical 2, drift high)
2. Render attraverso adapter Python che simula la lettura agent
3. Asserisci che l'output testuale contenga le 4 affermazioni atomiche: `"coverage_below_threshold"`, `"lint_errors=5"`, `"ci_critical=2"`, `"drift_severity=high"`
4. Asserisci che il verdetto agent inizi con "Block triggered:" e elenchi i block_reasons in ordine

Fixture: `tests/fixtures/review-evidence/{jacoco.xml, ruff.json, eslint.json, lcov.info, tflint.json, qodana.sarif, sonar.sarif, codeql.sarif, design_with_codefences.md, evidence_full_block.json, evidence_clean.json}`.

## Acceptance criteria

1. Hook `hooks/review-evidence` registrato in `hooks/hooks.json` su 3 trigger
2. Evidence JSON valido contro `schema.py` (versioned)
3. ≥1 collector per stack (Java, TypeScript, Python, HCL), ognuno emette `{"available": bool, "reason": str?, ...}`
4. CI-fetch SARIF generico funzionante (parser testato su Qodana, Sonar, CodeQL SARIF samples)
5. Spec-drift detector legge design doc da `docs/plans/` (auto + env override) + robusto contro code-fence/quote
6. Hard-block configurabile via env var con bypass primario via state file (`~/.claude/.devforge-skip-evidence`)
7. `code-reviewer.md` e `spec-reviewer.md` aggiornati con Step 0.5 evidence-loading
8. Test coverage ≥80% su `lib/review_evidence/`
9. `hooks/ENV_VARS.md` aggiornato con tutte le nuove env var
10. `CHANGELOG.md` entry sotto versione corrente
11. `commands/forge-evidence.md` registrato (skill on-demand)
12. Nessuna regressione su `pr-gate`, `post-commit-review`, `pr-blind-review-gate` (test suite verde)
13. `.gitignore` aggiornato con `.claude/review-evidence/`
14. E2E renderer test contract-based passa (asserisce che agent verdetto contenga affermazioni atomiche dell'evidence)
15. CI report availability lifecycle documentato in `commands/forge-evidence.md` (pattern primo create + edit re-trigger)

## Stima Storia Punti

Stime aggiornate post W6 (Java multi-tool sottostimato, CI-fetch SARIF multi-tool sottostimato):

| Componente | Umano | Augmented |
|---|---|---|
| Hook bash + dispatcher | 1.0 | 0.5 |
| Schema + atomic write + iCloud retry | 1.5 | 0.5 |
| Collector framework orchestrator | 2.0 | 1.0 |
| Java collector (Maven+Gradle+jacoco+checkstyle+pmd) | 3.5 | 1.0 |
| TypeScript collector (vitest+eslint+complexity) | 2.0 | 0.5 |
| Python collector (coverage+ruff+radon) | 1.0 | 0.5 |
| HCL collector (tflint+terraform validate) | 1.0 | 0.5 |
| CI-fetch + SARIF parse multi-tool (Qodana/Sonar/CodeQL) | 3.5 | 1.5 |
| Spec-drift detector + code-fence robustness | 1.5 | 0.5 |
| Renderer integration (2 agent) | 1.0 | 0.5 |
| Bypass via state file + abuse logging | 0.5 | 0.5 |
| Skill `/forge-evidence` + command | 0.5 | 0.5 |
| Test suite (12 file) | 2.5 | 1.0 |
| Docs (ENV_VARS, CHANGELOG, .gitignore, README) | 1.0 | 0.5 |
| **TOTALE** | **21.5** | **8.5** |

## Rischi

| ID | Descrizione | Mitigazione |
|---|---|---|
| R1 | Repo SIAE senza coverage configurato | Collector emette `{"available": false}`, agent non blocca su missing |
| R2 | Compute >15s timeout PreToolUse | Per-collector timeout 10s, CI-fetch sempre async, fast-path cache hit |
| R3 | Cache pollution su iCloudDocs (race, EBUSY) | `atomic_write` con retry 3× exp-backoff; fallback fuori iCloud (`~/.claude/review-evidence-fallback/<repo-hash>/`); `.gitignore` entry; warning se cwd iCloud |
| R4 | Spec-drift false positive su rename | `git log --follow` e `git diff -M` rename-aware |
| R5 | `gh` non installato in repo target | `ci_fetch.py` cattura FileNotFoundError, ritorna `{"available": false, "reason": "gh CLI missing"}` |
| R6 | Bypass abuse | State file primary + env fallback; abuse log `evidence_bypass_abuse_suspected` su 5/day (pattern esistente) |

## ADR riassuntivi

- **ADR-1** Hook bash thin wrapper, collector framework Python in `lib/review_evidence/`
- **ADR-2** Schema evidence v1 versioned, retro-compat policy
- **ADR-3** Trigger triplice: PreToolUse `gh pr` (block), PostToolUse Bash (async warm), Skill (on-demand)
- **ADR-4** Dual signal local + CI-fetch async, `source` field per claim
- **ADR-5** Hard block su soglie critical configurabili, bypass tracked
- **ADR-6** Cache key = SHA, dirty tree → no cache + flag
- **ADR-7** Renderer integration: `code-reviewer.md` + `spec-reviewer.md` con Step 0.5 evidence-loading

## Out of scope (Future Work)

- Integrazione SonarQube (analogo a Qodana, future ADR)
- SBOM/dependency-check (security ortogonale a quality)
- Skill `/forge-evidence-diff` per confrontare evidence tra due SHA (use case: PR review)
- Dashboard aggregata cross-repo (Control Tower-side, scope downstream)
- Multi-design-doc handling (oggi: solo il più recente)
