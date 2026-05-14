# Mutation Testing Adapters — Design Doc

**Data:** 2026-05-14 · **Status:** approved (utente conferma Approccio C)
**Stima:** 3 SP umano / 1 SP augmented · **Target release:** v1.58.0

## Goal

Chiudere il gap "test quality verification" nel toolchain DevForge integrando **mutation testing** come 18°-20° runner OSS. ThoughtWorks Radar Apr 2026 flagga PIT/mutmut/Stryker come "table stakes for AI-written suites" — critico perchè SIAE usa Claude Code (AI-written code).

Coverage % misura execution, mutation score misura verification. Test possono avere 95% coverage ma uccidere solo 30% dei mutanti = bug invisibili.

## Decisione architetturale (Approccio C)

**Standalone advisory, opt-in.**

- `MutationFindings` dataclass aggiunta a `lib/review_evidence/scoring.py` (additive Optional)
- `Evidence.mutation: Optional[MutationFindings]` campo additive (forward-compat v1/v2)
- Opt-in via env `DEVFORGE_MUTATION_ENABLED=1` (default `0`, slow tests evitano friction)
- Reviewer agent advisory: mutation_score < threshold (default 60%) → `REVIEWER_HANDOFF`, **mai BLOCK**
- Nessun ribilanciamento weights template (mutation NON è dimensione first-class)
- Pattern adapter identico Semgrep (auto-register, is_applicable, run → Optional)

## Componenti

### 1. Schema additive

`lib/review_evidence/scoring.py`:

```python
@dataclass
class MutationFindings:
    score_pct: float           # 0-100 — killed/total ratio
    killed: int = 0
    survived: int = 0
    timeout: int = 0
    no_coverage: int = 0
    total_mutants: int = 0
    tool: str = ""              # "pit" | "mutmut" | "stryker"
```

`lib/review_evidence/schema.py`:

```python
@dataclass
class Evidence:
    ...existing fields...
    mutation: Optional[MutationFindings] = None   # NEW, v1.57+, additive
```

### 2. Adapter — `lib/review_evidence/runners/pit.py`

Java mutation testing via PIT (`pitest.org`).

- `is_applicable`: `pom.xml` esiste E directory `target/pit-reports/` o file `pit-coverage.xml` (parse pre-existing report, no esegue tool slow live)
- `run`: parse XML report → MutationFindings
- Env override: `DEVFORGE_PIT_REPORT_PATH` (default `target/pit-reports/index.html` o `mutations.xml`)

### 3. Adapter — `lib/review_evidence/runners/mutmut.py`

Python mutation testing via mutmut (`mutmut`).

- `is_applicable`: `pyproject.toml` o `setup.py` esiste E `.mutmut-cache` directory esiste
- `run`: invoca `mutmut results --json` (fast, legge cache), parse → MutationFindings
- Env override: `DEVFORGE_MUTMUT_CACHE_PATH`

### 4. Adapter — `lib/review_evidence/runners/stryker.py`

JS/TS mutation testing via Stryker (`stryker-mutator.io`).

- `is_applicable`: `package.json` esiste E `reports/mutation/mutation.json` esiste (Stryker default output)
- `run`: parse JSON report → MutationFindings
- Env override: `DEVFORGE_STRYKER_REPORT_PATH` (default `reports/mutation/mutation.json`)

### 5. Integration collector

`lib/review_evidence/collector.py`:
- In `orchestrate_v2`, dopo runner registry sweep, raccoglie mutation findings via `[r for r in registry if r.category == "mutation"]` e popola `Evidence.mutation` (priorità: tool che ritorna primo result non-None)
- Se `DEVFORGE_MUTATION_ENABLED != "1"` → skip mutation runner entirely (no overhead)

### 6. Reviewer agent advisory

`agents/code-reviewer.md` Step 0.6 — aggiunge guidance:

```
If Evidence.mutation.score_pct < DEVFORGE_MUTATION_THRESHOLD (default 60):
  decision = REVIEWER_HANDOFF (advisory)
  reason = "mutation_score:X<Y"
  Reviewer judges qualitatively. NEVER BLOCK on mutation alone.
```

### 7. Env vars

`hooks/ENV_VARS.md` nuova sub-sezione "Mutation Testing (v1.58+)":

| Env var | Default | Note |
|---|---|---|
| `DEVFORGE_MUTATION_ENABLED` | `0` | Master switch. Opt-in (slow tests). |
| `DEVFORGE_MUTATION_THRESHOLD` | `60` | mutation_score < threshold → REVIEWER_HANDOFF |
| `DEVFORGE_PIT_REPORT_PATH` | `target/pit-reports/mutations.xml` | Override Java PIT report path |
| `DEVFORGE_MUTMUT_CACHE_PATH` | `.mutmut-cache` | Override Python mutmut cache |
| `DEVFORGE_STRYKER_REPORT_PATH` | `reports/mutation/mutation.json` | Override JS/TS Stryker report |

### 8. Setup script update

`scripts/devforge-install-runners.sh` — add tools al `--stack java|python|cross` se opt-in:

- macOS: `brew install pitest` (Java), `pip3 install mutmut` (Python), `npm i -g stryker-cli @stryker-mutator/core` (JS/TS)
- Linux: idem (`brew` skip, usa apt/pip/npm fallback)
- Gate: install solo se flag `--with-mutation-testing` passato (default OFF, slow tools)

## Acceptance criteria

- [ ] `MutationFindings` dataclass + `Evidence.mutation: Optional` additive (v1/v2 forward-compat)
- [ ] 3 adapter (pit/mutmut/stryker) auto-register via pattern Semgrep
- [ ] Tutti gli adapter ritornano `None` quando `DEVFORGE_MUTATION_ENABLED != "1"` (opt-in guard)
- [ ] Tutti gli adapter ritornano `None` quando report file mancante (no esecuzione live)
- [ ] Collector popola `Evidence.mutation` con primo non-None match
- [ ] Reviewer agent advisory wired (Step 0.6 update) — `REVIEWER_HANDOFF`, mai BLOCK
- [ ] 5 nuove env var documentate in `ENV_VARS.md` + V2_EXPECTED_VARS update
- [ ] Setup script `--with-mutation-testing` flag installa pit/mutmut/stryker
- [ ] Test coverage: 4 adapter file (pit + mutmut + stryker + schema additive) × ~15 test = 60+ test
- [ ] No-regression: 332/334 pre-existing baseline (2 flaky e2e_v2 documented)
- [ ] `DEVFORGE_MUTATION_*` env consumed grep verified

## Edge case (8 identificati, tutti COVERED)

| ID | Edge case | Mitigazione |
|---|---|---|
| E1 | Mutation tool installed ma report missing | adapter `is_applicable=False` (no report) → None |
| E2 | Report file corrupted (XML/JSON parse fail) | `try/except (ParseError, JSONDecodeError)` → None |
| E3 | Mutation enabled ma project non Java/Py/JS | nessun adapter `is_applicable` → Evidence.mutation=None |
| E4 | Mutation enabled, opt-in, ma threshold env invalid (non-int) | parse `int(env, base=10)` con default fallback su ValueError |
| E5 | Multiple report file presenti (es. monorepo Java+Py+JS) | collector usa PRIMO non-None per evitare ambiguità — log warning multi-stack |
| E6 | Threshold = 100 (impossibile) | accept ma sarà sempre `REVIEWER_HANDOFF`, semantica corretta |
| E7 | Stryker report con `mutationScore` = NaN | `if math.isnan(score)`: return None |
| E8 | PIT report XML schema variations (PIT v1.x vs v2.x) | parser tolerante: cerca tag standard, fallback su altre forme attese |

## Out of scope (backlog)

- Differential mutation testing (PR diff only vs full repo) — backlog
- Mutation regression budget (baseline cache S3 integration) — backlog
- Custom mutation operators SIAE — backlog
- Auto-fix loop integration (mutation findings → siae-fix-evidence) — backlog (richiede subagent TDD)
- Mutation in `forge-score` skill output — backlog
- Real-time mutation run (esegue tool, non solo parse report) — backlog

## Implementation manifest

**Creare:**
- `lib/review_evidence/runners/pit.py`
- `lib/review_evidence/runners/mutmut.py`
- `lib/review_evidence/runners/stryker.py`
- `tests/test_review_evidence_runner_pit.py`
- `tests/test_review_evidence_runner_mutmut.py`
- `tests/test_review_evidence_runner_stryker.py`
- `tests/test_review_evidence_schema_mutation.py` (test additive forward-compat)

**Modificare:**
- `lib/review_evidence/scoring.py` (add `MutationFindings` dataclass)
- `lib/review_evidence/schema.py` (add `Evidence.mutation: Optional`)
- `lib/review_evidence/runners/__init__.py` (add 3 imports)
- `lib/review_evidence/collector.py` (populate `Evidence.mutation` post-runner-sweep)
- `agents/code-reviewer.md` (Step 0.6 advisory mutation_score)
- `hooks/ENV_VARS.md` (nuova sub-sezione Mutation Testing v1.58+)
- `tests/test_env_vars_doc_sync_v2.py` (5 nuove env var in V2_EXPECTED_VARS)
- `scripts/devforge-install-runners.sh` (`--with-mutation-testing` flag)
- `CHANGELOG.md` (v1.58.0 entry — added post-PR-merge)

## Stack template impact

Nessuna modifica ai 5 template `docs/templates/.devforge-scores-*.yml`. Mutation è advisory, non altera weights/floors.

## Test plan

- [x] Adapter pattern (3 file): registry + is_applicable + run with mock subprocess.run + 5 error path + env override
- [x] Schema additive: deserialize v1 evidence senza `mutation` field → ok, default None
- [x] Schema additive: serialize v2 con `Evidence.mutation = MutationFindings(...)` → roundtrip
- [x] Opt-in guard: `DEVFORGE_MUTATION_ENABLED=0` → tutti gli adapter ritornano None senza tentare parse
- [x] Threshold parse: invalid int → fallback default 60
- [x] No-regression: full pytest suite + ENV_VARS doc-sync
